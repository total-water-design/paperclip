"""Foundational cost and estimate-maturity engine for Total Economic Design.

This module intentionally does not replace ``economics.py``. The latter is the
validated Total RO Design ERD comparison. Total Economic Design needs a
plant/project-level cost language with provenance, estimate maturity, lifecycle
economics and a controlled path toward project-finance models.

AACE note
---------
The estimate-class recommendation implemented here is a transparent Suite
heuristic informed by AACE International's cost estimate classification
principle that class is driven primarily by maturity/quality of project
definition deliverables. The numerical weights and thresholds below are
Total Water Design Suite implementation choices; they are not presented as
AACE-prescribed percentages or accuracy ranges.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import math
import uuid


BUCKETS = {
    "equipment_purchase": "Purchased Equipment",
    "direct_installation": "Direct Installation",
    "construction_indirect": "Construction Indirects",
    "engineering_procurement": "Engineering / Procurement / PM",
    "owner_cost": "Owner Costs",
    "contingency": "Contingency",
    "escalation": "Escalation",
    "financing": "Financing / IDC",
    "working_capital": "Working Capital",
}

SOURCE_QUALITY = {
    "vendor_quote": ("Vendor quotation", 1.00),
    "subcontractor_quote": ("Subcontractor quotation", 0.95),
    "quantity_takeoff": ("Quantity takeoff / unit rate", 0.85),
    "database": ("Controlled cost database", 0.72),
    "historical": ("Historical project cost", 0.62),
    "capacity_factor": ("Capacity-factor estimate", 0.48),
    "parametric": ("Parametric estimate", 0.38),
    "allowance": ("Explicit allowance / factor", 0.32),
    "user": ("User-entered basis", 0.25),
}

# These are Suite-defined weights, not AACE-prescribed weights.
DEFINITION_DELIVERABLES = {
    "design_basis": ("Design basis", 0.07),
    "process_description": ("Process description", 0.04),
    "process_flow_diagrams": ("Process flow diagrams", 0.07),
    "mass_balance": ("Mass balance", 0.07),
    "equipment_list": ("Equipment list", 0.07),
    "equipment_sizing": ("Equipment sizing", 0.07),
    "major_equipment_pricing": ("Major equipment quotations / pricing", 0.07),
    "site_definition": ("Site definition / plot plan", 0.06),
    "civil_definition": ("Civil / geotechnical definition", 0.07),
    "piping_definition": ("Piping definition", 0.05),
    "electrical_definition": ("Electrical load / SLD definition", 0.05),
    "instrumentation_controls": ("Instrumentation / controls definition", 0.04),
    "execution_plan": ("Execution / constructability plan", 0.06),
    "procurement_strategy": ("Procurement / contracting strategy", 0.05),
    "schedule_maturity": ("Schedule maturity", 0.04),
    "quantity_takeoffs": ("Quantity takeoffs", 0.05),
    "risk_register": ("Risk register", 0.04),
    "escalation_basis": ("Escalation basis", 0.03),
    "contingency_methodology": ("Contingency methodology", 0.03),
}

CRITICAL_FOR_CLASS_3 = (
    "design_basis",
    "process_flow_diagrams",
    "mass_balance",
    "equipment_list",
    "equipment_sizing",
)


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Numeric inputs must be finite.")
    return result


def _clamp01(value: Any) -> float:
    return max(0.0, min(1.0, _number(value, 0.0)))


def _crf(rate: float, years: float) -> float:
    if years <= 0:
        raise ValueError("Project life / tenor must be greater than zero.")
    if abs(rate) < 1e-12:
        return 1.0 / years
    return rate * (1.0 + rate) ** years / ((1.0 + rate) ** years - 1.0)


def _pv_annuity(rate: float, years: float) -> float:
    if years <= 0:
        raise ValueError("Project life must be greater than zero.")
    if abs(rate) < 1e-12:
        return years
    return (1.0 - (1.0 + rate) ** (-years)) / rate


@dataclass(frozen=True)
class CostItem:
    item_id: str
    description: str
    bucket: str
    discipline: str
    quantity: float
    unit: str
    unit_cost: float
    amount: float
    source_type: str
    source_reference: str
    vendor: str
    quote_date: str
    currency: str
    notes: str

    @classmethod
    def from_payload(cls, data: dict, *, default_currency: str = "USD") -> "CostItem":
        bucket = str(data.get("bucket") or "").strip().lower()
        if bucket not in BUCKETS:
            raise ValueError(f"Unsupported cost bucket: {bucket or '(blank)'}")
        quantity = _number(data.get("quantity"), 1.0)
        unit_cost = _number(data.get("unit_cost"), 0.0)
        explicit_amount = data.get("amount")
        amount = _number(explicit_amount, quantity * unit_cost) if explicit_amount not in (None, "") else quantity * unit_cost
        if quantity < 0 or unit_cost < 0 or amount < 0:
            raise ValueError("Cost quantities and amounts cannot be negative.")
        source_type = str(data.get("source_type") or "user").strip().lower()
        if source_type not in SOURCE_QUALITY:
            source_type = "user"
        return cls(
            item_id=str(data.get("item_id") or uuid.uuid4().hex[:10]),
            description=str(data.get("description") or BUCKETS[bucket]).strip(),
            bucket=bucket,
            discipline=str(data.get("discipline") or "").strip(),
            quantity=quantity,
            unit=str(data.get("unit") or "LS").strip(),
            unit_cost=unit_cost,
            amount=amount,
            source_type=source_type,
            source_reference=str(data.get("source_reference") or "").strip(),
            vendor=str(data.get("vendor") or "").strip(),
            quote_date=str(data.get("quote_date") or "").strip(),
            currency=str(data.get("currency") or default_currency).strip().upper(),
            notes=str(data.get("notes") or "").strip(),
        )


def _add_allowance(items: list[CostItem], bucket: str, amount: float, description: str, reference: str, currency: str) -> None:
    if amount <= 0:
        return
    items.append(CostItem(
        item_id=f"allowance-{bucket}",
        description=description,
        bucket=bucket,
        discipline="Allowance",
        quantity=1.0,
        unit="LS",
        unit_cost=amount,
        amount=amount,
        source_type="allowance",
        source_reference=reference,
        vendor="",
        quote_date="",
        currency=currency,
        notes="Generated from an explicit user-entered allowance. Replace with detailed cost definition as estimate maturity improves.",
    ))


def _build_cost_items(payload: dict, currency: str) -> tuple[list[CostItem], list[str]]:
    raw = payload.get("cost_items") or []
    if not isinstance(raw, list):
        raise ValueError("cost_items must be a list.")
    items = [CostItem.from_payload(x or {}, default_currency=currency) for x in raw]
    notes: list[str] = []

    explicit = {bucket: sum(x.amount for x in items if x.bucket == bucket) for bucket in BUCKETS}
    allowances = payload.get("allowances") or {}
    equipment = explicit["equipment_purchase"]
    direct_install = explicit["direct_installation"]
    total_direct = equipment + direct_install

    if explicit["construction_indirect"] <= 0:
        pct = _number(allowances.get("construction_indirect_pct"), 0.0) / 100.0
        _add_allowance(items, "construction_indirect", total_direct * pct,
                       "Construction indirect allowance",
                       f"{pct * 100:.2f}% of Total Direct Cost", currency)

    after_ci = total_direct + sum(x.amount for x in items if x.bucket == "construction_indirect")
    if explicit["engineering_procurement"] <= 0:
        pct = _number(allowances.get("engineering_procurement_pct"), 0.0) / 100.0
        _add_allowance(items, "engineering_procurement", after_ci * pct,
                       "Engineering / procurement / PM allowance",
                       f"{pct * 100:.2f}% of TIC", currency)

    after_ep = after_ci + sum(x.amount for x in items if x.bucket == "engineering_procurement")
    if explicit["owner_cost"] <= 0:
        pct = _number(allowances.get("owner_cost_pct"), 0.0) / 100.0
        _add_allowance(items, "owner_cost", after_ep * pct,
                       "Owner cost allowance",
                       f"{pct * 100:.2f}% of TIC + E/P/PM", currency)

    before_contingency = after_ep + sum(x.amount for x in items if x.bucket == "owner_cost")
    if explicit["contingency"] <= 0:
        pct = _number(allowances.get("contingency_pct"), 0.0) / 100.0
        _add_allowance(items, "contingency", before_contingency * pct,
                       "Estimate contingency allowance",
                       f"{pct * 100:.2f}% of Project Cost Before Contingency", currency)

    before_escalation = before_contingency + sum(x.amount for x in items if x.bucket == "contingency")
    if explicit["escalation"] <= 0:
        pct = _number(allowances.get("escalation_pct"), 0.0) / 100.0
        _add_allowance(items, "escalation", before_contingency * pct,
                       "Escalation allowance",
                       f"{pct * 100:.2f}% of Project Cost Before Contingency", currency)
        if pct > 0:
            notes.append("Escalation currently uses an explicit percentage allowance. Replace it with schedule-linked escalation when a spend curve is available.")

    total_project = before_escalation + sum(x.amount for x in items if x.bucket == "escalation")
    if explicit["financing"] <= 0:
        pct = _number(allowances.get("financing_pct"), 0.0) / 100.0
        _add_allowance(items, "financing", total_project * pct,
                       "Financing / IDC allowance",
                       f"{pct * 100:.2f}% of Total Project Cost", currency)
        if pct > 0:
            notes.append("Financing / IDC is a simple allowance in this milestone. Replace it with time-phased debt draws for project-finance use.")

    if explicit["working_capital"] <= 0:
        pct = _number(allowances.get("working_capital_pct"), 0.0) / 100.0
        _add_allowance(items, "working_capital", total_project * pct,
                       "Working capital allowance",
                       f"{pct * 100:.2f}% of Total Project Cost", currency)

    return items, notes


def _cost_hierarchy(items: list[CostItem]) -> dict:
    by_bucket = {bucket: sum(x.amount for x in items if x.bucket == bucket) for bucket in BUCKETS}
    purchased = by_bucket["equipment_purchase"]
    direct_install = by_bucket["direct_installation"]
    total_direct = purchased + direct_install
    construction_indirect = by_bucket["construction_indirect"]
    tic = total_direct + construction_indirect
    ep_pm = by_bucket["engineering_procurement"]
    owner = by_bucket["owner_cost"]
    before_contingency = tic + ep_pm + owner
    contingency = by_bucket["contingency"]
    escalation = by_bucket["escalation"]
    total_project = before_contingency + contingency + escalation
    financing = by_bucket["financing"]
    working_capital = by_bucket["working_capital"]
    total_capital = total_project + financing + working_capital
    return {
        "by_bucket": by_bucket,
        "purchased_equipment_cost": purchased,
        "direct_installation_cost": direct_install,
        "total_direct_cost": total_direct,
        "construction_indirect_cost": construction_indirect,
        "total_installed_cost": tic,
        "engineering_procurement_pm": ep_pm,
        "owner_costs": owner,
        "project_cost_before_contingency": before_contingency,
        "contingency": contingency,
        "escalation": escalation,
        "total_project_cost": total_project,
        "financing_idc": financing,
        "working_capital": working_capital,
        "total_capital_requirement": total_capital,
    }


def _source_quality(items: list[CostItem]) -> dict:
    total = sum(x.amount for x in items)
    if total <= 0:
        return {"weighted_score": 0.0, "label": "No cost basis", "distribution": []}
    distribution = []
    weighted = 0.0
    for key, (label, score) in SOURCE_QUALITY.items():
        amount = sum(x.amount for x in items if x.source_type == key)
        if amount <= 0:
            continue
        weighted += amount * score
        distribution.append({
            "source_type": key,
            "label": label,
            "amount": amount,
            "share": amount / total,
            "quality_score": score,
        })
    weighted_score = weighted / total
    if weighted_score >= 0.85:
        label = "Strong quotation / quantity basis"
    elif weighted_score >= 0.65:
        label = "Developing estimate basis"
    elif weighted_score >= 0.45:
        label = "Preliminary estimate basis"
    else:
        label = "Conceptual / allowance-heavy basis"
    return {"weighted_score": weighted_score, "label": label, "distribution": distribution}


def assess_estimate_maturity(definition: dict | None) -> dict:
    definition = definition or {}
    weighted = 0.0
    total_weight = sum(weight for _, weight in DEFINITION_DELIVERABLES.values())
    rows = []
    for key, (label, weight) in DEFINITION_DELIVERABLES.items():
        maturity = _clamp01(definition.get(key, 0.0))
        weighted += maturity * weight
        rows.append({
            "key": key,
            "label": label,
            "weight": weight / total_weight,
            "maturity": maturity,
            "gap_priority": (1.0 - maturity) * weight,
        })
    score = weighted / total_weight if total_weight else 0.0
    critical_min = min((_clamp01(definition.get(k, 0.0)) for k in CRITICAL_FOR_CLASS_3), default=0.0)

    if score >= 0.86 and critical_min >= 0.75:
        estimate_class = "Class 1"
    elif score >= 0.72 and critical_min >= 0.60:
        estimate_class = "Class 2"
    elif score >= 0.52 and critical_min >= 0.50:
        estimate_class = "Class 3"
    elif score >= 0.28:
        estimate_class = "Class 4"
    else:
        estimate_class = "Class 5"

    next_steps = sorted(rows, key=lambda x: x["gap_priority"], reverse=True)
    next_steps = [x for x in next_steps if x["maturity"] < 0.999][:5]
    return {
        "recommended_class": estimate_class,
        "definition_maturity_score": score,
        "critical_definition_floor": critical_min,
        "deliverables": rows,
        "next_steps": next_steps,
        "method_note": (
            "Class recommendation is a Total Water Design Suite maturity heuristic informed by "
            "AACE cost-estimate classification principles. It uses the maturity and quality of "
            "specific project-definition deliverables, not percent design completion. The Suite "
            "weights/thresholds are not AACE-prescribed accuracy ranges."
        ),
        "reference": "AACE International RP 18R-97, Cost Estimate Classification System — Process Industries (rev. Aug. 7, 2020).",
    }


def _operating_economics(payload: dict, capital: float) -> dict:
    op = payload.get("operating") or {}
    capacity = _number(op.get("capacity_m3d", payload.get("project", {}).get("capacity_m3d")), 0.0)
    availability = _number(op.get("availability"), 0.95)
    if capacity < 0 or not (0 < availability <= 1):
        raise ValueError("Capacity must be non-negative and availability must be between 0 and 1.")
    annual_product = capacity * 365.0 * availability
    fixed = _number(op.get("fixed_opex_y"), 0.0)
    other = _number(op.get("other_opex_y"), 0.0)
    variable_per_m3 = _number(op.get("variable_opex_m3"), 0.0)
    energy_kwh_m3 = _number(op.get("energy_kwh_m3"), 0.0)
    power_price = _number(op.get("electricity_price_kwh"), 0.0)
    annual_variable = annual_product * variable_per_m3
    annual_energy = annual_product * energy_kwh_m3 * power_price
    annual_opex = fixed + other + annual_variable + annual_energy

    life = _number(op.get("project_life_years"), 25.0)
    discount = _number(op.get("discount_rate"), 0.06)
    crf = _crf(discount, life)
    pvaf = _pv_annuity(discount, life)
    annualized_capital = capital * crf
    lcow = (annualized_capital + annual_opex) / annual_product if annual_product > 0 else None
    lifecycle_npv = capital + annual_opex * pvaf
    return {
        "capacity_m3d": capacity,
        "availability": availability,
        "annual_product_m3": annual_product,
        "fixed_opex_y": fixed,
        "variable_opex_y": annual_variable,
        "energy_opex_y": annual_energy,
        "other_opex_y": other,
        "annual_opex_y": annual_opex,
        "project_life_years": life,
        "discount_rate": discount,
        "annualized_capital_y": annualized_capital,
        "lifecycle_cost_npv": lifecycle_npv,
        "lcow": lcow,
    }


def _finance_metrics(payload: dict, capital: float, operating: dict) -> dict:
    fin = payload.get("finance") or {}
    debt_fraction = _number(fin.get("debt_fraction"), 0.70)
    if not (0 <= debt_fraction <= 1):
        raise ValueError("Debt fraction must be between 0 and 1.")
    rate = _number(fin.get("interest_rate"), 0.06)
    tenor = _number(fin.get("debt_tenor_years"), 20.0)
    target_dscr = _number(fin.get("target_dscr"), 1.30)
    tariff = _number(fin.get("tariff_m3"), 0.0)

    debt = capital * debt_fraction
    equity = capital - debt
    annual_debt_service = debt * _crf(rate, tenor) if debt > 0 else 0.0
    annual_product = operating["annual_product_m3"]
    revenue = annual_product * tariff
    cfads = revenue - operating["annual_opex_y"]
    dscr = (cfads / annual_debt_service) if annual_debt_service > 0 else None
    required_tariff = None
    if annual_product > 0:
        required_tariff = (
            operating["annual_opex_y"] + target_dscr * annual_debt_service
        ) / annual_product
    return {
        "debt_fraction": debt_fraction,
        "debt_amount": debt,
        "equity_amount": equity,
        "interest_rate": rate,
        "debt_tenor_years": tenor,
        "annual_debt_service": annual_debt_service,
        "tariff_m3": tariff,
        "annual_revenue": revenue,
        "cash_flow_available_for_debt_service": cfads,
        "dscr": dscr,
        "target_dscr": target_dscr,
        "required_tariff_for_target_dscr": required_tariff,
        "method_note": (
            "This milestone uses level annual debt service. Interest during construction remains "
            "an explicit estimate line/allowance until schedule-linked debt draws are implemented."
        ),
    }


def default_payload() -> dict:
    return {
        "project": {
            "project_name": "New Water Infrastructure Project",
            "estimate_id": "E01",
            "location": "",
            "currency": "USD",
            "capacity_m3d": 100000,
            "delivery_method": "Progressive Design-Build",
            "base_date": "",
            "estimate_date": "",
        },
        "cost_items": [
            {"item_id": "eq-001", "description": "Process equipment", "bucket": "equipment_purchase", "discipline": "Process", "quantity": 1, "unit": "LS", "unit_cost": 65000000, "source_type": "database", "source_reference": "Replace with vendor/package pricing"},
            {"item_id": "di-001", "description": "Mechanical / piping / civil / E&I installation", "bucket": "direct_installation", "discipline": "Construction", "quantity": 1, "unit": "LS", "unit_cost": 52000000, "source_type": "parametric", "source_reference": "Conceptual installed-cost allowance"},
        ],
        "allowances": {
            "construction_indirect_pct": 12,
            "engineering_procurement_pct": 10,
            "owner_cost_pct": 5,
            "contingency_pct": 20,
            "escalation_pct": 0,
            "financing_pct": 0,
            "working_capital_pct": 0,
        },
        "definition": {
            "design_basis": 0.75,
            "process_description": 0.75,
            "process_flow_diagrams": 0.50,
            "mass_balance": 0.50,
            "equipment_list": 0.50,
            "equipment_sizing": 0.50,
            "major_equipment_pricing": 0.25,
            "site_definition": 0.25,
            "civil_definition": 0.25,
            "piping_definition": 0.25,
            "electrical_definition": 0.25,
            "instrumentation_controls": 0.25,
            "execution_plan": 0.25,
            "procurement_strategy": 0.50,
            "schedule_maturity": 0.25,
            "quantity_takeoffs": 0.0,
            "risk_register": 0.25,
            "escalation_basis": 0.25,
            "contingency_methodology": 0.50,
        },
        "operating": {
            "capacity_m3d": 100000,
            "availability": 0.95,
            "fixed_opex_y": 3500000,
            "variable_opex_m3": 0.16,
            "energy_kwh_m3": 3.2,
            "electricity_price_kwh": 0.09,
            "other_opex_y": 0,
            "project_life_years": 25,
            "discount_rate": 0.06,
        },
        "finance": {
            "debt_fraction": 0.70,
            "interest_rate": 0.06,
            "debt_tenor_years": 20,
            "target_dscr": 1.30,
            "tariff_m3": 1.35,
        },
        "reconciliation": {
            "prior_estimate_id": "",
            "prior_total_project_cost": None,
            "change_summary": "",
        },
    }


def analyze_estimate(payload: dict | None) -> dict:
    payload = payload or {}
    project = dict(default_payload()["project"])
    project.update(payload.get("project") or {})
    currency = str(project.get("currency") or "USD").upper()

    items, methodology_notes = _build_cost_items(payload, currency)
    hierarchy = _cost_hierarchy(items)
    maturity = assess_estimate_maturity(payload.get("definition") or {})
    provenance = _source_quality(items)
    operating = _operating_economics(payload, hierarchy["total_project_cost"])
    finance = _finance_metrics(payload, hierarchy["total_capital_requirement"], operating)

    prior = payload.get("reconciliation") or {}
    prior_total = prior.get("prior_total_project_cost")
    if prior_total in (None, ""):
        reconciliation = {
            "prior_estimate_id": str(prior.get("prior_estimate_id") or ""),
            "prior_total_project_cost": None,
            "movement": None,
            "movement_pct": None,
            "change_summary": str(prior.get("change_summary") or ""),
        }
    else:
        prior_total = _number(prior_total)
        movement = hierarchy["total_project_cost"] - prior_total
        reconciliation = {
            "prior_estimate_id": str(prior.get("prior_estimate_id") or ""),
            "prior_total_project_cost": prior_total,
            "movement": movement,
            "movement_pct": movement / prior_total if prior_total else None,
            "change_summary": str(prior.get("change_summary") or ""),
        }

    return {
        "application": "Total Economic Design",
        "engine_version": "0.1",
        "project": project,
        "estimate": {
            "estimate_id": str(project.get("estimate_id") or "E01"),
            "recommended_class": maturity["recommended_class"],
            "currency": currency,
        },
        "cost_items": [asdict(x) for x in items],
        "cost_hierarchy": hierarchy,
        "maturity": maturity,
        "provenance": provenance,
        "operating": operating,
        "finance": finance,
        "reconciliation": reconciliation,
        "methodology_notes": methodology_notes,
        "terminology": {
            "tic": "Total Installed Cost = Total Direct Cost + Construction Indirects.",
            "total_project_cost": "Total Project Cost = TIC + E/P/PM + Owner Costs + Contingency + Escalation.",
            "total_capital_requirement": "Total Capital Requirement = Total Project Cost + Financing/IDC + Working Capital.",
        },
    }
