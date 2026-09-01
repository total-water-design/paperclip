"""Project-level aggregation layer for Total Water Economics.

This module consumes zero, one, or many specialist application economic
summaries. Specialist applications remain authoritative for their own process
scope; Total Water Economics adds project-level allowances, lifecycle economics
and the optional time-phased project-finance / BOOT layer.
"""
from __future__ import annotations

from copy import deepcopy

import economic_summary_contract as economic_contract
from economic_cost_schema import canonicalize_cost_items
from economic_guardrails import install_contract_extensions, prepare_source_summaries
from economic_risk_costs import analyze_risk_costs
from project_finance import analyze_project_finance
from total_economic_design import analyze_estimate
from capex_wbs import analyze_capex_wbs

install_contract_extensions(economic_contract)


def _prepared_local_cost_items(raw_items: list[dict], project: dict) -> tuple[list[dict], dict]:
    """Canonicalize local costs and apply only explicit, provenance-backed FX."""
    reporting_currency = str(project.get("currency") or "USD").upper()
    context = {
        "currency": reporting_currency,
        "base_date": project.get("base_date") or "",
        "location": project.get("location") or "",
        "project_id": project.get("project_id") or "",
        "project_revision": project.get("revision") or "",
        "estimate_id": project.get("estimate_id") or "",
        "estimate_revision": project.get("estimate_revision") or project.get("revision") or "",
    }
    package = canonicalize_cost_items(
        raw_items,
        default_currency=reporting_currency,
        project_context=context,
    )
    lineage = []
    for item in package["items"]:
        if item["native_currency"] != item["reporting_currency"]:
            lineage.append({
                "item_id": item["item_id"],
                "native_amount": item["native_amount"],
                "native_currency": item["native_currency"],
                "converted_amount": item["amount"],
                "reporting_currency": item["reporting_currency"],
                "fx_rate": item["fx_rate"],
                "fx_source": item["fx_source"],
                "fx_snapshot_id": item["fx_snapshot_id"],
            })
    return package["items"], {
        "schema_id": package["schema_id"],
        "schema_version": package["schema_version"],
        "cbs_system": package["cbs_system"],
        "currency_lineage": lineage,
        "warnings": package["warnings"],
    }


def _add_finance_warning(project_finance: dict, message: str) -> None:
    project_finance.setdefault("warnings", []).append(message)
    project_finance.setdefault("limitations", []).insert(0, message)


def _finance_reconciliation(request: dict, result: dict, project_finance: dict) -> None:
    project_finance["version"] = "0.2"
    project_finance.setdefault("warnings", [])
    project_finance.setdefault("limitations", [])
    if not project_finance.get("enabled"):
        return
    hierarchy = result.get("cost_hierarchy") or {}
    allowances = request.get("allowances") if isinstance(request.get("allowances"), dict) else {}
    legacy_financing = float(hierarchy.get("financing_idc") or 0.0)
    legacy_working_capital = float(hierarchy.get("working_capital") or 0.0)
    construction = project_finance.get("construction") or {}
    advanced_funding = float(
        construction.get("funding_requirement_including_initial_dsra")
        or construction.get("total_funding_requirement")
        or 0.0
    )
    project_finance["capital_reconciliation"] = {
        "foundational_total_project_cost": float(hierarchy.get("total_project_cost") or 0.0),
        "foundational_financing_idc_allowance": legacy_financing,
        "foundational_working_capital_allowance": legacy_working_capital,
        "foundational_total_capital_requirement": float(hierarchy.get("total_capital_requirement") or 0.0),
        "advanced_construction_funding_requirement": advanced_funding,
        "advanced_initial_dsra": float(construction.get("initial_dsra") or 0.0),
        "note": (
            "Advanced construction funding is a separate time-phased financing view. "
            "It is not added on top of the foundational Total Capital Requirement."
        ),
    }
    if legacy_financing > 0 or float(allowances.get("financing_pct") or 0.0) > 0:
        _add_finance_warning(
            project_finance,
            "Time-phased project finance is enabled while a foundational Financing/IDC allowance is also present. "
            "Use the advanced construction IDC for finance decisions; do not add both financing amounts together.",
        )
    if legacy_working_capital > 0 or float(allowances.get("working_capital_pct") or 0.0) > 0:
        _add_finance_warning(
            project_finance,
            "Time-phased project finance is enabled while a foundational Working Capital allowance is also present. "
            "The advanced model calculates operating working-capital movements from receivable/inventory/payable days; reconcile the conceptual allowance before relying on Total Capital Requirement.",
        )


def analyze_total_economic_design(payload: dict | None) -> dict:
    request = deepcopy(payload or {})
    project = request.get("project") if isinstance(request.get("project"), dict) else {}
    operating = request.get("operating") if isinstance(request.get("operating"), dict) else {}
    project_currency = str(project.get("currency") or "USD").upper()
    electricity_price = float(operating.get("electricity_price_kwh") or 0.0)

    raw_sources, guard_warnings = prepare_source_summaries(request.get("source_summaries") or [])
    aggregation = economic_contract.aggregate_summaries(
        raw_sources,
        project_currency=project_currency,
        electricity_price_kwh=electricity_price,
    )
    aggregation["warnings"] = guard_warnings + list(aggregation.get("warnings") or [])

    wbs = analyze_capex_wbs(request.get("capex_wbs") or {}, reporting_currency=project_currency)
    local_items = request.get("cost_items") or []
    if not isinstance(local_items, list):
        raise ValueError("cost_items must be a list.")
    prepared_local, cost_schema = _prepared_local_cost_items(list(local_items) + wbs["cost_items"], project)
    request["cost_items"] = list(aggregation["cost_items"]) + prepared_local

    risk_costs = analyze_risk_costs(request.get("risk_costs") or {})
    if risk_costs["capitalized_total"] > 0:
        request["cost_items"].append({
            "item_id": "tweco-d-capitalized-risk-costs",
            "description": "Land, ROW, insurance and guarantee capitalized costs",
            "bucket": "owner_cost",
            "discipline": "Project development",
            "quantity": 1,
            "unit": "LS",
            "unit_cost": risk_costs["capitalized_total"],
            "amount": risk_costs["capitalized_total"],
            "source_type": "user",
            "source_reference": "twds.risk_cost_schedule v1.0",
            "currency": project_currency,
            "notes": "Aggregate of explicitly modeled capitalized TWECO-D schedule rows.",
        })

    op = dict(operating)
    manual_other = float(op.get("other_opex_y") or 0.0)
    op["other_opex_y"] = manual_other + aggregation["annual_opex_total"] + risk_costs["annual_opex_steady_state"]
    if op.get("capacity_m3d") in (None, "", 0, 0.0):
        op["capacity_m3d"] = project.get("capacity_m3d") or 0.0
    request["operating"] = op

    result = analyze_estimate(request)
    result["engine_version"] = "0.2"
    result["source_aggregation"] = aggregation
    result["project_cost_schema"] = cost_schema
    result["project_cost_currency_lineage"] = cost_schema["currency_lineage"]
    result["capex_wbs"] = {key: value for key, value in wbs.items() if key != "cost_items"}
    result["risk_costs"] = risk_costs
    result["methodology_notes"] = list(result.get("methodology_notes") or []) + wbs["warnings"]
    if cost_schema["warnings"]:
        result.setdefault("methodology_notes", []).extend(cost_schema["warnings"])

    source_total = aggregation["annual_opex_total"]
    result["operating"]["source_application_opex_y"] = source_total
    result["operating"]["source_opex_breakdown"] = aggregation["opex"]
    result["operating"]["project_level_opex_y"] = result["operating"]["annual_opex_y"] - source_total
    result["operating"]["risk_cost_opex_y"] = risk_costs["annual_opex_steady_state"]
    result["operating"]["combined_annual_cost_y"] = (
        result["operating"]["annualized_capital_y"] + result["operating"]["annual_opex_y"]
    )

    result["integration"] = {
        "mode": "single_application" if aggregation["source_count"] == 1 else (
            "combined_applications" if aggregation["source_count"] > 1 else "manual_project_estimate"
        ),
        "application_count": aggregation["source_count"],
        "source_capex": aggregation["capex_total"],
        "source_annual_opex": aggregation["annual_opex_total"],
        "principle": (
            "Specialist applications contribute their own scope CAPEX/OPEX. Total Water Economics "
            "combines selected scopes and applies project-level cost, annualization and finance logic."
        ),
    }

    result["project_finance"] = analyze_project_finance(request, result)
    _finance_reconciliation(request, result, result["project_finance"])
    return result
