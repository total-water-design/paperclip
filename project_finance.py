"""Time-phased project-finance / BOOT model for Total Water Economics.

This module is intentionally separate from the foundational cost engine. It consumes
an already-built Total Water Economics project result, then adds construction funding,
IDC, operating cash flows, working capital, tax/depreciation, debt service, lender
coverage ratios and sponsor/project returns.

The implementation is deterministic and transparent. It does not imply a specific
jurisdiction's tax code, derivative hedge, lender document or termination formula.
Those belong in explicit adapters rather than hidden spreadsheet conventions.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

OPEX_CATEGORIES = (
    "fixed", "variable", "energy", "chemicals", "labor", "maintenance",
    "replacement", "disposal", "other",
)


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return float(default)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Project-finance numeric values must be finite.")
    return value


def _fraction(value: Any, default: float, name: str, *, allow_one: bool = True) -> float:
    out = _number(value, default)
    upper_ok = out <= 1.0 if allow_one else out < 1.0
    if out < 0 or not upper_ok:
        op = "between 0 and 1" if allow_one else ">= 0 and < 1"
        raise ValueError(f"{name} must be {op}.")
    return out


def _positive_int(value: Any, default: int, name: str) -> int:
    out = int(round(_number(value, default)))
    if out <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return out


def _normalize_curve(raw: Any, periods: int) -> list[float]:
    if raw in (None, "", []):
        return [1.0 / periods] * periods
    if not isinstance(raw, list) or len(raw) != periods:
        raise ValueError(f"construction_spend_curve must contain exactly {periods} values.")
    values = [_number(x, 0.0) for x in raw]
    if any(x < 0 for x in values):
        raise ValueError("Construction spend-curve values cannot be negative.")
    total = sum(values)
    if total <= 0:
        raise ValueError("Construction spend curve must have a positive total.")
    return [x / total for x in values]


def _npv(rate: float, cashflows: list[float], start_period: int = 0) -> float:
    if rate <= -1:
        raise ValueError("Discount rate must be greater than -100%.")
    return sum(cf / ((1.0 + rate) ** (i + start_period)) for i, cf in enumerate(cashflows))


def _xnpv(rate: float, timed_cashflows: list[tuple[float, float]]) -> float:
    if rate <= -1:
        return math.inf
    return sum(amount / ((1.0 + rate) ** t) for t, amount in timed_cashflows)


def _sign_changes(timed_cashflows: list[tuple[float, float]]) -> int:
    signs = []
    for _, amount in timed_cashflows:
        if abs(amount) <= 1e-12:
            continue
        signs.append(1 if amount > 0 else -1)
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


def _irr(timed_cashflows: list[tuple[float, float]]) -> float | None:
    if not timed_cashflows:
        return None
    amounts = [x[1] for x in timed_cashflows]
    if not any(x < 0 for x in amounts) or not any(x > 0 for x in amounts):
        return None
    low, high = -0.9999, 1.0
    f_low, f_high = _xnpv(low, timed_cashflows), _xnpv(high, timed_cashflows)
    tries = 0
    while f_low * f_high > 0 and high < 1_000 and tries < 40:
        high *= 2.0
        f_high = _xnpv(high, timed_cashflows)
        tries += 1
    if f_low * f_high > 0:
        return None
    for _ in range(180):
        mid = (low + high) / 2.0
        f_mid = _xnpv(mid, timed_cashflows)
        if abs(f_mid) < 1e-8:
            return mid
        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def _depreciation_schedule(base: float, years: int, method: str, rate: float) -> list[float]:
    base = max(0.0, base)
    if method == "straight_line":
        annual = base / years if years else 0.0
        return [annual] * years
    if method != "declining_balance":
        raise ValueError("tax_depreciation_method must be straight_line or declining_balance.")
    if not (0 < rate <= 1):
        raise ValueError("tax_depreciation_rate must be > 0 and <= 1 for declining-balance depreciation.")
    remaining = base
    rows = []
    for _ in range(years):
        dep = min(remaining * rate, remaining)
        rows.append(dep)
        remaining -= dep
    return rows


def _tax_with_loss_carryforward(taxable_income: float, loss_balance: float, tax_rate: float) -> tuple[float, float]:
    loss_balance = max(0.0, float(loss_balance))
    if taxable_income < 0:
        return 0.0, loss_balance + abs(taxable_income)
    offset = min(loss_balance, taxable_income)
    taxable_after_losses = taxable_income - offset
    return taxable_after_losses * tax_rate, loss_balance - offset


def _opex_basis(result: dict) -> dict[str, float]:
    op = result.get("operating") or {}
    source = op.get("source_opex_breakdown") if isinstance(op.get("source_opex_breakdown"), dict) else {}
    out = {key: max(0.0, _number(source.get(key), 0.0)) for key in OPEX_CATEGORIES}
    identified = sum(out.values())
    total = max(0.0, _number(op.get("annual_opex_y"), 0.0))
    project_level = max(0.0, _number(op.get("project_level_opex_y"), max(0.0, total - identified)))
    out["other"] += project_level
    if sum(out.values()) <= 0 and total > 0:
        out["other"] = total
    return out


def _construction_schedule(base_capex: float, cfg: dict) -> dict:
    months = _positive_int(cfg.get("construction_months"), 24, "construction_months")
    curve = _normalize_curve(cfg.get("construction_spend_curve"), months)
    debt_fraction = _fraction(cfg.get("debt_fraction"), 0.70, "debt_fraction")
    rate = _number(cfg.get("construction_debt_rate", cfg.get("debt_interest_rate")), 0.07)
    if rate < 0:
        raise ValueError("Construction debt rate cannot be negative.")
    monthly_rate = rate / 12.0
    upfront_fee_pct = _fraction(cfg.get("upfront_financing_fee_pct"), 0.0, "upfront_financing_fee_pct")
    fee = base_capex * debt_fraction * upfront_fee_pct

    opening_debt = 0.0
    rows = []
    total_idc = total_debt = total_equity = 0.0
    for month, weight in enumerate(curve, 1):
        spend = base_capex * weight + (fee if month == 1 else 0.0)
        denominator = 1.0 - 0.5 * debt_fraction * monthly_rate
        debt_draw = debt_fraction * (spend + monthly_rate * opening_debt) / denominator if debt_fraction else 0.0
        interest = monthly_rate * (opening_debt + 0.5 * debt_draw)
        total_funding = spend + interest
        equity_draw = total_funding - debt_draw
        closing_debt = opening_debt + debt_draw
        rows.append({
            "month": month,
            "spend": spend,
            "base_capex_spend": base_capex * weight,
            "financing_fee": fee if month == 1 else 0.0,
            "opening_debt": opening_debt,
            "debt_draw": debt_draw,
            "equity_draw": equity_draw,
            "idc": interest,
            "closing_debt": closing_debt,
        })
        total_idc += interest
        total_debt += debt_draw
        total_equity += equity_draw
        opening_debt = closing_debt

    total = total_debt + total_equity
    return {
        "months": months,
        "curve": curve,
        "rows": rows,
        "base_capex": base_capex,
        "upfront_financing_fee": fee,
        "idc": total_idc,
        "total_funding_requirement": base_capex + fee + total_idc,
        "debt_funding": total_debt,
        "equity_funding": total_equity,
        "debt_fraction_effective": total_debt / total if total else 0.0,
    }


def _debt_schedule(initial_debt: float, debt_tenor: int, debt_rate: float, concession_years: int, repayment: str) -> list[dict]:
    if repayment not in {"equal_principal", "annuity"}:
        raise ValueError("repayment_profile must be equal_principal or annuity.")
    opening = initial_debt
    equal_principal = initial_debt / debt_tenor if repayment == "equal_principal" and debt_tenor else 0.0
    if repayment == "annuity":
        annuity_payment = initial_debt / debt_tenor if abs(debt_rate) < 1e-12 else initial_debt * debt_rate * (1 + debt_rate) ** debt_tenor / ((1 + debt_rate) ** debt_tenor - 1)
    else:
        annuity_payment = 0.0
    rows = []
    for year in range(1, concession_years + 1):
        if year <= debt_tenor and opening > 1e-9:
            if repayment == "equal_principal":
                principal = min(opening, equal_principal)
                closing = max(0.0, opening - principal)
                interest = ((opening + closing) / 2.0) * debt_rate
                debt_service = principal + interest
            else:
                interest = opening * debt_rate
                principal = min(opening, max(0.0, annuity_payment - interest))
                closing = max(0.0, opening - principal)
                debt_service = principal + interest
        else:
            principal = interest = debt_service = 0.0
            closing = 0.0
        rows.append({
            "year": year,
            "opening_debt": opening,
            "principal": principal,
            "interest": interest,
            "debt_service": debt_service,
            "closing_debt": closing,
        })
        opening = closing
    return rows


def _simulate(tariff: float, cfg: dict, project_result: dict, construction: dict) -> dict:
    concession_years = _positive_int(cfg.get("concession_years", (project_result.get("operating") or {}).get("project_life_years", 25)), 25, "concession_years")
    debt_tenor = _positive_int(cfg.get("debt_tenor_years"), 18, "debt_tenor_years")
    if debt_tenor > concession_years:
        raise ValueError("Debt tenor cannot exceed the concession/project life.")
    debt_rate = _number(cfg.get("debt_interest_rate"), 0.07)
    if debt_rate < 0:
        raise ValueError("Debt interest rate cannot be negative.")
    repayment = str(cfg.get("repayment_profile") or "equal_principal").strip().lower()

    operating = project_result.get("operating") or {}
    capacity = max(0.0, _number(operating.get("capacity_m3d"), 0.0))
    availability = _fraction(operating.get("availability"), 0.95, "availability")
    annual_design_volume = capacity * 365.0
    annual_physical_volume = annual_design_volume * availability
    minimum_offtake = _fraction(cfg.get("minimum_offtake_fraction"), 0.0, "minimum_offtake_fraction")
    tariff_escalation = _number(cfg.get("tariff_escalation_pct"), 0.02)
    if tariff_escalation < -1:
        raise ValueError("Tariff escalation cannot be below -100%.")
    fixed_payment = max(0.0, _number(cfg.get("fixed_capacity_payment_y"), 0.0))
    fixed_payment_escalation = _number(cfg.get("fixed_payment_escalation_pct"), tariff_escalation)

    tax_rate = _fraction(cfg.get("corporate_tax_rate"), 0.0, "corporate_tax_rate")
    depreciation_years = _positive_int(cfg.get("tax_depreciation_years"), concession_years, "tax_depreciation_years")
    dep_method = str(cfg.get("tax_depreciation_method") or "straight_line").strip().lower()
    dep_rate = _number(cfg.get("tax_depreciation_rate"), 0.0)
    depreciable_base = max(0.0, _number(cfg.get("depreciable_base"), (project_result.get("cost_hierarchy") or {}).get("total_project_cost", construction["base_capex"])))
    dep_base = _depreciation_schedule(depreciable_base, depreciation_years, dep_method, dep_rate)
    dep = (dep_base + [0.0] * max(0, concession_years - len(dep_base)))[:concession_years]

    receivable_days = max(0.0, _number(cfg.get("receivable_days"), 0.0))
    inventory_days = max(0.0, _number(cfg.get("inventory_days"), 0.0))
    payable_days = max(0.0, _number(cfg.get("payable_days"), 0.0))
    inventory_fraction = _fraction(cfg.get("inventory_eligible_opex_fraction"), 1.0, "inventory_eligible_opex_fraction")
    dsra_months = max(0.0, _number(cfg.get("dsra_months"), 0.0))
    dsra_funding_source = str(cfg.get("dsra_funding_source") or "equity").strip().lower()
    if dsra_funding_source != "equity":
        raise ValueError("The current DSRA implementation supports equity funding only.")

    opex_base = _opex_basis(project_result)
    generic_escalation = _number(cfg.get("opex_escalation_pct"), 0.02)
    escalation_by_category = cfg.get("opex_escalation_by_category") if isinstance(cfg.get("opex_escalation_by_category"), dict) else {}
    escalation_by_category = {k: _number(escalation_by_category.get(k), generic_escalation) for k in OPEX_CATEGORIES}
    if any(v < -1 for v in escalation_by_category.values()):
        raise ValueError("OPEX escalation cannot be below -100%.")

    maintenance_by_year: dict[int, float] = {}
    for item in cfg.get("major_maintenance") or []:
        if not isinstance(item, dict):
            raise ValueError("major_maintenance items must be objects.")
        year = _positive_int(item.get("year"), 1, "major-maintenance year")
        if year > concession_years:
            raise ValueError("Major-maintenance year cannot exceed concession life.")
        amount = max(0.0, _number(item.get("amount"), 0.0))
        maintenance_by_year[year] = maintenance_by_year.get(year, 0.0) + amount

    terminal_value = _number(cfg.get("terminal_value"), 0.0)
    handback_cost = max(0.0, _number(cfg.get("handback_cost"), 0.0))

    initial_debt = construction["debt_funding"]
    debt_schedule = _debt_schedule(initial_debt, debt_tenor, debt_rate, concession_years, repayment)
    initial_dsra = debt_schedule[0]["debt_service"] * dsra_months / 12.0 if debt_schedule else 0.0

    project_loss = levered_loss = prior_nwc = 0.0
    prior_dsra = initial_dsra
    rows = []
    project_cashflows = []
    equity_cashflows = []
    construction_years = construction["months"] / 12.0
    for row in construction["rows"]:
        t = row["month"] / 12.0
        project_cashflows.append((t, -row["base_capex_spend"]))
        equity_cashflows.append((t, -row["equity_draw"]))
    if initial_dsra > 0:
        equity_cashflows.append((construction_years, -initial_dsra))

    for year in range(1, concession_years + 1):
        tariff_y = tariff * ((1.0 + tariff_escalation) ** (year - 1))
        billed_volume = max(annual_physical_volume, annual_design_volume * minimum_offtake)
        revenue_variable = billed_volume * tariff_y
        revenue_fixed = fixed_payment * ((1.0 + fixed_payment_escalation) ** (year - 1))
        revenue = revenue_variable + revenue_fixed

        opex_by_category = {key: opex_base[key] * ((1.0 + escalation_by_category[key]) ** (year - 1)) for key in OPEX_CATEGORIES}
        opex = sum(opex_by_category.values())
        ebitda = revenue - opex

        debt_row = debt_schedule[year - 1]
        opening_debt = debt_row["opening_debt"]
        principal = debt_row["principal"]
        interest = debt_row["interest"]
        debt_service = debt_row["debt_service"]
        closing_debt = debt_row["closing_debt"]

        depreciation = dep[year - 1] if year - 1 < len(dep) else 0.0
        project_taxable = ebitda - depreciation
        project_tax, project_loss = _tax_with_loss_carryforward(project_taxable, project_loss, tax_rate)
        levered_taxable = project_taxable - interest
        levered_tax, levered_loss = _tax_with_loss_carryforward(levered_taxable, levered_loss, tax_rate)

        receivables = revenue * receivable_days / 365.0
        inventory = opex * inventory_fraction * inventory_days / 365.0
        payables = opex * payable_days / 365.0
        nwc = max(0.0, receivables + inventory - payables)
        delta_nwc = nwc - prior_nwc
        wc_release = nwc if year == concession_years else 0.0
        major_maintenance = maintenance_by_year.get(year, 0.0)

        project_cfads = ebitda - project_tax - delta_nwc - major_maintenance + wc_release
        levered_cfads = ebitda - levered_tax - delta_nwc - major_maintenance + wc_release
        dscr = levered_cfads / debt_service if debt_service > 1e-9 else None

        next_debt_service = debt_schedule[year]["debt_service"] if year < concession_years else 0.0
        closing_dsra = next_debt_service * dsra_months / 12.0
        change_dsra = closing_dsra - prior_dsra
        dsra_funding = max(0.0, change_dsra)
        dsra_release = max(0.0, -change_dsra)

        final_adjustment = (terminal_value - handback_cost) if year == concession_years else 0.0
        project_free_cash_flow = project_cfads + final_adjustment
        equity_cash_flow = levered_cfads - debt_service - change_dsra + final_adjustment
        t = construction_years + year
        project_cashflows.append((t, project_free_cash_flow))
        equity_cashflows.append((t, equity_cash_flow))

        rows.append({
            "year": year, "tariff_m3": tariff_y, "physical_volume_m3": annual_physical_volume,
            "billed_volume_m3": billed_volume, "revenue_variable": revenue_variable,
            "revenue_fixed": revenue_fixed, "revenue": revenue, "opex_by_category": opex_by_category,
            "opex": opex, "ebitda": ebitda, "depreciation": depreciation,
            "project_tax": project_tax, "levered_tax": levered_tax,
            "receivables": receivables, "inventory": inventory, "payables": payables,
            "net_working_capital": nwc, "change_in_working_capital": delta_nwc,
            "working_capital_release": wc_release, "major_maintenance": major_maintenance,
            "opening_debt": opening_debt, "principal": principal, "interest": interest,
            "debt_service": debt_service, "closing_debt": closing_debt, "cfads": levered_cfads,
            "project_cfads": project_cfads, "dscr": dscr,
            "dsra_opening": prior_dsra, "dsra_closing": closing_dsra,
            "dsra_funding": dsra_funding, "dsra_release": dsra_release,
            "terminal_value": terminal_value if year == concession_years else 0.0,
            "handback_cost": handback_cost if year == concession_years else 0.0,
            "project_free_cash_flow": project_free_cash_flow, "equity_cash_flow": equity_cash_flow,
        })
        prior_nwc = nwc
        prior_dsra = closing_dsra

    cost_of_equity = _number(cfg.get("cost_of_equity"), 0.20)
    if cost_of_equity <= -1:
        raise ValueError("Cost of equity must be greater than -100%.")
    after_tax_debt_cost = debt_rate * (1.0 - tax_rate)
    f = construction["debt_fraction_effective"]
    wacc = f * after_tax_debt_cost + (1.0 - f) * cost_of_equity
    debt_rows = [row for row in rows if row["debt_service"] > 1e-9]
    dscr_values = [row["dscr"] for row in debt_rows if row["dscr"] is not None]
    min_dscr = min(dscr_values) if dscr_values else None
    avg_dscr = sum(dscr_values) / len(dscr_values) if dscr_values else None
    cfads_to_maturity = [row["cfads"] for row in rows[:debt_tenor]]
    cfads_project_life = [row["cfads"] for row in rows]
    llcr = (_npv(debt_rate, cfads_to_maturity, 1) / initial_debt) if initial_debt > 1e-9 else None
    plcr = (_npv(debt_rate, cfads_project_life, 1) / initial_debt) if initial_debt > 1e-9 else None
    project_irr = _irr(project_cashflows)
    equity_irr = _irr(equity_cashflows)
    project_npv = _xnpv(wacc, project_cashflows) if wacc > -1 else None
    equity_npv = _xnpv(cost_of_equity, equity_cashflows) if cost_of_equity > -1 else None
    project_sign_changes = _sign_changes(project_cashflows)
    equity_sign_changes = _sign_changes(equity_cashflows)

    return {
        "tariff_m3": tariff, "wacc": wacc, "project_irr": project_irr, "equity_irr": equity_irr,
        "project_npv": project_npv, "equity_npv": equity_npv, "min_dscr": min_dscr,
        "average_dscr": avg_dscr, "llcr": llcr, "plcr": plcr, "debt_at_cod": initial_debt,
        "initial_dsra": initial_dsra,
        "funding_requirement_including_initial_dsra": construction["total_funding_requirement"] + initial_dsra,
        "project_cashflow_sign_changes": project_sign_changes,
        "equity_cashflow_sign_changes": equity_sign_changes,
        "rows": rows, "project_cashflows": project_cashflows, "equity_cashflows": equity_cashflows,
    }


def _meets_targets(result: dict, cfg: dict) -> bool:
    min_dscr_target = _number(cfg.get("target_min_dscr"), 0.0)
    equity_target = _number(cfg.get("target_equity_irr"), 0.0)
    project_npv_target = _number(cfg.get("target_project_npv"), -math.inf)
    if min_dscr_target > 0 and (result.get("min_dscr") is None or result["min_dscr"] < min_dscr_target):
        return False
    if equity_target > 0 and (result.get("equity_irr") is None or result["equity_irr"] < equity_target):
        return False
    if math.isfinite(project_npv_target) and (result.get("project_npv") is None or result["project_npv"] < project_npv_target):
        return False
    return True


def _solve_tariff(cfg: dict, project_result: dict, construction: dict) -> dict:
    lower = max(0.0, _number(cfg.get("tariff_solver_min"), 0.0))
    upper = max(lower + 1e-6, _number(cfg.get("tariff_solver_max"), 20.0))
    high_result = _simulate(upper, cfg, project_result, construction)
    if not _meets_targets(high_result, cfg):
        return {"solved": False, "required_tariff_m3": None, "reason": "Targets are not met at the configured maximum tariff."}
    for _ in range(100):
        mid = (lower + upper) / 2.0
        result = _simulate(mid, cfg, project_result, construction)
        if _meets_targets(result, cfg):
            upper = mid
        else:
            lower = mid
    final = _simulate(upper, cfg, project_result, construction)
    return {
        "solved": True, "required_tariff_m3": upper,
        "result_at_required_tariff": {"min_dscr": final["min_dscr"], "equity_irr": final["equity_irr"], "project_npv": final["project_npv"]},
    }


def analyze_project_finance(payload: dict, project_result: dict) -> dict:
    cfg = deepcopy(payload.get("project_finance") or {})
    if not cfg.get("enabled"):
        return {"enabled": False, "status": "disabled", "method_note": "Enable project_finance to run time-phased BOOT/project-finance analysis."}

    base_capex = max(0.0, _number(cfg.get("construction_base_capex"), (project_result.get("cost_hierarchy") or {}).get("total_project_cost", 0.0)))
    construction = _construction_schedule(base_capex, cfg)
    tariff = max(0.0, _number(cfg.get("tariff_m3"), (payload.get("finance") or {}).get("tariff_m3", 0.0)))
    scenario = _simulate(tariff, cfg, project_result, construction)
    solver = _solve_tariff(cfg, project_result, construction) if cfg.get("solve_tariff") else {"solved": False, "required_tariff_m3": None, "reason": "Tariff solver not requested."}

    limitations = [
        "No jurisdiction-specific MAT/AMT, VAT/GST recovery, withholding tax or tax-credit rules are implied by this generic engine.",
        "No interest-rate swaps, FX hedges, refinancing, cash sweep, distribution lock-up or lender default waterfall are modeled yet.",
        "DSRA is modeled as an equity-funded reserve with no reserve interest. Alternative reserve funding sources and letter-of-credit structures remain future lender-structure extensions.",
    ]
    if scenario["project_cashflow_sign_changes"] > 1:
        limitations.append("Project cash flow changes sign more than once; project IRR may be economically ambiguous. Review NPV and the full cash-flow series rather than relying on IRR alone.")
    if scenario["equity_cashflow_sign_changes"] > 1:
        limitations.append("Equity cash flow changes sign more than once; equity IRR may be economically ambiguous. Review equity NPV and the full cash-flow series rather than relying on IRR alone.")

    construction_output = deepcopy(construction)
    construction_output["initial_dsra"] = scenario["initial_dsra"]
    construction_output["funding_requirement_including_initial_dsra"] = scenario["funding_requirement_including_initial_dsra"]

    return {
        "enabled": True, "status": "calculated", "model": str(cfg.get("model") or "BOOT/DBOOM"),
        "construction": construction_output,
        "operations": {"concession_years": len(scenario["rows"]), "tariff_m3": scenario["tariff_m3"], "rows": scenario["rows"]},
        "returns": {
            "wacc": scenario["wacc"], "project_irr": scenario["project_irr"], "equity_irr": scenario["equity_irr"],
            "project_npv": scenario["project_npv"], "equity_npv": scenario["equity_npv"],
            "project_cashflow_sign_changes": scenario["project_cashflow_sign_changes"],
            "equity_cashflow_sign_changes": scenario["equity_cashflow_sign_changes"],
        },
        "debt": {
            "debt_at_cod": scenario["debt_at_cod"], "min_dscr": scenario["min_dscr"], "average_dscr": scenario["average_dscr"],
            "llcr": scenario["llcr"], "plcr": scenario["plcr"], "initial_dsra": scenario["initial_dsra"],
        },
        "tariff_solver": solver,
        "methodology": {
            "construction": "Monthly spend curve with pro-rata debt/equity funding and algebraically resolved capitalized IDC on average debt balance.",
            "debt_service": "Equal-principal or annuity amortization. Equal-principal interest uses average opening/closing balance, matching periodic amortization economics more closely than opening-balance-only interest.",
            "cfads": "Revenue less cash OPEX, cash tax, working-capital movement and major maintenance; before debt service, reserve funding and equity distributions.",
            "coverage": "DSCR is period CFADS / principal+interest. LLCR/PLCR are NPV of future CFADS divided by outstanding debt, discounted at debt rate.",
            "dsra": "Initial reserve equals configured months of first-period debt service, funded by equity at COD. Closing reserve follows the next period debt-service requirement and is released as debt amortizes.",
            "tax": "Jurisdiction-neutral corporate tax with tax-loss carryforward and configurable straight-line or declining-balance tax depreciation.",
            "terminal": "Terminal value and handback cost are explicit separate inputs; contractual termination compensation is not conflated with terminal value.",
        },
        "limitations": limitations,
    }
