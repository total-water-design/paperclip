#!/usr/bin/env python3
"""Fail-closed verifier for the TOT-73 conventional RO manifest.

The draft is intentionally allowed to exist with missing fields, but it must
never be mistaken for an approved immutable registry.  This verifier checks
the required topology and reports NOT VALIDATABLE until every approval gate is
complete.  It does not fill values, derive tolerances, or inspect TWDS output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CASE_FIELDS = ("reference_document", "exact_product", "wet_dry_variant",
               "product_data_sheet_form", "product_data_sheet_revision",
               "source_document_sha256", "inputs", "expected_outputs",
               "tolerance", "handling")
INPUT_FIELDS = ("feed_composition", "analytical_basis", "nacl_mg_l",
                "boron_mg_l", "feed_temperature_c", "feed_ph",
                "applied_feed_pressure_bar", "permeate_backpressure_bar",
                "recovery_percent", "element_count", "element_arrangement",
                "feed_flow_m3_h", "hydraulic_boundaries",
                "fouling_or_flow_factor", "salt_passage_factor",
                "temperature_correction", "concentration_polarization",
                "pressure_drop_bar", "stabilization_assumptions",
                "unit_constants")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    path = args.manifest.resolve()
    errors: list[str] = []
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read manifest: {exc}")
        return 1

    if data.get("schema") != "tot-73-conventional-ro-vector-manifest/v1":
        errors.append("unexpected schema")
    if data.get("scope") != "conventional steady-state BWRO/SWRO only":
        errors.append("scope is not conventional BWRO/SWRO only")
    if data.get("preregistration_controls", {}).get("batch_ro_tolerance_scope_reused") is not False:
        errors.append("Batch RO tolerance reuse control is not false")
    if data.get("preregistration_controls", {}).get("tolerances_may_use_observed_twds_outputs") is not False:
        errors.append("observed TWDS tolerance fitting control is not false")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array")
        cases = []
    for index, case in enumerate(cases):
        prefix = f"case[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} is not an object")
            continue
        for field in CASE_FIELDS:
            if field not in case:
                errors.append(f"{prefix}.{field} is absent")
            elif field not in ("tolerance", "handling") and case[field] is None:
                errors.append(f"{prefix}.{field} is null")
        inputs = case.get("inputs", {})
        if not isinstance(inputs, dict):
            errors.append(f"{prefix}.inputs is not an object")
        else:
            for field in INPUT_FIELDS:
                if field not in inputs:
                    errors.append(f"{prefix}.inputs.{field} is absent")
                elif inputs[field] is None:
                    errors.append(f"{prefix}.inputs.{field} is null")
        tolerance = case.get("tolerance", {})
        if not isinstance(tolerance, dict) or not all(key in tolerance for key in ("absolute", "relative", "combined_rule")):
            errors.append(f"{prefix}.tolerance lacks absolute/relative/combined_rule")
    registry = data.get("registry", {})
    if not isinstance(registry, dict) or not registry.get("quantity_rules"):
        errors.append("registry.quantity_rules is empty")
    else:
        for index, rule in enumerate(registry["quantity_rules"]):
            required = ("quantity", "absolute_tolerance",
                        "relative_tolerance_percent", "justification")
            if not isinstance(rule, dict) or any(rule.get(field) in (None, "") for field in required):
                errors.append(f"registry.quantity_rules[{index}] is incomplete")
    approval = data.get("approval", {})
    approved = (data.get("status") == "APPROVED_IMMUTABLE" and
                data.get("immutable") is True and
                approval.get("approved_by") and approval.get("approved_at") and
                approval.get("approval_record") and approval.get("manifest_sha256") == sha256(path))
    if errors:
        print("NOT VALIDATABLE: structural or required-field gaps remain")
        for error in errors:
            print(f"- {error}")
        return 2
    if not approved:
        print("PENDING HUMAN APPROVAL: manifest and tolerance registry are structurally complete; human approval/immutable hash is the only remaining gap")
        return 2
    print(f"PASS: approved immutable TOT-73 manifest sha256={sha256(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
