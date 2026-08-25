"""Configurable ZLD process-train state and validation.

The train is intentionally not a fixed flowsheet. Users may add, remove and
reorder supported unit operations. This module validates serializable state and
returns engineering advisories without forcing one universal ZLD sequence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

UNIT_CATALOG: dict[str, dict[str, str]] = {
    "forward_osmosis": {"label": "Forward Osmosis", "code": "FO", "workspace": "fo-design"},
    "brine_concentrator": {"label": "Brine Concentrator", "code": "BC", "workspace": "thermal"},
    "falling_film_evaporator": {"label": "Falling Film Evaporator", "code": "FFE", "workspace": "thermal"},
    "crystallizer": {"label": "Crystallizer", "code": "CRYS", "workspace": "crystallization"},
}

_DEFAULT_TRAIN = [
    {"instance_id": "forward_osmosis-1", "unit_type": "forward_osmosis", "enabled": True},
    {"instance_id": "brine_concentrator-1", "unit_type": "brine_concentrator", "enabled": True},
    {"instance_id": "falling_film_evaporator-1", "unit_type": "falling_film_evaporator", "enabled": True},
    {"instance_id": "crystallizer-1", "unit_type": "crystallizer", "enabled": True},
]


def default_process_train() -> list[dict[str, Any]]:
    return deepcopy(_DEFAULT_TRAIN)


def _next_instance_id(unit_type: str, train: Iterable[dict[str, Any]]) -> str:
    used = {str(item.get("instance_id", "")) for item in train}
    n = 1
    while f"{unit_type}-{n}" in used:
        n += 1
    return f"{unit_type}-{n}"


def normalize_process_train(train: Any | None) -> list[dict[str, Any]]:
    """Return canonical serializable train state.

    Duplicate unit types are allowed because real ZLD trains may use repeated
    effects/steps. Optional per-unit ``config`` and ``last_result`` dictionaries
    are preserved so the Project Library can restore design state without making
    the current unit-specific engines pretend to be a fully coupled flowsheet solver.
    """
    if train is None:
        return default_process_train()
    if not isinstance(train, list):
        raise ValueError("Process train must be a list.")
    out: list[dict[str, Any]] = []
    for raw in train:
        if isinstance(raw, str):
            unit_type = raw
            item: dict[str, Any] = {"unit_type": unit_type, "enabled": True}
        elif isinstance(raw, dict):
            item = dict(raw)
            unit_type = str(item.get("unit_type", ""))
        else:
            raise ValueError("Process-train entries must be strings or objects.")
        if unit_type not in UNIT_CATALOG:
            raise ValueError(f"Unsupported ZLD unit operation: {unit_type!r}")
        instance_id = str(item.get("instance_id") or _next_instance_id(unit_type, out))
        if any(existing["instance_id"] == instance_id for existing in out):
            raise ValueError(f"Duplicate process-train instance_id: {instance_id}")
        normalized = {
            "instance_id": instance_id,
            "unit_type": unit_type,
            "enabled": bool(item.get("enabled", True)),
        }
        if isinstance(item.get("config"), dict):
            normalized["config"] = deepcopy(item["config"])
        if isinstance(item.get("last_result"), dict):
            normalized["last_result"] = deepcopy(item["last_result"])
        out.append(normalized)
    return out


def add_unit(train: Any, unit_type: str, index: int | None = None) -> list[dict[str, Any]]:
    current = normalize_process_train(train)
    if unit_type not in UNIT_CATALOG:
        raise ValueError(f"Unsupported ZLD unit operation: {unit_type!r}")
    item = {"instance_id": _next_instance_id(unit_type, current), "unit_type": unit_type, "enabled": True}
    if index is None:
        current.append(item)
    else:
        if index < 0 or index > len(current):
            raise ValueError("Process-train insertion index is out of range.")
        current.insert(index, item)
    return current


def remove_unit(train: Any, instance_id: str) -> list[dict[str, Any]]:
    current = normalize_process_train(train)
    result = [item for item in current if item["instance_id"] != instance_id]
    if len(result) == len(current):
        raise ValueError(f"Process-train unit not found: {instance_id}")
    return result


def move_unit(train: Any, instance_id: str, new_index: int) -> list[dict[str, Any]]:
    current = normalize_process_train(train)
    if new_index < 0 or new_index >= len(current):
        raise ValueError("Process-train destination index is out of range.")
    old_index = next((i for i, item in enumerate(current) if item["instance_id"] == instance_id), None)
    if old_index is None:
        raise ValueError(f"Process-train unit not found: {instance_id}")
    item = current.pop(old_index)
    current.insert(new_index, item)
    return current


def process_train_advisories(train: Any) -> list[dict[str, str]]:
    current = [item for item in normalize_process_train(train) if item["enabled"]]
    types = [item["unit_type"] for item in current]
    advisories: list[dict[str, str]] = []
    if not current:
        advisories.append({"severity": "warning", "code": "TRAIN-EMPTY", "message": "No active ZLD unit operations are configured."})
        return advisories
    if "crystallizer" in types:
        c = types.index("crystallizer")
        upstream_concentration = any(t in {"brine_concentrator", "falling_film_evaporator", "forward_osmosis"} for t in types[:c])
        if not upstream_concentration:
            advisories.append({
                "severity": "review",
                "code": "TRAIN-CRYS-FEED",
                "message": "Crystallizer has no upstream concentration operation; verify that incoming feed is already at the required crystallizer basis.",
            })
    if "forward_osmosis" in types and "falling_film_evaporator" in types and types.index("forward_osmosis") > types.index("falling_film_evaporator"):
        advisories.append({
            "severity": "review",
            "code": "TRAIN-FO-DOWNSTREAM",
            "message": "FO is downstream of thermal evaporation. Confirm draw/feed temperature, salinity and membrane compatibility for this nonstandard sequence.",
        })
    if types.count("crystallizer") > 1:
        advisories.append({
            "severity": "information",
            "code": "TRAIN-MULTI-CRYS",
            "message": "Multiple crystallizers are configured; species-specific split/precipitation sequencing must be defined before coupled simulation.",
        })
    return advisories


def process_train_payload(train: Any | None = None) -> dict[str, Any]:
    normalized = normalize_process_train(train)
    return {
        "units": normalized,
        "catalog": deepcopy(UNIT_CATALOG),
        "advisories": process_train_advisories(normalized),
        "coupled_solver_status": "configuration persisted; fully coupled arbitrary-order solver is future work",
    }


def process_train_capabilities() -> dict[str, Any]:
    return {
        "status": "configurable and project-persistable",
        "actions": ["add", "remove", "move", "enable/disable"],
        "unit_catalog": deepcopy(UNIT_CATALOG),
        "principle": "Do not force one fixed ZLD train; validate unconventional order rather than silently forbidding it.",
        "coupled_calculation": "current calculation engines remain unit-specific until arbitrary-order handoff solving is implemented",
    }
