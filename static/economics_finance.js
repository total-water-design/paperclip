(() => {
  "use strict";

  function money(value) {
    if (value == null || !Number.isFinite(Number(value))) return "—";
    const currency = document.querySelector('[data-path="project.currency"]')?.value || "USD";
    const n = Number(value), a = Math.abs(n);
    const pair = a >= 1e9 ? [n / 1e9, "B"] : a >= 1e6 ? [n / 1e6, "M"] : a >= 1e3 ? [n / 1e3, "k"] : [n, ""];
    return `${currency} ${pair[0].toLocaleString(undefined, {maximumFractionDigits: 2})}${pair[1]}`;
  }
  function pct(value) { return value == null || !Number.isFinite(Number(value)) ? "—" : `${(Number(value) * 100).toFixed(2)}%`; }
  function ratio(value) { return value == null || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toFixed(2)}×`; }
  function unitMoney(value) {
    if (value == null || !Number.isFinite(Number(value))) return "—";
    const currency = document.querySelector('[data-path="project.currency"]')?.value || "USD";
    return `${currency} ${Number(value).toFixed(3)}/m³`;
  }
  function escapeHtml(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;"); }

  function field(label, path, attrs = "", unit = "", defaultValue = "") {
    return `<label class="ted-field" data-origin="user"><span>${label}</span><div class="ted-field-control"><input ${attrs} data-path="${path}" data-finance-default="${defaultValue}">${unit ? `<span>${unit}</span>` : ""}</div><small class="ted-field-origin">User input</small></label>`;
  }
  function selectField(label, path, options, defaultValue = "") {
    return `<label class="ted-field" data-origin="user"><span>${label}</span><select data-path="${path}" data-finance-default="${defaultValue}">${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join("")}</select><small class="ted-field-origin">User input</small></label>`;
  }

  function injectInputs() {
    const panel = document.querySelector('[data-panel-content="finance"]');
    if (!panel || document.getElementById("tedAdvancedFinanceInputs")) return;
    const article = document.createElement("article");
    article.className = "twds-panel ted-panel-gap";
    article.id = "tedAdvancedFinanceInputs";
    article.innerHTML = `
      <div class="twds-panel__title"><div><span>TIME-PHASED PROJECT FINANCE</span><h2>BOOT / DBOOM cash-flow model</h2></div><span class="twds-chip twds-chip--review">Advanced</span></div>
      <p class="ted-copy">Adds construction funding and IDC, operating cash flows, working capital, tax/depreciation, explicit debt service, DSCR/LLCR/PLCR, project/equity returns and tariff solving. It does not replace the simple finance screen above.</p>
      <div class="ted-guidance-inline"><strong>Reference-model improvements:</strong> the uploaded BOOT workbook is used as a regression basis for debt/revenue mechanics, while its broken standalone DSCR units, stale tenor text, disabled MAT logic and legacy #REF! terminal-value sheets are not reproduced.</div>
      <details class="ted-finance-disclosure" open><summary>Commercial & construction</summary><div class="ted-grid ted-finance-grid">
        ${selectField("Advanced model", "project_finance.enabled", [["", "Disabled"], ["1", "Enabled"]], "")}
        ${selectField("Model", "project_finance.model", [["BOOT", "BOOT"], ["DBOOM", "DBOOM"], ["DBFOM", "DBFOM"], ["P3", "P3 / PPP"]], "BOOT")}
        ${field("Construction period", "project_finance.construction_months", 'type="number" min="1" step="1"', "months", "24")}
        ${field("Construction debt rate", "project_finance.construction_debt_rate", 'type="number" min="0" step="0.001"', "fraction", "0.06")}
        ${field("Upfront financing fee", "project_finance.upfront_financing_fee_pct", 'type="number" min="0" max="1" step="0.001"', "fraction", "0")}
        ${field("Concession / operating life", "project_finance.concession_years", 'type="number" min="1" step="1"', "years", "25")}
        ${field("Base volumetric tariff", "project_finance.tariff_m3", 'type="number" min="0" step="0.001"', "/m³", "1.35")}
        ${field("Tariff escalation", "project_finance.tariff_escalation_pct", 'type="number" step="0.001"', "fraction/y", "0.02")}
        ${field("Minimum offtake / take-or-pay", "project_finance.minimum_offtake_fraction", 'type="number" min="0" max="1" step="0.01"', "fraction", "0")}
        ${field("Fixed capacity payment", "project_finance.fixed_capacity_payment_y", 'type="number" min="0" step="1000"', "/year", "0")}
      </div></details>
      <details class="ted-finance-disclosure"><summary>Debt, reserves & lender metrics</summary><div class="ted-grid ted-finance-grid">
        ${field("Debt fraction", "project_finance.debt_fraction", 'type="number" min="0" max="1" step="0.01"', "fraction", "0.70")}
        ${field("Post-COD debt rate", "project_finance.debt_interest_rate", 'type="number" min="0" step="0.001"', "fraction", "0.06")}
        ${field("Debt tenor", "project_finance.debt_tenor_years", 'type="number" min="1" step="1"', "years", "20")}
        ${selectField("Repayment profile", "project_finance.repayment_profile", [["equal_principal", "Equal principal"], ["annuity", "Level debt service / annuity"]], "equal_principal")}
        ${field("DSRA requirement", "project_finance.dsra_months", 'type="number" min="0" step="0.5"', "months", "3")}
        ${selectField("Covenant DSCR basis", "project_finance.covenant_dscr_basis", [["reserve_aware", "Reserve-aware (default)"], ["raw", "Raw CFADS"]], "reserve_aware")}
        ${field("Sculpting scenario ID", "project_finance.sculpting_scenario_id", 'type="text"', "", "base")}
        ${field("Target minimum DSCR", "project_finance.target_min_dscr", 'type="number" min="0" step="0.01"', "×", "1.30")}
        ${field("Cost of equity", "project_finance.cost_of_equity", 'type="number" step="0.001"', "fraction", "0.15")}
      </div></details>
      <details class="ted-finance-disclosure"><summary>Equity cure (disabled by default)</summary><div class="ted-grid ted-finance-grid">
        ${selectField("Enable equity cure", "project_finance.equity_cure.enabled", [["", "Disabled"], ["1", "Enabled"]], "")}
        ${selectField("Cure amount basis", "project_finance.equity_cure.amount_basis", [["dscr_shortfall", "DSCR shortfall"], ["fixed_amount", "Fixed amount"]], "dscr_shortfall")}
        ${field("Fixed cure amount", "project_finance.equity_cure.amount", 'type="number" min="0" step="1000"', "", "0")}
        ${selectField("Cure frequency", "project_finance.equity_cure.frequency", [["per_period", "Per annual period"], ["once", "Once only"]], "per_period")}
        ${field("Consecutive-use cap (0 = unlimited)", "project_finance.equity_cure.consecutive_use_cap", 'type="number" min="0" step="1"', "uses", "0")}
        ${field("Total-use cap (0 = unlimited)", "project_finance.equity_cure.total_use_cap", 'type="number" min="0" step="1"', "uses", "0")}
        ${selectField("Cure treatment", "project_finance.equity_cure.treatment", [["cfads_addition", "CFADS addition"], ["debt_prepayment", "Debt prepayment"]], "cfads_addition")}
      </div></details>
      <details class="ted-finance-disclosure"><summary>Tax, OPEX escalation & working capital</summary><div class="ted-grid ted-finance-grid">
        ${field("Corporate tax rate", "project_finance.corporate_tax_rate", 'type="number" min="0" max="1" step="0.001"', "fraction", "0")}
        ${selectField("Tax depreciation", "project_finance.tax_depreciation_method", [["straight_line", "Straight line"], ["declining_balance", "Declining balance"]], "straight_line")}
        ${field("Tax depreciation life", "project_finance.tax_depreciation_years", 'type="number" min="1" step="1"', "years", "25")}
        ${field("Declining-balance rate", "project_finance.tax_depreciation_rate", 'type="number" min="0" max="1" step="0.001"', "fraction", "0.04")}
        ${field("General OPEX escalation", "project_finance.opex_escalation_pct", 'type="number" step="0.001"', "fraction/y", "0.02")}
        ${field("Receivable days", "project_finance.receivable_days", 'type="number" min="0" step="1"', "days", "30")}
        ${field("Inventory days", "project_finance.inventory_days", 'type="number" min="0" step="1"', "days", "30")}
        ${field("Inventory-eligible OPEX", "project_finance.inventory_eligible_opex_fraction", 'type="number" min="0" max="1" step="0.01"', "fraction", "0.15")}
        ${field("Payable days", "project_finance.payable_days", 'type="number" min="0" step="1"', "days", "30")}
      </div></details>
      <details class="ted-finance-disclosure"><summary>Handback, terminal value & tariff solver</summary><div class="ted-grid ted-finance-grid">
        ${field("Terminal / residual value", "project_finance.terminal_value", 'type="number" step="1000"', "", "0")}
        ${field("BOOT handback cost", "project_finance.handback_cost", 'type="number" min="0" step="1000"', "", "0")}
        ${selectField("Solve required tariff", "project_finance.solve_tariff", [["", "No"], ["1", "Yes"]], "")}
        ${field("Target equity IRR", "project_finance.target_equity_irr", 'type="number" min="0" step="0.001"', "fraction", "0")}
        ${field("Target project NPV", "project_finance.target_project_npv", 'type="number" step="1000"', "", "-1e99")}
        ${field("Tariff solver maximum", "project_finance.tariff_solver_max", 'type="number" min="0" step="0.1"', "/m³", "20")}
      </div></details>
      <p class="ted-finance-footnote">A custom monthly construction spend curve and category-specific OPEX escalation can also be supplied through the saved project/API payload. The UI defaults to an even monthly construction curve until a dedicated schedule editor is added.</p>`;
    panel.appendChild(article);
  }

  function injectResults() {
    const stack = document.querySelector('[data-panel-content="results"] .twds-results-stack');
    if (!stack || document.getElementById("tedAdvancedFinanceResults")) return;
    const section = document.createElement("section");
    section.className = "twds-results-section";
    section.id = "tedAdvancedFinanceResults";
    section.innerHTML = `
      <header><div><span class="ted-section-label">PROJECT FINANCE / BOOT</span><h2>Time-phased cash-flow and lender metrics</h2></div><span class="twds-chip twds-chip--review" id="pfStatus">Disabled</span></header>
      <div class="twds-kpi-grid ted-pf-kpis">
        <article class="twds-kpi"><span>Total Funding Requirement</span><strong id="pfFunding">—</strong></article>
        <article class="twds-kpi"><span>Capitalized IDC</span><strong id="pfIdc">—</strong></article>
        <article class="twds-kpi"><span>Debt at COD</span><strong id="pfDebt">—</strong></article>
        <article class="twds-kpi"><span>Initial DSRA</span><strong id="pfDsra">—</strong></article>
        <article class="twds-kpi"><span>WACC</span><strong id="pfWacc">—</strong></article>
        <article class="twds-kpi"><span>Project IRR (unlevered tax)</span><strong id="pfProjectIrr">—</strong></article>
        <article class="twds-kpi"><span>Project IRR (levered-tax variant)</span><strong id="pfLeveredTaxProjectIrr">—</strong></article>
        <article class="twds-kpi"><span>Equity IRR</span><strong id="pfEquityIrr">—</strong></article>
        <article class="twds-kpi"><span>Minimum DSCR</span><strong id="pfMinDscr">—</strong></article>
        <article class="twds-kpi"><span>Average DSCR</span><strong id="pfAvgDscr">—</strong></article>
        <article class="twds-kpi"><span>LLCR</span><strong id="pfLlcr">—</strong></article>
        <article class="twds-kpi"><span>PLCR</span><strong id="pfPlcr">—</strong></article>
        <article class="twds-kpi"><span>Required Tariff</span><strong id="pfSolvedTariff">—</strong></article>
      </div>
      <div class="ted-guidance-inline">Project IRR uses unlevered tax and excludes the interest shield. Raw and reserve-aware DSCR are both shown; the selected covenant basis is used for testing. Annual periods do not model seasonality, and VAT/GST is unsupported in v1.</div>
      <div class="twds-engineering-table-wrap ted-panel-gap"><table class="twds-engineering-table ted-pf-table"><thead><tr><th>Year</th><th>Tariff</th><th>Revenue</th><th>OPEX</th><th>CFADS</th><th>Principal</th><th>Interest</th><th>Debt Service</th><th>Raw DSCR</th><th>Reserve-aware DSCR</th><th>Tested DSCR</th><th>Reserve deficiency</th><th>DSRA</th><th>Closing Debt</th></tr></thead><tbody id="pfScheduleRows"></tbody></table></div>
      <div id="pfLimitations" class="ted-warning-list ted-panel-gap"></div>`;
    stack.appendChild(section);
  }

  const financeValueIds = ["pfFunding", "pfIdc", "pfDebt", "pfDsra", "pfWacc", "pfProjectIrr", "pfLeveredTaxProjectIrr", "pfEquityIrr", "pfMinDscr", "pfAvgDscr", "pfLlcr", "pfPlcr", "pfSolvedTariff"];
  function clearProjectFinance(message = "Enable the time-phased model in Project Finance to calculate BOOT/DBOOM metrics.") {
    const status = document.getElementById("pfStatus");
    if (status) status.textContent = "Disabled";
    financeValueIds.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "—"; });
    const rows = document.getElementById("pfScheduleRows");
    if (rows) rows.innerHTML = `<tr><td colspan="14">${escapeHtml(message)}</td></tr>`;
    const limits = document.getElementById("pfLimitations");
    if (limits) limits.innerHTML = "";
  }

  function renderProjectFinance(result) {
    const pf = result?.project_finance;
    if (!pf || !document.getElementById("tedAdvancedFinanceResults")) return;
    clearProjectFinance();
    const status = document.getElementById("pfStatus");
    if (!pf.enabled) return;
    status.textContent = "Calculated";
    const c = pf.construction || {}, d = pf.debt || {}, r = pf.returns || {}, solver = pf.tariff_solver || {};
    document.getElementById("pfFunding").textContent = money(c.funding_requirement_including_initial_dsra ?? c.total_funding_requirement);
    document.getElementById("pfIdc").textContent = money(c.idc);
    document.getElementById("pfDebt").textContent = money(d.debt_at_cod);
    document.getElementById("pfDsra").textContent = money(c.initial_dsra ?? d.initial_dsra);
    document.getElementById("pfWacc").textContent = pct(r.wacc);
    document.getElementById("pfProjectIrr").textContent = pct(r.project_irr);
    document.getElementById("pfLeveredTaxProjectIrr").textContent = pct(r.levered_tax_project_irr);
    document.getElementById("pfEquityIrr").textContent = pct(r.equity_irr);
    document.getElementById("pfMinDscr").textContent = ratio(d.min_dscr);
    document.getElementById("pfAvgDscr").textContent = ratio(d.average_dscr);
    document.getElementById("pfLlcr").textContent = ratio(d.llcr);
    document.getElementById("pfPlcr").textContent = ratio(d.plcr);
    document.getElementById("pfSolvedTariff").textContent = solver.solved ? unitMoney(solver.required_tariff_m3) : "—";
    document.getElementById("pfScheduleRows").innerHTML = (pf.operations?.rows || []).map(row => `<tr><td>${row.year}</td><td>${unitMoney(row.tariff_m3)}</td><td>${money(row.revenue)}</td><td>${money(row.opex)}</td><td>${money(row.cfads)}</td><td>${money(row.principal)}</td><td>${money(row.interest)}</td><td>${money(row.debt_service)}</td><td>${ratio(row.raw_dscr)}</td><td>${ratio(row.reserve_aware_dscr)}</td><td>${ratio(row.tested_dscr)}</td><td>${money(row.reserve_deficiency)}</td><td>${money(row.dsra_closing)}</td><td>${money(row.closing_debt)}</td></tr>`).join("");
    document.getElementById("pfLimitations").innerHTML = (pf.limitations || []).map(text => `<div class="review"><strong>Model boundary / reconciliation</strong><p>${escapeHtml(text)}</p></div>`).join("");
  }

  function applyDefaults() {
    document.querySelectorAll("[data-finance-default]").forEach(el => {
      if (el.value !== "") return;
      el.value = el.dataset.financeDefault || "";
      el.dispatchEvent(new Event("change", {bubbles: true}));
    });
  }

  injectInputs();
  injectResults();
  clearProjectFinance();
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    try {
      const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (url.includes("/api/economics") && response.ok) {
        response.clone().json().then(renderProjectFinance).catch(() => {});
      } else if (/\/api\/projects\/\d+/.test(url) && response.ok) {
        response.clone().json().then(data => {
          if (data?.snapshot?.result) renderProjectFinance(data.snapshot.result);
        }).catch(() => {});
      }
    } catch (_) { }
    return response;
  };

  window.addEventListener("DOMContentLoaded", () => setTimeout(applyDefaults, 0));
  document.addEventListener("twds:project-action", event => {
    if (event.detail?.action === "new") {
      clearProjectFinance();
      setTimeout(applyDefaults, 0);
    }
  });
})();
