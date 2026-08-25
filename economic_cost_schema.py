"""Canonical cost-item schema and Cost Breakdown Structure for Total Economic Design.

This module defines the economic data object that carries a cost from its
engineering/source basis into project-level estimating.  It deliberately keeps
cost classification, currency conversion, estimate context, and provenance
separate so later estimate revisions remain auditable.

The TWDS CBS codes defined here are Suite conventions, not AACE or DBIA codes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math
import uuid

SCHEMA_ID = "twds.cost_item"
SCHEMA_VERSION = "1.0"

COST_BREAKDOWN_STRUCTURE = {
    "equipment_purchase": {
        "code": "1000",
        "label": "Purchased Equipment",
        "definition": "Purchase price of permanent equipment before field installation.",
    },
    "direct_installation": {
        "code": "2000",
        "label": "Direct Installation",
        "definition": "Direct field installation costs such as mechanical, piping, civil, structural, electrical, instrumentation and controls.",
    },
    "construction_indirect": {
        "code": "3000",
        "label": "Construction Indirects",
        "definition": "Temporary facilities, field supervision, construction management, safety, QA/QC, mobilization and other construction indirects.",
    },
    "engineering_procurement": {
        "code": "4000",
        "label": "Engineering / Procurement / PM",
        "definition": "Project engineering, procurement, vendor management, project management and document-control costs.",
    },
    "owner_cost": {
        "code": "5000",
        "label": "Owner Costs",
        "definition": "Owner-side development, permitting, legal, land, environmental, owner engineering and owner project-management costs.",
    },
    "contingency": {
        "code": "6000",
        "label": "Contingency",
        "definition": "Explicit estimate contingency or risk allowance; kept separate from escalation.",
    },
    "escalation": {
        "code": "7000",
        "label": "Escalation",
        "definition": "Time-related cost escalation from a stated price/base date to the applicable expenditure date.",
    },
    "financing": {
        "code": "8000",
        "label": "Financing / IDC",
        "definition": "Financing fees and interest during construction or other capitalized financing costs.",
    },
    "working_capital": {
        "code": "9000",
        "label": "Working Capital",
        "definition": "Initial working-capital funding required in addition to project cost.",
    },
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

SOURCE_TYPE_ALIASES = {
    "vendor": "vendor_quote",
    "supplier_quote": "vendor_quote",
    "subcontract_quote": "subcontractor_quote",
    "quantity": "quantity_takeoff",
    "controlled_database": "database",
    "project_history": "historical",
    "factor": "allowance",
    "user_entered_estimate": "user",
    "user-entered-estimate": "user",
    "user entered estimate": "user",
}

# Required provenance is deliberately source-specific. Missing fields do not
# invalidate conceptual estimates; they lower provenance completeness and
# create explicit warnings so early estimates can mature without hiding gaps.
PROVENANCE_REQUIRED = {
    "vendor_quote": ("source_reference", "vendor", "quote_date", "price_date"),
    "subcontractor_quote": ("source_reference", "vendor", "quote_date", "price_date"),
    "quantity_takeoff": ("source_reference", "price_date"),
    "database": ("source_reference", "price_date"),
    "historical": ("source_reference", "price_date", "location"),
    "capacity_factor": ("source_reference", "base_date"),
    "parametric": ("source_reference", "base_date"),
    "allowance": ("source_reference",),
    "user": ("source_reference",),
}


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Cost-item numeric values must be finite.")
    return result


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_source_type(value: Any) -> tuple[str, str]:
    original = _text(value or "user").lower()
    canonical = SOURCE_TYPE_ALIASES.get(original, original)
    if canonical not in SOURCE_QUALITY:
        canonical = "user"
    return canonical, original


@dataclass(frozen=True)
class CanonicalCostItem:
    schema_id: str
    schema_version: str
    item_id: str
    scope_key: str
    description: str
    bucket: str
    cbs_system: str
    cbs_code: str
    discipline: str
    quantity: float
    unit: str
    native_unit_cost: float
    native_amount: float
    native_currency: str
    fx_rate: float
    fx_source: str
    fx_snapshot_id: str
    unit_cost: float
    amount: float
    currency: str
    reporting_currency: str
    source_type: str
    source_type_original: str
    source_quality_score: float
    source_reference: str
    source_document_id: str
    vendor: str
    quote_number: str
    quote_date: str
    price_date: str
    base_date: str
    location: str
    escalation_index_name: str
    escalation_index_value: float | None
    escalation_index_date: str
    source_application: str
    source_project_id: str
    source_project_revision: str
    source_scenario_id: str
    source_calculation_revision: str
    source_summary_id: str
    estimate_id: str
    estimate_revision: str
    estimate_class_context: str
    cost_basis: str
    notes: str

    def to_dict(self) -> dict:
        data = asdict(self)
        # Compatibility alias used by the existing economics engine/contract.
        data["converted_amount"] = self.amount
        return data


def assess_provenance(item: CanonicalCostItem | dict) -> dict:
    data = item.to_dict() if isinstance(item, CanonicalCostItem) else dict(item or {})
    source_type, _ = normalize_source_type(data.get("source_type"))
    required = PROVENANCE_REQUIRED[source_type]
    missing = [field for field in required if data.get(field) in (None, "")]
    score = 1.0 if not required else (len(required) - len(missing)) / len(required)

    if score >= 0.999:
        label = "Complete for source type"
    elif score >= 0.75:
        label = "Minor provenance gaps"
    elif score >= 0.50:
        label = "Material provenance gaps"
    else:
        label = "Weak provenance"

    warnings = []
    if missing:
        warnings.append(
            f"{data.get('item_id') or '(unidentified item)'}: {source_type} basis is missing "
            + ", ".join(missing)
            + "."
        )
    if _text(data.get("native_currency")) != _text(data.get("reporting_currency")):
        if data.get("fx_rate") in (None, "") or not _text(data.get("fx_source")):
            warnings.append(
                f"{data.get('item_id') or '(unidentified item)'}: cross-currency cost lacks complete FX provenance."
            )

    return {
        "source_type": source_type,
        "source_label": SOURCE_QUALITY[source_type][0],
        "source_quality_score": SOURCE_QUALITY[source_type][1],
        "required_fields": list(required),
        "missing_fields": missing,
        "completeness_score": score,
        "label": label,
        "is_complete": not missing,
        "warnings": warnings,
    }


def canonicalize_cost_item(
    raw: dict | None,
    *,
    default_currency: str = "USD",
    project_context: dict | None = None,
) -> dict:
    raw = dict(raw or {})
    context = dict(project_context or {})

    bucket = _text(raw.get("bucket")).lower()
    if bucket not in COST_BREAKDOWN_STRUCTURE:
        raise ValueError(f"Unsupported cost bucket: {bucket or '(blank)'}")

    quantity = _number(raw.get("quantity"), 1.0)
    native_unit_cost = _number(
        raw.get("native_unit_cost"),
        raw.get("unit_cost") if raw.get("unit_cost") not in (None, "") else 0.0,
    )
    explicit_native_amount = raw.get("native_amount")
    if explicit_native_amount in (None, ""):
        explicit_native_amount = raw.get("amount")
    native_amount = (
        _number(explicit_native_amount)
        if explicit_native_amount not in (None, "")
        else quantity * native_unit_cost
    )
    if quantity < 0 or native_unit_cost < 0 or native_amount < 0:
        raise ValueError("Cost quantities and amounts cannot be negative.")

    native_currency = _text(
        raw.get("native_currency") or raw.get("currency") or default_currency
    ).upper()
    reporting_currency = _text(
        raw.get("reporting_currency") or context.get("currency") or default_currency
    ).upper()
    if not native_currency or not reporting_currency:
        raise ValueError("Native and reporting currency are required.")

    fx_source = _text(raw.get("fx_source"))
    fx_snapshot_id = _text(raw.get("fx_snapshot_id"))
    converted_amount_input = raw.get("converted_amount")
    fx_rate_input = raw.get("fx_rate")

    if native_currency == reporting_currency:
        fx_rate = 1.0
        fx_source = fx_source or "identity"
        amount = native_amount
        if converted_amount_input not in (None, ""):
            stated = _number(converted_amount_input)
            tolerance = max(0.01, abs(native_amount) * 1e-9)
            if abs(stated - native_amount) > tolerance:
                raise ValueError("Identity-currency converted_amount must equal native_amount.")
    else:
        if fx_rate_input in (None, ""):
            raise ValueError(
                f"Explicit fx_rate is required to convert {native_currency} to {reporting_currency}."
            )
        fx_rate = _number(fx_rate_input)
        if fx_rate <= 0:
            raise ValueError("fx_rate must be greater than zero.")
        if not fx_source:
            raise ValueError("fx_source is required for cross-currency cost conversion.")
        computed = native_amount * fx_rate
        if converted_amount_input in (None, ""):
            amount = computed
        else:
            amount = _number(converted_amount_input)
            tolerance = max(0.01, abs(computed) * 1e-8)
            if abs(amount - computed) > tolerance:
                raise ValueError(
                    "converted_amount is inconsistent with native_amount × fx_rate."
                )

    unit_cost = amount / quantity if quantity > 0 else 0.0
    source_type, source_type_original = normalize_source_type(raw.get("source_type"))

    cbs_system = _text(raw.get("cbs_system") or "TWDS-CBS-1.0")
    cbs_code = _text(raw.get("cbs_code") or COST_BREAKDOWN_STRUCTURE[bucket]["code"])
    if cbs_system == "TWDS-CBS-1.0":
        expected_family = COST_BREAKDOWN_STRUCTURE[bucket]["code"][0]
        if not cbs_code.startswith(expected_family):
            raise ValueError(
                f"CBS code {cbs_code!r} is inconsistent with bucket {bucket!r} under TWDS-CBS-1.0."
            )

    escalation_index_value = raw.get("escalation_index_value")
    if escalation_index_value in (None, ""):
        escalation_value = None
    else:
        escalation_value = _number(escalation_index_value)

    item = CanonicalCostItem(
        schema_id=SCHEMA_ID,
        schema_version=SCHEMA_VERSION,
        item_id=_text(raw.get("item_id") or uuid.uuid4().hex[:12]),
        scope_key=_text(raw.get("scope_key")),
        description=_text(raw.get("description") or COST_BREAKDOWN_STRUCTURE[bucket]["label"]),
        bucket=bucket,
        cbs_system=cbs_system,
        cbs_code=cbs_code,
        discipline=_text(raw.get("discipline")),
        quantity=quantity,
        unit=_text(raw.get("unit") or "LS"),
        native_unit_cost=native_unit_cost,
        native_amount=native_amount,
        native_currency=native_currency,
        fx_rate=fx_rate,
        fx_source=fx_source,
        fx_snapshot_id=fx_snapshot_id,
        unit_cost=unit_cost,
        amount=amount,
        currency=reporting_currency,
        reporting_currency=reporting_currency,
        source_type=source_type,
        source_type_original=source_type_original,
        source_quality_score=SOURCE_QUALITY[source_type][1],
        source_reference=_text(raw.get("source_reference")),
        source_document_id=_text(raw.get("source_document_id")),
        vendor=_text(raw.get("vendor")),
        quote_number=_text(raw.get("quote_number")),
        quote_date=_text(raw.get("quote_date")),
        price_date=_text(raw.get("price_date") or raw.get("quote_date")),
        base_date=_text(raw.get("base_date") or context.get("base_date")),
        location=_text(raw.get("location") or context.get("location")),
        escalation_index_name=_text(raw.get("escalation_index_name")),
        escalation_index_value=escalation_value,
        escalation_index_date=_text(raw.get("escalation_index_date")),
        source_application=_text(raw.get("source_application") or context.get("source_application")),
        source_project_id=_text(raw.get("source_project_id") or context.get("project_id")),
        source_project_revision=_text(raw.get("source_project_revision") or context.get("project_revision")),
        source_scenario_id=_text(raw.get("source_scenario_id") or context.get("scenario_id")),
        source_calculation_revision=_text(raw.get("source_calculation_revision") or context.get("calculation_revision")),
        source_summary_id=_text(raw.get("source_summary_id") or context.get("summary_id")),
        estimate_id=_text(raw.get("estimate_id") or context.get("estimate_id")),
        estimate_revision=_text(raw.get("estimate_revision") or context.get("estimate_revision")),
        estimate_class_context=_text(raw.get("estimate_class_context") or context.get("estimate_class")),
        cost_basis=_text(raw.get("cost_basis")),
        notes=_text(raw.get("notes")),
    )
    result = item.to_dict()
    result["provenance"] = assess_provenance(item)
    return result


def canonicalize_cost_items(
    raw_items: list[dict] | None,
    *,
    default_currency: str = "USD",
    project_context: dict | None = None,
) -> dict:
    raw_items = raw_items or []
    if not isinstance(raw_items, list):
        raise ValueError("Cost items must be supplied as a list.")

    items = [
        canonicalize_cost_item(
            raw,
            default_currency=default_currency,
            project_context=project_context,
        )
        for raw in raw_items
    ]
    seen: set[str] = set()
    for item in items:
        item_id = item["item_id"]
        if item_id in seen:
            raise ValueError(f"Duplicate cost item_id {item_id!r}.")
        seen.add(item_id)

    warnings = [
        warning
        for item in items
        for warning in item["provenance"].get("warnings", [])
    ]
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "cbs_system": "TWDS-CBS-1.0",
        "items": items,
        "warnings": warnings,
    }
