(() => {
  "use strict";

  const starterEl = document.getElementById("tedStarterPayload");
  const starter = starterEl ? JSON.parse(starterEl.textContent || "{}") : {};
  let state = structuredClone(starter);
  let lastResult = null;
  let currentProjectRevisionId = null;

  const panelTitles = {
    sources: ["Application Summaries", "Use one specialist application or combine several application economic summaries into one project-level CAPEX, OPEX and annualized cost model."],
    overview: ["Estimate Overview", "Set the common project and reporting basis for the selected application economic scopes."],
    basis: ["Estimate Basis", "Review cost provenance, source quality and the basis used to mature the estimate."],
    costs: ["Project Cost Build-Up", "Add only project-level costs that are not already included in specialist application summaries."],
    maturity: ["AACE Maturity", "Assess project-definition maturity independently from contingency, accuracy and project risk."],
    reconciliation: ["Estimate Reconciliation", "Explain how app revisions, quantities, pricing and project assumptions move the combined estimate."],
    operating: ["Project OPEX Adders", "Add common operating costs outside the specialist application economic summaries."],
    finance: ["Project Finance", "Apply debt service, DSCR and tariff requirements to the complete selected project scope."],
    pdb: ["Progressive Design-Build", "Track estimate development as specialist definitions and open-book pricing mature."],
    results: ["Economic Results", "Review project KPIs, application cost contributions, detailed build-up, warnings, lifecycle economics and finance."]
  };

  const maturityLabels = {
    design_basis: "Design basis", process_description: "Process description", process_flow_diagrams: "Process flow diagrams",
    mass_balance: "Mass balance", equipment_list: "Equipment list", equipment_sizing: "Equipment sizing",
    major_equipment_pricing: "Major equipment quotations / pricing", site_definition: "Site definition / plot plan",
    civil_definition: "Civil / geotechnical definition", piping_definition: "Piping definition",
    electrical_definition: "Electrical load / SLD definition", instrumentation_controls: "Instrumentation / controls definition",
    execution_plan: "Execution / constructability plan", procurement_strategy: "Procurement / contracting strategy",
    schedule_maturity: "Schedule maturity", quantity_takeoffs: "Quantity takeoffs", risk_register: "Risk register",
    escalation_basis: "Escalation basis", contingency_methodology: "Contingency methodology"
  };
  const buckets = [
    ["equipment_purchase", "Purchased Equipment"], ["direct_installation", "Direct Installation"],
    ["construction_indirect", "Construction Indirects"], ["engineering_procurement", "Engineering / Procurement / PM"],
    ["owner_cost", "Owner Costs"], ["contingency", "Contingency"], ["escalation", "Escalation"],
    ["financing", "Financing / IDC"], ["working_capital", "Working Capital"]
  ];
  const sources = [
    ["vendor_quote", "Vendor quotation"], ["subcontractor_quote", "Subcontractor quotation"],
    ["quantity_takeoff", "Quantity takeoff / unit rate"], ["database", "Controlled cost database"],
    ["historical", "Historical project cost"], ["capacity_factor", "Capacity-factor estimate"],
    ["parametric", "Parametric estimate"], ["allowance", "Explicit allowance / factor"], ["user", "User-entered basis"]
  ];
  const applications = [
    ["pretreatment", "Total Pretreatment Design"], ["bio", "Total Bio Design"], ["ro", "Total RO Design"],
    ["zld", "Total ZLD Design"], ["balance", "Total Water Balance"], ["system_integration", "System Integration & Optimization"],
    ["water_design", "Total Water Design"], ["other", "Other / External Scope"]
  ];
  const applicationName = Object.fromEntries(applications);
  const opexKeys = ["fixed", "variable", "energy", "chemicals", "labor", "maintenance", "replacement", "disposal", "other"];

  function clone(v) { return structuredClone(v); }
  function getPath(path) { return path.split(".").reduce((acc, key) => acc == null ? undefined : acc[key], state); }
  function setPath(path, value) { const parts = path.split("."); let cursor = state; parts.slice(0, -1).forEach(key => { if (!cursor[key] || typeof cursor[key] !== "object") cursor[key] = {}; cursor = cursor[key]; }); cursor[parts.at(-1)] = value; }
  function parseInput(el) { if (el.type === "number") { if (el.value === "") return null; const n = Number(el.value); return Number.isFinite(n) ? n : null; } if (el.type === "checkbox") return el.checked; return el.value; }
  function escapeHtml(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;"); }
  function optionList(items, selected) { return items.map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`).join(""); }
  function markDirty(value = true) { if (window.TWDSAppUI) window.TWDSAppUI.markDirty(value); }
  function setCalcState(value, detail = "") { const button = document.getElementById("calculateEstimateBtn"); if (window.TWDSAppUI) window.TWDSAppUI.setCalculationState(button, value, detail); else if (button) button.dataset.twdsCalculateState = value; }
  function csrfHeaders(extra = {}) { const token = document.querySelector('meta[name="csrf-token"]')?.content; return token ? {...extra, "X-CSRFToken": token} : extra; }
  function authEnabled() { return document.getElementById("tedRuntime")?.dataset.authEnabled === "1"; }

  function showError(message) { const card = document.getElementById("tedError"); document.getElementById("tedErrorMessage").textContent = message || "The economic calculation could not be completed."; card.hidden = false; }
  function clearError() { document.getElementById("tedError").hidden = true; }
  function showReview(title, message) { document.getElementById("tedReviewTitle").textContent = title || "Review economic basis"; document.getElementById("tedReviewMessage").textContent = message || "Review the current economic assumptions."; document.getElementById("tedReview").hidden = false; }
  function clearReview() { document.getElementById("tedReview").hidden = true; }

  function bindPathInputs() {
    document.querySelectorAll("[data-path]").forEach(el => {
      const val = getPath(el.dataset.path); el.value = val == null ? "" : val;
      const handler = () => { setPath(el.dataset.path, parseInput(el)); syncProjectHeader(); };
      el.addEventListener("input", handler); el.addEventListener("change", handler);
    });
  }

  function syncProjectHeader() {
    const p = state.project || {};
    const name = p.project_name || "Untitled project";
    const id = p.project_id || "TWECO-DRAFT";
    const revision = p.revision || "Unsaved";
    document.querySelectorAll("[data-twds-project-name]").forEach(el => el.textContent = name);
    document.querySelectorAll("[data-twds-project-id]").forEach(el => el.textContent = id);
    document.querySelectorAll("[data-twds-project-revision]").forEach(el => el.textContent = revision);
  }

  function newSource(appId = "ro") {
    const id = `${appId}:${Date.now()}:${Math.random().toString(36).slice(2, 7)}`;
    return {
      contract: "twds.economic_summary", version: "1.0", summary_id: id, included: true, _ui_manual: true,
      source: {application_id: appId, application_name: applicationName[appId] || applicationName.other, project_id: "", project_revision: "", scenario_id: "base", calculation_revision: ""},
      currency: state.project?.currency || "USD", capex: {buckets: {equipment_purchase: 0, direct_installation: 0}},
      opex: {annual: {energy: 0, chemicals: 0, labor: 0, maintenance: 0, replacement: 0, disposal: 0, other: 0}}, scope_keys: []
    };
  }

  function capexBuckets(summary) {
    const result = {equipment_purchase: 0, direct_installation: 0};
    const capex = summary.capex && typeof summary.capex === "object" ? summary.capex : {};
    const mapped = capex.buckets && typeof capex.buckets === "object" ? capex.buckets : capex;
    for (const key of Object.keys(result)) if (Number.isFinite(Number(mapped[key]))) result[key] = Number(mapped[key]);
    if ((!result.equipment_purchase && !result.direct_installation) && Array.isArray(capex.cost_items)) {
      capex.cost_items.forEach(item => { if (item && keyIn(item.bucket, result)) result[item.bucket] += Number(item.amount || (Number(item.quantity || 1) * Number(item.unit_cost || 0))) || 0; });
    }
    return result;
  }
  function keyIn(key, object) { return Object.prototype.hasOwnProperty.call(object, key); }
  function annualOpex(summary) {
    const block = summary.opex && typeof summary.opex === "object" ? summary.opex : {};
    const annual = block.annual && typeof block.annual === "object" ? block.annual : (summary.opex_annual && typeof summary.opex_annual === "object" ? summary.opex_annual : {});
    const out = Object.fromEntries(opexKeys.map(k => [k, Number(annual[k] || 0)]));
    if (!opexKeys.some(k => out[k]) && Array.isArray(block.opex_items)) block.opex_items.forEach(item => { if (item && keyIn(item.category, out)) out[item.category] += Number(item.amount_annual || 0) || 0; });
    return out;
  }
  function summaryOrigin(summary) { return summary._ui_override ? "override" : summary._ui_manual ? "user" : "inherited"; }
  function summaryOriginLabel(summary) { const o = summaryOrigin(summary); return o === "override" ? "Overridden" : o === "user" ? "User input" : "Inherited"; }

  function convertToOverride(summary) {
    const capex = capexBuckets(summary), annual = annualOpex(summary), originalId = summary.summary_id || "inherited";
    const source = clone(summary.source || {}); source.override_of_summary_id = originalId;
    return {
      contract: "twds.economic_summary", version: "1.0", summary_id: `${originalId}:override:${Date.now()}`, included: summary.included !== false,
      _ui_override: true, source, currency: summary.currency || summary.basis?.currency || state.project?.currency || "USD",
      capex: {buckets: capex}, opex: {annual}, scope_keys: clone(summary.scope_keys || [])
    };
  }

  function renderSourceRows() {
    const body = document.getElementById("sourceSummaryRows"), empty = document.getElementById("sourceEmptyState");
    body.innerHTML = ""; const rows = state.source_summaries || []; empty.hidden = rows.length > 0;
    rows.forEach((summary, index) => {
      summary.source = summary.source || {};
      const capex = capexBuckets(summary), annual = annualOpex(summary), inherited = summaryOrigin(summary) === "inherited";
      const origin = summaryOrigin(summary), tr = document.createElement("tr"); if (inherited) tr.classList.add("ted-source-readonly");
      const laborMaint = annual.labor + annual.maintenance;
      tr.innerHTML = `
        <td class="ted-check-cell"><input type="checkbox" data-source-field="included" ${summary.included !== false ? "checked" : ""}></td>
        <td><span class="ted-source-origin ${origin}">${summaryOriginLabel(summary)}</span></td>
        <td><select data-source-field="application_id" ${inherited ? "disabled" : ""}>${optionList(applications, summary.source.application_id || "other")}</select></td>
        <td><input data-source-field="project_id" value="${escapeHtml(summary.source.project_id || summary.source.scenario_id || "")}" placeholder="Project / case" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="equipment_purchase" value="${capex.equipment_purchase}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="direct_installation" value="${capex.direct_installation}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="energy" value="${annual.energy}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="chemicals" value="${annual.chemicals}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="labor_maintenance" value="${laborMaint}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="replacement" value="${annual.replacement}" ${inherited ? "readonly" : ""}></td>
        <td><input class="num" type="number" min="0" step="1" data-source-field="other" value="${annual.disposal + annual.other}" ${inherited ? "readonly" : ""}></td>
        <td>${inherited ? '<button type="button" class="ted-row-action" data-source-override>Override</button>' : '<button type="button" class="ted-row-remove" title="Remove application summary">×</button>'}</td>`;
      tr.querySelectorAll("[data-source-field]").forEach(el => {
        const field = el.dataset.sourceField;
        const handler = () => {
          const value = parseInput(el);
          if (field === "included") summary.included = value;
          else if (field === "application_id") { summary.source.application_id = value; summary.source.application_name = applicationName[value] || applicationName.other; if (summary._ui_manual) summary.summary_id = `${value}:${Date.now()}:${Math.random().toString(36).slice(2, 7)}`; }
          else if (field === "project_id") summary.source.project_id = value;
          else {
            summary.capex = summary.capex || {}; summary.capex.buckets = summary.capex.buckets || {};
            summary.opex = summary.opex || {}; summary.opex.annual = summary.opex.annual || {};
            if (["equipment_purchase", "direct_installation"].includes(field)) summary.capex.buckets[field] = value || 0;
            else if (field === "labor_maintenance") { summary.opex.annual.labor = 0; summary.opex.annual.maintenance = value || 0; }
            else if (field === "other") { summary.opex.annual.disposal = 0; summary.opex.annual.other = value || 0; }
            else summary.opex.annual[field] = value || 0;
          }
          markDirty(true); renderLineageCards();
        };
        el.addEventListener("input", handler); el.addEventListener("change", handler);
      });
      tr.querySelector("[data-source-override]")?.addEventListener("click", () => { rows[index] = convertToOverride(summary); renderSourceRows(); renderLineageCards(); markDirty(true); showReview("Inherited values overridden", "This source now uses an explicit local override while retaining the original summary identifier in its lineage metadata."); });
      tr.querySelector(".ted-row-remove")?.addEventListener("click", () => { rows.splice(index, 1); renderSourceRows(); renderLineageCards(); markDirty(true); });
      body.appendChild(tr);
    });
    renderLineageCards();
  }

  function renderLineageCards() {
    const root = document.getElementById("sourceLineageCards"); if (!root) return;
    const inherited = (state.source_summaries || []).filter(s => !s._ui_manual);
    if (!inherited.length) { root.innerHTML = '<p class="ted-empty-inline">No inherited application summaries loaded.</p>'; return; }
    root.innerHTML = inherited.map(summary => {
      const src = summary.source || {}, overridden = Boolean(summary._ui_override), lineage = src.override_of_summary_id || summary.summary_id || "—";
      const revision = [src.project_revision ? `Rev ${src.project_revision}` : "", src.scenario_id || "", src.calculation_revision || ""].filter(Boolean).join(" · ");
      return `<section class="twds-handoff-card"><div class="twds-handoff-card__route"><div><span>Source</span><strong>${escapeHtml(src.application_name || applicationName[src.application_id] || "Suite application")}</strong><small>${escapeHtml(src.project_id || "Standalone scope")}</small></div><span class="twds-handoff-card__arrow" aria-hidden="true">→</span><div><span>Receiving application</span><strong>Total Water Economics</strong><small>${overridden ? "Inherited basis with local override" : "Inherited economic summary"}</small></div></div><div class="ted-lineage-meta"><span>Lineage: ${escapeHtml(lineage)}</span>${revision ? `<span>${escapeHtml(revision)}</span>` : ""}<span>${escapeHtml(summary.currency || summary.basis?.currency || "")}</span></div></section>`;
    }).join("");
  }

  function importSummaryJson() {
    const input = document.getElementById("summaryImportText"); clearError();
    try {
      const parsed = JSON.parse(input.value || "{}"); let summaries;
      if (Array.isArray(parsed)) summaries = parsed; else if (Array.isArray(parsed.source_summaries)) summaries = parsed.source_summaries; else if (Array.isArray(parsed.input?.source_summaries)) summaries = parsed.input.source_summaries; else summaries = [parsed];
      summaries = summaries.filter(x => x && typeof x === "object").map(x => { const item = clone(x); delete item._ui_manual; delete item._ui_override; return item; });
      if (!summaries.length) throw new Error("No economic summaries were found in the JSON.");
      state.source_summaries = [...(state.source_summaries || []), ...summaries]; input.value = ""; renderSourceRows(); markDirty(true); showReview("Inherited economic data loaded", "Review project/revision lineage and any integration warnings before relying on the combined estimate.");
    } catch (err) { showError(`The economic-summary JSON could not be imported. ${err.message || err}`); }
  }

  function renderCostRows() {
    const body = document.getElementById("costItemRows"); body.innerHTML = "";
    (state.cost_items || []).forEach((item, index) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td><input data-cost-field="description" value="${escapeHtml(item.description)}"></td><td><select data-cost-field="bucket">${optionList(buckets, item.bucket)}</select></td><td><input data-cost-field="discipline" value="${escapeHtml(item.discipline || "")}"></td><td><input class="num" data-cost-field="quantity" type="number" min="0" step="0.01" value="${item.quantity ?? 1}"></td><td><input class="num" data-cost-field="unit_cost" type="number" min="0" step="1" value="${item.unit_cost ?? 0}"></td><td><select data-cost-field="source_type">${optionList(sources, item.source_type || "user")}</select></td><td><input data-cost-field="source_reference" value="${escapeHtml(item.source_reference || "")}" placeholder="Quote / database / basis"></td><td><button type="button" class="ted-row-remove" title="Remove cost item">×</button></td>`;
      tr.querySelectorAll("[data-cost-field]").forEach(el => { const field = el.dataset.costField; const handler = () => { item[field] = el.type === "number" ? (el.value === "" ? null : Number(el.value)) : el.value; markDirty(true); }; el.addEventListener("input", handler); el.addEventListener("change", handler); });
      tr.querySelector(".ted-row-remove").addEventListener("click", () => { state.cost_items.splice(index, 1); renderCostRows(); markDirty(true); }); body.appendChild(tr);
    });
  }

  function renderMaturityRows() {
    const root = document.getElementById("maturityRows"); root.innerHTML = "";
    Object.entries(maturityLabels).forEach(([key, label]) => {
      const row = document.createElement("label"); row.className = "ted-maturity-row";
      row.innerHTML = `<span>${label}</span><select aria-label="${escapeHtml(label)} maturity"><option value="0">Not available</option><option value="0.25">Preliminary</option><option value="0.5">Developing</option><option value="0.75">Defined</option><option value="1">Mature</option></select>`;
      const select = row.querySelector("select"); select.value = String((state.definition || {})[key] ?? 0); select.addEventListener("change", () => { state.definition[key] = Number(select.value); markDirty(true); }); root.appendChild(row);
    });
  }

  function money(v, digits = 1) {
    if (v == null || !Number.isFinite(Number(v))) return "—"; const n = Number(v), abs = Math.abs(n); let value, suffix;
    if (abs >= 1e9) { value = n / 1e9; suffix = "B"; } else if (abs >= 1e6) { value = n / 1e6; suffix = "M"; } else if (abs >= 1e3) { value = n / 1e3; suffix = "k"; } else { value = n; suffix = ""; }
    return `${state.project?.currency || "USD"} ${value.toLocaleString(undefined, {maximumFractionDigits: digits, minimumFractionDigits: digits})}${suffix}`;
  }
  function unitMoney(v, suffix = "") { return v == null || !Number.isFinite(Number(v)) ? "—" : `${state.project?.currency || "USD"} ${Number(v).toFixed(3)}${suffix}`; }
  function pct(v, digits = 0) { return v == null || !Number.isFinite(Number(v)) ? "—" : `${(Number(v) * 100).toFixed(digits)}%`; }
  function number(v, digits = 0) { return v == null || !Number.isFinite(Number(v)) ? "—" : Number(v).toLocaleString(undefined, {maximumFractionDigits: digits}); }
  function hierarchyRows(rows) { return rows.map(([label, value, major]) => `<div class="${major ? "major" : ""}"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`).join(""); }

  function renderResult(result) {
    lastResult = result; const h = result.cost_hierarchy, op = result.operating || {}, fin = result.finance || {};
    document.getElementById("resultTotalProjectCost").textContent = money(h.total_project_cost);
    document.getElementById("resultTIC").textContent = money(h.total_installed_cost);
    document.getElementById("resultCapital").textContent = money(h.total_capital_requirement);
    document.getElementById("resultAnnualizedCapex").textContent = money(op.annualized_capital_y);
    document.getElementById("resultOpex").textContent = money(op.annual_opex_y);
    document.getElementById("resultAnnualizedCost").textContent = money(op.combined_annual_cost_y);
    document.getElementById("resultLifecycleCost").textContent = money(op.lifecycle_cost_npv);
    document.getElementById("resultClass").textContent = result.maturity.recommended_class;
    document.getElementById("resultMaturity").textContent = `${pct(result.maturity.definition_maturity_score)} maturity`;
    document.getElementById("resultLcow").textContent = unitMoney(op.lcow, "/m³");
    document.getElementById("resultTariff").textContent = unitMoney(fin.required_tariff_for_target_dscr, "/m³");
    document.getElementById("resultDscr").textContent = fin.dscr == null ? "—" : `${Number(fin.dscr).toFixed(2)}×`;
    document.getElementById("resultAnnualProduct").textContent = number(op.annual_product_m3);

    document.getElementById("hierarchyRows").innerHTML = hierarchyRows([
      ["Purchased Equipment", money(h.purchased_equipment_cost)], ["Direct Installation", money(h.direct_installation_cost)], ["Total Direct Cost", money(h.total_direct_cost), true], ["Construction Indirects", money(h.construction_indirect_cost)], ["Total Installed Cost", money(h.total_installed_cost), true], ["Engineering / Procurement / PM", money(h.engineering_procurement_pm)], ["Owner Costs", money(h.owner_costs)], ["Before Contingency", money(h.project_cost_before_contingency), true], ["Contingency", money(h.contingency)], ["Escalation", money(h.escalation)], ["Total Project Cost", money(h.total_project_cost), true], ["Financing / IDC", money(h.financing_idc)], ["Working Capital", money(h.working_capital)], ["Total Capital Requirement", money(h.total_capital_requirement), true]
    ]);

    const agg = result.source_aggregation || {sources: [], warnings: [], opex: {}};
    const included = (agg.sources || []).filter(s => s.included);
    document.getElementById("sourceSummaryResult").innerHTML = included.map(s => `<article><div><strong>${escapeHtml(s.source.application_name)}</strong><small>${escapeHtml([s.source.project_id, s.source.project_revision ? `Rev ${s.source.project_revision}` : "", s.source.scenario_id].filter(Boolean).join(" · ") || "Standalone scope")}</small></div><div><span>${money(s.capex_total)} CAPEX</span><span>${money(s.opex.total)} / y OPEX</span></div></article>`).join("") || "<p>No application summaries included; result uses project-level inputs only.</p>";

    const prov = result.provenance || {distribution: []}; const dist = (prov.distribution || []).slice(0, 7).map(item => `<div><span>${escapeHtml(item.label)}</span><b>${pct(item.share)}</b></div>`).join("");
    document.getElementById("sourceQuality").innerHTML = `<strong>${escapeHtml(prov.label || "No cost basis")}</strong><p class="ted-copy">Weighted source-quality score: ${pct(prov.weighted_score)}</p><div class="ted-source-list">${dist}</div>`;

    const rec = result.reconciliation || {}, recEl = document.getElementById("reconciliationResult");
    if (rec.prior_total_project_cost == null) recEl.innerHTML = "<p>No prior estimate entered.</p>";
    else { const direction = rec.movement >= 0 ? "increase" : "decrease"; recEl.innerHTML = `<span>${escapeHtml(rec.prior_estimate_id || "Prior estimate")} → ${escapeHtml(result.estimate.estimate_id)}</span><strong>${money(Math.abs(rec.movement))} ${direction}</strong><small>${rec.movement_pct == null ? "" : `${Math.abs(rec.movement_pct * 100).toFixed(1)}% movement from prior Total Project Cost`}</small>`; }

    const sourceOpex = agg.opex || {};
    document.getElementById("opexBreakdownRows").innerHTML = hierarchyRows([
      ["Application energy", money(sourceOpex.energy)], ["Application chemicals", money(sourceOpex.chemicals)], ["Application labor", money(sourceOpex.labor)], ["Application maintenance", money(sourceOpex.maintenance)], ["Application replacement", money(sourceOpex.replacement)], ["Application disposal / other", money(Number(sourceOpex.disposal || 0) + Number(sourceOpex.other || 0))], ["Project-level OPEX", money(op.project_level_opex_y), true], ["Combined Annual OPEX", money(op.annual_opex_y), true]
    ]);
    document.getElementById("financeSummaryRows").innerHTML = hierarchyRows([
      ["Debt fraction", pct(fin.debt_fraction)], ["Debt amount", money(fin.debt_amount)], ["Equity amount", money(fin.equity_amount)], ["Interest rate", pct(fin.interest_rate, 2)], ["Debt tenor", `${number(fin.debt_tenor_years)} years`], ["Annual debt service", money(fin.annual_debt_service)], ["Target DSCR", fin.target_dscr == null ? "—" : `${Number(fin.target_dscr).toFixed(2)}×`, true]
    ]);

    const warnings = [...(agg.warnings || []), ...(result.methodology_notes || [])];
    document.getElementById("warningList").innerHTML = warnings.length ? warnings.map(w => `<div class="warning"><strong>Review</strong><p>${escapeHtml(w)}</p></div>`).join("") : "<p>No calculation warnings.</p>";
    document.getElementById("nextSteps").innerHTML = (result.maturity.next_steps || []).map(item => `<article><span>${Math.round(item.maturity * 100)}%</span><div><strong>${escapeHtml(item.label)}</strong><small>Definition gap to review</small></div></article>`).join("") || "";
    if (warnings.length) showReview("Economic basis requires review", `${warnings.length} integration or methodology item${warnings.length === 1 ? "" : "s"} should be reviewed in Warnings & Constraints.`); else clearReview();
  }

  function requestPayload() {
    const payload = clone(state); payload.model = "total_economic_design";
    payload.source_summaries = (payload.source_summaries || []).map(summary => { const out = clone(summary); if (out._ui_manual) out.currency = payload.project?.currency || "USD"; delete out._ui_manual; delete out._ui_override; return out; });
    if (payload.project && payload.operating && (payload.operating.capacity_m3d == null || payload.operating.capacity_m3d === 0)) payload.operating.capacity_m3d = payload.project.capacity_m3d;
    return payload;
  }

  function validateInputs() {
    const p = state.project || {}, op = state.operating || {};
    if (!p.project_name?.trim()) throw new Error("Enter a project name before calculating.");
    if (!p.currency?.trim()) throw new Error("Select the project reporting currency before calculating.");
    if (Number(op.availability) <= 0 || Number(op.availability) > 1) throw new Error("Availability must be greater than 0 and not exceed 1.0.");
    if (Number(op.project_life_years) <= 0) throw new Error("Project life must be greater than zero.");
  }

  async function calculate() {
    clearError(); clearReview(); setCalcState("validating", "Validating economic inputs…");
    try {
      validateInputs(); setCalcState("calculating", "Calculating combined project economics…");
      const headers = csrfHeaders({"Content-Type": "application/json", "X-TotalRO-Effective-Tier": "platinum"});
      const response = await fetch("/api/economics", {method: "POST", headers, body: JSON.stringify(requestPayload())}); const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Economic analysis failed.");
      renderResult(data); setCalcState("idle", "Economic results updated."); activatePanel("results");
    } catch (err) { setCalcState("failed", "Calculation failed."); showError(err.message || String(err)); }
  }

  function activatePanel(name) {
    document.querySelectorAll("[data-panel]").forEach(btn => { const active = btn.dataset.panel === name; btn.classList.toggle("active", active); if (active) btn.setAttribute("aria-current", "page"); else btn.removeAttribute("aria-current"); });
    document.querySelectorAll("[data-panel-content]").forEach(panel => panel.classList.toggle("active", panel.dataset.panelContent === name));
    const [title, subtitle] = panelTitles[name] || panelTitles.sources; document.getElementById("workspaceTitle").textContent = title; document.getElementById("workspaceSubtitle").textContent = subtitle; document.querySelector(".twds-workspace")?.scrollTo({top: 0, behavior: "smooth"});
  }

  function setModelMode(mode) {
    const labels = {quick: "Quick Economics", financial: "Financial Model", "project-finance": "Project Finance"};
    document.querySelectorAll("[data-model-mode]").forEach(button => { const active = button.dataset.modelMode === mode; button.classList.toggle("active", active); button.setAttribute("aria-checked", String(active)); });
    document.getElementById("activeModeStatus").textContent = `${labels[mode] || labels.quick} active`;
    document.querySelector("[data-twds-app-shell]")?.setAttribute("data-economics-mode", mode);
  }

  function openFirstRun() { const dialog = document.getElementById("firstRunDialog"); if (dialog && !dialog.open) dialog.showModal(); }
  function chooseStart(choice) {
    document.getElementById("firstRunDialog")?.close();
    if (choice === "twds") activatePanel("sources");
    else if (choice === "template") { activatePanel("overview"); showReview("Template assumptions visible", "Choose and review a template in Model Setup before calculating; no output is hidden or pre-calculated."); }
    else activatePanel("overview");
  }

  function resetState() {
    state = clone(starter); lastResult = null; currentProjectRevisionId = null;
    document.querySelectorAll("[data-path]").forEach(el => { const val = getPath(el.dataset.path); el.value = val == null ? "" : val; });
    renderSourceRows(); renderCostRows(); renderMaturityRows(); syncProjectHeader(); clearError(); clearReview(); activatePanel("sources"); markDirty(false); setCalcState("idle", "New economic project ready.");
  }

  function exportSnapshot() {
    const snapshot = {application: "Total Water Economics", contract: "twds.economic_project_snapshot", version: "0.3", exported_at: new Date().toISOString(), input: requestPayload(), result: lastResult};
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], {type: "application/json"}), a = document.createElement("a"); const project = (state.project?.project_name || "project").replace(/[^a-z0-9_-]+/gi, "_"), estimate = (state.project?.estimate_id || "E01").replace(/[^a-z0-9_-]+/gi, "_"); a.href = URL.createObjectURL(blob); a.download = `${project}_${estimate}_economic_snapshot.json`; a.click(); URL.revokeObjectURL(a.href);
  }

  function projectSnapshot() {
    return {format: "Total Water Economics Project", schema_version: 1, app_version: "0.3", project: clone(state.project || {}), economics: requestPayload(), result: lastResult};
  }

  async function saveProject() {
    if (!authEnabled()) { showReview("Project library unavailable", "Authenticated Suite project storage is not enabled in this build. Export Snapshot remains available."); return; }
    clearError();
    try {
      const method = currentProjectRevisionId ? "PUT" : "POST"; const url = currentProjectRevisionId ? `/api/projects/${currentProjectRevisionId}` : "/api/projects";
      const body = currentProjectRevisionId ? {snapshot: projectSnapshot()} : {product_id: "economics", snapshot: projectSnapshot()};
      const response = await fetch(url, {method, headers: csrfHeaders({"Content-Type":"application/json"}), body: JSON.stringify(body)}); const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Project could not be saved.");
      const meta = data.project || {}; currentProjectRevisionId = meta.id || currentProjectRevisionId; state.project.project_id = meta.visible_id || state.project.project_id; state.project.revision = meta.revision == null ? state.project.revision : `Rev ${meta.revision}`; syncProjectHeader(); markDirty(false); showReview("Project saved", `${meta.visible_id || "The project"} is stored in the Suite Project Library.`);
    } catch (err) {
      const message = /Unsupported Total Water Design Suite project format/i.test(String(err.message)) ? "Project storage for Total Water Economics requires the pending Suite Core project-format extension. Export Snapshot preserves this assessment until that shared dependency is integrated." : (err.message || String(err));
      showReview("Project save needs attention", message);
    }
  }

  async function openProjectLibrary() {
    const dialog = document.getElementById("projectLibraryDialog"), rows = document.getElementById("projectLibraryRows"), message = document.getElementById("projectLibraryMessage"); rows.innerHTML = "";
    if (!authEnabled()) { message.textContent = "Authenticated Suite project storage is not enabled in this build."; dialog.showModal(); return; }
    message.textContent = "Loading projects…"; dialog.showModal();
    try {
      const response = await fetch("/api/projects", {headers: csrfHeaders({})}); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Project Library could not be loaded.");
      const projects = (data.projects || []).filter(p => p.product_id === "economics"); message.textContent = projects.length ? `${projects.length} Total Water Economics project revision${projects.length === 1 ? "" : "s"}.` : "No Total Water Economics projects have been saved yet.";
      rows.innerHTML = projects.map(p => `<div class="ted-library-row"><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.visible_id)} · Rev ${p.revision}</small></div><button type="button" class="twds-button twds-button--secondary" data-open-project="${p.id}">Open</button></div>`).join("");
    } catch (err) { message.textContent = err.message || String(err); }
  }

  async function loadProject(revisionId) {
    clearError();
    try {
      const response = await fetch(`/api/projects/${revisionId}`, {headers: csrfHeaders({})}); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Project could not be opened.");
      const snapshot = data.snapshot || {}, restored = snapshot.economics || snapshot.input || null; if (!restored || typeof restored !== "object") throw new Error("This project does not contain a Total Water Economics snapshot.");
      state = clone(restored); delete state.model; lastResult = snapshot.result || null; currentProjectRevisionId = Number(revisionId); const meta = data.project || {}; state.project = state.project || {}; state.project.project_id = meta.visible_id || state.project.project_id; state.project.revision = meta.revision == null ? state.project.revision : `Rev ${meta.revision}`;
      document.querySelectorAll("[data-path]").forEach(el => { const val = getPath(el.dataset.path); el.value = val == null ? "" : val; }); renderSourceRows(); renderCostRows(); renderMaturityRows(); syncProjectHeader(); if (lastResult) renderResult(lastResult); markDirty(false); document.getElementById("projectLibraryDialog").close(); activatePanel(lastResult ? "results" : "sources");
    } catch (err) { showError(err.message || String(err)); }
  }

  async function createRevision() {
    if (!currentProjectRevisionId) { showReview("Save the project first", "Create the initial project before making a revision or copy."); return; }
    try {
      const response = await fetch(`/api/projects/${currentProjectRevisionId}/copy`, {method:"POST", headers:csrfHeaders({"Content-Type":"application/json"}), body:JSON.stringify({snapshot:projectSnapshot()})}); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Revision could not be created."); const meta=data.project||{}; currentProjectRevisionId=meta.id; state.project.project_id=meta.visible_id; state.project.revision=`Rev ${meta.revision}`; syncProjectHeader(); markDirty(false); showReview("Revision created", `${meta.visible_id} is now the active economic project revision.`);
    } catch (err) { showReview("Revision needs attention", err.message || String(err)); }
  }

  function handleProjectAction(action) {
    if (action === "new") { if (!window.TWDSAppUI?.dirty || confirm("Discard unsaved changes and start a new Total Water Economics project?")) { resetState(); openFirstRun(); } }
    else if (action === "library") openProjectLibrary();
    else if (action === "save") saveProject();
    else if (action === "revision") createRevision();
    else if (action === "save-as") showReview("Save As", "The current Suite project API creates controlled revisions rather than an independent duplicate family. Use Revision for now; Suite Core owns any broader project-lifecycle extension.");
    else if (action === "duplicate") showReview("Duplicate", "Independent project-family duplication is not exposed by the current shared Project Library API. No duplicate has been created.");
    else if (action === "handoff") { activatePanel("sources"); showReview("Handoff and lineage", "Economic handoffs are represented by twds.economic_summary v1.0 source summaries. Import or review the connected source lineage here."); }
  }

  function bindEvents() {
    document.querySelectorAll("[data-panel]").forEach(btn => btn.addEventListener("click", () => activatePanel(btn.dataset.panel)));
    document.querySelectorAll("[data-model-mode]").forEach(btn => btn.addEventListener("click", () => setModelMode(btn.dataset.modelMode)));
    document.querySelectorAll("[data-start-choice]").forEach(btn => btn.addEventListener("click", () => chooseStart(btn.dataset.startChoice)));
    document.getElementById("addSourceBtn").addEventListener("click", () => { state.source_summaries = state.source_summaries || []; state.source_summaries.push(newSource(state.source_summaries.length ? "other" : "ro")); renderSourceRows(); markDirty(true); });
    document.getElementById("importSummaryBtn").addEventListener("click", importSummaryJson);
    document.getElementById("addCostItemBtn").addEventListener("click", () => { state.cost_items = state.cost_items || []; state.cost_items.push({item_id:`item-${Date.now()}`,description:"New project cost item",bucket:"equipment_purchase",discipline:"Project",quantity:1,unit:"LS",unit_cost:0,source_type:"user",source_reference:""}); renderCostRows(); markDirty(true); });
    document.getElementById("calculateEstimateBtn").addEventListener("click", calculate);
    document.getElementById("exportEstimateBtn").addEventListener("click", exportSnapshot);
    document.getElementById("reportEstimateBtn").addEventListener("click", () => { if (!lastResult) { showReview("Calculate before reporting", "Run the economic calculation before generating the report view."); return; } activatePanel("results"); setTimeout(() => window.print(), 80); });
    document.addEventListener("twds:project-action", e => handleProjectAction(e.detail?.action));
    document.getElementById("projectLibraryDialog").addEventListener("click", e => { if (e.target.matches("[data-dialog-close]")) e.currentTarget.close(); const open = e.target.closest("[data-open-project]"); if (open) loadProject(open.dataset.openProject); });
  }

  function init() { bindPathInputs(); renderSourceRows(); renderCostRows(); renderMaturityRows(); syncProjectHeader(); bindEvents(); setModelMode("quick"); activatePanel("overview"); markDirty(false); setCalcState("idle", "Total Water Economics ready."); openFirstRun(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
