"""Economic analysis routing for Total RO Design and Total Economic Design.

The legacy RO energy-recovery comparison remains unchanged for existing callers.
A payload with ``model=total_economic_design`` is routed to the plant/project
cost and finance engine owned by Total Economic Design.
"""
from __future__ import annotations

import math

from economic_aggregator import analyze_total_economic_design

# Baseline installed-capital fractions from the workbook's PX / Isobaric ERD case.
CAPEX_CATEGORIES = [
    ("Site preparation, road and parking", 0.011024156918232103, "fixed"),
    ("Intake", 0.05245978119710449, "fixed"),
    ("Pretreatment", 0.08819325534585683, "pretreatment_flow"),
    ("RO system equipment", 0.3527730213834273, "ro_equipment"),
    ("Post-treatment", 0.022048313836464207, "fixed"),
    ("Concentrate disposal", 0.027560392295580258, "fixed"),
    ("Waste and solids handling", 0.016536235377348156, "fixed"),
    ("Electrical and instrumentation systems", 0.02470931723052023, "electrical"),
    ("Auxiliary and service equipment and utilities", 0.022048313836464207, "fixed"),
    ("Buildings / footprint", 0.03307247075469631, "building_flow"),
    ("Start-up, commissioning and acceptance testing", 0.022048313836464207, "startup"),
    ("Preliminary engineering", 0.011024156918232103, "engineering"),
    ("Pilot testing", 0.011024156918232103, "engineering"),
    ("Detailed design", 0.055120784591160515, "engineering"),
    ("Construction management and oversight", 0.03307247075469631, "engineering"),
    ("Administration, contracting and management", 0.022048313836464207, "fixed"),
    ("Environmental permitting", 0.04960870613204446, "fixed"),
    ("Legal services", 0.016536235377348156, "fixed"),
    ("Interest during construction", 0.022048313836464207, "fixed"),
    ("Debt service fund", 0.055120784591160515, "fixed"),
    ("Other financing costs", 0.044096627672928414, "fixed"),
    ("Contingency", 0.00782587735911073, "fixed"),
]

# Workbook savings for a conventional FEDCO Turbocharger vs PX / Isobaric ERD.
WORKBOOK_TURBO_SAVINGS = {
    "ro_equipment": 0.15,
    "electrical": 0.15,
    "building": 0.05,
    "startup": 0.10,
    "engineering": 0.10,
}

TECH_LABELS = {
    "px": "Isobaric Chamber",
    "single": "Single Turbo",
    "biturbo": "BiTurbo",
}


def _f(data, key, default):
    v = data.get(key, default)
    return float(default if v in (None, "") else v)


def _crf(rate: float, years: float) -> float:
    if years <= 0:
        raise ValueError("Project life must be greater than zero.")
    if abs(rate) < 1e-12:
        return 1.0 / years
    return rate * (1.0 + rate) ** years / ((1.0 + rate) ** years - 1.0)


def _pv_annuity_factor(rate: float, years: float) -> float:
    if abs(rate) < 1e-12:
        return years
    return (1.0 - (1.0 + rate) ** (-years)) / rate


def economic_analysis(data: dict) -> dict:
    if str(data.get("model") or "").strip().lower() == "total_economic_design":
        return analyze_total_economic_design(data)

    cases = data.get("cases") or {}
    if "px" not in cases:
        raise ValueError("Calculate the Isobaric Chamber case before running the economic comparison.")

    if data.get("product_capacity_m3d") in (None, ""):
        raise ValueError("Enter the project product capacity before running the economic comparison.")
    capacity = _f(data, "product_capacity_m3d", 10000.0)
    availability = _f(data, "availability", 0.95)
    power_price = _f(data, "electricity_price", 0.10)
    years = _f(data, "project_life", 25.0)
    discount = _f(data, "discount_rate", 0.06)
    if data.get("base_capex_per_m3d") in (None, ""):
        raise ValueError("Enter the baseline installed CAPEX per m³/day before running the economic comparison.")
    base_capex_rate = _f(data, "base_capex_per_m3d", 1000.0)
    if capacity <= 0 or not (0 < availability <= 1.0) or base_capex_rate <= 0:
        raise ValueError("Capacity, availability and baseline CAPEX must be positive.")

    ro_saving = _f(data, "turbo_ro_equipment_saving", WORKBOOK_TURBO_SAVINGS["ro_equipment"])
    elec_saving = _f(data, "turbo_electrical_saving", WORKBOOK_TURBO_SAVINGS["electrical"])
    building_saving = _f(data, "turbo_building_saving", WORKBOOK_TURBO_SAVINGS["building"])
    startup_saving = _f(data, "turbo_startup_saving", WORKBOOK_TURBO_SAVINGS["startup"])
    engineering_saving = _f(data, "turbo_engineering_saving", WORKBOOK_TURBO_SAVINGS["engineering"])
    biturbo_ro_adder = _f(data, "biturbo_ro_equipment_adder", 0.0)
    building_flow_exponent = _f(data, "building_flow_exponent", 1.0)
    pret_flow_exponent = _f(data, "pretreatment_flow_exponent", 1.0)

    baseline_capex = capacity * base_capex_rate
    annual_product = capacity * 365.0 * availability
    crf = _crf(discount, years)
    pvaf = _pv_annuity_factor(discount, years)

    px = cases["px"]
    px_specific_feed = float(px["feed_flow_m3h"]) / max(float(px["product_flow_m3h"]), 1e-12)

    outputs = {}
    for tech, c in cases.items():
        if tech not in TECH_LABELS:
            continue
        product = max(float(c.get("product_flow_m3h", 0.0)), 1e-12)
        feed = max(float(c.get("feed_flow_m3h", 0.0)), 0.0)
        specific_feed = feed / product
        flow_factor = specific_feed / max(px_specific_feed, 1e-12)
        flow_factor = max(0.25, min(2.0, flow_factor))
        is_px = tech == "px"

        categories = []
        total_capex = 0.0
        pret_base = pret_cost = building_base = building_cost = 0.0
        for name, frac, category_type in CAPEX_CATEGORIES:
            base = baseline_capex * frac
            cost = base
            if not is_px:
                if category_type == "pretreatment_flow":
                    cost = base * (flow_factor ** pret_flow_exponent)
                elif category_type == "ro_equipment":
                    cost = base * (1.0 - ro_saving)
                    if tech == "biturbo":
                        cost *= (1.0 + biturbo_ro_adder)
                elif category_type == "electrical":
                    cost = base * (1.0 - elec_saving)
                elif category_type == "building_flow":
                    cost = base * (flow_factor ** building_flow_exponent) * (1.0 - building_saving)
                elif category_type == "startup":
                    cost = base * (1.0 - startup_saving)
                elif category_type == "engineering":
                    cost = base * (1.0 - engineering_saving)
            if category_type == "pretreatment_flow":
                pret_base, pret_cost = base, cost
            if category_type == "building_flow":
                building_base, building_cost = base, cost
            total_capex += cost
            categories.append({"name": name, "baseline_usd": base, "cost_usd": cost, "saving_usd": base - cost})

        ro_sec = float(c.get("ro_sec", 0.0))
        pret_sec = float(c.get("pretreatment_sec", 0.0))
        total_sec = float(c.get("total_sec", ro_sec + pret_sec))
        fixed_om = _f(data, f"fixed_om_{tech}", 0.0)
        ro_energy_cost = ro_sec * annual_product * power_price
        pret_energy_cost = pret_sec * annual_product * power_price
        annual_energy_cost = total_sec * annual_product * power_price
        annualized_capex = total_capex * crf
        equivalent_annual = annualized_capex + annual_energy_cost + fixed_om
        lcow = equivalent_annual / annual_product
        npv = total_capex + (annual_energy_cost + fixed_om) * pvaf

        outputs[tech] = {
            "label": TECH_LABELS[tech], "specific_feed_ratio": specific_feed,
            "feed_capacity_factor_vs_px": flow_factor, "capex_usd": total_capex,
            "capex_usd_per_m3d": total_capex / capacity, "categories": categories,
            "pretreatment_capex_usd": pret_cost, "pretreatment_capex_saving_vs_baseline_usd": pret_base - pret_cost,
            "building_capex_usd": building_cost, "building_capex_saving_vs_baseline_usd": building_base - building_cost,
            "ro_sec": ro_sec, "pretreatment_sec": pret_sec, "total_sec": total_sec,
            "annual_ro_energy_cost_usd": ro_energy_cost, "annual_pretreatment_energy_cost_usd": pret_energy_cost,
            "annual_energy_cost_usd": annual_energy_cost, "fixed_om_usd_y": fixed_om,
            "annualized_capex_usd_y": annualized_capex, "equivalent_annual_cost_usd_y": equivalent_annual,
            "lcow_usd_m3": lcow, "npv_usd": npv,
        }

    pxout = outputs["px"]
    for tech, o in outputs.items():
        if tech == "px":
            o.update({"capex_saving_vs_px_usd": 0.0, "annual_energy_delta_vs_px_usd": 0.0,
                      "annual_cost_advantage_vs_px_usd": 0.0, "annual_cost_advantage_usd": 0.0,
                      "annual_cost_advantage_winner": None, "break_even_power_price_usd_kwh": None})
            continue
        cap_saving = pxout["capex_usd"] - o["capex_usd"]
        energy_delta = o["annual_energy_cost_usd"] - pxout["annual_energy_cost_usd"]
        annual_adv = pxout["equivalent_annual_cost_usd_y"] - o["equivalent_annual_cost_usd_y"]
        delta_sec = o["total_sec"] - pxout["total_sec"]
        annual_cap_adv = cap_saving * crf
        if delta_sec > 1e-12:
            bep = annual_cap_adv / (annual_product * delta_sec)
        else:
            bep = None
        o.update({"capex_saving_vs_px_usd": cap_saving, "annual_energy_delta_vs_px_usd": energy_delta,
                  "annual_cost_advantage_vs_px_usd": annual_adv,
                  "annual_cost_advantage_usd": abs(annual_adv),
                  "annual_cost_advantage_winner": o["label"] if annual_adv >= 0 else pxout["label"],
                  "break_even_power_price_usd_kwh": bep})

    preferred = min(outputs, key=lambda k: outputs[k]["equivalent_annual_cost_usd_y"])
    return {
        "product_capacity_m3d": capacity, "availability": availability,
        "annual_product_m3": annual_product, "electricity_price": power_price,
        "project_life": years, "discount_rate": discount, "crf": crf,
        "baseline_capex_usd": baseline_capex, "baseline_capex_per_m3d": base_capex_rate,
        "preferred": preferred, "preferred_label": TECH_LABELS[preferred], "cases": outputs,
        "source_note": "Baseline CAPEX allocation and conventional Turbo savings are from the supplied PX_vs_Turbocharger_CAPEX_OPEX_Revised_v10 workbook. Pretreatment and building/footprint costs are additionally scaled by each calculated design's feed-per-product ratio relative to the Isobaric Chamber case. Interstage Turbo is intentionally excluded from this economic comparison.",
    }
