"""Land, right-of-way, insurance, and credit-enhancement economics.

All rates and premiums are explicit inputs.  This module deliberately does not
derive a premium, discount rate, or WACC adjustment from a coverage category.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


LAND_TYPES = {
    "purchase", "fixed_easement", "annual_rental", "per_km_row",
    "per_parcel", "crossing", "deposit", "handback",
}
POLITICAL_RISK_CATEGORIES = {
    "expropriation", "transfer_restriction", "war_civil_disturbance",
    "breach_of_contract", "non_honoring_financial_obligations",
}
INSURANCE_CATEGORIES = {
    "construction_all_risk", "delay_in_startup", "third_party_liability",
    "marine_cargo", "operating_property", "business_interruption",
    *POLITICAL_RISK_CATEGORIES,
}
GUARANTEE_TYPES = {
    "partial_risk", "partial_credit", "payment_guarantee", "liquidity_facility",
    "letter_of_credit", "non_honoring_guarantee",
}


def _number(value: Any, *, field: str, required: bool = False) -> float:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field} is required; no default is assumed.")
        return 0.0
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{field} must be a finite non-negative number.")
    return result


def _period(value: Any, *, field: str, default: int | None = None) -> int:
    if value in (None, ""):
        if default is None:
            raise ValueError(f"{field} is required.")
        return default
    result = int(value)
    if result < 0:
        raise ValueError(f"{field} cannot be negative.")
    return result


def _identity(row: dict, *, field: str, index: int) -> str:
    value = str(row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} is required for row {index + 1}.")
    return value


def _provenance(row: dict) -> dict:
    return {
        "source": str(row.get("source") or "user").strip(),
        "reference": str(row.get("reference") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
        "scenario": str(row.get("scenario") or "base").strip(),
        "override_state": str(row.get("override_state") or "inherited").strip(),
    }


def _schedule_amount(schedule: dict[int, float], period: int, amount: float) -> None:
    schedule[period] = schedule.get(period, 0.0) + amount


def _land_schedule(rows: list[dict], warnings: list[str]) -> tuple[list[dict], dict[int, float], dict[int, float]]:
    normalized, capex, opex = [], {}, {}
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = deepcopy(raw or {})
        item_id = _identity(row, field="item_id", index=index)
        if item_id in seen:
            raise ValueError(f"Duplicate land/right-of-way item_id: {item_id}")
        seen.add(item_id)
        kind = str(row.get("type") or "").strip().lower()
        if kind not in LAND_TYPES:
            raise ValueError(f"Unsupported land/right-of-way type: {kind or '(blank)'}")
        start = _period(row.get("start_period"), field=f"{item_id}.start_period", default=0)
        end = _period(row.get("end_period"), field=f"{item_id}.end_period", default=start)
        if end < start:
            raise ValueError(f"{item_id}.end_period cannot precede start_period.")
        if kind == "per_km_row":
            base = _number(row.get("length_km"), field=f"{item_id}.length_km", required=True) * _number(row.get("rate_per_km"), field=f"{item_id}.rate_per_km", required=True)
        elif kind == "per_parcel":
            base = _number(row.get("parcel_count"), field=f"{item_id}.parcel_count", required=True) * _number(row.get("rate_per_parcel"), field=f"{item_id}.rate_per_parcel", required=True)
        else:
            base = _number(row.get("amount"), field=f"{item_id}.amount", required=True)
        treatment = str(row.get("treatment") or ("opex" if kind == "annual_rental" else "capex")).lower()
        if treatment not in {"capex", "opex"}:
            raise ValueError(f"{item_id}.treatment must be capex or opex.")
        frequency = str(row.get("frequency") or ("annual" if kind == "annual_rental" else "once")).lower()
        periods = range(start, end + 1) if frequency == "annual" else (start,)
        explicit_steps = row.get("period_amounts") or {}
        for period in periods:
            amount = _number(explicit_steps.get(str(period), explicit_steps.get(period, base)), field=f"{item_id}.period_amounts[{period}]")
            _schedule_amount(capex if treatment == "capex" else opex, period, amount)
        if kind in {"annual_rental", "fixed_easement"} and row.get("required_through_period") not in (None, ""):
            required = _period(row["required_through_period"], field=f"{item_id}.required_through_period")
            if end < required:
                warnings.append(f"Land/ROW {item_id} expires in period {end}, before required period {required}.")
        normalized.append({**row, "item_id": item_id, "type": kind, "start_period": start, "end_period": end, "base_amount": base, "treatment": treatment, "provenance": _provenance(row)})
    return normalized, capex, opex


def _premium(row: dict, policy_id: str) -> float:
    basis = str(row.get("premium_basis") or "").lower()
    if basis == "fixed":
        premium = _number(row.get("premium_amount"), field=f"{policy_id}.premium_amount", required=True)
    elif basis == "percent_insured_value":
        insured = _number(row.get("insured_value"), field=f"{policy_id}.insured_value", required=True)
        rate = _number(row.get("premium_rate"), field=f"{policy_id}.premium_rate", required=True)
        premium = insured * rate
    else:
        raise ValueError(f"{policy_id}.premium_basis must be fixed or percent_insured_value; no premium default is assumed.")
    return premium + _number(row.get("broker_fee"), field=f"{policy_id}.broker_fee") + _number(row.get("premium_tax"), field=f"{policy_id}.premium_tax")


def _insurance_schedule(rows: list[dict], warnings: list[str]) -> tuple[list[dict], dict[int, float], dict[int, float]]:
    normalized, capex, opex = [], {}, {}
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = deepcopy(raw or {})
        policy_id = _identity(row, field="policy_id", index=index)
        if policy_id in seen:
            raise ValueError(f"Duplicate insurance policy_id: {policy_id}")
        seen.add(policy_id)
        category = str(row.get("category") or "").lower()
        if category not in INSURANCE_CATEGORIES:
            raise ValueError(f"Unsupported insurance category: {category or '(blank)'}")
        start = _period(row.get("start_period"), field=f"{policy_id}.start_period")
        end = _period(row.get("end_period"), field=f"{policy_id}.end_period")
        if end < start:
            raise ValueError(f"{policy_id}.end_period cannot precede start_period.")
        treatment = str(row.get("treatment") or "").lower()
        if treatment not in {"capitalized", "expensed"}:
            raise ValueError(f"{policy_id}.treatment must explicitly be capitalized or expensed.")
        premium = _premium(row, policy_id)
        renewal = str(row.get("frequency") or "once").lower()
        periods = range(start, end + 1) if renewal == "annual" else (start,)
        for period in periods:
            _schedule_amount(capex if treatment == "capitalized" else opex, period, premium)
        required = row.get("required_through_period")
        if required not in (None, "") and end < _period(required, field=f"{policy_id}.required_through_period"):
            warnings.append(f"Insurance {policy_id} expires in period {end}, before required period {required}.")
        normalized.append({**row, "policy_id": policy_id, "category": category, "start_period": start, "end_period": end, "premium_with_fees": premium, "treatment": treatment, "miga_relevant": category in POLITICAL_RISK_CATEGORIES, "provenance": _provenance(row)})
    return normalized, capex, opex


def _guarantee_schedule(rows: list[dict], warnings: list[str]) -> tuple[list[dict], dict[int, float], dict[int, float]]:
    normalized, capex, opex = [], {}, {}
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = deepcopy(raw or {})
        instrument_id = _identity(row, field="instrument_id", index=index)
        if instrument_id in seen:
            raise ValueError(f"Duplicate guarantee instrument_id: {instrument_id}")
        seen.add(instrument_id)
        kind = str(row.get("type") or "").lower()
        if kind not in GUARANTEE_TYPES:
            raise ValueError(f"Unsupported guarantee/credit-enhancement type: {kind or '(blank)'}")
        start = _period(row.get("start_period"), field=f"{instrument_id}.start_period")
        end = _period(row.get("end_period"), field=f"{instrument_id}.end_period")
        if end < start:
            raise ValueError(f"{instrument_id}.end_period cannot precede start_period.")
        fee = _number(row.get("fee_amount"), field=f"{instrument_id}.fee_amount", required=True)
        treatment = str(row.get("treatment") or "").lower()
        if treatment not in {"capitalized", "expensed"}:
            raise ValueError(f"{instrument_id}.treatment must explicitly be capitalized or expensed.")
        periods = range(start, end + 1) if str(row.get("frequency") or "once").lower() == "annual" else (start,)
        for period in periods:
            _schedule_amount(capex if treatment == "capitalized" else opex, period, fee)
        required = row.get("required_through_period")
        if required not in (None, "") and end < _period(required, field=f"{instrument_id}.required_through_period"):
            warnings.append(f"Guarantee {instrument_id} expires in period {end}, before required period {required}.")
        normalized.append({**row, "instrument_id": instrument_id, "type": kind, "start_period": start, "end_period": end, "fee_amount": fee, "treatment": treatment, "provenance": _provenance(row)})
    return normalized, capex, opex


def analyze_risk_costs(payload: dict | None) -> dict:
    """Return normalized entities and non-overlapping CAPEX/OPEX schedules."""
    data = payload or {}
    warnings: list[str] = []
    land, land_capex, land_opex = _land_schedule(data.get("land_rights") or [], warnings)
    policies, insurance_capex, insurance_opex = _insurance_schedule(data.get("insurance_policies") or [], warnings)
    guarantees, guarantee_capex, guarantee_opex = _guarantee_schedule(data.get("guarantees") or [], warnings)
    periods = sorted(set(land_opex) | set(insurance_opex) | set(guarantee_opex))
    opex_by_period = {p: land_opex.get(p, 0.0) + insurance_opex.get(p, 0.0) + guarantee_opex.get(p, 0.0) for p in periods}
    capex = sum(land_capex.values()) + sum(insurance_capex.values()) + sum(guarantee_capex.values())
    return {
        "contract": "twds.risk_cost_schedule",
        "version": "1.0",
        "land_rights": land,
        "insurance_policies": policies,
        "guarantees": guarantees,
        "schedules": {
            "land_capex_by_period": land_capex, "land_opex_by_period": land_opex,
            "insurance_capex_by_period": insurance_capex, "insurance_opex_by_period": insurance_opex,
            "guarantee_capex_by_period": guarantee_capex, "guarantee_opex_by_period": guarantee_opex,
            "combined_opex_by_period": opex_by_period,
        },
        "capitalized_total": capex,
        "annual_opex_steady_state": opex_by_period.get(1, opex_by_period.get(0, 0.0)),
        "warnings": warnings,
        "checks": {
            "coverage_warning_count": len(warnings),
            "premium_defaults_used": False,
            "wacc_adjustment_applied": False,
            "double_counting_control": "Capitalized costs enter CAPEX once; expensed costs enter OPEX only.",
        },
    }
