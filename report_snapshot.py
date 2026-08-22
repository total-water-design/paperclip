"""Immutable customer-report snapshot validation for Total RO Design.

This module has no Flask dependency so report-integrity rules can be exercised in
CI/build environments before the authenticated server is installed.  It never
changes engineering results; it only confirms that one solved-case snapshot is
complete, current, internally consistent, and safe to render.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

SCHEMA = "TotalRODesign.ReportSnapshot.v1"
VALID_STATES = {"ready"}


def as_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _first_number(mapping: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = as_number(mapping.get(key))
        if value is not None:
            return value
    return None


def _flow_tolerance(reference: float | None) -> float:
    return max(1e-6, 0.003 * max(abs(reference or 0.0), 1.0))


def validate_report_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(snapshot, dict):
        return ["A report snapshot object is required."]
    if snapshot.get("schema") != SCHEMA:
        errors.append("Unsupported report snapshot schema.")
    if str(snapshot.get("state") or "").strip().lower() not in VALID_STATES:
        errors.append("The selected case is not ready for customer-report generation.")
    if bool(snapshot.get("stale")):
        errors.append("The selected case is stale because an input changed after calculation.")

    result = snapshot.get("result")
    if not isinstance(result, dict):
        errors.append("A solved-case result is required.")
        return errors

    integrity = snapshot.get("report_integrity")
    if isinstance(integrity, dict):
        calculated = str(integrity.get("last_calculated_signature") or "")
        active = str(integrity.get("active_signature") or "")
        if calculated and active and calculated != active:
            errors.append("The selected case is stale because its active inputs no longer match the calculated result.")

    try:
        stages = int(snapshot.get("stage_count") or result.get("stage_count") or 0)
    except (TypeError, ValueError):
        stages = 0
    if stages not in {1, 2, 3, 4}:
        errors.append("Stage count must be between one and four.")
        return errors

    feed = _first_number(result, "feed_flow", "stage1_feed_flow")
    product = _first_number(result, "product_flow", "permeate_flow", "composite_permeate_flow")
    final_reject = _first_number(
        result,
        f"reject_flow_{stages}",
        f"stage{stages}_concentrate_flow",
        "reject_flow_final",
        "final_concentrate_flow",
    )
    if None not in {feed, product, final_reject}:
        imbalance = abs(feed - product - final_reject)
        if imbalance > _flow_tolerance(feed):
            errors.append("Report integrity check failed: feed flow does not equal permeate plus concentrate within tolerance.")

    stage_totals: list[float] = []
    stage_permeates: list[float] = []
    for stage in range(1, stages + 1):
        vessels = _first_number(result, f"stage{stage}_pressure_vessels", f"vessels_{stage}")
        elements_per = _first_number(result, f"stage{stage}_elements_per_vessel", f"elements_per_vessel_{stage}")
        total = _first_number(result, f"stage{stage}_total_elements", f"total_elements_{stage}")
        if None not in {vessels, elements_per, total} and abs(vessels * elements_per - total) > 0.51:
            errors.append(f"Report integrity check failed: Stage {stage} element inventory is inconsistent.")
        if total is not None:
            stage_totals.append(total)

        stage_perm = _first_number(result, f"stage{stage}_permeate_flow", f"product_flow_{stage}")
        if stage_perm is not None:
            stage_permeates.append(stage_perm)

        profile = result.get(f"stage{stage}_element_profile")
        if profile is not None and not isinstance(profile, list):
            errors.append(f"Report integrity check failed: Stage {stage} element profile is invalid.")
        elif isinstance(profile, list) and profile and elements_per is not None:
            # The report profile represents one vessel; it should contain the
            # actual element positions selected for that stage.
            if abs(len(profile) - elements_per) > 0.51:
                errors.append(f"Report integrity check failed: Stage {stage} profile length does not match elements per vessel.")

        if stage < stages:
            reject = _first_number(result, f"reject_flow_{stage}", f"stage{stage}_concentrate_flow")
            next_feed = _first_number(result, f"stage{stage + 1}_feed_flow")
            if None not in {reject, next_feed} and abs(reject - next_feed) > _flow_tolerance(reject):
                errors.append(f"Report integrity check failed: Stage {stage + 1} feed does not match Stage {stage} concentrate.")

    total_elements = _first_number(result, "total_membrane_elements", "total_elements")
    if total_elements is not None and len(stage_totals) == stages:
        if abs(total_elements - sum(stage_totals)) > 0.51:
            errors.append("Report integrity check failed: total membrane-element count does not match the stage inventory.")

    if product is not None and len(stage_permeates) == stages:
        if abs(product - sum(stage_permeates)) > _flow_tolerance(product):
            errors.append("Report integrity check failed: composite permeate flow does not match the sum of stage permeate flows.")

    recovery = _first_number(result, "recovery", "overall_recovery")
    if feed not in {None, 0.0} and product is not None and recovery is not None:
        expected_fraction = product / feed
        normalized = recovery / 100.0 if abs(recovery) > 1.5 else recovery
        if abs(normalized - expected_fraction) > 0.004:
            errors.append("Report integrity check failed: overall recovery does not match solved feed and permeate flows.")

    unit_system = snapshot.get("unit_system")
    if not isinstance(unit_system, dict):
        errors.append("The report snapshot is missing its active unit system.")
    else:
        for key in ("flow", "pressure", "flux"):
            if not str(unit_system.get(key) or "").strip():
                errors.append(f"The report snapshot is missing its {key} unit.")

    options = snapshot.get("options")
    if isinstance(options, dict):
        if options.get("include_detailed_chemistry") and not isinstance(snapshot.get("chemistry_detail"), dict):
            errors.append("Detailed chemistry was requested but is not ready.")
        if options.get("include_tail_chemistry") and not isinstance(snapshot.get("tail_chemistry"), dict):
            errors.append("Tail-element chemistry was requested but is not ready.")
        if options.get("include_hydraulic_envelope") and not isinstance(snapshot.get("hydraulic_envelope"), dict):
            errors.append("Hydraulic Envelope was requested but has not been calculated.")

    return errors
