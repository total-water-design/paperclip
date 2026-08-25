"""Shared request/response helpers used by Flask and the standalone preview."""

from __future__ import annotations

from typing import Any

from .defaults import thermal_defaults, fo_defaults
from .fo import fo_engineering_defaults
from .falling_film_evaporator import falling_film_capabilities, falling_film_defaults
from .process_train import process_train_capabilities, process_train_payload
from .engine import calculate
from .snapshot import build_snapshot
from .tiers import commercial_payload
from .solution_properties import solution_property_capabilities
from .crystal_kinetics import crystal_kinetics_capabilities
from .crystallization_inhibitors import crystallizer_inhibitor_capabilities
from .population_balance import population_balance_capabilities
from .crystallizer_design import crystallizer_design_capabilities


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
        "fo_engineering": fo_engineering_defaults(),
        "falling_film": falling_film_defaults(),
        "process_train": process_train_payload(),
        "solution_properties": solution_property_capabilities(),
        "crystal_kinetics": crystal_kinetics_capabilities(),
        "crystallization_inhibitors": crystallizer_inhibitor_capabilities(),
        "population_balance": population_balance_capabilities(),
        "crystallizer_design": crystallizer_design_capabilities(),
        "falling_film_capabilities": falling_film_capabilities(),
        "process_train_capabilities": process_train_capabilities(),
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
