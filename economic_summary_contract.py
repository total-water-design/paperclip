"""Economic-summary handoff contract for Total Water Design Suite applications.

Specialist applications own their engineering calculations and may produce a
compact economic summary for their scope. Total Economic Design consumes one or
many of these summaries and applies project-level economics on top.

The contract is intentionally tolerant during migration: canonical v1 summaries
are preferred, but common legacy total-CAPEX / annual-OPEX keys are normalized
with explicit warnings rather than silently discarded.

Currency note
-------------
The long-term Suite architecture supports multiple native currencies and one
selected reporting currency. Until the shared FX service is implemented, this
module preserves native-currency metadata but refuses to aggregate non-zero
amounts that still require currency conversion. It never assumes a 1:1 FX rate.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
import math

CONTRACT_ID = "twds.economic_summary"
CONTRACT_VERSION = "1.0"

APPLICATION_NAMES = {
    "pretreatment": "Total Pretreatment Design",
    "bio": "Total Bio Design",
    "ro": "Total RO Design",
    "zld": "Total ZLD Design",
    "balance": "Total Water Balance",
    "water_design": "Total Water Design",
    "other": "Other / External Scope",
}

CAPEX_BUCKETS = {
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

OPEX_CATEGORIES = (
    "fixed",
    "variable",
    "energy",
    "chemicals",
    "labor",
    "maintenance",
    "replacement",
    "disposal",
    "other",
)

SOURCE_TYPE_ALIASES = {
    "user_entered_estimate": "user",
    "user-entered-estimate": "user",
    "user entered estimate": "user",
    "vendor": "vendor_quote",
    "supplier_quote": "vendor_quote",
    "subcontract_quote": "subcontractor_quote",
    "quantity": "quantity_takeoff",
    "controlled_database": "database",
    "project_history": "historical",
    "factor": "allowance",
}


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Economic-summary numeric values must be finite.")
    return value


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def _first(mapping: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _source_type(value: Any) -> tuple[str, str]:
    original = str(value or "user").strip().lower()
    canonical = SOURCE_TYPE_ALIASES.get(original, original)
    valid = {
        "vendor_quote", "subcontractor_quote", "quantity_takeoff", "database",
        "historical", "capacity_factor", "parametric", "allowance", "user",
    }
    if canonical not in valid:
        canonical = "user"
    return canonical, original


def _validate_declared_contract(raw: dict) -> None:
    declared_contract = _first(raw, "contract_id", "contract", default=None)
    if declared_contract not in (None, "") and str(declared_contract) != CONTRACT_ID:
        raise ValueError(
            f"Unsupported economic-summary contract {declared_contract!r}; expected {CONTRACT_ID!r}."
        )
    declared_version = _first(raw, "contract_version", "version", default=None)
    if declared_version not in (None, "") and str(declared_version) != CONTRACT_VERSION:
        raise ValueError(
            f"Unsupported {CONTRACT_ID} version {declared_version!r}; expected {CONTRACT_VERSION!r}."
        )


def _app_id(raw: dict, source: dict) -> str:
    value = _first(source, "application_id", "app_id", "product_id", default=None)
    if value in (None, ""):
        value = _first(raw, "application_id", "app_id", "product_id", default="other")
    value = str(value or "other").strip().lower().replace("total-", "").replace("_design", "")
    aliases = {
        "total_ro_design": "ro", "total ro design": "ro", "ro_design": "ro",
        "total_bio_design": "bio", "total bio design": "bio",
        "total_pretreatment_design": "pretreatment", "total pretreatment design": "pretreatment",
        "total_zld_design": "zld", "total zld design": "zld",
        "total_water_balance": "balance", "total water balance": "balance",
        "total_water_design": "water_design", "total water design": "water_design",
    }
    return aliases.get(value, value if value in APPLICATION_NAMES else "other")


def _stable_item_id(summary_id: str, item_id: Any, fallback: Any) -> str:
    raw_id = str(item_id or fallback).strip()
    if raw_id.startswith(f"{summary_id}:") or raw_id == summary_id:
        return raw_id
    return f"{summary_id}:{raw_id}"


def _capex_cost_items(raw: dict, app_id: str, app_name: str, summary_id: str, currency: str) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    capex = raw.get("capex") if isinstance(raw.get("capex"), dict) else {}
    raw_items = capex.get("cost_items") or raw.get("cost_items") or (raw.get("details") or {}).get("cost_items") or []
    output: list[dict] = []

    if raw_items:
        if not isinstance(raw_items, list):
            raise ValueError(f"{app_name}: capex.cost_items must be a list.")
        for index, item in enumerate(raw_items, 1):
            item = dict(item or {})
            bucket = str(item.get("bucket") or "equipment_purchase").strip().lower()
            if bucket not in CAPEX_BUCKETS:
                raise ValueError(f"{app_name}: unsupported CAPEX bucket {bucket!r}.")
            quantity = _number(item.get("quantity"), 1.0)
            unit_cost = _number(item.get("unit_cost"), 0.0)
            amount = _number(item.get("amount"), quantity * unit_cost)
            if amount < 0:
                raise ValueError(f"{app_name}: CAPEX amounts cannot be negative.")
            item_currency = str(item.get("native_currency") or item.get("currency") or currency).strip().upper()
            canonical_source, original_source = _source_type(item.get("source_type") or raw.get("source_type") or "user")
            normalized = {
                "item_id": _stable_item_id(summary_id, item.get("item_id"), index),
                "scope_key": str(item.get("scope_key") or "").strip(),
                "description": str(item.get("description") or f"{app_name} scope").strip(),
                "bucket": bucket,
                "discipline": str(item.get("discipline") or app_name).strip(),
                "quantity": quantity,
                "unit": str(item.get("unit") or "LS").strip(),
                "unit_cost": unit_cost if item.get("unit_cost") not in (None, "") else amount,
                "amount": amount,
                "native_amount": _number(item.get("native_amount"), amount),
                "native_currency": item_currency,
                "currency": item_currency,
                "source_type": canonical_source,
                "source_reference": str(item.get("source_reference") or f"{app_name} economic summary {summary_id}").strip(),
                "vendor": str(item.get("vendor") or "").strip(),
                "quote_date": str(item.get("quote_date") or "").strip(),
                "notes": str(item.get("notes") or f"Imported from {app_name}; summary {summary_id}.").strip(),
            }
            if original_source != canonical_source:
                normalized["source_type_original"] = original_source
            for key in ("fx_rate", "fx_rate_timestamp", "fx_source", "fx_snapshot_id", "reporting_currency", "converted_amount"):
                if key in item and item[key] not in (None, ""):
                    normalized[key] = item[key]
            output.append(normalized)
        return output, warnings

    bucket_values: dict[str, float] = {}
    bucket_map = capex.get("buckets") if isinstance(capex.get("buckets"), dict) else {}
    for bucket in CAPEX_BUCKETS:
        value = _first(bucket_map, bucket, default=None)
        if value in (None, ""):
            value = _first(capex, bucket, default=None)
        if value not in (None, ""):
            amount = _number(value)
            if amount < 0:
                raise ValueError(f"{app_name}: CAPEX amounts cannot be negative.")
            if amount:
                bucket_values[bucket] = amount

    canonical_source, original_source = _source_type(raw.get("source_type") or "user")
    for bucket, amount in bucket_values.items():
        item = {
            "item_id": f"{summary_id}:{bucket}",
            "scope_key": "",
            "description": f"{app_name} — {CAPEX_BUCKETS[bucket]}",
            "bucket": bucket,
            "discipline": app_name,
            "quantity": 1.0,
            "unit": "LS",
            "unit_cost": amount,
            "amount": amount,
            "native_amount": amount,
            "native_currency": currency,
            "currency": currency,
            "source_type": canonical_source,
            "source_reference": f"{app_name} economic summary {summary_id}",
            "notes": f"Imported application economic summary ({CONTRACT_ID} v{CONTRACT_VERSION}).",
        }
        if original_source != canonical_source:
            item["source_type_original"] = original_source
        output.append(item)

    if output:
        return output, warnings

    legacy_total = _first(raw, "capex_usd", "total_capex", "capex_total", default=None)
    if legacy_total in (None, "") and isinstance(raw.get("capex"), (int, float, str)):
        legacy_total = raw.get("capex")
    if legacy_total not in (None, ""):
        amount = _number(legacy_total)
        if amount < 0:
            raise ValueError(f"{app_name}: CAPEX cannot be negative.")
        if amount:
            output.append({
                "item_id": f"{summary_id}:legacy-capex",
                "scope_key": "",
                "description": f"{app_name} — imported legacy CAPEX",
                "bucket": "equipment_purchase",
                "discipline": app_name,
                "quantity": 1.0,
                "unit": "LS",
                "unit_cost": amount,
                "amount": amount,
                "native_amount": amount,
                "native_currency": currency,
                "currency": currency,
                "source_type": "user",
                "source_reference": f"Legacy economic summary {summary_id}",
                "notes": "Legacy total CAPEX imported as an application-scope direct cost. Replace with bucketed CAPEX before a mature estimate.",
            })
            warnings.append(f"{app_name}: legacy total CAPEX was imported as one application-scope direct cost; provide bucketed CAPEX for a mature estimate.")
    return output, warnings


def _opex(raw: dict, app_name: str, electricity_price_kwh: float) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    block = raw.get("opex") if isinstance(raw.get("opex"), dict) else {}
    if isinstance(block.get("annual"), dict):
        annual = block.get("annual") or {}
    elif isinstance(raw.get("opex_annual"), dict):
        annual = raw.get("opex_annual") or {}
    else:
        annual = block
    aliases = {
        "fixed": ("fixed", "annual_fixed", "fixed_opex_y"),
        "variable": ("variable", "annual_variable", "variable_opex_y"),
        "energy": ("energy", "annual_energy", "energy_opex_y", "annual_energy_cost_usd"),
        "chemicals": ("chemicals", "annual_chemicals", "chemical_opex_y"),
        "labor": ("labor", "annual_labor", "labor_opex_y"),
        "maintenance": ("maintenance", "annual_maintenance", "maintenance_opex_y"),
        "replacement": ("replacement", "replacements", "annual_replacement", "replacement_opex_y", "consumables"),
        "disposal": ("disposal", "annual_disposal", "disposal_opex_y"),
        "other": ("other", "annual_other", "other_opex_y"),
    }
    result = {key: 0.0 for key in OPEX_CATEGORIES}
    for category, keys in aliases.items():
        value = _first(annual, *keys, default=None)
        if value not in (None, ""):
            result[category] = _number(value)
            if result[category] < 0:
                raise ValueError(f"{app_name}: annual OPEX components cannot be negative.")

    energy_kwh_y = _number(
        _first(block, "energy_kwh_y", "annual_energy_kwh", default=None)
        or _first(annual, "energy_kwh_y", "annual_energy_kwh", default=0.0),
        0.0,
    )
    if result["energy"] <= 0 and energy_kwh_y > 0 and electricity_price_kwh > 0:
        result["energy"] = energy_kwh_y * electricity_price_kwh
        warnings.append(f"{app_name}: annual energy OPEX calculated from imported kWh/year and the Total Economic Design electricity price.")

    component_total = sum(result.values())
    reported_total = _first(block, "total_annual", "annual_total", "total_opex_y", default=None)
    if reported_total in (None, ""):
        reported_total = _first(annual, "total", "total_annual", "annual_total", default=None)
    if reported_total in (None, ""):
        reported_total = _first(raw, "annual_opex_usd", "opex_usd_y", "annual_opex", default=None)
    if reported_total not in (None, ""):
        reported_total = _number(reported_total)
        if reported_total < 0:
            raise ValueError(f"{app_name}: annual OPEX cannot be negative.")
        if component_total <= 0:
            result["other"] = reported_total
            component_total = reported_total
            warnings.append(f"{app_name}: legacy/total-only annual OPEX imported as unspecified OPEX; provide component OPEX for a mature lifecycle model.")
        elif reported_total > component_total + max(1.0, abs(reported_total) * 1e-6):
            result["other"] += reported_total - component_total
            component_total = reported_total
            warnings.append(f"{app_name}: reported total OPEX exceeded identified components; the difference was retained as unspecified OPEX.")
        elif reported_total + max(1.0, abs(reported_total) * 1e-6) < component_total:
            warnings.append(f"{app_name}: reported total OPEX was below the sum of components; component detail was treated as authoritative.")

    result["energy_kwh_y"] = energy_kwh_y
    result["total"] = sum(result[key] for key in OPEX_CATEGORIES)
    return result, warnings


def normalize_summary(raw_summary: dict, *, project_currency: str = "USD", electricity_price_kwh: float = 0.0) -> dict:
    if not isinstance(raw_summary, dict):
        raise ValueError("Each application economic summary must be an object.")
    raw = deepcopy(raw_summary)
    _validate_declared_contract(raw)
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    basis = raw.get("basis") if isinstance(raw.get("basis"), dict) else {}
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    app_id = _app_id(raw, source)
    app_name = str(_first(source, "application_name", "name", default=None) or _first(raw, "application_name", "name", default=None) or APPLICATION_NAMES.get(app_id, APPLICATION_NAMES["other"])).strip()
    project_id = str(_first(source, "project_id", default=None) or _first(raw, "project_id", default="")).strip()
    project_revision = str(_first(source, "project_revision", "project_revision_id", default="")).strip()
    scenario_id = str(_first(source, "scenario_id", "case_id", default=None) or _first(raw, "scenario_id", "case_id", default="base")).strip()
    calculation_revision = str(_first(source, "calculation_revision", default="")).strip()
    summary_id = str(raw.get("summary_id") or source.get("summary_id") or f"{app_id}:{project_id or 'standalone'}:{scenario_id or 'base'}").strip()
    currency = str(raw.get("native_currency") or raw.get("currency") or basis.get("currency") or source.get("currency") or project_currency or "USD").strip().upper()
    project_currency = str(project_currency or "USD").strip().upper()
    included = _bool(raw.get("included"), True)
    capacity = _number(
        _first(raw, "capacity_m3d", default=None)
        or _first(basis, "capacity_m3d", default=None)
        or _first(source, "capacity_m3d", default=0.0),
        0.0,
    )
    if capacity < 0:
        raise ValueError(f"{app_name}: capacity cannot be negative.")

    items, capex_warnings = _capex_cost_items(raw, app_id, app_name, summary_id, currency)
    opex, opex_warnings = _opex(raw, app_name, electricity_price_kwh)
    raw_opex_items = details.get("opex_items") or ((raw.get("opex") or {}).get("opex_items") if isinstance(raw.get("opex"), dict) else []) or []
    if raw_opex_items and not isinstance(raw_opex_items, list):
        raise ValueError(f"{app_name}: details.opex_items must be a list when supplied.")

    native_currencies = {currency}
    for item in items:
        native_currencies.add(str(item.get("native_currency") or currency).upper())
    for item in raw_opex_items:
        if isinstance(item, dict):
            native_currencies.add(str(item.get("native_currency") or item.get("currency") or currency).upper())

    nonzero = sum(x.get("amount", 0.0) for x in items) + opex["total"]
    currencies_requiring_fx = sorted(x for x in native_currencies if x and x != project_currency)
    if included and nonzero > 0 and currencies_requiring_fx:
        raise ValueError(
            f"{app_name}: native currency/currencies {', '.join(currencies_requiring_fx)} do not match reporting currency {project_currency}. "
            "The shared FX service is not active yet; preserve the native values and convert explicitly before aggregation."
        )

    for item in items:
        item["reporting_currency"] = project_currency
        if str(item.get("native_currency") or project_currency).upper() == project_currency:
            item.setdefault("fx_rate", 1.0)
            item.setdefault("fx_source", "identity")
            item.setdefault("converted_amount", item["amount"])

    scope_keys = raw.get("scope_keys") or source.get("scope_keys") or []
    if isinstance(scope_keys, str):
        scope_keys = [x.strip() for x in scope_keys.split(",") if x.strip()]
    if not isinstance(scope_keys, list):
        raise ValueError(f"{app_name}: scope_keys must be a list when supplied.")
    inferred_scopes = [str(x.get("scope_key") or "").strip() for x in items if str(x.get("scope_key") or "").strip()]
    inferred_scopes.extend(
        str(x.get("scope_key") or "").strip()
        for x in raw_opex_items if isinstance(x, dict) and str(x.get("scope_key") or "").strip()
    )
    scope_keys = list(dict.fromkeys([str(x).strip() for x in scope_keys if str(x).strip()] + inferred_scopes))

    return {
        "contract": CONTRACT_ID,
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "summary_id": summary_id,
        "included": included,
        "source": {
            "application_id": app_id,
            "application_name": app_name,
            "project_id": project_id,
            "project_revision": project_revision,
            "scenario_id": scenario_id or "base",
            "calculation_revision": calculation_revision,
        },
        "currency": project_currency if included else currency,
        "native_currency": currency,
        "native_currencies": sorted(x for x in native_currencies if x),
        "reporting_currency": project_currency,
        "fx": {
            "status": "identity" if not currencies_requiring_fx else "conversion_required",
            "service_required": bool(currencies_requiring_fx),
            "rate_snapshot_required_for_saved_estimate": True,
        },
        "capacity_m3d": capacity,
        "basis": {
            **basis,
            "currency": currency,
            "capacity_m3d": capacity,
        },
        "scope_keys": scope_keys,
        "cost_items": items,
        "opex_items": deepcopy(raw_opex_items),
        "capex_total": sum(x.get("amount", 0.0) for x in items),
        "opex": opex,
        "warnings": capex_warnings + opex_warnings,
    }


def aggregate_summaries(raw_summaries: list[dict] | None, *, project_currency: str = "USD", electricity_price_kwh: float = 0.0) -> dict:
    raw_summaries = raw_summaries or []
    if not isinstance(raw_summaries, list):
        raise ValueError("source_summaries must be a list.")

    normalized: list[dict] = []
    seen_ids: set[str] = set()
    seen_item_ids: set[str] = set()
    scopes: dict[str, list[str]] = {}
    cost_items: list[dict] = []
    opex = {key: 0.0 for key in OPEX_CATEGORIES}
    annual_energy_kwh = 0.0
    warnings: list[str] = []

    for raw in raw_summaries:
        summary = normalize_summary(raw or {}, project_currency=project_currency, electricity_price_kwh=electricity_price_kwh)
        if not summary["included"]:
            normalized.append(summary)
            continue
        sid = summary["summary_id"]
        if sid in seen_ids:
            raise ValueError(f"Duplicate economic summary {sid!r}; the same source summary cannot be counted twice.")
        seen_ids.add(sid)
        for item in summary["cost_items"]:
            item_id = item.get("item_id")
            if item_id in seen_item_ids:
                raise ValueError(f"Duplicate economic item {item_id!r}; item IDs must be unique across included summaries.")
            seen_item_ids.add(item_id)
        normalized.append(summary)
        cost_items.extend(summary["cost_items"])
        for key in OPEX_CATEGORIES:
            opex[key] += summary["opex"][key]
        annual_energy_kwh += summary["opex"].get("energy_kwh_y", 0.0)
        warnings.extend(summary["warnings"])
        for scope_key in summary["scope_keys"]:
            scopes.setdefault(scope_key, []).append(sid)

    overlaps = {key: ids for key, ids in scopes.items() if len(ids) > 1}
    for scope_key, ids in overlaps.items():
        warnings.append(f"Potential scope overlap {scope_key!r} appears in {', '.join(ids)}; verify that CAPEX/OPEX is not duplicated.")

    opex["total"] = sum(opex[key] for key in OPEX_CATEGORIES)
    opex["energy_kwh_y"] = annual_energy_kwh
    included_sources = [x for x in normalized if x["included"]]
    return {
        "contract": CONTRACT_ID,
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "project_currency": str(project_currency or "USD").upper(),
        "reporting_currency": str(project_currency or "USD").upper(),
        "fx_service_status": "not_implemented",
        "source_count": len(included_sources),
        "sources": normalized,
        "cost_items": cost_items,
        "capex_total": sum(x.get("amount", 0.0) for x in cost_items),
        "opex": opex,
        "annual_opex_total": opex["total"],
        "scope_overlaps": overlaps,
        "warnings": warnings,
    }
