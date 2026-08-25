"""Cross-application economic handoff guardrails for Total Water Economics.

These checks sit outside the v1 normalization module so specialist producer rules,
project-level cost ownership and detailed-OPEX identity can evolve without
weakening the migration-tolerant handoff parser. Project-cost FX validation is
delegated to the canonical ``twds.cost_item`` schema so the Suite has one
currency-conversion convention.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from economic_cost_schema import canonicalize_cost_item

SPECIALIST_APPLICATIONS = {"pretreatment", "bio", "ro", "zld", "balance", "water_design", "system_integration"}
SPECIALIST_SCOPE_BUCKETS = {"equipment_purchase", "direct_installation"}
PROJECT_LEVEL_BUCKETS = {
    "construction_indirect", "engineering_procurement", "owner_cost", "contingency",
    "escalation", "financing", "working_capital",
}
OPEX_CATEGORIES = {"fixed", "variable", "energy", "chemicals", "labor", "maintenance", "replacement", "disposal", "other"}


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Economic values must be finite.")
    return result


def _included(summary: dict) -> bool:
    value = summary.get("included")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def install_contract_extensions(contract_module) -> None:
    contract_module.APPLICATION_NAMES.setdefault(
        "system_integration", "Total Water Design — System Integration & Optimization"
    )


def validate_project_cost_currencies(cost_items: list[dict] | None, reporting_currency: str) -> None:
    """Validate manual project costs using the canonical cost-item FX rules."""
    reporting_currency = str(reporting_currency or "USD").strip().upper()
    for raw in cost_items or []:
        canonicalize_cost_item(
            raw or {},
            default_currency=reporting_currency,
            project_context={"currency": reporting_currency},
        )


def _raw_capex_items(summary: dict) -> list[dict]:
    capex = summary.get("capex") if isinstance(summary.get("capex"), dict) else {}
    details = summary.get("details") if isinstance(summary.get("details"), dict) else {}
    items = capex.get("cost_items") or summary.get("cost_items") or details.get("cost_items") or []
    return items if isinstance(items, list) else []


def _raw_bucket_map(summary: dict) -> dict:
    capex = summary.get("capex") if isinstance(summary.get("capex"), dict) else {}
    buckets = capex.get("buckets") if isinstance(capex.get("buckets"), dict) else {}
    return {**capex, **buckets}


def _annual_opex(summary: dict) -> dict:
    block = summary.get("opex") if isinstance(summary.get("opex"), dict) else {}
    if isinstance(block.get("annual"), dict):
        return block.get("annual") or {}
    if isinstance(summary.get("opex_annual"), dict):
        return summary.get("opex_annual") or {}
    return block


def _opex_items(summary: dict) -> list[dict]:
    details = summary.get("details") if isinstance(summary.get("details"), dict) else {}
    block = summary.get("opex") if isinstance(summary.get("opex"), dict) else {}
    items = details.get("opex_items") or block.get("opex_items") or summary.get("opex_items") or []
    return items if isinstance(items, list) else []


def validate_specialist_scope_ownership(summary: dict) -> None:
    source = summary.get("source") if isinstance(summary.get("source"), dict) else {}
    app_id = str(source.get("application_id") or summary.get("application_id") or "other").strip().lower()
    if app_id not in SPECIALIST_APPLICATIONS:
        return
    for item in _raw_capex_items(summary):
        if not isinstance(item, dict):
            continue
        bucket = str(item.get("bucket") or "equipment_purchase").strip().lower()
        if bucket in PROJECT_LEVEL_BUCKETS:
            raise ValueError(
                f"{app_id}: specialist economic summaries may not own project-level CAPEX bucket {bucket!r}. "
                "Export process-scope equipment/direct installation here and apply project-wide costs once in Total Water Economics."
            )
    buckets = _raw_bucket_map(summary)
    for bucket in PROJECT_LEVEL_BUCKETS:
        if bucket in buckets and _number(buckets.get(bucket), 0.0) > 0:
            raise ValueError(
                f"{app_id}: specialist economic summaries may not own project-level CAPEX bucket {bucket!r}. "
                "Apply that cost once in Total Water Economics."
            )


def validate_opex_detail(summary: dict, *, tolerance: float = 1e-6) -> list[str]:
    warnings: list[str] = []
    annual = _annual_opex(summary)
    items = _opex_items(summary)
    seen: set[str] = set()
    by_category = {key: 0.0 for key in OPEX_CATEGORIES}
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError("OPEX detail items must be objects.")
        item_id = str(item.get("item_id") or "").strip()
        if not item_id:
            raise ValueError(f"OPEX detail item {index} is missing item_id.")
        if item_id in seen:
            raise ValueError(f"Duplicate OPEX economic item {item_id!r} within one source summary.")
        seen.add(item_id)
        category = str(item.get("category") or "other").strip().lower()
        if category not in OPEX_CATEGORIES:
            raise ValueError(f"OPEX detail item {item_id!r} uses unsupported category {category!r}.")
        amount = _number(item.get("amount_annual"), _number(item.get("amount"), 0.0))
        if amount < 0:
            raise ValueError(f"OPEX detail item {item_id!r} cannot be negative.")
        by_category[category] += amount
    for category, detail_total in by_category.items():
        if detail_total <= 0:
            continue
        reported = _number(annual.get(category), 0.0)
        limit = max(1.0, abs(detail_total), abs(reported)) * tolerance
        if abs(reported - detail_total) > limit:
            warnings.append(
                f"OPEX detail for {category} totals {detail_total:.6g} but the annual summary reports {reported:.6g}; annual summary remains authoritative until reconciled."
            )
    return warnings


def prepare_source_summaries(raw_summaries: list[dict] | None) -> tuple[list[dict], list[str]]:
    output = []
    warnings: list[str] = []
    seen_opex_ids: set[str] = set()
    for raw in raw_summaries or []:
        summary = deepcopy(raw or {})
        output.append(summary)
        if not _included(summary):
            continue
        validate_specialist_scope_ownership(summary)
        warnings.extend(validate_opex_detail(summary))
        for item in _opex_items(summary):
            item_id = str((item or {}).get("item_id") or "").strip()
            if item_id in seen_opex_ids:
                raise ValueError(f"Duplicate OPEX economic item {item_id!r}; item IDs must be unique across included summaries.")
            seen_opex_ids.add(item_id)
    return output, warnings
