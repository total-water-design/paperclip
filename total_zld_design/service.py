"""Shared request/response helpers used by Flask and the standalone preview."""

from __future__ import annotations

from typing import Any

from .defaults import thermal_defaults, fo_defaults
from .engine import calculate
from .snapshot import build_snapshot
from .tiers import commercial_payload


def defaults_payload() -> dict[str, Any]:
    return {
        "app": {
            "name": "Total ZLD Design",
            "version": "0.2.0",
            "state": "Engineering Preview",
            "product_id": "zld",
        },
        "thermal": thermal_defaults(),
        "fo": fo_defaults(),
        "commercial": commercial_payload(),
    }


def handle_calculation_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    mode = payload.get("mode", "thermal_legacy")
    result = calculate(mode, payload.get("inputs"))
    return {"ok": True, "result": result.to_dict()}


def handle_snapshot_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    result = calculate(payload.get("mode", "thermal_legacy"), payload.get("inputs"))
    snapshot = build_snapshot(
        project=payload.get("project"),
        inputs=result.inputs,
        results=result.to_dict(),
        active_mode=result.mode,
        source_handoff=payload.get("source_handoff"),
    )
    return {"ok": True, "snapshot": snapshot}
