"""RO-scope CAPEX/OPEX and twds.economic_summary v1.0 producer.

This module consumes solved Total RO Design results. It does not rerun membrane,
pump, chemistry, ERD, or optimization engineering models.
"""
from __future__ import annotations

from copy import deepcopy
import math

CONTRACT_ID = "twds.economic_summary"
CONTRACT_VERSION = "1.0"
APPLICATION_ID = "ro"
APPLICATION_NAME = "Total RO Design"
COST_BASIS_ID = "ro-scope-parametric-v1.0"
COST_BASIS_DATE = "2026-08-22"
FLOW_TO_M3H = {"m3/h": 1.0, "L/s": 3.6, "gpm": 0.227124707}

DEFAULT_ASSUMPTIONS = {
    "currency": "USD",
    "availability": 0.95,
    "electricity_price_kwh": 0.10,
    "membrane_unit_cost": 700.0,
    "pressure_vessel_unit_cost": 4500.0,
    "hpp_cost_per_kw": 450.0,
    "hpp_base_cost_each": 30000.0,
    "booster_cost_per_kw": 500.0,
    "booster_base_cost_each": 12000.0,
    "px_cost_per_m3d": 115.0,
    "turbo_cost_per_kw": 500.0,
    "dweer_cost_per_m3d": 125.0,
    "pelton_cost_per_kw": 450.0,
    "skid_piping_fraction": 0.16,
    "valves_instrumentation_fraction": 0.08,
    "electrical_vfd_fraction": 0.09,
    "cip_flush_fraction": 0.06,
    "chemical_skid_fraction": 0.035,
    "controls_fraction": 0.025,
    "direct_installation_fraction": 0.35,
    "membrane_replacement_interval_years": 5.0,
    "maintenance_fraction_y": 0.015,
    "cleanings_per_year": 1.0,
    "cleaning_cost_per_membrane": 20.0,
    "labor_fte": 0.0,
    "labor_loaded_cost_per_fte_y": 85000.0,
    "antiscalant_cost_per_kg": 4.0,
    "acid_cost_per_kg": 0.35,
    "caustic_cost_per_kg": 0.55,
    "bisulfite_cost_per_kg": 0.80,
    "include_pretreatment_energy": False,
}

OPEX_CATEGORIES = (
    "fixed", "variable", "energy", "chemicals", "labor", "maintenance",
    "replacement", "disposal", "other",
)


def _number(value, default=0.0):
    if value in (None, ""):
        return float(default)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Economic inputs must be finite.")
    return value


def _first(mapping, *keys, default=None):
    mapping = mapping or {}
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _assumptions(raw):
    raw = dict(raw or {})
    values = dict(DEFAULT_ASSUMPTIONS)
    values.update({key: value for key, value in raw.items() if key in values})
    values["_overrides"] = set(raw)
    if str(values["currency"]).upper() != "USD":
        raise ValueError("RO cost inputs must be USD until Total Economic Design applies explicit FX conversion.")
    values["currency"] = "USD"
    values["availability"] = _number(values["availability"])
    if not 0 < values["availability"] <= 1:
        raise ValueError("Availability must be > 0 and <= 1.")
    for key in DEFAULT_ASSUMPTIONS:
        if key in {"currency", "include_pretreatment_energy", "availability"}:
            continue
        values[key] = _number(values[key])
        if values[key] < 0:
            raise ValueError(f"{key} cannot be negative.")
    if values["membrane_replacement_interval_years"] <= 0:
        raise ValueError("Membrane replacement interval must be > 0.")
    values["include_pretreatment_energy"] = bool(values["include_pretreatment_energy"])
    return values


def _provenance(assumptions, key, notes):
    overridden = key in assumptions["_overrides"]
    return {
        "source_type": "user_entered_estimate" if overridden else "parametric",
        "source_reference": "User-entered RO economic assumption" if overridden else f"Total RO Design {COST_BASIS_ID}",
        "vendor": "",
        "quote_date": "",
        "base_date": COST_BASIS_DATE,
        "currency": "USD",
        "notes": notes,
    }


def _capacity_m3d(result, basis):
    explicit = _first(basis, "capacity_m3d")
    if explicit not in (None, ""):
        return max(0.0, _number(explicit))
    direct = _first(result, "product_m3d")
    if direct not in (None, ""):
        return max(0.0, _number(direct))
    train = _first(result, "train_product_capacity_m3d")
    if train not in (None, ""):
        return max(0.0, _number(train)) * max(1.0, _number(_first(result, "operating_trains", default=1), 1))
    flow = _first(result, "product_flow_m3h", "product_flow", "permeate_flow_m3h", "permeate_flow")
    if flow in (None, ""):
        raise ValueError("Solved RO product capacity/flow is required.")
    unit = str(_first(result, "flow_unit", default="m3/h"))
    return max(0.0, _number(flow)) * FLOW_TO_M3H.get(unit, 1.0) * 24.0


def _installed_trains(result):
    return max(1, int(round(_number(_first(result, "installed_trains", default=1), 1))))


def _pressure_vessels(result):
    trains = _installed_trains(result)
    total = _first(result, "total_pressure_vessels")
    if total not in (None, ""):
        return int(round(max(0.0, _number(total)) * trains))
    return int(round(sum(
        max(0.0, _number(_first(result, f"stage{i}_pressure_vessels", f"vessels_{i}", default=0)))
        for i in range(1, 5)
    ) * trains))


def _membranes(result):
    trains = _installed_trains(result)
    total = _first(result, "total_membrane_elements")
    if total not in (None, ""):
        return int(round(max(0.0, _number(total)) * trains))
    return int(round(sum(
        max(0.0, _number(_first(result, f"stage{i}_pressure_vessels", f"vessels_{i}", default=0)))
        * max(0.0, _number(_first(result, f"elements_per_vessel_{i}", default=0)))
        for i in range(1, 5)
    ) * trains))


def _scenario(result, source):
    return str(_first(source, "scenario_id", "case_id", default=None)
               or _first(result, "technology", "mode", default="conventional")).strip().lower()


def _capex_item(item_id, description, bucket, quantity, unit, unit_cost,
                assumptions, assumption_key, scope_key, notes):
    quantity = max(0.0, _number(quantity))
    unit_cost = max(0.0, _number(unit_cost))
    return {
        "item_id": item_id,
        "scope_key": scope_key,
        "description": description,
        "bucket": bucket,
        "discipline": "RO",
        "quantity": quantity,
        "unit": unit,
        "unit_cost": unit_cost,
        "amount": quantity * unit_cost,
        **_provenance(assumptions, assumption_key, notes),
    }


def _pump_duties(result, capacity_m3d):
    duties = []
    definitions = (
        ("high_pressure_pump", ("electric_kw", "hpp_kw", "high_pressure_pump_kw", "feed_pump_electric_kw")),
        ("interstage_booster", ("interstage_booster_kw", "interstage_pump_kw", "booster_kw")),
        ("circulation_booster", ("circulation_booster_kw", "circulation_pump_kw", "px_booster_kw")),
        ("erd_auxiliary", ("erd_aux_kw", "erd_auxiliary_kw", "motorized_px_kw")),
    )
    for name, keys in definitions:
        value = _first(result, *keys)
        if value not in (None, "") and _number(value) > 0:
            duties.append((name, _number(value)))
    if not duties:
        ro_sec = max(0.0, _number(_first(result, "ro_sec", "ro_gross_sec", "gross_sec", default=0)))
        wire_kw = ro_sec * capacity_m3d / 24.0
        if wire_kw > 0:
            duties.append(("ro_pumping", wire_kw))
    return duties


def _dose(result, inputs, *keys):
    for mapping in (result, inputs):
        value = _first(mapping, *keys)
        if value not in (None, ""):
            return max(0.0, _number(value))
    return 0.0


def build_ro_economic_summary(payload):
    if not isinstance(payload, dict):
        raise ValueError("Economic-summary request must be an object.")
    result = deepcopy(payload.get("result") or {})
    inputs = deepcopy(payload.get("inputs") or {})
    source = deepcopy(payload.get("source") or {})
    basis = deepcopy(payload.get("basis") or {})
    assumptions = _assumptions(payload.get("assumptions") or {})
    if not result:
        raise ValueError("A solved Total RO Design result is required.")

    capacity = _capacity_m3d(result, basis)
    annual_product = capacity * 365.0 * assumptions["availability"]
    recovery = _number(_first(result, "recovery", default=0))
    recovery = recovery / 100.0 if recovery > 1.0 else recovery
    annual_feed = annual_product / recovery if recovery > 1e-9 else annual_product

    project_id = str(source.get("project_id") or "")
    scenario_id = str(source.get("scenario_id") or source.get("case_id") or _scenario(result, source) or "base")
    summary_id = str(source.get("summary_id") or f"ro:{project_id or 'standalone'}:{scenario_id}")
    scope = f"ro.{project_id or 'standalone'}.{scenario_id}"

    membrane_count = _membranes(result)
    vessel_count = _pressure_vessels(result)
    capex_items = []
    if membrane_count:
        capex_items.append(_capex_item(
            f"{summary_id}:membranes", "RO/NF membrane elements", "equipment_purchase",
            membrane_count, "ea", assumptions["membrane_unit_cost"], assumptions,
            "membrane_unit_cost", f"{scope}.membranes",
            "Quantity from solved membrane inventory; price is an RO-scope estimate unless overridden.",
        ))
    if vessel_count:
        capex_items.append(_capex_item(
            f"{summary_id}:pressure-vessels", "RO membrane pressure vessels", "equipment_purchase",
            vessel_count, "ea", assumptions["pressure_vessel_unit_cost"], assumptions,
            "pressure_vessel_unit_cost", f"{scope}.pressure_vessels",
            "Quantity from solved pressure-vessel inventory.",
        ))

    for index, (kind, wire_kw) in enumerate(_pump_duties(result, capacity), 1):
        hpp = kind in {"high_pressure_pump", "ro_pumping"}
        base = assumptions["hpp_base_cost_each"] if hpp else assumptions["booster_base_cost_each"]
        rate = assumptions["hpp_cost_per_kw"] if hpp else assumptions["booster_cost_per_kw"]
        base_count = _installed_trains(result) if kind != "erd_auxiliary" else 1
        total = base * base_count + rate * wire_kw
        capex_items.append(_capex_item(
            f"{summary_id}:pump:{kind}:{index}", kind.replace("_", " ").title(), "equipment_purchase",
            1, "LS", total, assumptions, "hpp_cost_per_kw" if hpp else "booster_cost_per_kw",
            f"{scope}.pump.{kind}.{index}",
            f"Uses solved electrical duty {wire_kw:.3f} kW; pump hydraulic selection is not duplicated.",
        ))

    ro_sec = max(0.0, _number(_first(result, "ro_sec", "ro_gross_sec", "gross_sec", default=0)))
    pretreatment_sec = max(0.0, _number(_first(result, "pretreatment_sec", default=0))) if assumptions["include_pretreatment_energy"] else 0.0
    scoped_sec = ro_sec + pretreatment_sec
    ro_power_scale_kw = scoped_sec * capacity / 24.0
    mode = _scenario(result, source)
    if "px" in mode or "isobaric" in mode:
        capex_items.append(_capex_item(
            f"{summary_id}:erd:px", "Isobaric energy-recovery equipment", "equipment_purchase",
            capacity, "m3/d", assumptions["px_cost_per_m3d"], assumptions, "px_cost_per_m3d",
            f"{scope}.erd.isobaric", "Parametric RO-scope allowance; replace with supplier quotation when available.",
        ))
    elif "dweer" in mode:
        capex_items.append(_capex_item(
            f"{summary_id}:erd:dweer", "DWEER energy-recovery equipment", "equipment_purchase",
            capacity, "m3/d", assumptions["dweer_cost_per_m3d"], assumptions, "dweer_cost_per_m3d",
            f"{scope}.erd.dweer", "Parametric RO-scope allowance.",
        ))
    elif "pelton" in mode:
        capex_items.append(_capex_item(
            f"{summary_id}:erd:pelton", "Pelton energy-recovery turbine", "equipment_purchase",
            1, "LS", max(ro_power_scale_kw, 1.0) * assumptions["pelton_cost_per_kw"], assumptions,
            "pelton_cost_per_kw", f"{scope}.erd.pelton", "Parametric RO-scope allowance keyed to solved RO power scale.",
        ))
    elif any(token in mode for token in ("turbo", "single", "biturbo", "interstage")):
        count = 2 if "biturbo" in mode else 1
        capex_items.append(_capex_item(
            f"{summary_id}:erd:turbo", "Turbocharger energy-recovery equipment", "equipment_purchase",
            count, "ea", max(ro_power_scale_kw, 1.0) * assumptions["turbo_cost_per_kw"] / count,
            assumptions, "turbo_cost_per_kw", f"{scope}.erd.turbo",
            "Parametric RO-scope allowance keyed to solved RO power scale.",
        ))

    core_purchase = sum(item["amount"] for item in capex_items)
    allowances = (
        ("skid-piping", "RO skids and RO-specific piping", "skid_piping_fraction"),
        ("valves-instrumentation", "RO valves and instrumentation", "valves_instrumentation_fraction"),
        ("electrical-vfd", "RO electrical equipment, MCC allocation and VFDs", "electrical_vfd_fraction"),
        ("cip-flush", "Membrane cleaning / CIP and flushing systems", "cip_flush_fraction"),
        ("chemical-skids", "RO chemical dosing skids", "chemical_skid_fraction"),
        ("controls", "RO-package controls", "controls_fraction"),
    )
    for suffix, description, key in allowances:
        if core_purchase and assumptions[key]:
            capex_items.append(_capex_item(
                f"{summary_id}:{suffix}", description, "equipment_purchase", 1, "LS",
                core_purchase * assumptions[key], assumptions, key, f"{scope}.{suffix}",
                f"RO-scope allowance = {100.0 * assumptions[key]:.1f}% of identified core equipment.",
            ))

    equipment_purchase = sum(item["amount"] for item in capex_items)
    if equipment_purchase and assumptions["direct_installation_fraction"]:
        capex_items.append(_capex_item(
            f"{summary_id}:direct-installation", "RO-scope direct installation", "direct_installation",
            1, "LS", equipment_purchase * assumptions["direct_installation_fraction"], assumptions,
            "direct_installation_fraction", f"{scope}.direct_installation",
            "RO-scope installation only; excludes whole-project EPC, owner, financing and general-site costs.",
        ))
    direct_installation = sum(item["amount"] for item in capex_items if item["bucket"] == "direct_installation")
    ro_installed_cost = equipment_purchase + direct_installation

    opex_items = []
    energy_kwh_y = scoped_sec * annual_product
    energy_prov = _provenance(assumptions, "electricity_price_kwh", "Solved SEC × annual product volume.")
    opex_items.append({
        "item_id": f"{summary_id}:opex:energy", "scope_key": f"{scope}.opex.energy",
        "category": "energy", "description": "RO electrical energy" + (" plus explicitly included pretreatment energy" if pretreatment_sec else ""),
        "quantity": energy_kwh_y, "unit": "kWh/y", "unit_cost": assumptions["electricity_price_kwh"],
        "amount_annual": energy_kwh_y * assumptions["electricity_price_kwh"], **energy_prov,
    })

    chemicals = (
        ("antiscalant", ("antiscalant_dose_mg_l", "antiscalant_dose"), "antiscalant_cost_per_kg"),
        ("acid", ("acid_solution_dose_mg_l", "acid_dose_mg_l", "acid_dose"), "acid_cost_per_kg"),
        ("caustic", ("caustic_dose_mg_l", "caustic_dose"), "caustic_cost_per_kg"),
        ("bisulfite", ("bisulfite_dose_mg_l", "sbs_dose_mg_l", "dechlorination_dose_mg_l"), "bisulfite_cost_per_kg"),
    )
    for name, keys, cost_key in chemicals:
        dose_mg_l = _dose(result, inputs, *keys)
        if dose_mg_l <= 0:
            continue
        kg_y = dose_mg_l * annual_feed * 0.001
        opex_items.append({
            "item_id": f"{summary_id}:opex:{name}", "scope_key": f"{scope}.opex.chemical.{name}",
            "category": "chemicals", "description": name.title(), "quantity": kg_y, "unit": "kg/y",
            "unit_cost": assumptions[cost_key], "amount_annual": kg_y * assumptions[cost_key],
            **_provenance(assumptions, cost_key, f"Calculated {name} dose × annual RO feed volume."),
        })

    cleaning_cost = membrane_count * assumptions["cleaning_cost_per_membrane"] * assumptions["cleanings_per_year"]
    if cleaning_cost:
        opex_items.append({
            "item_id": f"{summary_id}:opex:cleaning", "scope_key": f"{scope}.opex.membrane_cleaning",
            "category": "chemicals", "description": "Membrane cleaning chemicals",
            "quantity": assumptions["cleanings_per_year"], "unit": "cleanings/y",
            "unit_cost": membrane_count * assumptions["cleaning_cost_per_membrane"], "amount_annual": cleaning_cost,
            **_provenance(assumptions, "cleaning_cost_per_membrane", "Annual membrane cleaning chemical allowance."),
        })

    membrane_replacement = membrane_count * assumptions["membrane_unit_cost"] / assumptions["membrane_replacement_interval_years"]
    if membrane_replacement:
        opex_items.append({
            "item_id": f"{summary_id}:opex:membrane-replacement", "scope_key": f"{scope}.opex.membrane_replacement",
            "category": "replacement", "description": "Membrane replacement",
            "quantity": membrane_count / assumptions["membrane_replacement_interval_years"], "unit": "equivalent membranes/y",
            "unit_cost": assumptions["membrane_unit_cost"], "amount_annual": membrane_replacement,
            **_provenance(assumptions, "membrane_unit_cost", "Membrane count × unit price ÷ replacement interval."),
        })

    maintenance = equipment_purchase * assumptions["maintenance_fraction_y"]
    if maintenance:
        opex_items.append({
            "item_id": f"{summary_id}:opex:maintenance", "scope_key": f"{scope}.opex.maintenance",
            "category": "maintenance", "description": "RO equipment maintenance allowance",
            "quantity": 1, "unit": "y", "unit_cost": maintenance, "amount_annual": maintenance,
            **_provenance(assumptions, "maintenance_fraction_y", "RO-specific equipment maintenance allowance."),
        })

    labor = assumptions["labor_fte"] * assumptions["labor_loaded_cost_per_fte_y"]
    if labor:
        opex_items.append({
            "item_id": f"{summary_id}:opex:labor", "scope_key": f"{scope}.opex.labor", "category": "labor",
            "description": "RO-specific operating labor", "quantity": assumptions["labor_fte"], "unit": "FTE",
            "unit_cost": assumptions["labor_loaded_cost_per_fte_y"], "amount_annual": labor,
            "source_type": "user_entered_estimate", "source_reference": "User-entered RO labor basis",
            "vendor": "", "quote_date": "", "base_date": COST_BASIS_DATE, "currency": "USD",
            "notes": "Excluded by default; included only when explicitly modeled.",
        })

    annual = {key: 0.0 for key in OPEX_CATEGORIES}
    for item in opex_items:
        annual[item["category"]] += item["amount_annual"]
    annual["variable"] = 0.0
    annual_total = sum(annual[key] for key in OPEX_CATEGORIES)

    all_ids = [item["item_id"] for item in capex_items + opex_items]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("Duplicate RO economic item identifiers were generated.")

    summary = {
        "contract": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "summary_id": summary_id,
        "included": True,
        "source": {
            "application_id": APPLICATION_ID,
            "application_name": APPLICATION_NAME,
            "project_id": project_id,
            "project_revision": str(source.get("project_revision") or ""),
            "scenario_id": scenario_id,
            "calculation_revision": str(source.get("calculation_revision") or ""),
        },
        "currency": "USD",
        "capacity_m3d": capacity,
        "basis": {
            "currency": "USD", "capacity_m3d": capacity, "availability": assumptions["availability"],
            "annual_product_m3": annual_product, "annual_feed_m3": annual_feed,
            "base_date": str(basis.get("base_date") or COST_BASIS_DATE),
        },
        "scope_keys": [item["scope_key"] for item in capex_items + opex_items],
        "capex": {
            "equipment_purchase": equipment_purchase,
            "direct_installation": direct_installation,
            "buckets": {"equipment_purchase": equipment_purchase, "direct_installation": direct_installation},
            "cost_items": capex_items,
            "ro_scope_installed_cost": ro_installed_cost,
        },
        "opex": {"annual": annual, "energy_kwh_y": energy_kwh_y, "total_annual": annual_total, "opex_items": opex_items},
        "opex_annual": {**annual, "total": annual_total},
        "details": {"cost_items": capex_items, "opex_items": opex_items},
        "unit_economics": {
            "ro_capex_per_m3d": ro_installed_cost / capacity if capacity else 0.0,
            "ro_annual_opex": annual_total,
            "ro_opex_per_m3": annual_total / annual_product if annual_product else 0.0,
            "energy_cost_per_m3": annual["energy"] / annual_product if annual_product else 0.0,
            "membrane_replacement_cost_per_m3": membrane_replacement / annual_product if annual_product else 0.0,
            "chemical_cost_per_m3": annual["chemicals"] / annual_product if annual_product else 0.0,
        },
        "cost_basis": {
            "basis_id": COST_BASIS_ID,
            "base_date": COST_BASIS_DATE,
            "hierarchy_note": "Vendor quotation > supplier/database price > project history > controlled database > parametric > user-entered estimate. Default monetary inputs are explicit RO-scope parametric assumptions until stronger provenance is supplied.",
            "whole_project_exclusions": [
                "whole-plant contingency", "owner costs", "whole-project EPC management", "general site development",
                "financing", "interest during construction", "working capital", "whole-project escalation",
                "project debt", "equity", "DSCR", "WACC", "project IRR", "equity IRR", "total plant LCOW", "BOOT tariff",
            ],
        },
    }
    validate_twds_economic_summary(summary)
    return summary


def validate_twds_economic_summary(summary):
    if not isinstance(summary, dict):
        raise ValueError("Economic summary must be an object.")
    if (summary.get("contract") or summary.get("contract_id")) != CONTRACT_ID:
        raise ValueError("Economic summary must use twds.economic_summary.")
    if (summary.get("version") or summary.get("contract_version")) != CONTRACT_VERSION:
        raise ValueError("Economic summary must use version 1.0.")
    if (summary.get("source") or {}).get("application_id") != APPLICATION_ID:
        raise ValueError("source.application_id must be ro.")
    capex = summary.get("capex") or {}
    if not isinstance(capex.get("buckets"), dict):
        raise ValueError("capex.buckets is required.")
    annual = (summary.get("opex") or {}).get("annual")
    if not isinstance(annual, dict) or any(key not in annual for key in OPEX_CATEGORIES):
        raise ValueError("opex.annual must include the v1.0 OPEX categories.")
    items = list(capex.get("cost_items") or []) + list((summary.get("opex") or {}).get("opex_items") or [])
    ids = [item.get("item_id") for item in items]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Economic item IDs must be present and unique.")
    return True


def register_ro_economic_summary(app):
    from flask import jsonify, request
    if getattr(app, "_ro_economic_summary_registered", False):
        return app
    app._ro_economic_summary_registered = True

    @app.get("/api/ro/economic-summary/schema")
    def ro_economic_summary_schema():
        return jsonify({
            "contract": CONTRACT_ID, "version": CONTRACT_VERSION, "application_id": APPLICATION_ID,
            "default_assumptions": DEFAULT_ASSUMPTIONS, "cost_basis_id": COST_BASIS_ID, "base_date": COST_BASIS_DATE,
        })

    @app.post("/api/ro/economic-summary")
    def ro_economic_summary_calculate():
        try:
            return jsonify(build_ro_economic_summary(request.get_json(force=True) or {}))
        except (TypeError, ValueError, KeyError, ZeroDivisionError) as exc:
            return jsonify({"error": str(exc), "error_type": type(exc).__name__}), 400

    @app.post("/api/ro/economic-summary/validate")
    def ro_economic_summary_validate():
        try:
            validate_twds_economic_summary(request.get_json(force=True) or {})
            return jsonify({"ok": True, "contract": CONTRACT_ID, "version": CONTRACT_VERSION})
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
    return app
