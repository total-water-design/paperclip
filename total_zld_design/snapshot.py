"""Versioned project snapshot schema for the Suite Project Library."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_snapshot(
    *,
    project: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    results: dict[str, Any] | None = None,
    active_mode: str = "thermal_legacy",
    source_handoff: dict[str, Any] | None = None,
    active_case: int = 1,
) -> dict[str, Any]:
    """Build a complete restorable Total ZLD Design snapshot.

    Hosted persistence belongs to the Suite Project Library. This function only defines
    the application-level JSON state that should be stored in ProjectRevision.snapshot_json.
    """
    case_key = str(active_case)
    return {
        "format": "Total ZLD Design Project",
        "schema_version": 1,
        "app_version": "0.2.0",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "project": project or {},
        "active_case": active_case,
        "active_mode": active_mode,
        "units": {
            "flow": "m3/h",
            "temperature": "degC",
            "tds": "mg/L",
            "power": "kW",
            "steam": "t/h",
            "solids": "t/h",
        },
        "cases": {
            case_key: {
                "inputs": inputs or {},
                "results": results or {},
            }
        },
        "source_handoff": source_handoff or {},
        "zld_model": {
            "thermal_model": "legacy_seed_regression",
            "fo_model": "saved_workbook_transport_regression",
            "validation_state": "engineering_preview",
        },
    }
