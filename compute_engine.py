"""Desktop compute acceleration for CalcOsPower.

The production RO solver remains the reference implementation in calculations.py.
This module adds two acceleration layers without changing the engineering equations:

1) Process-based multicore execution for independent cases/technologies.
2) Optional cross-vendor OpenCL kernels for large vector/batch engineering math.

The OpenCL path is deliberately opt-in/automatic by workload size. The coupled
membrane/pyEQL inverse solver is branch-heavy and element-sequential, so it stays
on CPU; independent full calculations are distributed across CPU processes.
"""
from __future__ import annotations

import atexit
import math
import multiprocessing as mp
import os
import platform
import subprocess
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from functools import lru_cache
from itertools import count
from typing import Any, Iterable

# Hosted AWS deployments intentionally use CPU-only engineering paths.  Keep
# scientific libraries from starting their own large thread pools inside each
# Total RO Design worker process.  Administrators may still override these
# variables explicitly for a workstation build.
for _thread_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_thread_var, "1")

COMPUTE_MODE = str(os.environ.get("TOTALRO_COMPUTE_MODE", "auto") or "auto").strip().lower()
CPU_ONLY_MODE = COMPUTE_MODE in {"cpu", "cpu-only", "hosted-cpu"}

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy is normally brought by pyEQL
    np = None


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except Exception:
        return default


LOGICAL_CPUS = max(1, os.cpu_count() or 1)
# During the hosted Alpha only one heavy calculation is admitted at a time, so
# that calculation may use all logical CPUs for genuinely independent work.
# Workstation/portable builds retain the conservative one-CPU reserve.
USABLE_CPU_WORKERS = LOGICAL_CPUS if CPU_ONLY_MODE else max(1, LOGICAL_CPUS - 1 if LOGICAL_CPUS > 1 else 1)

def _worker_limit_from_env() -> int:
    raw = str(os.environ.get("TOTALRO_MAX_ENGINEERING_WORKERS",
                             os.environ.get("CALCOSPOWER_MAX_WORKERS", "auto")) or "auto").strip().lower()
    if raw in {"", "auto", "all", "available"}:
        return USABLE_CPU_WORKERS if CPU_ONLY_MODE else min(16, USABLE_CPU_WORKERS)
    try:
        return max(1, min(USABLE_CPU_WORKERS, int(raw)))
    except Exception:
        return USABLE_CPU_WORKERS if CPU_ONLY_MODE else min(16, USABLE_CPU_WORKERS)

DEFAULT_CPU_WORKERS = _worker_limit_from_env()
MIN_SINGLE_CPU_WORKERS = max(1, min(USABLE_CPU_WORKERS, int(math.ceil(LOGICAL_CPUS / 2.0))))
# Conservative built-in GPU threshold. On supported hardware this is replaced
# at runtime by a measured CPU/OpenCL break-even threshold.
GPU_VECTOR_THRESHOLD = _int_env("CALCOSPOWER_GPU_THRESHOLD", 4096)
_gpu_calibration: dict[str, Any] | None = None

def select_worker_count(job_count: int, requested: int | None = None, *, enforce_quarter_floor: bool = True) -> int:
    """Central CalcOsPower CPU-worker policy.

    The legacy argument name is retained for compatibility, but the floor is now
    50% of available logical CPUs whenever at least that many genuinely independent
    jobs exist. We never manufacture dummy work just to raise CPU utilization.
    One logical processor is reserved for Windows/UI where possible.
    """
    jobs = max(0, int(job_count or 0))
    if jobs <= 0:
        return 0
    if os.environ.get("CALCOSPOWER_TEST_SERIAL", "0") == "1":
        return 1
    req = int(requested or DEFAULT_CPU_WORKERS)
    target = min(max(1, req), USABLE_CPU_WORKERS)
    if enforce_quarter_floor and jobs >= MIN_SINGLE_CPU_WORKERS:
        target = max(target, MIN_SINGLE_CPU_WORKERS)
    return max(1, min(target, jobs, USABLE_CPU_WORKERS))


# ---- Live compute diagnostics ---------------------------------------------------------
# The monitor reports CalcOsPower scheduling state, not merely theoretical capability.
# It is intentionally kept in the main Flask process; worker processes receive their
# engineering task payloads but do not need to share UI state.
_monitor_lock = threading.RLock()
_run_counter = count(1)
_compute_state: dict[str, Any] = {
    "active": False,
    "run_id": None,
    "kind": "idle",
    "backend": "cpu",
    "workers": 0,
    "active_workers": 0,
    "total_jobs": 0,
    "completed_jobs": 0,
    "failed_jobs": 0,
    "progress_total": 0,
    "progress_completed": 0,
    "progress_explicit": False,
    "phase": "idle",
    "cancel_requested": False,
    "cancelled": False,
    "started_at": None,
    "finished_at": None,
    "duration_seconds": 0.0,
    "fallback": False,
    "fallback_reason": "",
}
_cpu_sample = {"wall": None, "cpu": None}
_cancel_event = threading.Event()
_PENDING_CANCEL_TTL_SECONDS = 5.0
_pending_cancel: dict[str, Any] | None = None
_duration_history: dict[str, list[float]] = {}


class CalculationCancelled(RuntimeError):
    """Raised when the user explicitly stops the active calculation."""


def cancellation_requested() -> bool:
    return _cancel_event.is_set()


def raise_if_cancelled() -> None:
    if _cancel_event.is_set():
        raise CalculationCancelled("Calculation cancelled by user.")


def set_compute_progress(*, total: int | None = None, completed: int | None = None,
                         phase: str | None = None) -> None:
    """Publish high-level work-unit progress used for ETA calculation.

    Pressure-search worker counters remain available separately as completed_jobs /
    total_jobs.  Auto Design uses these work units for a stable, user-facing ETA.
    """
    with _monitor_lock:
        _compute_state["progress_explicit"] = True
        if total is not None:
            _compute_state["progress_total"] = max(0, int(total))
        if completed is not None:
            cap = int(_compute_state.get("progress_total", 0))
            value = max(0, int(completed))
            _compute_state["progress_completed"] = min(value, cap) if cap > 0 else value
        if phase is not None:
            _compute_state["phase"] = str(phase)


def advance_compute_progress(delta: int = 1, *, phase: str | None = None,
                             extend_total: int = 0) -> None:
    with _monitor_lock:
        if extend_total:
            _compute_state["progress_total"] = max(0, int(_compute_state.get("progress_total", 0)) + int(extend_total))
        total = int(_compute_state.get("progress_total", 0))
        completed = max(0, int(_compute_state.get("progress_completed", 0)) + max(0, int(delta)))
        _compute_state["progress_completed"] = min(completed, total) if total > 0 else completed
        if phase is not None:
            _compute_state["phase"] = str(phase)


def begin_compute_run(kind: str, total_jobs: int = 1, workers: int = 1,
                      backend: str = "cpu", *, owner: str | None = None) -> int:
    global _pending_cancel
    now = time.time()
    total_jobs = max(1, int(total_jobs or 1))
    workers = max(1, int(workers or 1))
    with _monitor_lock:
        pending_cancel = _pending_cancel
        consume_pending_cancel = bool(
            pending_cancel is not None
            and pending_cancel.get("owner") == owner
            and now - float(pending_cancel.get("requested_at", 0.0)) <= _PENDING_CANCEL_TTL_SECONDS
        )
        _pending_cancel = None
        if consume_pending_cancel:
            _cancel_event.set()
        else:
            _cancel_event.clear()
        run_id = next(_run_counter)
        _compute_state.update({
            "active": True,
            "run_id": run_id,
            "kind": str(kind or "calculation"),
            "backend": str(backend or "cpu"),
            "workers": workers,
            "active_workers": min(workers, total_jobs),
            "total_jobs": total_jobs,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "progress_total": total_jobs,
            "progress_completed": 0,
            "progress_explicit": False,
            "phase": str(kind or "calculation"),
            "cancel_requested": consume_pending_cancel,
            "cancelled": False,
            "started_at": now,
            "finished_at": None,
            "duration_seconds": 0.0,
            "fallback": False,
            "fallback_reason": "",
        })
    return run_id


def update_compute_run(*, completed_delta: int = 0, failed_delta: int = 0,
                       backend: str | None = None, workers: int | None = None) -> None:
    with _monitor_lock:
        if backend:
            _compute_state["backend"] = backend
        if workers is not None:
            _compute_state["workers"] = max(1, int(workers))
        _compute_state["completed_jobs"] = min(
            int(_compute_state.get("total_jobs", 0)),
            int(_compute_state.get("completed_jobs", 0)) + max(0, int(completed_delta)),
        )
        _compute_state["failed_jobs"] = int(_compute_state.get("failed_jobs", 0)) + max(0, int(failed_delta))
        # For calculations that do not publish explicit work-unit progress, mirror
        # the job counters so the overlay can still show a useful ETA.
        if not bool(_compute_state.get("progress_explicit")):
            _compute_state["progress_completed"] = min(
                int(_compute_state.get("progress_total", 0)),
                int(_compute_state.get("progress_completed", 0)) + max(0, int(completed_delta)),
            )
        remaining = max(0, int(_compute_state.get("total_jobs", 0)) - int(_compute_state.get("completed_jobs", 0)))
        _compute_state["active_workers"] = min(int(_compute_state.get("workers", 1)), remaining) if _compute_state.get("active") else 0


def finish_compute_run(*, fallback: bool = False, fallback_reason: str = "",
                       cancelled: bool = False) -> dict[str, Any]:
    now = time.time()
    with _monitor_lock:
        started = _compute_state.get("started_at") or now
        duration = max(0.0, now - float(started))
        kind = str(_compute_state.get("kind") or "calculation")
        was_cancelled = bool(cancelled or _compute_state.get("cancel_requested"))
        _compute_state.update({
            "active": False,
            "active_workers": 0,
            "finished_at": now,
            "duration_seconds": duration,
            "cancelled": was_cancelled,
            "phase": "cancelled" if was_cancelled else "complete",
            "fallback": bool(fallback),
            "fallback_reason": str(fallback_reason or ""),
        })
        if not was_cancelled and duration > 0.05:
            hist = _duration_history.setdefault(kind, [])
            hist.append(duration)
            del hist[:-5]
        return dict(_compute_state)


def _calcospower_cpu_sample() -> tuple[float | None, int | None]:
    """Return CalcOsPower process-tree CPU as percent of the whole machine.

    This is sampled from accumulated process CPU time, so 12.5% on an 8-thread
    machine is roughly one logical processor fully occupied. psutil is optional;
    the scheduling counters remain available if it is absent.
    """
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        processes = [proc] + proc.children(recursive=True)
        cpu_seconds = 0.0
        alive_children = 0
        for item in processes:
            try:
                times = item.cpu_times()
                cpu_seconds += float(times.user) + float(times.system)
                if item.pid != proc.pid:
                    alive_children += 1
            except Exception:
                continue
        now = time.perf_counter()
        with _monitor_lock:
            prev_wall, prev_cpu = _cpu_sample["wall"], _cpu_sample["cpu"]
            _cpu_sample["wall"], _cpu_sample["cpu"] = now, cpu_seconds
        if prev_wall is None or prev_cpu is None or now <= prev_wall:
            return None, alive_children
        pct = 100.0 * max(0.0, cpu_seconds - prev_cpu) / ((now - prev_wall) * LOGICAL_CPUS)
        return min(100.0, pct), alive_children
    except Exception:
        return None, None


def compute_status() -> dict[str, Any]:
    cpu_pct, children = _calcospower_cpu_sample()
    now = time.time()
    with _monitor_lock:
        out = dict(_compute_state)
    if out.get("active") and out.get("started_at"):
        out["duration_seconds"] = max(0.0, now - float(out["started_at"]))
    elapsed = float(out.get("duration_seconds") or 0.0)
    ptotal = int(out.get("progress_total") or 0)
    pdone = int(out.get("progress_completed") or 0)
    if ptotal <= 0:
        ptotal = int(out.get("total_jobs") or 0)
        pdone = int(out.get("completed_jobs") or 0)
    fraction = (min(1.0, max(0.0, pdone / ptotal)) if ptotal > 0 else 0.0)
    out["progress_fraction"] = fraction
    eta = None
    estimated_total = None
    if out.get("active"):
        if fraction > 0.0 and elapsed > 0.0:
            estimated_total = elapsed / max(fraction, 1e-9)
        else:
            hist = _duration_history.get(str(out.get("kind") or "calculation"), [])
            if hist:
                estimated_total = sum(hist) / len(hist)
        if estimated_total is not None:
            eta = max(0.0, estimated_total - elapsed)
    out["estimated_total_seconds"] = estimated_total
    out["eta_seconds"] = eta
    out["calcospower_cpu_percent"] = cpu_pct
    out["worker_processes_detected"] = children
    out["logical_processors"] = LOGICAL_CPUS
    return out


@dataclass
class OpenCLDeviceInfo:
    platform: str
    vendor: str
    name: str
    version: str
    type: str
    global_memory_mb: float
    compute_units: int
    fp64: bool


def _opencl_device_type_name(cl, dtype: int) -> str:
    if dtype & cl.device_type.GPU:
        return "GPU"
    if dtype & cl.device_type.ACCELERATOR:
        return "Accelerator"
    if dtype & cl.device_type.CPU:
        return "CPU"
    return "Other"


@lru_cache(maxsize=1)
def _windows_graphics_adapters() -> list[str]:
    """Best-effort Windows display-adapter inventory for clearer diagnostics."""
    if platform.system().lower() != "windows":
        return []
    try:
        flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        cmd = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4, creationflags=flags)
        if r.returncode != 0:
            return []
        return [line.strip() for line in r.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def detect_opencl_devices() -> tuple[list[OpenCLDeviceInfo], str]:
    """Return usable OpenCL devices without making OpenCL a hard dependency."""
    if CPU_ONLY_MODE:
        return [], "OpenCL probing is disabled by TOTALRO_COMPUTE_MODE=cpu."
    try:
        import pyopencl as cl
    except Exception as exc:
        return [], f"PyOpenCL not installed in this build: {exc}"
    devices: list[OpenCLDeviceInfo] = []
    try:
        for p in cl.get_platforms():
            for d in p.get_devices():
                dtype = _opencl_device_type_name(cl, int(d.type))
                if dtype not in {"GPU", "Accelerator"}:
                    continue
                extensions = set(str(getattr(d, "extensions", "")).split())
                devices.append(OpenCLDeviceInfo(
                    platform=str(getattr(p, "name", "OpenCL")),
                    vendor=str(getattr(d, "vendor", "")),
                    name=str(getattr(d, "name", "OpenCL device")).strip(),
                    version=str(getattr(d, "version", "")),
                    type=dtype,
                    global_memory_mb=float(getattr(d, "global_mem_size", 0)) / (1024.0 * 1024.0),
                    compute_units=int(getattr(d, "max_compute_units", 0)),
                    fp64=("cl_khr_fp64" in extensions or "cl_amd_fp64" in extensions),
                ))
        return devices, "" if devices else "No GPU/accelerator OpenCL device reported by the installed drivers."
    except Exception as exc:
        return [], f"OpenCL runtime unavailable: {exc}"


def hardware_info() -> dict[str, Any]:
    devices, error = detect_opencl_devices()
    pyopencl_installed = False
    pyopencl_version = ""
    platforms: list[str] = []
    if not CPU_ONLY_MODE:
        try:
            import pyopencl as cl
            pyopencl_installed = True
            pyopencl_version = str(getattr(cl, "VERSION_TEXT", getattr(cl, "__version__", "installed")))
            try:
                platforms = [str(p.name).strip() for p in cl.get_platforms()]
            except Exception:
                platforms = []
        except Exception:
            pass
    adapters = _windows_graphics_adapters()
    return {
        "cpu": {
            "logical_processors": LOGICAL_CPUS,
            "default_workers": DEFAULT_CPU_WORKERS,
            "usable_workers": USABLE_CPU_WORKERS,
            "minimum_parallel_job_workers": MIN_SINGLE_CPU_WORKERS,
            "architecture": platform.machine(),
            "processor": platform.processor() or "CPU",
        },
        "graphics_adapters": adapters,
        "opencl": {
            "available": bool(devices),
            "pyopencl_installed": pyopencl_installed,
            "pyopencl_version": pyopencl_version,
            "platforms": platforms,
            "devices": [asdict(x) for x in devices],
            "message": error,
            "vector_threshold": gpu_break_even_threshold(),
            "calibration": dict(_gpu_calibration or {}),
        },
        "compute_mode": COMPUTE_MODE,
        "policy": {
            "full_ro_solver": "multicore CPU for genuinely independent cases and pressure candidates",
            "cpu_floor": "all configured hosted CPUs are available to the single admitted heavy job; no dummy work is created",
            "gpu": ("disabled for the authenticated AWS CPU deployment" if CPU_ONLY_MODE else
                    "optional OpenCL vector screening; final engineering validation remains CPU-authoritative"),
            "fallback": "CPU is always available and remains the numerical reference",
        },
    }


# ---- Full calculation multicore path -------------------------------------------------

def _calculation_worker(task: dict[str, Any]) -> dict[str, Any]:
    """Top-level picklable worker for ProcessPoolExecutor/PyInstaller."""
    from calculations import CALCS

    task_id = task.get("id")
    mode = str(task.get("mode", ""))
    data = dict(task.get("data") or {})
    # A multi-case worker is already parallelized at the case level. Prevent
    # nested CPU process pools, but do NOT disable GPU vector work. GPU and CPU
    # nesting are independent policies.
    data["_disable_nested_cpu_pool"] = True
    data["_inside_batch_worker"] = True
    if mode not in CALCS:
        return {"id": task_id, "mode": mode, "ok": False, "error": "Unknown calculation mode."}
    try:
        result = CALCS[mode](data)
        # Diagnostic metadata only; it does not alter engineering fields.
        result["compute_backend"] = "cpu-worker"
        return {"id": task_id, "mode": mode, "ok": True, "result": result}
    except Exception as exc:
        return {"id": task_id, "mode": mode, "ok": False, "error": str(exc)}


_pool_lock = threading.Lock()
_pool: ProcessPoolExecutor | None = None
_pool_workers: int | None = None


def _get_pool(workers: int) -> ProcessPoolExecutor:
    global _pool, _pool_workers
    workers = max(1, int(workers))
    with _pool_lock:
        if _pool is None or _pool_workers != workers:
            if _pool is not None:
                _pool.shutdown(wait=False, cancel_futures=True)
            # spawn matches Windows behavior and is compatible with frozen apps
            _pool = ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"))
            _pool_workers = workers
        return _pool


def shutdown_pool() -> None:
    global _pool, _pool_workers
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        _pool = None
        _pool_workers = None


atexit.register(shutdown_pool)

def _terminate_active_pool() -> None:
    """Terminate current spawned calculation workers so Stop is responsive.

    ProcessPoolExecutor has no public hard-cancel API for already-running work.
    We terminate only the processes owned by Total RO Design's private executor,
    discard that executor, and recreate it automatically on the next calculation.
    """
    global _pool, _pool_workers
    pool = None
    processes = []
    with _pool_lock:
        pool = _pool
        if pool is not None:
            try:
                processes = list((getattr(pool, "_processes", {}) or {}).values())
            except Exception:
                processes = []
            _pool = None
            _pool_workers = None
    for proc in processes:
        try:
            if proc is not None and proc.is_alive():
                proc.terminate()
        except Exception:
            pass
    for proc in processes:
        try:
            proc.join(timeout=0.25)
        except Exception:
            pass
    if pool is not None:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


def request_compute_cancel(run_id: int | None = None, *, hard: bool = True,
                           owner: str | None = None,
                           allow_pending: bool = True) -> dict[str, Any]:
    global _pending_cancel
    with _monitor_lock:
        active = bool(_compute_state.get("active"))
        current_id = _compute_state.get("run_id")
        if run_id is not None and current_id is not None and int(run_id) != int(current_id):
            return {"ok": False, "active": active, "run_id": current_id, "reason": "run_id_mismatch"}
        if not active:
            if not allow_pending:
                return {"ok": True, "active": False, "run_id": current_id, "already_finished": True}
            _pending_cancel = {"owner": owner, "requested_at": time.time()}
            return {"ok": True, "active": False, "run_id": current_id, "pending_cancel": True}
        _compute_state["cancel_requested"] = True
        _compute_state["phase"] = "Cancelling calculation"
    _cancel_event.set()
    if hard:
        _terminate_active_pool()
    return {"ok": True, "active": True, "run_id": current_id, "cancel_requested": True}



def calculate_batch(tasks: Iterable[dict[str, Any]], workers: int | None = None) -> dict[str, Any]:
    """Calculate independent full RO/ERD tasks concurrently with live diagnostics."""
    task_list = list(tasks)
    if not task_list:
        return {"results": [], "backend": "cpu", "workers": 0, "fallback": False,
                "jobs_total": 0, "jobs_completed": 0, "elapsed_seconds": 0.0}

    n_workers = select_worker_count(len(task_list), workers, enforce_quarter_floor=True)
    run_id = begin_compute_run("batch", len(task_list), n_workers,
                               "cpu-multiprocess" if n_workers > 1 else "cpu-sequential")
    started = time.perf_counter()

    if len(task_list) == 1 or n_workers == 1:
        results = []
        for t in task_list:
            raise_if_cancelled()
            item = _calculation_worker(t)
            results.append(item)
            update_compute_run(completed_delta=1, failed_delta=0 if item.get("ok") else 1)
        final = finish_compute_run()
        return {"results": results, "backend": "cpu-sequential", "workers": 1,
                "fallback": False, "run_id": run_id, "jobs_total": len(task_list),
                "jobs_completed": len(results), "elapsed_seconds": time.perf_counter() - started,
                "monitor": final}

    try:
        pool = _get_pool(n_workers)
        futures = {pool.submit(_calculation_worker, t): i for i, t in enumerate(task_list)}
        ordered: list[dict[str, Any] | None] = [None] * len(task_list)
        update_compute_run(backend="cpu-multiprocess", workers=n_workers)
        for fut in as_completed(futures):
            raise_if_cancelled()
            idx = futures[fut]
            try:
                ordered[idx] = fut.result()
            except Exception as exc:
                t = task_list[idx]
                ordered[idx] = {"id": t.get("id"), "mode": t.get("mode"), "ok": False, "error": str(exc)}
            item = ordered[idx] or {}
            update_compute_run(completed_delta=1, failed_delta=0 if item.get("ok") else 1)
        final = finish_compute_run()
        return {"results": ordered, "backend": "cpu-multiprocess", "workers": n_workers,
                "fallback": False, "run_id": run_id, "jobs_total": len(task_list),
                "jobs_completed": len(task_list), "elapsed_seconds": time.perf_counter() - started,
                "monitor": final}
    except Exception as exc:
        if cancellation_requested():
            finish_compute_run(cancelled=True, fallback_reason="Calculation cancelled by user.")
            raise CalculationCancelled("Calculation cancelled by user.")
        # If process creation fails, preserve correctness with the reference solver.
        update_compute_run(backend="cpu-sequential", workers=1)
        results = []
        for t in task_list:
            raise_if_cancelled()
            item = _calculation_worker(t)
            results.append(item)
            update_compute_run(completed_delta=1, failed_delta=0 if item.get("ok") else 1)
        final = finish_compute_run(fallback=True, fallback_reason=str(exc))
        return {"results": results, "backend": "cpu-sequential", "workers": 1,
                "fallback": True, "fallback_reason": str(exc), "run_id": run_id,
                "jobs_total": len(task_list), "jobs_completed": len(results),
                "elapsed_seconds": time.perf_counter() - started, "monitor": final}


# ---- Interstage pressure-search multicore path ---------------------------------------

def _pressure_trial_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one independent requested-pressure trial in a spawned worker.

    Pressure-root payloads are already prepared by the public calculation wrapper.
    When a private base-calculation name is supplied, execute that fixed hydraulic
    configuration directly instead of re-entering the public Auto Design wrapper.
    This prevents each pressure point in an Auto Design candidate from recursively
    launching a second array search on Windows.
    """
    import calculations as calc_module
    from calculations import CALCS
    mode = str(payload.get("mode", ""))
    data = dict(payload.get("data") or {})
    data["solve_basis"] = "pressure"
    data["_solver_fast"] = True
    data["_disable_nested_cpu_pool"] = True
    data["_inside_batch_worker"] = True
    base_calc_name = str(payload.get("base_calc_name") or "")
    allowed_base_calcs = {
        "_single_stage_base", "_multistage_base", "_interstage_base",
        "_biturbo_base", "_pressure_exchanger_base", "_multistage_px_base",
    }
    try:
        if base_calc_name in allowed_base_calcs:
            fn = getattr(calc_module, base_calc_name, None)
            if fn is None:
                raise ValueError(f"Unknown pressure-trial base calculation: {base_calc_name}")
            result = fn(data)
        else:
            if mode not in CALCS:
                raise ValueError("Unknown pressure-trial calculation mode.")
            result = CALCS[mode](data)
        return {"ok": True, "result": result, "pressure": payload.get("pressure")}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "pressure": payload.get("pressure")}


def parallel_pressure_trials(mode: str, payloads: Iterable[dict[str, Any]], workers: int | None = None) -> dict[str, Any]:
    """Evaluate independent feed-pressure candidates without overspawning Windows workers.

    Root searches normally have only a handful of expensive membrane/PX trial
    points.  On Windows, spawning one Python process per candidate can cost more
    than the engineering calculation itself because each worker imports the
    scientific stack.  Default to the agreed 50%-CPU floor; callers may
    explicitly request more workers for unusually large batches.
    """
    items = list(payloads)
    raise_if_cancelled()
    if not items:
        return {"results": [], "backend": "cpu-sequential", "workers": 0, "fallback": False}
    requested_workers = workers if workers is not None else MIN_SINGLE_CPU_WORKERS
    n_workers = select_worker_count(len(items), requested_workers, enforce_quarter_floor=True)
    wrapped = [{"mode": mode, "data": dict(x.get("data") or {}), "pressure": x.get("pressure"),
                "base_calc_name": x.get("base_calc_name")} for x in items]
    if n_workers == 1:
        return {"results": [_pressure_trial_worker(x) for x in wrapped], "backend": "cpu-sequential", "workers": 1, "fallback": False}
    try:
        pool = _get_pool(n_workers)
        futures = {pool.submit(_pressure_trial_worker, item): i for i, item in enumerate(wrapped)}
        ordered = [None] * len(wrapped)
        for fut in as_completed(futures):
            raise_if_cancelled()
            i = futures[fut]
            try: ordered[i] = fut.result()
            except Exception as exc: ordered[i] = {"ok": False, "error": str(exc), "pressure": wrapped[i].get("pressure")}
        return {"results": ordered, "backend": "cpu-multiprocess", "workers": n_workers, "fallback": False}
    except Exception as exc:
        if cancellation_requested():
            raise CalculationCancelled("Calculation cancelled by user.")
        return {"results": [_pressure_trial_worker(x) for x in wrapped], "backend": "cpu-sequential", "workers": 1, "fallback": True, "fallback_reason": str(exc)}


def _interstage_trial_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Picklable Stage-2 membrane trial used by the hybrid interstage solver."""
    try:
        from calculations import _interstage_membrane_trial
        result = _interstage_membrane_trial(**payload)
        return {"ok": True, "result": result, "p2": payload.get("p2")}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "p2": payload.get("p2")}


def parallel_interstage_trials(payloads: Iterable[dict[str, Any]], workers: int | None = None) -> dict[str, Any]:
    """Evaluate independent Stage-2 membrane pressure trials across CPU processes.

    The coupled root remains deterministic: this routine only parallelizes the
    expensive independent membrane states used to discover a pressure bracket.
    Final root refinement is still performed by the reference solver.
    """
    items = list(payloads)
    raise_if_cancelled()
    if not items:
        return {"results": [], "backend": "cpu-sequential", "workers": 0, "fallback": False}
    n_workers = select_worker_count(len(items), workers, enforce_quarter_floor=True)
    if len(items) == 1 or n_workers == 1:
        return {"results": [_interstage_trial_worker(x) for x in items],
                "backend": "cpu-sequential", "workers": 1, "fallback": False}
    try:
        pool = _get_pool(n_workers)
        futures = {pool.submit(_interstage_trial_worker, item): i for i, item in enumerate(items)}
        ordered: list[dict[str, Any] | None] = [None] * len(items)
        for fut in as_completed(futures):
            raise_if_cancelled()
            idx = futures[fut]
            try:
                ordered[idx] = fut.result()
            except Exception as exc:
                ordered[idx] = {"ok": False, "error": str(exc), "p2": items[idx].get("p2")}
        return {"results": ordered, "backend": "cpu-multiprocess", "workers": n_workers, "fallback": False}
    except Exception as exc:
        if cancellation_requested():
            raise CalculationCancelled("Calculation cancelled by user.")
        return {"results": [_interstage_trial_worker(x) for x in items],
                "backend": "cpu-sequential", "workers": 1, "fallback": True,
                "fallback_reason": str(exc)}


# ---- Cross-vendor OpenCL vector kernels ----------------------------------------------

_TURBO_KERNEL_FLOAT = r"""
__kernel void design_proxy_scores(
    __global const float *membranes,
    __global const float *area,
    __global const float *recovery,
    const int objective,
    __global float *score)
{
    int i = get_global_id(0);
    float rec = fmax(recovery[i], 1.0e-6f);
    float mem = fmax(membranes[i], 1.0f);
    float ar = fmax(area[i], 1.0f);
    if (objective == 1) score[i] = mem;
    else if (objective == 2) score[i] = mem / rec + 0.00002f * ar;
    else if (objective == 3) score[i] = mem / rec + 0.000015f * ar;
    else score[i] = mem / rec + 0.00001f * ar;
}

__kernel void turbo_metrics(
    __global const float *qf,
    __global const float *qr,
    __global const float *dp_bar,
    __global const float *sg,
    __global float *eff,
    __global float *cv)
{
    int i = get_global_id(0);
    float q = qf[i];
    float e = 0.0f;
    if (q > 0.0f) {
        if (q <= 350.0f) e = (6.2398554051631f * log(q) + 44.44463643353859f) / 100.0f;
        else if (q < 3200.0f) e = (2.040755708597643f * log(q) + 67.11912592185516f) / 100.0f;
    }
    eff[i] = e;
    float dp_psi = fmax(dp_bar[i] * 14.5037738f, 1.0e-12f);
    float q_gpm = qr[i] / 0.227124707f;
    cv[i] = q_gpm * sqrt(fmax(sg[i], 0.0f) / dp_psi);
}
"""


def _cpu_turbo_metrics(qf, qr, dp_bar, sg):
    if np is None:
        out_eff = []
        out_cv = []
        for a, b, c, d in zip(qf, qr, dp_bar, sg):
            a = float(a); b = float(b); c = float(c); d = float(d)
            if a <= 0:
                e = 0.0
            elif a <= 350:
                e = (6.2398554051631 * math.log(a) + 44.44463643353859) / 100.0
            elif a < 3200:
                e = (2.040755708597643 * math.log(a) + 67.11912592185516) / 100.0
            else:
                e = 0.0
            cv = (b / 0.227124707) * math.sqrt(max(d, 0.0) / max(c * 14.5037738, 1e-12))
            out_eff.append(e); out_cv.append(cv)
        return out_eff, out_cv
    qf = np.asarray(qf, dtype=np.float64)
    qr = np.asarray(qr, dtype=np.float64)
    dp = np.asarray(dp_bar, dtype=np.float64)
    sg = np.asarray(sg, dtype=np.float64)
    eff = np.zeros_like(qf)
    m1 = (qf > 0) & (qf <= 350)
    m2 = (qf > 350) & (qf < 3200)
    eff[m1] = (6.2398554051631 * np.log(qf[m1]) + 44.44463643353859) / 100.0
    eff[m2] = (2.040755708597643 * np.log(qf[m2]) + 67.11912592185516) / 100.0
    cv = (qr / 0.227124707) * np.sqrt(np.maximum(sg, 0.0) / np.maximum(dp * 14.5037738, 1e-12))
    return eff.tolist(), cv.tolist()


_opencl_runtime_lock = threading.Lock()
_opencl_runtime: dict[str, Any] | None = None


def _get_opencl_runtime() -> dict[str, Any]:
    """Create and cache one cross-vendor OpenCL context/program for the selected GPU."""
    if CPU_ONLY_MODE:
        raise RuntimeError("OpenCL is disabled by TOTALRO_COMPUTE_MODE=cpu.")
    global _opencl_runtime
    with _opencl_runtime_lock:
        if _opencl_runtime is not None:
            return _opencl_runtime
        import pyopencl as cl
        gpu_devices = []
        for p in cl.get_platforms():
            for d in p.get_devices():
                if int(d.type) & int(cl.device_type.GPU | cl.device_type.ACCELERATOR):
                    gpu_devices.append((p, d))
        if not gpu_devices:
            raise RuntimeError("No GPU/accelerator OpenCL device reported by the installed drivers.")
        p, d = gpu_devices[0]
        ctx = cl.Context([d])
        program = cl.Program(ctx, _TURBO_KERNEL_FLOAT).build()
        # Cache the compiled Kernel itself. Accessing program.turbo_metrics on every
        # call causes PyOpenCL RepeatedKernelRetrieval warnings and needlessly
        # recreates independent kernel wrappers.
        kernel = cl.Kernel(program, "turbo_metrics")
        design_kernel = cl.Kernel(program, "design_proxy_scores")
        _opencl_runtime = {"cl": cl, "platform": p, "device": d, "context": ctx, "program": program,
                           "turbo_metrics_kernel": kernel, "design_proxy_kernel": design_kernel,
                           "kernel_lock": threading.Lock()}
        return _opencl_runtime


def calibrate_gpu_break_even(sizes=(256, 1024, 4096, 16384), repeats: int = 2) -> dict[str, Any]:
    """Measure CPU/OpenCL vector throughput and store a safe automatic crossover."""
    global _gpu_calibration
    if CPU_ONLY_MODE:
        _gpu_calibration={"ok":False,"reason":"OpenCL disabled by TOTALRO_COMPUTE_MODE=cpu",
                          "threshold":GPU_VECTOR_THRESHOLD,"rows":[],"compute_mode":COMPUTE_MODE}
        return dict(_gpu_calibration)
    if np is None:
        _gpu_calibration={"ok":False,"reason":"NumPy unavailable","threshold":GPU_VECTOR_THRESHOLD,"rows":[]}
        return dict(_gpu_calibration)
    rows=[]; threshold=None
    for raw_n in sizes:
        n=max(8,int(raw_n))
        qf=np.linspace(350.0,2500.0,n,dtype=float); qr=0.67*qf
        dp=np.full(n,18.0,dtype=float); sg=np.full(n,1.02,dtype=float)
        t0=time.perf_counter()
        for _ in range(max(1,int(repeats))): _cpu_turbo_metrics(qf,qr,dp,sg)
        cpu_ms=1000.0*(time.perf_counter()-t0)/max(1,int(repeats))
        try:
            runtime = _get_opencl_runtime()
            cl = runtime["cl"]
            ctx = runtime["context"]
            kernel = runtime["turbo_metrics_kernel"]
            kernel_lock = runtime["kernel_lock"]
            # Queue creation is intentionally part of the measured GPU round-trip
            # path so the crossover reflects the real cost seen by CalcOsPower.
            queue = cl.CommandQueue(ctx, properties=cl.command_queue_properties.PROFILING_ENABLE)
            mf = cl.mem_flags
            qf32=qf.astype(np.float32); qr32=qr.astype(np.float32); dp32=dp.astype(np.float32); sg32=sg.astype(np.float32)
            eff=np.empty(n,dtype=np.float32); cv=np.empty(n,dtype=np.float32)
            t1=time.perf_counter()
            for _ in range(max(1,int(repeats))):
                bqf=cl.Buffer(ctx,mf.READ_ONLY|mf.COPY_HOST_PTR,hostbuf=qf32); bqr=cl.Buffer(ctx,mf.READ_ONLY|mf.COPY_HOST_PTR,hostbuf=qr32)
                bdp=cl.Buffer(ctx,mf.READ_ONLY|mf.COPY_HOST_PTR,hostbuf=dp32); bsg=cl.Buffer(ctx,mf.READ_ONLY|mf.COPY_HOST_PTR,hostbuf=sg32)
                be=cl.Buffer(ctx,mf.WRITE_ONLY,eff.nbytes); bc=cl.Buffer(ctx,mf.WRITE_ONLY,cv.nbytes)
                with kernel_lock:
                    kernel(queue, (n,), None, bqf, bqr, bdp, bsg, be, bc)
                    cl.enqueue_copy(queue, eff, be)
                    cl.enqueue_copy(queue, cv, bc)
                    queue.finish()
            gpu_ms=1000.0*(time.perf_counter()-t1)/max(1,int(repeats))
            speedup=cpu_ms/max(gpu_ms,1e-12)
            rows.append({"points":n,"cpu_ms":cpu_ms,"gpu_ms":gpu_ms,"speedup":speedup})
            if threshold is None and gpu_ms <= 0.85*cpu_ms: threshold=n
        except Exception as exc:
            _gpu_calibration={"ok":False,"reason":str(exc),"threshold":GPU_VECTOR_THRESHOLD,"rows":rows}
            return dict(_gpu_calibration)
    _gpu_calibration={"ok":threshold is not None,"threshold":int(threshold or GPU_VECTOR_THRESHOLD),"rows":rows,
                      "criterion":"GPU round-trip <= 85% of CPU vector time"}
    return dict(_gpu_calibration)


def gpu_break_even_threshold() -> int:
    if CPU_ONLY_MODE:
        return GPU_VECTOR_THRESHOLD
    if os.environ.get("CALCOSPOWER_GPU_THRESHOLD"):
        return GPU_VECTOR_THRESHOLD
    global _gpu_calibration
    if _gpu_calibration is None:
        try: calibrate_gpu_break_even()
        except Exception: pass
    return int((_gpu_calibration or {}).get("threshold",GPU_VECTOR_THRESHOLD))

def turbo_metrics_batch(qf, qr, dp_bar, sg, preference: str = "auto") -> dict[str, Any]:
    """Vector turbo efficiency/Cv kernel with automatic CPU/OpenCL routing.

    This kernel is useful for large turbo maps, sensitivity sweeps and future
    optimization grids. For small arrays Auto intentionally stays on CPU because
    PCIe/driver launch overhead is larger than the arithmetic itself.
    """
    qf = list(qf); qr = list(qr); dp_bar = list(dp_bar); sg = list(sg)
    n = len(qf)
    if not (len(qr) == len(dp_bar) == len(sg) == n):
        raise ValueError("Vector inputs must have the same length.")
    if n == 0:
        return {"backend": "cpu-vector", "device": None, "efficiency": [], "cv": [], "validated": True}
    pref = str(preference or "auto").lower()
    threshold = gpu_break_even_threshold() if pref == "auto" else GPU_VECTOR_THRESHOLD
    use_gpu = (not CPU_ONLY_MODE) and (pref in {"gpu", "opencl"} or (pref == "auto" and n >= threshold))
    if use_gpu and np is not None:
        try:
            runtime = _get_opencl_runtime()
            cl = runtime["cl"]; p = runtime["platform"]; d = runtime["device"]
            ctx = runtime["context"]; kernel = runtime["turbo_metrics_kernel"]; kernel_lock = runtime["kernel_lock"]
            queue = cl.CommandQueue(ctx, properties=cl.command_queue_properties.PROFILING_ENABLE)
            if d is not None:
                mf = cl.mem_flags
                qf_a = np.asarray(qf, dtype=np.float32); qr_a = np.asarray(qr, dtype=np.float32)
                dp_a = np.asarray(dp_bar, dtype=np.float32); sg_a = np.asarray(sg, dtype=np.float32)
                eff_a = np.empty(n, dtype=np.float32); cv_a = np.empty(n, dtype=np.float32)
                bufs = [cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a) for a in (qf_a, qr_a, dp_a, sg_a)]
                eff_b = cl.Buffer(ctx, mf.WRITE_ONLY, eff_a.nbytes); cv_b = cl.Buffer(ctx, mf.WRITE_ONLY, cv_a.nbytes)
                # One cached kernel wrapper is reused; guard argument binding so
                # concurrent UI/GPU validation calls cannot overwrite its args.
                with kernel_lock:
                    evt = kernel(queue, (n,), None, *bufs, eff_b, cv_b)
                    cl.enqueue_copy(queue, eff_a, eff_b); cl.enqueue_copy(queue, cv_a, cv_b); queue.finish()
                kernel_ms = max(0.0, (evt.profile.end - evt.profile.start) / 1.0e6)
                # Validate GPU arithmetic against the CPU reference before using it.
                ref_eff, ref_cv = _cpu_turbo_metrics(qf, qr, dp_bar, sg)
                ref_eff_a = np.asarray(ref_eff); ref_cv_a = np.asarray(ref_cv)
                if np.allclose(eff_a.astype(float), ref_eff_a, rtol=2e-5, atol=2e-6) and np.allclose(cv_a.astype(float), ref_cv_a, rtol=2e-5, atol=2e-5):
                    return {"backend": "opencl-gpu", "device": str(d.name).strip(), "platform": str(p.name).strip(), "efficiency": eff_a.astype(float).tolist(), "cv": cv_a.astype(float).tolist(), "validated": True, "kernel_ms": kernel_ms}
        except Exception as exc:
            gpu_error = str(exc)
        else:
            gpu_error = "No GPU OpenCL device available."
    else:
        gpu_error = "GPU not selected for this workload."
    eff, cv = _cpu_turbo_metrics(qf, qr, dp_bar, sg)
    return {"backend": "cpu-vector", "device": None, "efficiency": eff, "cv": cv, "validated": True, "gpu_fallback_reason": gpu_error}



def design_proxy_scores_batch(membranes, area, recovery_fraction, objective: str = "min_sec", preference: str = "auto") -> dict[str, Any]:
    """Score large plant-design candidate arrays on GPU when available.

    This is deliberately a *screening* surrogate. It performs no authoritative RO
    physics; shortlisted candidates are always recalculated by the full CPU solver.
    The kernel mirrors the lightweight candidate proxy used by design_optimizer.py.
    """
    membranes=list(membranes); area=list(area); recovery_fraction=list(recovery_fraction)
    n=len(membranes)
    if not (len(area)==len(recovery_fraction)==n):
        raise ValueError("Design-screen vectors must have the same length.")
    obj={"min_sec":0,"min_membranes":1,"min_pressure":2,"balanced":3}.get(str(objective or "min_sec"),0)
    def cpu_scores():
        out=[]
        for mem,ar,rec in zip(membranes,area,recovery_fraction):
            mem=max(float(mem),1.0); ar=max(float(ar),1.0); rec=max(float(rec),1e-6)
            if obj==1: v=mem
            elif obj==2: v=mem/rec+0.00002*ar
            elif obj==3: v=mem/rec+0.000015*ar
            else: v=mem/rec+0.00001*ar
            out.append(v)
        return out
    if n==0:
        return {"backend":"cpu-vector","device":None,"scores":[],"validated":True,"points":0}
    pref=str(preference or "auto").lower()
    threshold=gpu_break_even_threshold() if pref=="auto" else GPU_VECTOR_THRESHOLD
    use_gpu=(not CPU_ONLY_MODE) and (pref in {"gpu","opencl"} or (pref=="auto" and n>=threshold))
    if use_gpu and np is not None:
        try:
            runtime=_get_opencl_runtime(); cl=runtime["cl"]; ctx=runtime["context"]
            d=runtime["device"]; p=runtime["platform"]; kernel=runtime["design_proxy_kernel"]
            lock=runtime["kernel_lock"]
            queue=cl.CommandQueue(ctx,properties=cl.command_queue_properties.PROFILING_ENABLE); mf=cl.mem_flags
            mem=np.asarray(membranes,dtype=np.float32); ar=np.asarray(area,dtype=np.float32); rec=np.asarray(recovery_fraction,dtype=np.float32)
            scores=np.empty(n,dtype=np.float32)
            bufs=[cl.Buffer(ctx,mf.READ_ONLY|mf.COPY_HOST_PTR,hostbuf=a) for a in (mem,ar,rec)]
            bout=cl.Buffer(ctx,mf.WRITE_ONLY,scores.nbytes)
            with lock:
                evt=kernel(queue,(n,),None,*bufs,np.int32(obj),bout)
                cl.enqueue_copy(queue,scores,bout); queue.finish()
            ref=np.asarray(cpu_scores(),dtype=float)
            if np.allclose(scores.astype(float),ref,rtol=3e-5,atol=3e-4):
                return {"backend":"opencl-gpu","device":str(d.name).strip(),"platform":str(p.name).strip(),
                        "scores":scores.astype(float).tolist(),"validated":True,"points":n,
                        "kernel_ms":max(0.0,(evt.profile.end-evt.profile.start)/1e6),"threshold":threshold}
            gpu_error="GPU design-screen arithmetic did not match CPU reference tolerance."
        except Exception as exc:
            gpu_error=str(exc)
    else:
        gpu_error="GPU not selected for this workload."
    return {"backend":"cpu-vector","device":None,"scores":cpu_scores(),"validated":True,"points":n,
            "threshold":threshold,"gpu_fallback_reason":gpu_error}


def gpu_self_test(points: int = 32768) -> dict[str, Any]:
    """Execute a real OpenCL kernel and verify its results against CPU arithmetic."""
    if CPU_ONLY_MODE:
        return {"ok": False, "backend": "cpu", "reason":
                "GPU validation is disabled for the authenticated AWS CPU deployment.",
                "compute_mode": COMPUTE_MODE}
    points = max(1024, min(int(points or 32768), 262144))
    if np is None:
        return {"ok": False, "backend": "cpu", "reason": "NumPy unavailable; GPU validation cannot run."}
    qf = np.linspace(24.0, 2500.0, points, dtype=np.float64)
    qr = qf * 0.58
    dp = np.linspace(8.0, 55.0, points, dtype=np.float64)
    sg = np.linspace(1.01, 1.08, points, dtype=np.float64)

    t0 = time.perf_counter()
    cpu_eff, cpu_cv = _cpu_turbo_metrics(qf, qr, dp, sg)
    cpu_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    result = turbo_metrics_batch(qf, qr, dp, sg, preference="gpu")
    roundtrip_ms = (time.perf_counter() - t1) * 1000.0
    if result.get("backend") != "opencl-gpu":
        return {
            "ok": False, "backend": result.get("backend", "cpu-vector"),
            "reason": result.get("gpu_fallback_reason", "OpenCL GPU execution unavailable."),
            "points": points, "cpu_ms": cpu_ms,
        }
    gpu_eff = np.asarray(result["efficiency"], dtype=float)
    gpu_cv = np.asarray(result["cv"], dtype=float)
    ref_eff = np.asarray(cpu_eff, dtype=float)
    ref_cv = np.asarray(cpu_cv, dtype=float)
    max_eff_error = float(np.max(np.abs(gpu_eff - ref_eff))) if points else 0.0
    max_cv_rel_error = float(np.max(np.abs(gpu_cv - ref_cv) / np.maximum(np.abs(ref_cv), 1e-12))) if points else 0.0
    return {
        "ok": bool(result.get("validated")),
        "backend": "opencl-gpu",
        "device": result.get("device"),
        "platform": result.get("platform"),
        "points": points,
        "kernel_ms": result.get("kernel_ms"),
        "gpu_roundtrip_ms": roundtrip_ms,
        "cpu_vector_ms": cpu_ms,
        "max_efficiency_abs_error": max_eff_error,
        "max_cv_relative_error": max_cv_rel_error,
        "message": "OpenCL kernel executed on the GPU and matched the CPU reference within CalcOsPower tolerances.",
    }
