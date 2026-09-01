"""CAPEX work-breakdown, procurement and construction scheduling.

The WBS is an input/output contract for Total Water Economics.  Parent nodes are
classification/roll-up nodes; only leaf nodes carry cost.  This rule makes the
roll-up invariant explicit and prevents a parent budget from being counted a
second time with its children.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
import math
from typing import Any


SCOPES = {"process", "balance_of_plant", "owner", "excluded"}
SOURCING = {"local", "foreign", "mixed", "not_applicable"}


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("WBS numeric inputs must be finite.")
    return result


def _iso_date(value: Any, field: str) -> str:
    if value in (None, ""):
        return ""
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD).") from exc


def _stable_id(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} is required; stable IDs are never generated during calculation.")
    return result


def _normalize_node(raw: dict, reporting_currency: str) -> dict:
    node_id = _stable_id(raw.get("wbs_id"), "wbs_id")
    scope = str(raw.get("scope") or "process").strip().lower()
    sourcing = str(raw.get("sourcing") or "not_applicable").strip().lower()
    if scope not in SCOPES:
        raise ValueError(f"Unsupported scope for {node_id}: {scope}")
    if sourcing not in SOURCING:
        raise ValueError(f"Unsupported sourcing for {node_id}: {sourcing}")
    currency = str(raw.get("currency") or reporting_currency).strip().upper()
    fx_rate = _number(raw.get("fx_rate"), 1.0 if currency == reporting_currency else 0.0)
    if currency != reporting_currency and fx_rate <= 0:
        raise ValueError(f"WBS item {node_id} requires a positive FX rate for {currency}/{reporting_currency}.")
    cpi_index = str(raw.get("cpi_index") or "").strip()
    cpi_base = _number(raw.get("cpi_base"), 1.0)
    cpi_current = _number(raw.get("cpi_current"), cpi_base)
    if cpi_base <= 0 or cpi_current <= 0:
        raise ValueError(f"WBS item {node_id} CPI values must be positive.")
    quantity = _number(raw.get("quantity"), 1.0)
    unit_cost = _number(raw.get("unit_cost"), 0.0)
    native_amount = _number(raw.get("native_amount"), quantity * unit_cost)
    if min(quantity, unit_cost, native_amount) < 0:
        raise ValueError(f"WBS item {node_id} costs cannot be negative.")
    escalation_factor = cpi_current / cpi_base
    amount = native_amount * escalation_factor * fx_rate
    procurement = deepcopy(raw.get("procurement") or {})
    logistics = deepcopy(raw.get("logistics") or {})
    schedule = deepcopy(raw.get("schedule") or {})
    for key in ("rfq_date", "po_date", "required_on_site_date"):
        procurement[key] = _iso_date(procurement.get(key), f"{node_id} procurement.{key}")
    for key in ("ship_date", "arrival_date"):
        logistics[key] = _iso_date(logistics.get(key), f"{node_id} logistics.{key}")
    schedule["start_date"] = _iso_date(schedule.get("start_date"), f"{node_id} schedule.start_date")
    schedule["duration_days"] = int(_number(schedule.get("duration_days"), 0.0))
    if schedule["duration_days"] < 0:
        raise ValueError(f"WBS item {node_id} schedule duration cannot be negative.")
    return {
        "wbs_id": node_id,
        "parent_wbs_id": str(raw.get("parent_wbs_id") or "").strip(),
        "name": str(raw.get("name") or node_id).strip(),
        "scope": scope,
        "sourcing": sourcing,
        "discipline": str(raw.get("discipline") or "Project").strip(),
        "cost_bucket": str(raw.get("cost_bucket") or "equipment_purchase").strip().lower(),
        "quantity": quantity,
        "unit": str(raw.get("unit") or "LS").strip(),
        "unit_cost": unit_cost,
        "native_amount": native_amount,
        "currency": currency,
        "reporting_currency": reporting_currency,
        "fx_rate": fx_rate,
        "fx_source": str(raw.get("fx_source") or "").strip(),
        "fx_snapshot_id": str(raw.get("fx_snapshot_id") or "").strip(),
        "cpi_index": cpi_index,
        "cpi_base": cpi_base,
        "cpi_current": cpi_current,
        "cpi_factor": escalation_factor,
        "amount": amount,
        "source_type": str(raw.get("source_type") or "user").strip().lower(),
        "source_reference": str(raw.get("source_reference") or "").strip(),
        "source_lineage": deepcopy(raw.get("source_lineage") or {}),
        "procurement": procurement,
        "logistics": logistics,
        "schedule": schedule,
        "notes": str(raw.get("notes") or "").strip(),
    }


def _validate_tree(nodes: list[dict]) -> tuple[dict[str, dict], dict[str, list[str]]]:
    by_id: dict[str, dict] = {}
    children: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        node_id = node["wbs_id"]
        if node_id in by_id:
            raise ValueError(f"Duplicate WBS ID: {node_id}")
        by_id[node_id] = node
    for node in nodes:
        parent = node["parent_wbs_id"]
        if parent:
            if parent not in by_id:
                raise ValueError(f"WBS item {node['wbs_id']} references missing parent {parent}.")
            children[parent].append(node["wbs_id"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise ValueError(f"WBS hierarchy contains a cycle at {node_id}.")
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in children[node_id]:
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in by_id:
        visit(node_id)
    return by_id, children


def _spend_curve(node: dict) -> list[dict]:
    start_text = node["schedule"]["start_date"]
    days = node["schedule"]["duration_days"]
    if not start_text or days <= 0 or node["amount"] <= 0:
        return []
    start = date.fromisoformat(start_text)
    finish = start + timedelta(days=days - 1)
    buckets: list[tuple[str, int]] = []
    cursor = start
    while cursor <= finish:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        segment_end = min(finish + timedelta(days=1), next_month)
        buckets.append((cursor.strftime("%Y-%m"), (segment_end - cursor).days))
        cursor = segment_end
    allocated = 0.0
    curve = []
    for index, (month, bucket_days) in enumerate(buckets):
        amount = node["amount"] - allocated if index == len(buckets) - 1 else node["amount"] * bucket_days / days
        allocated += amount
        curve.append({"month": month, "amount": amount})
    return curve


def analyze_capex_wbs(payload: dict | None, *, reporting_currency: str = "USD") -> dict:
    """Validate and roll up a CAPEX WBS without counting parent nodes twice."""
    raw_nodes = (payload or {}).get("nodes") or []
    if not isinstance(raw_nodes, list):
        raise ValueError("capex_wbs.nodes must be a list.")
    reporting_currency = str(reporting_currency or "USD").upper()
    nodes = [_normalize_node(raw or {}, reporting_currency) for raw in raw_nodes]
    by_id, children = _validate_tree(nodes)
    leaves = [node for node in nodes if not children[node["wbs_id"]]]
    for node in nodes:
        if children[node["wbs_id"]] and node["native_amount"]:
            raise ValueError(f"WBS parent {node['wbs_id']} cannot carry cost; assign cost to leaf nodes to prevent double counting.")

    def descendant_total(node_id: str) -> float:
        return by_id[node_id]["amount"] if not children[node_id] else sum(descendant_total(x) for x in children[node_id])

    rollups = [{
        "wbs_id": node["wbs_id"],
        "parent_wbs_id": node["parent_wbs_id"],
        "name": node["name"],
        "is_leaf": not children[node["wbs_id"]],
        "amount": descendant_total(node["wbs_id"]),
    } for node in nodes]
    roots = [node for node in nodes if not node["parent_wbs_id"]]
    total = sum(descendant_total(node["wbs_id"]) for node in roots)
    by_scope = {key: sum(node["amount"] for node in leaves if node["scope"] == key) for key in sorted(SCOPES)}
    by_sourcing = {key: sum(node["amount"] for node in leaves if node["sourcing"] == key) for key in sorted(SOURCING)}
    spend: dict[str, float] = defaultdict(float)
    scheduled_leaf_total = 0.0
    for node in leaves:
        curve = _spend_curve(node)
        node["schedule"]["spend_curve"] = curve
        if curve:
            scheduled_leaf_total += node["amount"]
        for row in curve:
            spend[row["month"]] += row["amount"]
    warnings = []
    unscheduled = total - scheduled_leaf_total
    if unscheduled > 1e-9:
        warnings.append(f"{unscheduled:.2f} {reporting_currency} of leaf CAPEX is not construction-scheduled.")
    cost_items = [{
        "item_id": node["wbs_id"], "description": node["name"], "bucket": node["cost_bucket"],
        "discipline": node["discipline"], "quantity": 1, "unit": "LS", "unit_cost": node["amount"],
        "amount": node["amount"], "currency": reporting_currency, "native_currency": reporting_currency,
        "source_type": node["source_type"], "source_reference": node["source_reference"],
        "notes": node["notes"], "wbs_id": node["wbs_id"], "source_lineage": node["source_lineage"],
    } for node in leaves if node["scope"] != "excluded"]
    included_total = sum(item["amount"] for item in cost_items)
    return {
        "version": "1.0", "reporting_currency": reporting_currency, "nodes": nodes, "rollups": rollups,
        "leaf_ids": [node["wbs_id"] for node in leaves], "total": total, "included_total": included_total,
        "excluded_total": by_scope["excluded"], "by_scope": by_scope, "by_sourcing": by_sourcing,
        "procurement": [{"wbs_id": n["wbs_id"], **n["procurement"]} for n in leaves],
        "logistics": [{"wbs_id": n["wbs_id"], **n["logistics"]} for n in leaves],
        "construction_schedule": {"monthly_spend": [{"month": key, "amount": spend[key]} for key in sorted(spend)], "scheduled_total": scheduled_leaf_total, "unscheduled_total": unscheduled},
        "cost_items": cost_items, "warnings": warnings,
    }
