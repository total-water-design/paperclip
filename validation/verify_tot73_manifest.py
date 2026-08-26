#!/usr/bin/env python3
"""Fail-closed verifier for the TOT-73 conventional RO manifest."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

CASE_FIELDS = ("reference_document", "exact_product", "wet_dry_variant", "product_data_sheet_form", "product_data_sheet_revision", "source_document_sha256", "inputs", "expected_outputs", "tolerance", "handling")
INPUT_FIELDS = ("feed_composition", "analytical_basis", "nacl_mg_l", "boron_mg_l", "feed_temperature_c", "feed_ph", "applied_feed_pressure_bar", "permeate_backpressure_bar", "recovery_percent", "element_count", "element_arrangement", "feed_flow_m3_h", "hydraulic_boundaries", "fouling_or_flow_factor", "salt_passage_factor", "temperature_correction", "concentration_polarization", "pressure_drop_bar", "stabilization_assumptions", "unit_constants")
APPROVAL_SCHEMA = "tot-73-conventional-ro-detached-approval/v1"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def verify(manifest_path: Path, approval_path: Path) -> tuple[str, list[str]]:
    errors: list[str] = []
    try:
        data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "FAIL", [f"cannot read manifest: {exc}"]
    if data.get("schema") != "tot-73-conventional-ro-vector-manifest/v1": errors.append("unexpected schema")
    if data.get("scope") != "conventional steady-state BWRO/SWRO only": errors.append("scope is not conventional BWRO/SWRO only")
    controls = data.get("preregistration_controls", {})
    if controls.get("batch_ro_tolerance_scope_reused") is not False: errors.append("Batch RO tolerance reuse control is not false")
    if controls.get("tolerances_may_use_observed_twds_outputs") is not False: errors.append("observed TWDS tolerance fitting control is not false")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array"); cases = []
    repository_root = manifest_path.parent.parent
    for index, case in enumerate(cases):
        prefix = f"case[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} is not an object"); continue
        for field in CASE_FIELDS:
            if field not in case: errors.append(f"{prefix}.{field} is absent")
            elif field not in ("tolerance", "handling") and case[field] is None: errors.append(f"{prefix}.{field} is null")
        source_reference = case.get("reference_document")
        if isinstance(source_reference, str):
            source_path = repository_root / source_reference
            if not source_path.is_file(): errors.append(f"{prefix}.reference_document does not exist: {source_reference}")
            elif sha256(source_path) != case.get("source_document_sha256"): errors.append(f"{prefix}.source_document_sha256 does not match source file")
        inputs = case.get("inputs", {})
        if not isinstance(inputs, dict): errors.append(f"{prefix}.inputs is not an object")
        else:
            for field in INPUT_FIELDS:
                if field not in inputs: errors.append(f"{prefix}.inputs.{field} is absent")
                elif inputs[field] is None: errors.append(f"{prefix}.inputs.{field} is null")
        tolerance = case.get("tolerance", {})
        if not isinstance(tolerance, dict) or not all(key in tolerance for key in ("absolute", "relative", "combined_rule")): errors.append(f"{prefix}.tolerance lacks absolute/relative/combined_rule")
    registry = data.get("registry", {})
    if not isinstance(registry, dict) or not registry.get("quantity_rules"): errors.append("registry.quantity_rules is empty")
    else:
        for index, rule in enumerate(registry["quantity_rules"]):
            required = ("quantity", "absolute_tolerance", "relative_tolerance_percent", "justification")
            if not isinstance(rule, dict) or any(rule.get(field) in (None, "") for field in required): errors.append(f"registry.quantity_rules[{index}] is incomplete")
    if errors: return "FAIL", errors
    try:
        approval: dict[str, Any] = json.loads(approval_path.read_text(encoding="utf-8"))
    except FileNotFoundError: return "PENDING", [f"detached approval record not found: {approval_path}"]
    except (OSError, json.JSONDecodeError) as exc: return "FAIL", [f"cannot read detached approval record: {exc}"]
    if approval.get("schema") != APPROVAL_SCHEMA: return "FAIL", ["unexpected detached approval schema"]
    if approval.get("manifest_sha256") != sha256(manifest_path): return "FAIL", ["detached approval manifest_sha256 does not match manifest"]
    required = ("approved_by", "approved_at", "approval_record", "candidate_commit_sha")
    if any(approval.get(field) in (None, "") for field in required): return "PENDING", ["detached approval metadata is incomplete"]
    return "PASS", []

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    approval_path = args.approval.resolve() if args.approval else manifest_path.with_name("TOT-73_CONVENTIONAL_RO_APPROVAL.json")
    status, details = verify(manifest_path, approval_path)
    if status == "FAIL":
        print("NOT VALIDATABLE: integrity, structural, or required-field gaps remain")
        for detail in details: print(f"- {detail}")
        return 2
    if status == "PENDING":
        print("PENDING HUMAN APPROVAL: manifest and tolerance registry are structurally complete; detached human approval is the only remaining gap")
        for detail in details: print(f"- {detail}")
        return 2
    print(f"PASS: detached approval covers TOT-73 manifest sha256={sha256(manifest_path)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
