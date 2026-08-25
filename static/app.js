const $=s=>document.querySelector(s); let mode='water'; let membranes=[]; let seawaterPresets=[]; let lastResult=null;
let caseResults={}; let modeStates={}; let advancedDesignResult=null; let advancedDesignInput={};
let computeCapabilities=null; let computeLiveStatus=null; let lastComputeRun=null; let computePollTimer=null; let computePanelOpen=false; let lastGpuTest=null; let gpuTestRunning=false; let lastDesignOptimization=null; let designOptimizationRunning=false;
let activeCalculationController=null; let calculationCancelRequested=false;
let canonicalCalculationInFlight=false; let canonicalCalculationSequence=0;
let waterProfile={}; let lastChemistryResult=null; let chemistryStream='feed'; let chemistryTechnology='auto'; let waterBalanceNotice='';
let embeddedChemistryCache={}; let tailChemistryCache={}; let embeddedChemistryStreamByMode={multistage:'concentrate',single:'concentrate',px:'concentrate',interstage_px:'concentrate',interstage:'concentrate',biturbo:'concentrate',dweer:'concentrate',pelton:'concentrate'};
let currentUnits={flow:'m3/h',pressure:'bar',flux:'LMH'};
let resultSubtabByMode={multistage:'performance',single:'performance',px:'performance',interstage_px:'performance',interstage:'performance',biturbo:'performance',dweer:'performance',pelton:'performance'};
let turboDesignLocks={single:{case:'auto',stale:true,locked_fields:null,design:null},interstage:{case:'auto',stale:true,locked_fields:null,design:null},biturbo:{inter_case:'auto',feed_case:'auto',stale:true,locked_fields:null,design:null}};
const MAX_CASES=10; let activeCase=1; let caseStore={}; let caseSetupNotice=''; let summaryTechnology='auto';
let scenarioMatrixState={normal_trains:10,required_capacity_m3d:100000,maintain_capacity_nminus1:true}; let scenarioMatrixLastRun=null; let scenarioRunCancelled=false;
const economicDefaults={product_capacity_m3d:'',availability:0.95,electricity_price:0.10,project_life:25,discount_rate:0.06,base_capex_per_m3d:'',turbo_ro_equipment_saving:0.15,turbo_electrical_saving:0.15,turbo_building_saving:0.05,turbo_startup_saving:0.10,turbo_engineering_saving:0.10,biturbo_ro_equipment_adder:0,pretreatment_flow_exponent:1,building_flow_exponent:1,fixed_om_px:0,fixed_om_single:0,fixed_om_biturbo:0};
let economicState={...economicDefaults}; let lastEconomicResult=null;
const todayIso=()=>{const d=new Date();d.setMinutes(d.getMinutes()-d.getTimezoneOffset());return d.toISOString().slice(0,10);};
let projectMeta={project_name:'Total RO Design Project',user:'',client:'',project_date:todayIso(),revision:'Rev 0',project_location:'',project_country_code:'',project_country:''};
let serverProjectRecord=null; let projectLibraryCache=[];
let lastReportableError=null; let feedbackReporting=false;

// v0.2 Hotfix 10 — centralized cumulative tier entitlements.
// Entry ⊂ Silver ⊂ Gold ⊂ Platinum.  The desktop alpha defaults to an
// administrator Platinum account so the four preview buttons can emulate the
// customer experience without mutating the project or the actual license.
const TIER_ORDER={entry:0,silver:1,gold:2,platinum:3};
const ACID_PROPERTY_PROFILES=Object.freeze({hcl:Object.freeze({acid_type:'hcl',solution_strength_pct:32.0,solution_density_kg_l:1.16,molecular_weight_g_mol:36.46094,equivalents_per_mole:1}),h2so4:Object.freeze({acid_type:'h2so4',solution_strength_pct:93.0,solution_density_kg_l:1.83,molecular_weight_g_mol:98.07848,equivalents_per_mole:2})});

const FEATURE_REGISTRY={
  water_quality:{min:'entry',label:'Water Quality',maturity:'stable'},
  manual_plant_design:{min:'entry',label:'Plant Design',maturity:'stable'},
  hybrid_membrane_design:{min:'entry',label:'Hybrid membrane design',maturity:'stable'},
  basic_results:{min:'entry',label:'Results',maturity:'stable'},
  basic_report:{min:'entry',label:'Basic projection report',maturity:'stable'},
  project_save_load:{min:'entry',label:'Project save/load',maturity:'stable'},
  multi_case:{min:'silver',label:'Multiple cases',maturity:'stable'},
  hydraulic_envelope:{min:'silver',label:'Hydraulic Envelope',maturity:'stable'},
  case_comparison:{min:'silver',label:'Case comparison',maturity:'stable'},
  full_engineering_report:{min:'silver',label:'Full Engineering Report',maturity:'stable'},
  vcmp_pump_selection:{min:'silver',label:'VCMP pump database',maturity:'stable'},
  advanced_design:{min:'gold',label:'Advance Design',maturity:'stable'},
  auto_design:{min:'silver',label:'Auto Design',maturity:'stable'},
  erd:{min:'gold',label:'Energy-recovery devices',maturity:'stable'},
  economics:{min:'gold',label:'Economics',maturity:'stable'},
  design_optimizer:{min:'platinum',label:'Design Optimizer',maturity:'stable'},
  scenario_matrix:{min:'platinum',label:'Scenario Matrix',maturity:'internal'},
  background_optimizer:{min:'platinum',label:'Background Optimizer',maturity:'internal'},
  operations_normalization:{min:'platinum',label:'Operations / normalization',maturity:'internal'}
};
const MODE_FEATURE={water:'water_quality',chemistry:'water_quality',multistage:'manual_plant_design',summary:'basic_results',envelope:'hydraulic_envelope',comparison:'case_comparison',advanced:'advanced_design',single:'erd',px:'erd',interstage_px:'erd',interstage:'erd',biturbo:'erd',dweer:'erd',pelton:'erd',economic:'economics',scenario:'scenario_matrix'};
const SILVER_PUMP_FIELDS=new Set(['pump_curve_basis','vcmp_min_vfd_hz','vcmp_max_vfd_hz','vcmp_flow_margin','vcmp_head_margin','vcmp_reduced_impeller_eta_penalty_pp','vcmp_low_speed_eta_derate_pp_per_10pct','vcmp_reference_rpm_60','pump_bep_flow','pump_bep_dp','pump_shutoff_head_ratio']);
let entitlementContext={role:'admin',licensed_tier:'platinum',effective_tier:'platinum',is_admin:true,features:{}};
let effectiveTier='platinum';
function normalizeTier(v,fallback='entry'){const t=String(v||'').trim().toLowerCase();return Object.prototype.hasOwnProperty.call(TIER_ORDER,t)?t:fallback;}
function featureMinimumTier(featureId){return FEATURE_REGISTRY[featureId]?.min||'entry';}
function tierAllows(featureId,tier=effectiveTier){const f=FEATURE_REGISTRY[featureId];if(!f)return false;const level=TIER_ORDER[normalizeTier(tier)]>=TIER_ORDER[f.min];const mature=f.maturity==='stable'||Boolean(entitlementContext?.is_admin);return level&&mature;}
function featureLockMessage(featureId){const f=FEATURE_REGISTRY[featureId]||{label:featureId,min:'entry'};if(f.maturity!=='stable'&&!entitlementContext?.is_admin)return `${f.label} is not yet enabled for customer accounts.`;return `${f.label} requires the ${f.min[0].toUpperCase()+f.min.slice(1)} tier or higher.`;}
function modeEntitlementAccess(modeKey){const feature=MODE_FEATURE[modeKey];return !feature||tierAllows(feature)?{ok:true,feature}:{ok:false,feature,reason:featureLockMessage(feature)};}
function csrfToken(){return document.querySelector('meta[name="csrf-token"]')?.content||'';}
function entitlementRequestHeaders(existing={}){return {...existing,'X-TotalRO-Effective-Tier':effectiveTier};}
function totalroFetch(url,options={}){
  const opts={...options};opts.headers=entitlementRequestHeaders(opts.headers||{});opts.credentials=opts.credentials||'same-origin';
  const method=String(opts.method||'GET').toUpperCase();const token=csrfToken();
  if(token&&!['GET','HEAD','OPTIONS','TRACE'].includes(method))opts.headers={...opts.headers,'X-CSRFToken':token};
  return window.fetch(url,opts);
}
function configureEntitlements(payload={}){
  const role=String(payload.role||'user').toLowerCase();const licensed=normalizeTier(payload.licensed_tier,'entry');
  entitlementContext={...payload,role,licensed_tier:licensed,is_admin:role==='admin'};
  if(payload.account?.full_name&&!projectMeta.user)projectMeta.user=String(payload.account.full_name);
  Object.entries(payload.features||{}).forEach(([id,f])=>{if(FEATURE_REGISTRY[id])FEATURE_REGISTRY[id]={min:normalizeTier(f.minimum_tier,FEATURE_REGISTRY[id].min),label:f.label||FEATURE_REGISTRY[id].label,maturity:f.maturity||FEATURE_REGISTRY[id].maturity};});
  const remembered=sessionStorage.getItem('totalrodesign-admin-tier-preview');
  const requested=entitlementContext.is_admin?normalizeTier(remembered,licensed):licensed;
  effectiveTier=entitlementContext.is_admin?requested:licensed;
  entitlementContext.effective_tier=effectiveTier;applyTierEntitlements();
}
function enforceTierCaseAccess(){
  if(tierAllows('multi_case'))return;const ids=Object.keys(caseStore||{}).map(Number).sort((a,b)=>a-b);const first=ids[0];
  if(first&&activeCase!==first)loadCaseGlobals(first);
}
function renderTierPreview(){
  const bar=$('#adminTierPreview');if(!bar)return;bar.hidden=!entitlementContext?.is_admin;
  const licensed=normalizeTier(entitlementContext?.licensed_tier,'entry');
  bar.querySelectorAll('[data-tier-preview]').forEach(btn=>{const t=normalizeTier(btn.dataset.tierPreview);btn.classList.toggle('active',t===effectiveTier);btn.setAttribute('aria-pressed',t===effectiveTier?'true':'false');btn.disabled=false;btn.title='';});
  const status=$('#tierPreviewStatus');if(status)status.textContent=`Viewing as ${effectiveTier[0].toUpperCase()+effectiveTier.slice(1)}`;
  const note=$('#tierPreviewNote');if(note)note.textContent=`Preview only · licensed account unchanged (${licensed.toUpperCase()}) · project data is preserved`;
}
function applyTierEntitlements(){
  document.documentElement.dataset.effectiveTier=effectiveTier;renderTierPreview();
  document.querySelectorAll('[data-feature-id]').forEach(el=>{const feature=el.dataset.featureId,allowed=tierAllows(feature);el.hidden=!allowed;el.classList.toggle('tier-hidden',!allowed);if(!allowed)el.title=featureLockMessage(feature);});
  const fullReport=$('#printResultsBtn');if(fullReport)fullReport.hidden=!tierAllows('full_engineering_report');
  const reportLabel=$('#printTabBtn span:not(.sr-only)');if(reportLabel)reportLabel.textContent=tierAllows('full_engineering_report')?'Report':'Basic Report';
  const badge=$('#effectiveTierBadge');if(badge){badge.textContent=effectiveTier.toUpperCase();badge.dataset.tier=effectiveTier;}
  const caseDescription=$('#caseToolbarDescription');if(caseDescription)caseDescription.textContent=tierAllows('multi_case')?'Up to 10 independent water-quality and operating scenarios':'1 active case · Silver unlocks up to 10 independent cases';
  document.querySelectorAll('[data-tier-field-feature]').forEach(el=>{el.hidden=!tierAllows(el.dataset.tierFieldFeature);});
  updateWorkflowGates();updateErdNavAccess();
}
function refreshTierView(){
  enforceTierCaseAccess();const target=modeEntitlementAccess(mode).ok?mode:'water';
  if(target!==mode){mode=target;lastResult=caseResults[mode]||null;}
  updateWaterWorkspaceTabs();renderFields(modeStates[mode]||convertedDefaults());
  if(mode==='water')renderCurrentWaterChemistry();else if(mode==='summary')$('#results').innerHTML=summaryResults();else if(mode==='comparison')$('#results').innerHTML=comparisonResults();else if(mode==='envelope')$('#results').innerHTML=hydraulicEnvelopeStatusHtml();else if(mode==='advanced')$('#results').innerHTML=advancedResultHtml();else if(mode==='economic')$('#results').innerHTML=lastEconomicResult?economicResults(lastEconomicResult):'<p class="muted">Run the comparison after calculating the technology cases you want to evaluate.</p>';else if(caseResults[mode]){lastResult=caseResults[mode];show(lastResult);}else $('#results').innerHTML='<p class="muted">Enter required inputs and calculate.</p>';
  renderCaseBar();applyTierEntitlements();
}
function setAdminTierPreview(tier){
  if(!entitlementContext?.is_admin)return;const licensed=normalizeTier(entitlementContext.licensed_tier,'entry'),requested=normalizeTier(tier,licensed);
  persistActiveCase();effectiveTier=requested;entitlementContext.effective_tier=effectiveTier;sessionStorage.setItem('totalrodesign-admin-tier-preview',effectiveTier);refreshTierView();
}


// v18.2 suite shell. Only explicit Light and Dark appearance modes are supported.
const WORKSPACE_META={
  water:['WATER','Water Quality','Define the common source-water, temperature and membrane-condition basis used by every technology and operating case.'],
  chemistry:['WATER','Chemistry Results','Review electroneutrality, pH-dependent speciation, scaling indices and mineral saturation for the active case.'],
  multistage:['PROJECT','Plant Design','Fast manual membrane projection. Define the RO array and solve the basic membrane system before advanced optimization.'],
  advanced:['PROJECT','Advance Design','Warm-start Auto Design and numerical optimization from the latest converged Plant Design seed.'],
  envelope:['PROJECT','Hydraulic Envelope','Seeded hydraulic-envelope study generated from the active Plant Design Base Seed.'],
  single:['DESIGN','Single Stage Turbo Charger','Size and evaluate a locked turbocharger duty across membrane and hydraulic operating cases.'],
  px:['DESIGN','Isobaric Chamber','Evaluate a single-stage isobaric chamber configuration with explicit HPP and circulation/booster duties.'],
  interstage_px:['DESIGN','Interstage Isobaric Chamber','Evaluate 2–4 stage BWRO/SWRO isobaric recovery with automatic booster, direct-connection or throttling logic from the final-stage brine pressure.'],
  interstage:['DESIGN','Interstage Turbocharger','Couple two-stage RO hydraulics with an interstage turbocharger and off-design performance.'],
  biturbo:['DESIGN','BiTurbo™','Coordinate feed and interstage turbochargers across a coupled two-stage RO system.'],
  dweer:['DESIGN','DWEER','Evaluate a positive-displacement work-exchanger ERD using the final-stage brine duty and the attached DWEER screening basis.'],
  pelton:['DESIGN','Pelton Turbine','Evaluate a common-shaft Pelton energy-recovery turbine using the final-stage brine duty and runner/shaft screening equations.'],
  comparison:['ANALYSIS','Comparison','Compare RO, pretreatment and total SEC across calculated energy-recovery technologies.'],
  scenario:['PROJECT','Scenario Matrix','Plant Design scenario analysis: run every populated solution across N and N−1 and the four hydraulic-envelope conditions.'],
  summary:['ANALYSIS','Case Summary','Review selected case and operating-condition information.'],
  economic:['ANALYSIS','Economics','Compare CAPEX, annual energy, lifecycle cost and LCOW for the selected technology cases.']
};
function applyTheme(theme){
  const allowed=['dark','light'];theme=allowed.includes(theme)?theme:'dark';
  document.documentElement.dataset.theme=theme;localStorage.setItem('totalrodesign-theme',theme);
  const sel=$('#themeSelect');if(sel&&sel.value!==theme)sel.value=theme;
  const icon=$('#themeIcon');if(icon)icon.src=theme==='light'?'/static/icons_v18/sun.svg':'/static/icons_v18/moon.svg';
}
function initTheme(){const saved=localStorage.getItem('totalrodesign-theme')||localStorage.getItem('calcospower-theme');applyTheme(saved==='light'?'light':'dark')}
function updateSolutionNavState(){
  document.querySelectorAll('.solution-tab[data-mode]').forEach(btn=>{const k=btn.dataset.mode;const configured=processModeConfigured(k,modeStates?.[k])||Boolean(caseResults?.[k]);let dot=btn.querySelector('.solution-dot');if(configured&&!dot){dot=document.createElement('i');dot.className='solution-dot';btn.appendChild(dot)}else if(!configured&&dot)dot.remove();});
  const conventional=$('#conventionalSolutionBtn');if(conventional){const configured=processModeConfigured('multistage',modeStates?.multistage)||Boolean(caseResults?.multistage);let dot=conventional.querySelector('.solution-dot');if(configured&&!dot){dot=document.createElement('i');dot.className='solution-dot';conventional.appendChild(dot)}else if(!configured&&dot)dot.remove();}
}

const ERD_MODES=['px','interstage_px','biturbo','single','interstage','dweer','pelton'];
function basePlantSignature(state=modeStates.multistage||{}){
  const n=Math.max(1,Math.min(4,Number(state.stage_count||1)));const auto=String(state.design_mode||'manual')==='auto';
  const keys=['design_mode','max_design_flux_lmh','membrane_coupling','permeate_pressure','suction_pressure','operating_trains','standby_trains','required_capacity_m3d','energy_recovery_mode','solution_px','solution_interstage_px','solution_single','solution_interstage','solution_biturbo','solution_dweer','solution_pelton'];
  if(auto){keys.push('target_recovery');}else{keys.push('solve_basis','feed_flow');const basis=String(state.solve_basis||'recovery');if(basis==='pressure')keys.push('membrane_pressure_1');else if(basis==='product')keys.push('target_product_flow');else keys.push('target_recovery');}
  for(let i=1;i<=n;i++)keys.push(`membrane_${i}`,`vessels_${i}`,`elements_per_vessel_${i}`,`membrane_design_mode_${i}`,`membrane_recipe_${i}`);
  keys.push('interstage_control_objective','interstage_balance_basis');for(let i=2;i<=n;i++)keys.push(`interstage_equipment_${i}`,`interstage_boost_${i}`,`interstage_target_recovery_${i}`,`interstage_maximize_turbo_energy_${i}`);
  const o={};keys.forEach(k=>o[k]=state?.[k]??null);o.stage_count=n;o.source_water_type=waterProfile.source_water_type||null;
  o.water_tds=Number(waterProfile.analysis_tds||waterProfile.feed_tds||0);o.water_ph=Number(waterProfile.feed_ph||0);o.water_temp=Number(waterProfile.temperature_c||0);o.water_ff=Number(waterProfile.fouling_factor||0);o.water_sp=Number(waterProfile.salt_passage_factor||0);return JSON.stringify(o);
}
function basePlantIsCurrent(){const st=modeStates.multistage||{};return Boolean(caseResults.multistage)&&st._last_calculated_signature===basePlantSignature(st);}
function biturboTdsScreen(result=caseResults.multistage){
  const compTds=c=>c&&typeof c==='object'?Object.values(c).reduce((a,v)=>a+(Number(v)||0),0):NaN;
  const n=Math.max(1,Math.min(4,Number(result?.stage_count||modeStates.multistage?.stage_count||1)));
  const tdsAt=i=>{const v=compTds(result?.[`stage${i}_feed_composition_mg_l`]);if(Number.isFinite(v)&&v>0)return v;if(i===1)return Number(waterProfile.analysis_tds||waterProfile.feed_tds||0);return Number(result?.[`stage${i}_feed_tds_ppm`]||0)};
  const candidates=[];
  if(!result){const t=tdsAt(1);return {eligible:t>=30000,min_tds:t,values:[t],candidates:[],reason:t>=30000?'':'System feed TDS is below 30,000 mg/L.'};}
  if(n===1){const t=tdsAt(1);return {eligible:t>=30000,min_tds:t,values:[t],candidates:[],reason:t>=30000?'':'System feed TDS is below 30,000 mg/L.'};}
  if(n===2){
    const qf=Number(result.feed_flow||0),q1=Number(result.reject_flow_1||0),q2=Number(result.reject_flow_2||result.reject_flow_final||0);
    const feedRR=qf>0?q1/qf:0,interRR=q1>0?q2/q1:0;
    const feed={position:'feed',label:'Feed turbo',tds:tdsAt(1),reject_ratio:feedRR,eligible:tdsAt(1)>=30000&&feedRR>0.20};
    const inter={position:2,label:'Stage 1 → 2',tds:tdsAt(2),reject_ratio:interRR,eligible:tdsAt(2)>=30000&&interRR>0.20};
    candidates.push(feed,inter);const vals=candidates.map(x=>x.tds).filter(x=>x>0);return {eligible:candidates.every(x=>x.eligible),min_tds:vals.length?Math.min(...vals):0,values:vals,candidates,reason:candidates.every(x=>x.eligible)?'':'Both legacy BiTurbo turbochargers must have local TDS ≥ 30,000 mg/L and Qtr/Qpf > 0.20.'};
  }
  const qtr=Number(result.reject_flow_final||result[`reject_flow_${n}`]||0);
  for(let i=2;i<=n;i++){const qpf=Number(result[`reject_flow_${i-1}`]||0),rr=qpf>0?qtr/qpf:0,t=tdsAt(i);candidates.push({position:i,label:`Stage ${i-1} → ${i}`,tds:t,reject_ratio:rr,eligible:t>=30000&&rr>0.20});}
  const eligibleCandidates=candidates.filter(x=>x.eligible),vals=candidates.map(x=>x.tds).filter(x=>x>0);
  return {eligible:eligibleCandidates.length>=2,min_tds:vals.length?Math.min(...vals):0,values:vals,candidates,eligible_candidates:eligibleCandidates,reason:eligibleCandidates.length>=2?'':'BiTurbo needs at least two interstage turbo positions with local pump-side feed TDS ≥ 30,000 mg/L and Qtr/Qpf > 0.20.'};
}
function erdModeAccess(modeKey){
  if(!ERD_MODES.includes(modeKey))return {ok:true};
  if(!tierAllows('erd'))return {ok:false,reason:featureLockMessage('erd'),feature:'erd'};
  const base=modeStates.multistage||{},n=Math.max(1,Math.min(4,Number(base.stage_count||1)));
  if(!processModeConfigured('multistage',base))return {ok:false,reason:'Complete the Plant Design inputs first.'};
  if(!basePlantIsCurrent())return {ok:false,reason:'Calculate the current Plant Design before opening ERD configurations.'};
  if(['interstage_px','interstage','biturbo'].includes(modeKey)&&n<2)return {ok:false,reason:'This ERD requires at least two RO stages.'};
  if(modeKey==='single'&&n!==1)return {ok:false,reason:'Single Stage Turbocharger is available only for a one-stage Plant Design.'};
  if(modeKey==='biturbo'){const scr=biturboTdsScreen();if(!scr.eligible)return {ok:false,reason:scr.reason||'BiTurbo is unavailable at the current hydraulic/TDS conditions.'};}
  return {ok:true};
}
function ensureErdWorkspaceFromBase(modeKey){const base=modeStates.multistage||{};if(!basePlantIsCurrent())return;const key={px:'solution_px',interstage_px:'solution_interstage_px',single:'solution_single',interstage:'solution_interstage',biturbo:'solution_biturbo',dweer:'solution_dweer',pelton:'solution_pelton'}[modeKey];if(!key)return;if(modeStates[modeKey]?.generated_from_base_plant&&modeStates[modeKey]?._base_plant_signature===base._last_calculated_signature)return;const old=base[key];base[key]=true;modeStates.multistage=base;populateSelectedSolutions(base,false);base[key]=old;modeStates.multistage={...base};}
function updateErdNavAccess(){
  document.querySelectorAll('.solution-tab[data-mode]').forEach(btn=>{const k=btn.dataset.mode;if(!ERD_MODES.includes(k))return;const a=erdModeAccess(k);btn.disabled=!a.ok;btn.classList.toggle('erd-locked',!a.ok);btn.title=a.ok?'':a.reason;});
  const add=$('#addSolutionBtn');if(add){const entitled=tierAllows('erd'),ready=basePlantIsCurrent();add.disabled=!entitled||!ready;add.title=!entitled?featureLockMessage('erd'):(ready?'':'Calculate the Plant Design Basis before opening or adding ERD configurations.');}
}
function invalidateDerivedResultsFromBasePlant(){
  ERD_MODES.forEach(k=>{if(modeStates[k]?.generated_from_base_plant)caseResults[k]=undefined;});scenarioMatrixLastRun=null;embeddedChemistryCache={};tailChemistryCache={};lastEconomicResult=null;
  for(const c of Object.values(caseStore||{})){if(c?.scenarioMeta)c.caseResults={};}
}

function updateWorkspaceChrome(){
  const [group,title,subtitle]=WORKSPACE_META[mode]||WORKSPACE_META.water;
  const e=$('#workspaceEyebrow'),t=$('#workspaceTitle'),st=$('#workspaceSubtitle');if(e)e.textContent=`${group} WORKSPACE`;if(t)t.textContent=title;if(st)st.textContent=subtitle;
  const allIds=Object.keys(caseStore||{}),visibleIds=tierAllows('multi_case')?allIds:allIds.slice(0,1),project=$('#projectStatusTitle'),meta=$('#projectStatusMeta');
  if(project)project.textContent=projectMeta.project_name||'Total RO Design Project';
  if(meta){const client=projectMeta.client?` · ${projectMeta.client}`:'';const projectId=serverProjectRecord?.visible_id?` · ${escapeHtml(serverProjectRecord.visible_id)}`:'';const n=visibleIds.length||1;const preserved=!tierAllows('multi_case')&&allIds.length>n?` · ${allIds.length-n} preserved`:'';meta.innerHTML=`<i></i> Case ${activeCase} · ${n} operating case${n===1?'':'s'}${preserved}${projectId}${escapeHtml(client)}`;}
  const layout=document.querySelector('.layout'),resultsPanel=document.querySelector('.results');
  const waterHasResults=mode==='water'&&Boolean(lastChemistryResult);
  const waterOnly=mode==='water'&&!waterHasResults;
  if(layout)layout.classList.toggle('water-only',waterOnly);if(resultsPanel)resultsPanel.hidden=waterOnly;updateSolutionNavState();updateErdNavAccess();
}

// v18.2 Suite UI — free multistage plant design added; validated membrane osmotic/transport and carbonate thermodynamics retained. Guided errors retained from v16.7. Keep the red inline error for traceability,
// but also surface a prominent bubble that explains likely causes and useful next steps.
function errorGuidance(message,context='calculation'){
  const m=String(message||'').toLowerCase();
  if(m.includes('failed to fetch')||m.includes('could not reach the local calculation engine')||m.includes('network')||m.includes('connection')){
    return {title:'Local calculation engine not reachable',tips:[
      'Keep the Total RO Design desktop controller window open while calculating.',
      'Retry the calculation once. If the local server stopped, close Total RO Design and reopen the executable under dist\\TotalRODesign.',
      'If the same input repeatedly disconnects the engine, save the project and report the case so the failing solver path can be reproduced.'
    ]};
  }
  if(m.includes('did not converge')||m.includes('could not be balanced')||m.includes('no valid pressure range')||m.includes('outside the solvable range')||m.includes('no valid stage 2')||m.includes('no valid stage 3')||m.includes('auto design')||m.includes('multistage')){
    const stage2=m.includes('stage 2')||context==='interstage';
    return {title:stage2?'Coupled Stage 2 solution did not converge':'Membrane / hydraulic solution did not converge',tips:stage2?[
      'Reduce overall recovery or Stage 2 duty so the tail elements operate farther from their hydraulic/osmotic limit.',
      'Increase Stage 2 membrane area (more vessels/elements) or select a higher-permeability / higher-pressure-rated membrane.',
      'Review interstage boost, turbine discharge pressure and the locked turbo design case; an extreme locked duty can remove the feasible pressure intersection.'
    ]:[
      'Reduce recovery or permeate-flow demand, or increase membrane area to reduce element flux.',
      'Check feed/permeate pressure, turbine discharge pressure and the selected membrane pressure limit.',
      'Try another membrane or a less aggressive duty point, then recalculate before using the flux-balance optimizer.'
    ]};
  }
  if(m.includes('pressure limit')||m.includes('above the selected membrane')||m.includes('maximum operating pressure')){
    return {title:'Requested duty exceeds a membrane pressure limit',tips:[
      'Reduce recovery/permeate demand or turbo boost.',
      'Increase membrane area to lower the required feed pressure.',
      'Select a membrane with an appropriate pressure rating for this duty.'
    ]};
  }
  if(m.includes('mandatory')||m.includes('required')||m.includes('enter a valid')||m.includes('select a membrane')){
    return {title:'Input data needs attention',tips:[
      'Review the highlighted mandatory inputs and confirm the selected solve basis (P→Q, Q→P or R→P).',
      'Confirm membrane, vessel count, elements per vessel and pressure/flow units.',
      'Recalculate after correcting the input rather than changing calculated output fields directly.'
    ]};
  }
  return {title:'Calculation could not be completed',tips:[
    'Review the last input changed and confirm that the requested operating point is physically feasible.',
    'Try a less aggressive recovery/flux condition or increase membrane area.',
    'If the error repeats, save the project so the exact case can be reproduced.'
  ]};
}
function clearCalcError(){const e=$('#error');if(e)e.textContent='';const host=$('#errorBubbleHost');if(host)host.innerHTML='';}
function showCalcError(error,context='calculation'){
  const raw=error?.message||String(error||'Calculation error');
  const message=(error?.kind==='network'&&!raw.toLowerCase().includes('failed to fetch'))?`Failed to fetch — ${raw}`:raw;
  const inline=$('#error');if(inline)inline.textContent=message;
  const host=$('#errorBubbleHost');if(!host)return;
  const g=errorGuidance(message,context);
  lastReportableError={message,context,at:new Date().toISOString(),mode,case_id:activeCase};
  host.innerHTML=`<aside class="error-bubble" role="alert"><div class="error-bubble-head"><div><span>TOTAL RO DESIGN GUIDANCE</span><strong>${escapeHtml(g.title)}</strong></div><button type="button" class="error-bubble-close" aria-label="Dismiss error guidance">×</button></div><p>${escapeHtml(message)}</p><div class="error-bubble-help"><strong>Suggested actions</strong><ul>${g.tips.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul></div><div class="error-report-actions"><button type="button" class="ghost" id="copyDebugPromptBtn">Copy ChatGPT debugging prompt</button><button type="button" class="primary-inline" id="reportIssueBtn">Report this issue</button></div></aside>`;
  host.querySelector('.error-bubble-close')?.addEventListener('click',()=>{host.innerHTML=''});
  host.querySelector('#copyDebugPromptBtn')?.addEventListener('click',()=>copyDebugPrompt());
  host.querySelector('#reportIssueBtn')?.addEventListener('click',()=>reportCurrentIssue());
}
function buildChatGptDebugPrompt(err=lastReportableError){
  const e=err||{message:'Unknown error',context:'calculation'};
  return `ChatGPT investigation prompt: Investigate a potential Total RO Design v0.2 calculation error.\n\nWorkspace: ${mode}\nCase: ${activeCase}\nContext: ${e.context||'calculation'}\nError: ${e.message||'Unknown error'}\n\nUse the attached Total RO Design project-state JSON and screenshots from all captured tabs. Reproduce the engineering calculation, identify whether this is an input/feasibility problem, numerical-convergence problem, unit/variable mapping problem, or a calculation defect. Show the governing equations and expected result before proposing any code change. Preserve the existing calculation architecture unless the evidence requires a change.`;
}
async function copyDebugPrompt(){const text=buildChatGptDebugPrompt();try{await navigator.clipboard.writeText(text);alert('ChatGPT debugging prompt copied to the clipboard.')}catch(_){window.prompt('Copy this ChatGPT debugging prompt:',text)}}
async function captureFeedbackScreenshots(){
  const shots=[];let capture_error='';const originalMode=mode;
  if(!navigator.mediaDevices?.getDisplayMedia)return {screenshots:shots,capture_error:'Screen Capture API is not available in this browser/runtime.'};
  let stream=null;
  try{
    stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});const track=stream.getVideoTracks()[0];const video=document.createElement('video');video.srcObject=stream;video.muted=true;await video.play();await new Promise(r=>setTimeout(r,350));
    const targets=['water','multistage','envelope',...ERD_MODES,'summary','comparison','economic'].filter(m=>modeEntitlementAccess(m).ok);
    for(const m of targets){const btn=document.querySelector(`[data-mode="${m}"]`);if(btn?.disabled)continue;try{changeMode(m);await new Promise(r=>setTimeout(r,280));const canvas=document.createElement('canvas');canvas.width=video.videoWidth||window.innerWidth;canvas.height=video.videoHeight||window.innerHeight;canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);shots.push({mode:m,label:WORKSPACE_META[m]?.[1]||m,data_url:canvas.toDataURL('image/png')});}catch(_){} }
  }catch(e){capture_error=e?.message||String(e)}finally{stream?.getTracks()?.forEach(t=>t.stop());try{changeMode(originalMode)}catch(_){}}
  return {screenshots:shots,capture_error};
}
function startManualFeedback(){
  const note=window.prompt('Describe the issue, unexpected result, or calculation concern you want to report:','');
  if(note===null||!String(note).trim())return;
  lastReportableError={message:String(note).trim(),context:'user feedback',at:new Date().toISOString(),mode,case_id:activeCase};
  reportCurrentIssue();
}
async function requestJson(url,options={},fallbackMessage='Request failed'){
  let response;const opts={...options};opts.headers=entitlementRequestHeaders(opts.headers||{});
  if(!opts.signal&&activeCalculationController&&document.body.classList.contains('calculating')&&!String(url).startsWith('/api/compute/'))opts.signal=activeCalculationController.signal;
  try{response=await totalroFetch(url,opts)}catch(cause){if(cause?.name==='AbortError'||calculationCancelRequested){const e=new Error('Calculation stopped by user.');e.kind='cancelled';e.cancelled=true;throw e;}const e=new Error(`Total RO Design could not reach the local calculation engine. ${cause?.message||''}`.trim());e.kind='network';throw e;}
  let text='';try{text=await response.text()}catch(cause){const e=new Error(`Failed to fetch response from the local calculation engine. ${cause?.message||''}`.trim());e.kind='network';throw e;}
  let data={};
  if(text){try{data=JSON.parse(text)}catch(_){const e=new Error(response.ok?'The calculation engine returned an unreadable response.':`The calculation engine returned HTTP ${response.status} without a readable error message.`);e.kind='server';e.status=response.status;throw e;}}
  if(response.status===401){const target=encodeURIComponent(window.location.pathname+window.location.search);window.location.assign(`/login?next=${target}`);const e=new Error('Your session has expired. Sign in again.');e.kind='authentication';e.status=401;e.details=data;throw e;}
  if(!response.ok){const e=new Error(data?.error||`${fallbackMessage} (HTTP ${response.status})`);e.kind=response.status>=500?'server':'calculation';e.status=response.status;e.details=data;throw e;}
  return data;
}

const defaultMembrane='DuPont FilmTec|SW30HRLE-400|A / standard';

const operating={
  membrane_coupling:{label:'Legacy reject-flow coupling',type:'select',options:[['off','Off · manual reject flow'],['on','On · calculate permeate/reject dynamically']]},
  permeate_pressure:{label:'Permeate backpressure',type:'pressure',info:'Pressure on the permeate side of the membrane. A non-zero value increases the membrane feed pressure required for the same permeate production.'},
  fouling_factor:{label:'Flow / fouling factor',type:'number',suffix:'A multiplier',min:0.3,max:1.2,linkedWater:true,hint:'Common case input. Multiplies temperature-corrected water permeability A.',info:'Multiplier applied to temperature-corrected water permeability A. 1.00 represents the clean/reference membrane; lower values represent reduced water permeability. This factor does not directly change salt permeability B.'},
  salt_passage_factor:{label:'Salt passage factor',type:'number',suffix:'B multiplier',min:0.25,max:5,linkedWater:true,hint:'Common case input. Multiplies temperature-corrected salt permeability B; 1.00 = clean/reference salt passage.',info:'Multiplier applied after the temperature correction to salt permeability B(T). 1.00 represents the reference membrane condition; values above 1.00 increase salt passage and permeate TDS. It is independent of the Flow / Fouling Factor applied to A.'},
};
const chemistry={
  analysis_tds:{label:'Reported TDS · QC only',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_ammonium:{label:'Ammonium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_sodium:{label:'Sodium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_potassium:{label:'Potassium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_magnesium:{label:'Magnesium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_calcium:{label:'Calcium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_strontium:{label:'Strontium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_barium:{label:'Barium',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_iron_ii:{label:'Iron (II)',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_iron_iii:{label:'Iron (III)',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_manganese_ii:{label:'Manganese (II)',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_fluoride:{label:'Fluoride',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_chloride:{label:'Chloride',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_sulfate:{label:'Sulfate',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_nitrate:{label:'Nitrate',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_carbonate:{label:'Lab-reported carbonate · QC only',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_bicarbonate:{label:'Total alkalinity · as HCO₃⁻ equivalent',type:'number',suffix:'mg/L as HCO₃⁻',chemistryOnly:true},
  ion_phosphate:{label:'o-Phosphate',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_boron:{label:'Boron · as B',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_bromide:{label:'Bromide',type:'number',suffix:'mg/L',chemistryOnly:true},
  ion_silica:{label:'Silica · as SiO₂',type:'number',suffix:'mg/L',chemistryOnly:true},
};
const membrane1={
  vessels_1:{label:'Stage 1 pressure vessels',type:'number'},
  elements_per_vessel_1:{label:'Stage 1 membranes / vessel (1–8)',type:'integer'},
  permeate_pressure_1:{label:'Stage 1 permeate backpressure',type:'pressure',optional:true,info:'Permeate-side pressure applied to Stage 1 only. This value is included in the Stage 1 net driving pressure calculation.'},
};
const membrane2={
  vessels_2:{label:'Stage 2 pressure vessels',type:'number'},
  elements_per_vessel_2:{label:'Stage 2 membranes / vessel (1–8)',type:'integer'},
  permeate_pressure_2:{label:'Stage 2 permeate backpressure',type:'pressure',optional:true,info:'Permeate-side pressure applied to Stage 2 only. Use this when permeate collection/backpressure differs by stage.'},
};
const membrane3={
  vessels_3:{label:'Stage 3 pressure vessels',type:'number'},
  elements_per_vessel_3:{label:'Stage 3 membranes / vessel (1–8)',type:'integer'},
  permeate_pressure_3:{label:'Stage 3 permeate backpressure',type:'pressure',optional:true,info:'Permeate-side pressure applied to Stage 3 only. Use this when permeate collection/backpressure differs by stage.'},
};
const membrane4={
  vessels_4:{label:'Stage 4 pressure vessels',type:'number'},
  elements_per_vessel_4:{label:'Stage 4 membranes / vessel (1–8)',type:'integer'},
  permeate_pressure_4:{label:'Stage 4 permeate backpressure',type:'pressure',optional:true,info:'Permeate-side pressure applied to Stage 4 only. Use this when permeate collection/backpressure differs by stage.'},
};
const plantDesigner={
  design_mode:{label:'Array design mode',type:'select',options:[['manual','Manual · engineer defines array'],['auto','Auto · optimize membrane area + vessels + boost']],info:'Auto Design follows production → target flux → required active membrane area → whole elements / vessels → operating skids → tree/funnel stage distribution. It applies a Hydraulic prefilter before the full membrane solve and, if the requested permeate is outside the solvable range, automatically expands membrane area and retries nearby integer tree arrays. Automatic interstage boost is re-solved with every surviving candidate.'},
  stage_count:{label:'Number of RO stages',type:'select',options:[[1,'1 stage'],[2,'2 stages'],[3,'3 stages'],[4,'4 stages']]},
  max_design_flux_lmh:{label:'Auto Design · maximum average stage flux',type:'flux',min:4,max:30,optional:true,info:'Required area is calculated from requested permeate production ÷ this target flux. Auto Design then converts actual stage membrane recipes into whole vessels and searches 2:1, 3:2:1, 4:2:1, 4:3:2:1 and nearby integer funnel arrays. The Hydraulic prefilter rejects first-element overfeed, inadequate tail concentrate, excessive ΔP/flux and other impossible candidates before the expensive pressure-convergence calculation.'},
  operating_trains:{label:'Operating trains',type:'number',min:1,max:20,info:'Number of trains normally producing water.'},
  standby_trains:{label:'Standby trains',type:'number',min:0,max:20,optional:true,info:'Installed standby trains. N−1 capacity is calculated from total installed trains minus one unavailable train.'},
  required_capacity_m3d:{label:'Required plant product capacity',type:'number',suffix:'m³/d',min:0,optional:true,info:'Mandatory in Auto Design. Total RO Design divides this production among the operating trains, derives train feed flow from the recovery setpoint, sizes membrane area/vessels, and solves the minimum Stage 1 feed pressure.'},
};
const multistageHydraulic={
  feed_flow:{label:'Feed flow per operating train',type:'flow'},
  target_product_flow:{label:'Permeate flow per train',type:'flow',solveTarget:true,optional:true},
  target_recovery:{label:'Overall train recovery',type:'recoveryPct',suffix:'%',solveRecovery:true,optional:true},
  membrane_pressure_1:{label:'Stage 1 membrane feed pressure',type:'pressure',solvePressure:true},
  interstage_control_objective:{label:'Interstage pressure control · all stages',type:'select',options:[['manual','Manual pressure increase'],['balance_flux','Balance flux across all stages'],['balance_polarization','Balance polarization factor across all stages'],['target_recovery','Target downstream-stage recovery']],info:'Defines how Total RO Design determines interstage boost. Manual preserves the entered boost exactly. In Auto-select objectives, each entered boost is a starting seed only: positive values express the engineer’s desired starting point, while 0 bar means Total RO Design should generate the seed automatically from the osmotic-pressure rise since the last hydraulic-energy input. Balance modes then solve all controllable boosts together.'},
  interstage_balance_basis:{label:'Balancing basis',type:'select',options:[['lead','Lead element in each stage'],['average','Stage average']],info:'For flux or polarization balancing, choose whether the first membrane element of every stage is matched or the stage-average value is matched.'},
  interstage_equipment_2:{label:'Stage 1 → 2 equipment',type:'select',options:[['none','Nothing'],['pump','Booster pump'],['turbo','Turbocharger'],['turbo_pump','Turbocharger + booster pump']],info:'Select the hydraulic device between Stage 1 and Stage 2. Turbo options are screened against final-reject hydraulic energy.'},
  interstage_boost_2:{label:'Desired Stage 2 boost pressure',type:'pressure',optional:true,info:'Manual mode: this is the actual Stage 1 → 2 pressure increase. Auto-select modes: this is the desired starting boost and the solver may move it to balance the system. Enter 0 bar for no user bias; Total RO Design then seeds from the osmotic-pressure rise since the last hydraulic-energy input.'},
  interstage_target_recovery_2:{label:'Target Stage 2 recovery',type:'recoveryPct',suffix:'%',optional:true,info:'Used only when the interstage control objective is Target downstream-stage recovery.'},
  interstage_maximize_turbo_energy_2:{label:'Stage 1 → 2 turbo energy',type:'toggle',toggleText:'Use maximum available hydraulic energy',info:'For turbo-containing configurations, credit the maximum physically available reject hydraulic energy toward the required interstage boost. Turbo-only manual mode can use this to solve the maximum recoverable boost.'},
  interstage_equipment_3:{label:'Stage 2 → 3 equipment',type:'select',options:[['none','Nothing'],['pump','Booster pump'],['turbo','Turbocharger'],['turbo_pump','Turbocharger + booster pump']]},
  interstage_boost_3:{label:'Desired Stage 3 boost pressure',type:'pressure',optional:true,info:'Manual mode uses the entered boost exactly. In Auto-select, a positive value is the desired starting seed; 0 bar means automatic osmotic-rise seeding. The final boost remains a solved variable.'},
  interstage_target_recovery_3:{label:'Target Stage 3 recovery',type:'recoveryPct',suffix:'%',optional:true},
  interstage_maximize_turbo_energy_3:{label:'Stage 2 → 3 turbo energy',type:'toggle',toggleText:'Use maximum available hydraulic energy'},
  interstage_equipment_4:{label:'Stage 3 → 4 equipment',type:'select',options:[['none','Nothing'],['pump','Booster pump'],['turbo','Turbocharger'],['turbo_pump','Turbocharger + booster pump']]},
  interstage_boost_4:{label:'Desired Stage 4 boost pressure',type:'pressure',optional:true,info:'Manual mode uses the entered boost exactly. In Auto-select, a positive value is the desired starting seed; 0 bar means automatic osmotic-rise seeding. The final boost remains a solved variable.'},
  interstage_target_recovery_4:{label:'Target Stage 4 recovery',type:'recoveryPct',suffix:'%',optional:true},
  interstage_maximize_turbo_energy_4:{label:'Stage 3 → 4 turbo energy',type:'toggle',toggleText:'Use maximum available hydraulic energy'},
  suction_pressure:{label:'HP pump inlet pressure',type:'pressure'},
};

const hydraulic={
  feed_flow:{label:'Feed flow',type:'flow'},
  target_product_flow:{label:'Permeate flow',type:'flow',solveTarget:true,optional:true},
  target_recovery:{label:'Overall recovery',type:'recoveryPct',suffix:'%',solveRecovery:true,optional:true},
  membrane_pressure_1:{label:'Stage 1 membrane feed pressure',type:'pressure',solvePressure:true},
  reject_flow_1:{label:'Stage 1 reject flow',type:'flow',manualReject:true},
  pex:{label:'Turbine discharge / Pex',type:'pressure',info:'Pressure at the turbine concentrate discharge. Total RO Design uses this with turbine inlet pressure and flow to determine recoverable pressure energy and required turbine Cv.'},
  suction_pressure:{label:'HP pump inlet pressure',type:'pressure',info:'Pressure available at the high-pressure pump suction. It is included in the net pump head and therefore affects calculated pump power and SEC.'},
};
const stage2={
  membrane_pressure_2:{label:'Stage 2 membrane feed pressure',type:'pressure'},
  reject_flow_2:{label:'Stage 2 reject flow',type:'flow',manualReject:true},
};
const energy={
  pretreatment_discharge_pressure:{label:'Pretreatment pump discharge pressure',type:'pressure'},
  pretreatment_recovery:{label:'Pretreatment recovery',type:'percent',info:'Fraction of raw water delivered as RO feed after pretreatment. It is used to calculate pretreatment pumping flow and pretreatment SEC.'},
  pretreatment_pump_eff:{label:'Pretreatment pump efficiency',type:'percent'},
  pretreatment_motor_eff:{label:'Pretreatment motor efficiency',type:'percent'},
  pretreatment_vfd_eff:{label:'Pretreatment VFD efficiency',type:'percent'},
  pretreatment_no_vfd:{label:'Pretreatment · no VFD',type:'toggle'},
  pump_eff:{label:'Feed pump efficiency',type:'percent'},
  motor_eff:{label:'Feed pump motor efficiency',type:'percent'},
  vfd_eff:{label:'Feed pump VFD efficiency',type:'percent'},
  pump_no_vfd:{label:'Feed pump · no VFD',type:'toggle'},
  curve:{label:'Turbo efficiency curve',type:'select',options:[['cfd','3D rotor / CFD'],['std','Standard']]},
};
const multistageEnergy={...energy,
  pump_curve_basis:{label:'HPP curve screening',type:'select',options:[['vcmp_auto','VCMP database · auto-select if duty fits'],['auto','Legacy typical curve · auto-match BEP'],['manual','Legacy typical curve · enter selected pump BEP']],info:'VCMP database mode uses 431 digitized 60 Hz vertical-multistage pump curves with VFD speed matching. When a single VCMP curve covers the duty, its calculated hydraulic efficiency replaces the fallback fixed pump efficiency. If the duty is outside the database envelope, Total RO Design keeps the fallback input.'},
  vcmp_min_vfd_hz:{label:'VCMP minimum VFD frequency',type:'number',suffix:'Hz',min:20,max:60,info:'Default 40 Hz from the supplied optimizer workbook. A pump that would require a lower speed is held at this minimum and penalized for excess head/power.'},
  vcmp_max_vfd_hz:{label:'VCMP maximum VFD frequency',type:'number',suffix:'Hz',min:40,max:75,info:'Default 60 Hz. Total RO Design does not assume overspeed beyond this value.'},
  vcmp_reference_rpm_60:{label:'VCMP shaft speed at 60 Hz',type:'number',suffix:'rpm',info:'Default 3500 rpm for the current VCMP screening database. Replace this value with a verified model-specific 60 Hz shaft speed when available; shaft torque is calculated from shaft power and operating speed.'},
  pump_eff:{label:'Fallback HPP pump efficiency',type:'percent',info:'Used only when VCMP database mode cannot find a single pump curve that covers the HPP duty, or when a legacy pump-curve mode is selected.'},
  pump_bep_flow:{label:'Selected pump BEP flow',type:'flow',optional:true,info:'Used only for Legacy Manual pump-curve screening.'},
  pump_bep_dp:{label:'Selected pump BEP differential pressure',type:'pressure',optional:true,info:'Used only for Legacy Manual pump-curve screening.'},
  pump_shutoff_head_ratio:{label:'Typical shutoff head / BEP head',type:'number',optional:true,min:1.05,max:1.40,info:'Legacy normalized screening curve only.'},
  booster_pump_eff:{label:'Fallback interstage booster efficiency',type:'percent',info:'VCMP database efficiency is used automatically when the booster duty falls inside the database envelope. Verify a suitable high-pressure mechanical seal and pressure rating before final selection.'},
  booster_motor_eff:{label:'Interstage booster motor efficiency',type:'percent'},
  booster_vfd_eff:{label:'Interstage booster VFD efficiency',type:'percent'},
  booster_no_vfd:{label:'Interstage booster · no VFD',type:'toggle'},
};

const plantPumpEnergy={
  pretreatment_discharge_pressure:{...energy.pretreatment_discharge_pressure,info:'Manual pretreatment pump discharge pressure used for pretreatment hydraulic power and SEC.'},
  pretreatment_recovery:{...energy.pretreatment_recovery},pretreatment_pump_eff:{...energy.pretreatment_pump_eff},pretreatment_motor_eff:{...energy.pretreatment_motor_eff},pretreatment_vfd_eff:{...energy.pretreatment_vfd_eff},pretreatment_no_vfd:{...energy.pretreatment_no_vfd},
  pump_curve_basis:{...multistageEnergy.pump_curve_basis},pump_eff:{...multistageEnergy.pump_eff},motor_eff:{...energy.motor_eff,label:'HPP motor efficiency'},vfd_eff:{...energy.vfd_eff,label:'HPP VFD efficiency'},pump_no_vfd:{...energy.pump_no_vfd,label:'HPP · no VFD'},
  vcmp_min_vfd_hz:{...multistageEnergy.vcmp_min_vfd_hz},vcmp_max_vfd_hz:{...multistageEnergy.vcmp_max_vfd_hz},vcmp_reference_rpm_60:{...multistageEnergy.vcmp_reference_rpm_60},pump_bep_flow:{...multistageEnergy.pump_bep_flow},pump_bep_dp:{...multistageEnergy.pump_bep_dp},pump_shutoff_head_ratio:{...multistageEnergy.pump_shutoff_head_ratio}
};

const cvSingle={
  sg:{label:'Brine specific gravity (SG)',type:'number',optional:true,placeholder:'Auto from concentrate TDS',hint:'With membrane coupling active, leave blank to calculate SG from the converged concentrate TDS and temperature.'},
  cvc:{label:'Turbine Cvc design',type:'number',placeholder:'Auto = current design point',info:'Locked turbine hydraulic design coefficient. In multi-case studies Total RO Design normally selects the case with the lowest required Cvt. A higher-Cvt case may be selected manually if the user prefers; however, the case with the lowest required Cvt will then require backpressure, reducing energy recovery (energy-transfer efficiency).'},
  aux_range:{label:'Auxiliary range',type:'percent'},
  max_eff_loss:{label:'Efficiency loss at aux 100% open',type:'percent'},
};
const cvInter={
  inter_sg:{label:'Interstage turbo · brine SG',type:'number',optional:true,placeholder:'Auto from concentrate TDS',hint:'Leave blank to calculate SG from the Stage 2 concentrate TDS and temperature.'},
  inter_cvc:{label:'Interstage turbo · Cvc design',type:'number',placeholder:'Auto = current design point',info:'Locked interstage-turbine design coefficient. Auto uses the lowest required Cvt across configured cases. Selecting a higher-Cvt design case makes the lower-Cvt case require backpressure, reducing energy transfer efficiency.'},
  inter_aux_range:{label:'Interstage turbo · auxiliary range',type:'percent'},
  inter_max_eff_loss:{label:'Interstage turbo · max efficiency loss',type:'percent'},
};
const cvFeed={
  feed_sg:{label:'Feed turbo · brine SG',type:'number',optional:true,placeholder:'Auto from concentrate TDS',hint:'Leave blank to calculate SG from the Stage 1 concentrate TDS and temperature.'},
  feed_cvc:{label:'Feed turbo · Cvc design',type:'number',placeholder:'Auto = current design point',info:'Locked feed-turbine design coefficient. Auto uses the lowest required Cvt across configured cases. Selecting a higher-Cvt design case makes the lower-Cvt case require backpressure, reducing energy transfer efficiency.'},
  feed_aux_range:{label:'Feed turbo · auxiliary range',type:'percent'},
  feed_max_eff_loss:{label:'Feed turbo · max efficiency loss',type:'percent'},
};

const pxDevice={
  px_architecture:{label:'Isobaric Chamber type',type:'select',options:[['passive','Passive Isobaric Chamber'],['motorized','Active / motorized Isobaric Chamber']]},
  px_model:{label:'Passive Isobaric Chamber model',type:'select',options:[['auto','Auto · IC300 / IC260 / IC220 legacy correlations'],['IC660','IC660 · high-capacity screening'],['IC600','IC600 · high-capacity screening'],['IC300','IC300'],['IC260','IC260'],['IC220','IC220']],info:'Trademark-neutral Total RO Design names. IC300/260/220 retain the existing legacy reference correlations. IC600/660 use nominal flow screening plus the editable generic loss/mixing assumptions below until verified device curves are added.'},
  px_generic_hp_dp:{label:'IC600 / IC660 HP-side screening loss',type:'pressure',optional:true,info:'Generic preliminary screening assumption used only for IC600/IC660; replace with verified project/vendor hydraulic data when available.'},
  px_generic_lp_dp:{label:'IC600 / IC660 LP-side screening loss',type:'pressure',optional:true,info:'Generic preliminary screening assumption used only for IC600/IC660; replace with verified project/vendor hydraulic data when available.'},
  px_generic_mixing:{label:'IC600 / IC660 mixing screening fraction',type:'percent',optional:true,info:'Generic preliminary mixing assumption used only for IC600/IC660.'},
  px_lp_outlet_pressure:{label:'Isobaric Chamber brine exit backpressure',type:'pressure',minPressureBar:1.5,hint:'Minimum screening backpressure: 1.5 bar. Editable for project conditions.',info:'Low-pressure brine-side backpressure maintained at the isobaric chamber outlet.'},
};
const bwpxDevice={
  bwpx_model:{label:'Interstage Isobaric Chamber model',type:'select',options:[['Generic BWRO Isobaric Chamber','Generic Isobaric Chamber'],['IC660','IC660 · nominal 660 gpm screening'],['IC600','IC600 · nominal 600 gpm screening'],['IC300','IC300 · legacy flow-envelope screening'],['IC260','IC260 · legacy flow-envelope screening'],['IC220','IC220 · legacy flow-envelope screening']],info:'Trademark-neutral Total RO Design model names. IC300/260/220 retain the embedded legacy flow envelopes; IC600/660 add high-capacity nominal-flow bank screening. Verify final device suitability with project-specific data.'},
  bwpx_auto_size:{label:'Isobaric Chamber bank sizing',type:'toggle',toggleText:'Auto-size operating units from unit-flow limits',info:'When a maximum unit flow is available, Total RO Design increases the operating IC/PX count as needed. Scenario Matrix then fixes installed quantity to the governing N/N−1 case.'},
  bwpx_qty:{label:'Manual IC units per train',type:'number',optional:true,min:1,max:100,info:'Used when automatic bank sizing cannot be performed or is turned off.'},
  bwpx_min_unit_flow:{label:'Generic minimum unit flow',type:'flow',optional:true,info:'Optional minimum preferred flow per unit for the Generic BWRO Isobaric Chamber. Leave blank if no verified device limit is available.'},
  bwpx_max_unit_flow:{label:'Generic maximum unit flow',type:'flow',optional:true,info:'Optional maximum allowable flow per unit for automatic N/N−1 bank sizing. Leave blank rather than inventing a vendor limit.'},
  bwpx_pressure_transfer_eff:{label:'Net pressure-transfer efficiency',type:'percent',info:'Fraction of the available final-brine pressure differential transferred to the low-pressure feed branch. The excess pressure from interstage boosting is not credited as additional isobaric efficiency.'},
  bwpx_flow_balance_eff:{label:'Flow-balance / volumetric efficiency',type:'percent',info:'Ratio used to match the pressurized feed branch to the available final-stage reject flow.'},
  bwpx_mixing_fraction:{label:'Feed / brine mixing fraction',type:'percent',info:'Volumetric mixing fraction used to propagate final-brine chemistry into the pressure-exchanged feed branch before recombination with the HPP stream.'},
  bwpx_brine_backpressure:{label:'Final brine outlet backpressure',type:'pressure',minPressureBar:0,info:'Pressure maintained on the depressurized brine leaving the isobaric chamber.'},
  bwpx_header_tolerance_bar:{label:'Header pressure-match tolerance',type:'pressure',optional:true,readOnly:true,linkedHppInlet:true,info:'Automatically linked to the HP pump inlet pressure. It is not an independent input.'},
};

const pxEnergy={
  pump_curve_basis:{label:'Pump performance basis',type:'select',options:[['vcmp_auto','VCMP database · auto-select if duty fits'],['auto','Fixed efficiency / legacy screening']],info:'For lower-pressure HPP and Isobaric Chamber booster duties, Total RO Design attempts the VCMP curve database first. If no single curve covers the duty, the entered fallback efficiencies remain in force.'},
  vcmp_min_vfd_hz:{label:'VCMP minimum VFD frequency',type:'number',suffix:'Hz',min:20,max:60},
  vcmp_max_vfd_hz:{label:'VCMP maximum VFD frequency',type:'number',suffix:'Hz',min:40,max:75},
  vcmp_reference_rpm_60:{label:'VCMP shaft speed at 60 Hz',type:'number',suffix:'rpm',info:'Default 3500 rpm for the current VCMP screening database. Replace with verified model-specific shaft speed when available.'},
  pretreatment_discharge_pressure:{label:'Pretreatment pump discharge pressure',type:'pressure'},
  pretreatment_recovery:{label:'Pretreatment recovery',type:'percent',info:'Fraction of raw water delivered as RO feed after pretreatment. It is used to calculate pretreatment pumping flow and pretreatment SEC.'},
  pretreatment_pump_eff:{label:'Pretreatment pump efficiency',type:'percent'},
  pretreatment_motor_eff:{label:'Pretreatment motor efficiency',type:'percent'},
  pretreatment_vfd_eff:{label:'Pretreatment VFD efficiency',type:'percent'},
  pretreatment_no_vfd:{label:'Pretreatment · no VFD',type:'toggle'},
  pump_eff:{label:'Fallback HP pump efficiency',type:'percent'},
  motor_eff:{label:'HP pump motor efficiency',type:'percent'},
  vfd_eff:{label:'HP pump VFD efficiency',type:'percent'},
  pump_no_vfd:{label:'HP pump · no VFD',type:'toggle'},
  circ_pump_eff:{label:'Fallback Isobaric Chamber booster pump efficiency',type:'percent',info:'VCMP database efficiency is used when the duty is covered. For Isobaric Chamber booster service, verify a suitable high-pressure mechanical seal and pressure rating.'},
  circ_motor_eff:{label:'Circulation / booster motor efficiency',type:'percent'},
  circ_vfd_eff:{label:'Circulation / booster VFD efficiency',type:'percent'},
  circ_no_vfd:{label:'Circulation / booster · no VFD',type:'toggle'},
};

const dweerDevice={
  dweer_hp_side_dp:{label:'DWEER high-pressure side loss',type:'pressure',info:'Pressure loss between the final-brine HP inlet and the pressure-exchanged feed outlet, including the work exchanger / control valve basis.'},
  dweer_lp_side_dp:{label:'DWEER low-pressure side loss',type:'pressure',info:'Low-pressure feed-side loss charged to the DWEER arrangement.'},
  dweer_overflush_fraction:{label:'DWEER piston overflush',type:'percent',info:'Additional LP feed used as piston/face overflush. The attached comparison calculator uses 3%.'},
  dweer_mixing_fraction:{label:'DWEER feed/brine mixing',type:'percent',info:'Volumetric feed/brine mixing fraction used to estimate the salinity and osmotic-pressure penalty. The attached calculator uses 2%.'},
  dweer_apply_mixing_penalty:{label:'Mixing pressure penalty',type:'toggle',toggleText:'Apply DWEER mixing/osmotic pressure penalty'},
  dweer_module_flow:{label:'Design flow per DWEER module',type:'flow',info:'Sizing-screen flow per module. The attached calculator uses 200 m³/h as a placeholder; replace with current vendor data for final sizing.'},
  dweer_booster_pump_eff:{label:'DWEER HP booster pump efficiency',type:'percent'},
  dweer_booster_motor_eff:{label:'DWEER HP booster motor efficiency',type:'percent'},
  dweer_booster_vfd_eff:{label:'DWEER HP booster VFD efficiency',type:'percent'},
  dweer_lp_pump_eff:{label:'DWEER LP pump efficiency',type:'percent'},
  dweer_lp_motor_eff:{label:'DWEER LP pump motor efficiency',type:'percent'},
  erd_motor_sizing_factor:{label:'Motor sizing factor',type:'number',info:'1.10 = 10% sizing margin before rounding to the next motor frame.'},
  erd_motor_partload_k:{label:'Motor part-load correction k',type:'number',info:'Quadratic motor part-load efficiency correction used by the attached calculator.'}
};
const peltonDevice={
  pelton_turbine_eff:{label:'Pelton runner efficiency',type:'percent'},
  pelton_discharge_pressure:{label:'Pelton discharge backpressure',type:'pressure'},
  pelton_shaft_eff:{label:'Common-shaft mechanical efficiency',type:'percent',info:'Bearing, coupling, seal and windage efficiency from runner shaft to HP pump shaft.'},
  pelton_shaft_speed_rpm:{label:'Common shaft speed',type:'number',suffix:'rpm'},
  pelton_jets:{label:'Number of Pelton jets',type:'select',options:[[1,'1 jet'],[2,'2 jets'],[3,'3 jets'],[4,'4 jets']]},
  pelton_nozzle_cv:{label:'Nozzle velocity coefficient Cv',type:'number'},
  pelton_speed_ratio:{label:'Runner speed ratio φ',type:'number',info:'Runner pitch-circle velocity divided by jet velocity. The attached calculator uses 0.47.'},
  pelton_motor_sizing_basis:{label:'HP motor sizing basis',type:'select',options:[['full_start','Full pump start-up duty'],['net_run','Net running shaft duty']]},
  pelton_brine_sg:{label:'Brine specific gravity',type:'number',optional:true,placeholder:'Auto from final brine TDS'},
  erd_motor_sizing_factor:{label:'Motor sizing factor',type:'number'},
  erd_motor_partload_k:{label:'Motor part-load correction k',type:'number'}
};

const defaults={
 single:{solve_basis:'recovery',target_product_flow:'',target_recovery:'',membrane_coupling:'on',water_mode:'tds',feed_ph:7.6,analysis_tds:6415.38,ion_ammonium:0,ion_sodium:1436.94,ion_potassium:34.27,ion_magnesium:231.73,ion_calcium:424.44,ion_strontium:0,ion_barium:0,ion_fluoride:0,ion_chloride:2232.38,ion_sulfate:1617.30,ion_nitrate:62.27,ion_carbonate:1.75,ion_bicarbonate:360.64,ion_boron:1.5,ion_bromide:0,ion_silica:0,feed_tds:35000,temperature_c:25,permeate_pressure:0,membrane_1:defaultMembrane,vessels_1:65,elements_per_vessel_1:8,
   pex:1.5,suction_pressure:2,pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,curve:'cfd',feed_flow:1500,membrane_pressure_1:58,reject_pressure_1:57.5,reject_flow_1:900,sg:'',cvc:'',aux_range:.85,max_eff_loss:.03},
 interstage:{solve_basis:'recovery',target_product_flow:'',target_recovery:'',membrane_coupling:'on',water_mode:'tds',feed_ph:7.6,analysis_tds:6415.38,ion_ammonium:0,ion_sodium:1436.94,ion_potassium:34.27,ion_magnesium:231.73,ion_calcium:424.44,ion_strontium:0,ion_barium:0,ion_fluoride:0,ion_chloride:2232.38,ion_sulfate:1617.30,ion_nitrate:62.27,ion_carbonate:1.75,ion_bicarbonate:360.64,ion_boron:1.5,ion_bromide:0,ion_silica:0,feed_tds:35000,temperature_c:25,permeate_pressure:0,membrane_1:defaultMembrane,vessels_1:30,elements_per_vessel_1:6,membrane_2:defaultMembrane,vessels_2:20,elements_per_vessel_2:5,
   pex:1.5,suction_pressure:2,pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,curve:'cfd',feed_flow:500,membrane_pressure_1:18,reject_pressure_1:17,reject_flow_1:300,membrane_pressure_2:24,reject_pressure_2:22,reject_flow_2:100,sg:'',cvc:'',aux_range:.85,max_eff_loss:.03},
 biturbo:{solve_basis:'recovery',target_product_flow:'',target_recovery:'',membrane_coupling:'on',water_mode:'tds',feed_ph:7.6,analysis_tds:6415.38,ion_ammonium:0,ion_sodium:1436.94,ion_potassium:34.27,ion_magnesium:231.73,ion_calcium:424.44,ion_strontium:0,ion_barium:0,ion_fluoride:0,ion_chloride:2232.38,ion_sulfate:1617.30,ion_nitrate:62.27,ion_carbonate:1.75,ion_bicarbonate:360.64,ion_boron:1.5,ion_bromide:0,ion_silica:0,feed_tds:35000,temperature_c:25,permeate_pressure:0,membrane_1:defaultMembrane,vessels_1:50,elements_per_vessel_1:6,membrane_2:defaultMembrane,vessels_2:20,elements_per_vessel_2:6,
   pex:1.5,suction_pressure:2,pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,curve:'cfd',feed_flow:1000,membrane_pressure_1:60,reject_pressure_1:59.5,reject_flow_1:575,membrane_pressure_2:75,reject_pressure_2:74.5,reject_flow_2:400,target_interstage_boost:15,inter_sg:'',inter_cvc:'',inter_aux_range:.85,inter_max_eff_loss:.03,feed_sg:'',feed_cvc:'',feed_aux_range:.85,feed_max_eff_loss:.03},
 px:{solve_basis:'recovery',target_product_flow:'',target_recovery:'',membrane_coupling:'on',water_mode:'tds',feed_ph:7.6,analysis_tds:6415.38,ion_ammonium:0,ion_sodium:1436.94,ion_potassium:34.27,ion_magnesium:231.73,ion_calcium:424.44,ion_strontium:0,ion_barium:0,ion_fluoride:0,ion_chloride:2232.38,ion_sulfate:1617.30,ion_nitrate:62.27,ion_carbonate:1.75,ion_bicarbonate:360.64,ion_boron:1.5,ion_bromide:0,ion_silica:0,feed_tds:35000,temperature_c:25,permeate_pressure:0,membrane_1:defaultMembrane,vessels_1:65,elements_per_vessel_1:8,feed_flow:1500,membrane_pressure_1:58,reject_flow_1:900,suction_pressure:2,px_architecture:'passive',px_model:'auto',px_generic_hp_dp:.8,px_generic_lp_dp:.8,px_generic_mixing:.02,px_lp_outlet_pressure:1.5,mpe_hp_dp:.66,mpe_lp_dp:.74,mpe_mixing:.02,mpe_motor_power:.8,pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,circ_pump_eff:.82,circ_motor_eff:.96,circ_vfd_eff:.98,circ_no_vfd:false,bwpx_model:'Generic BWRO Isobaric Chamber',bwpx_pressure_transfer_eff:.96,bwpx_flow_balance_eff:.98,bwpx_mixing_fraction:.02,bwpx_brine_backpressure:1.5,plant_solution:false}
};

defaults.multistage={solve_basis:'recovery',target_product_flow:'',target_recovery:'',membrane_coupling:'on',permeate_pressure:0,permeate_pressure_1:0,permeate_pressure_2:0,permeate_pressure_3:0,permeate_pressure_4:0,source_water_type:'seawater',design_mode:'manual',stage_count:2,max_design_flux_lmh:'',
  membrane_1:defaultMembrane,vessels_1:'',elements_per_vessel_1:'',membrane_2:defaultMembrane,vessels_2:'',elements_per_vessel_2:'',membrane_3:defaultMembrane,vessels_3:'',elements_per_vessel_3:'',membrane_4:defaultMembrane,vessels_4:'',elements_per_vessel_4:'',
  feed_flow:'',membrane_pressure_1:'',interstage_control_objective:'manual',interstage_balance_basis:'average',interstage_control_max_boost_bar:40,
  interstage_equipment_2:'pump',interstage_boost_2:'',interstage_target_recovery_2:'',interstage_maximize_turbo_energy_2:true,
  interstage_equipment_3:'pump',interstage_boost_3:'',interstage_target_recovery_3:'',interstage_maximize_turbo_energy_3:true,
  interstage_equipment_4:'pump',interstage_boost_4:'',interstage_target_recovery_4:'',interstage_maximize_turbo_energy_4:true,suction_pressure:'',
  energy_recovery_mode:'with',solution_conventional:true,solution_px:true,solution_interstage_px:true,solution_single:true,solution_interstage:false,solution_biturbo:true,solution_dweer:false,solution_pelton:false,scenario_matrix_enabled:false,scenario_maintain_capacity_nminus1:true,
  operating_trains:'',standby_trains:'',required_capacity_m3d:'',pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,
  pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,pump_curve_basis:'vcmp_auto',vcmp_min_vfd_hz:40,vcmp_max_vfd_hz:60,vcmp_flow_margin:.05,vcmp_head_margin:.05,vcmp_reduced_impeller_eta_penalty_pp:2,vcmp_low_speed_eta_derate_pp_per_10pct:0,vcmp_reference_rpm_60:3500,pump_bep_flow:'',pump_bep_dp:'',pump_shutoff_head_ratio:1.18,booster_pump_eff:.82,booster_motor_eff:.96,booster_vfd_eff:.97,booster_no_vfd:false,curve:'cfd'};

defaults.interstage_px={...defaults.px,...defaults.multistage,stage_count:2,plant_solution:true,source_water_type:'well',solution_enabled:true,bwpx_model:'Generic BWRO Isobaric Chamber',bwpx_auto_size:true,bwpx_qty:1,bwpx_min_unit_flow:'',bwpx_max_unit_flow:'',bwpx_pressure_transfer_eff:.96,bwpx_flow_balance_eff:.98,bwpx_mixing_fraction:.02,bwpx_brine_backpressure:1.5};
defaults.px={...defaults.px,pump_curve_basis:'vcmp_auto',vcmp_min_vfd_hz:40,vcmp_max_vfd_hz:60,vcmp_flow_margin:.05,vcmp_head_margin:.05,vcmp_reduced_impeller_eta_penalty_pp:2,vcmp_low_speed_eta_derate_pp_per_10pct:0,vcmp_reference_rpm_60:3500,bwpx_auto_size:true,bwpx_qty:1,bwpx_min_unit_flow:'',bwpx_max_unit_flow:''};
defaults.dweer={...defaults.multistage,solution_enabled:true,generated_from_base_plant:false,dweer_hp_side_dp:.9,dweer_lp_side_dp:.7,dweer_overflush_fraction:.03,dweer_mixing_fraction:.02,dweer_apply_mixing_penalty:true,dweer_module_flow:200,dweer_booster_pump_eff:.80,dweer_booster_motor_eff:.955,dweer_booster_vfd_eff:.97,dweer_lp_pump_eff:.82,dweer_lp_motor_eff:.94,erd_motor_sizing_factor:1.10,erd_motor_partload_k:.06};
defaults.pelton={...defaults.multistage,solution_enabled:true,generated_from_base_plant:false,pelton_turbine_eff:.87,pelton_discharge_pressure:.5,pelton_shaft_eff:.99,pelton_shaft_speed_rpm:1780,pelton_jets:1,pelton_nozzle_cv:.98,pelton_speed_ratio:.47,pelton_motor_sizing_basis:'full_start',pelton_brine_sg:'',erd_motor_sizing_factor:1.10,erd_motor_partload_k:.06};

['single','interstage','biturbo','px','interstage_px'].forEach(name=>{Object.keys(defaults[name]).forEach(key=>{if(key.startsWith('vessels_'))defaults[name][key]='';});});
[
  ['single',['suction_pressure','pretreatment_discharge_pressure','feed_flow','membrane_pressure_1','reject_flow_1']],
  ['interstage',['suction_pressure','pretreatment_discharge_pressure','feed_flow','membrane_pressure_1','reject_flow_1','membrane_pressure_2','reject_flow_2']],
  ['biturbo',['suction_pressure','pretreatment_discharge_pressure','feed_flow','membrane_pressure_1','reject_flow_1','membrane_pressure_2','reject_flow_2']],
  ['px',['feed_flow','membrane_pressure_1','reject_flow_1','suction_pressure','pretreatment_discharge_pressure']],
  ['interstage_px',['feed_flow','membrane_pressure_1','suction_pressure','pretreatment_discharge_pressure']]
].forEach(([name,keys])=>keys.forEach(key=>defaults[name][key]=''));

function turboPlacementScreen(stageNo,forBiturbo=false,result=caseResults.multistage){
  if(!result)return {allow:true,ratio:null,tds:null,reason:''};
  const n=Math.max(1,Math.min(4,Number(result.stage_count||modeStates.multistage?.stage_count||1))),qtr=Number(result.reject_flow_final||result[`reject_flow_${n}`]||0),qpf=Number(result[`reject_flow_${stageNo-1}`]||0),ratio=qpf>0?qtr/qpf:0,tds=Number(result[`stage${stageNo}_feed_tds_ppm`]||0);
  if(ratio<=0.20)return {allow:false,ratio,tds,reason:`Turbo disabled: Qtr/Qpf = ${ratio.toFixed(3)} ≤ 0.20.`};
  if(forBiturbo&&tds<30000)return {allow:false,ratio,tds,reason:`BiTurbo disabled at this position: Stage ${stageNo} feed TDS ${Math.round(tds).toLocaleString()} mg/L < 30,000 mg/L.`};
  return {allow:true,ratio,tds,reason:`Qtr/Qpf = ${ratio.toFixed(3)}${ratio>=0.65&&ratio<=0.70?' · peak region 0.65–0.70':''}.`};
}
function multistageHydraulicFor(n,forBiturbo=false){
  // Keep plant-wide interstage optimization controls out of the downstream
  // stage cards. The Base Plant renders those controls in Plant / array
  // configuration because one objective governs every controllable stage.
  const hyd={...multistageHydraulic};
  delete hyd.interstage_control_objective;delete hyd.interstage_balance_basis;
  for(let i=2;i<=4;i++){delete hyd[`interstage_equipment_${i}`];delete hyd[`interstage_boost_${i}`];delete hyd[`interstage_target_recovery_${i}`];delete hyd[`interstage_maximize_turbo_energy_${i}`];}
  return hyd;
}
function interstageStageFields(stageNo,forBiturbo=false,includeGlobalControl=true){
  if(stageNo<2||stageNo>4)return {};
  // v0.2 Plant Design is intentionally equipment-agnostic. The engineer
  // defines only the hydraulic pressure increase required before the stage.
  // The device that supplies that boost (pump, turbocharger, etc.) is selected
  // later in Advance Design / the dedicated ERD workspace.
  const k=`interstage_boost_${stageNo}`;
  return multistageHydraulic[k]?{[k]:{...multistageHydraulic[k]}}:{};
}
function stageMembraneSection(stageNo,forBiturbo=false,values=null,includeGlobalControl=true){
  const raw={1:membrane1,2:membrane2,3:membrane3,4:membrane4}[stageNo]||{},base={...raw};
  const autoPlant=mode==='multistage'&&String(values?.design_mode||'manual')==='auto';
  const vk=`vessels_${stageNo}`;
  if(autoPlant&&base[vk])base[vk]={...base[vk],optional:true,info:'Calculated by Auto Design from membrane area, array geometry, flux limits and the coupled interstage-pressure solution. The calculated value is written back after Run and remains editable if you later switch to Manual array design.'};
  return [`Stage ${stageNo} membrane train`,{...base,...(stageNo>=2?interstageStageFields(stageNo,forBiturbo,includeGlobalControl):{})}];
}

function sections(values=null){
  const memBasis=['RO / membrane model',{...operating}];
  if(mode==='multistage'){
    const src=values||modeStates.multistage||defaults.multistage;const n=Math.max(1,Math.min(4,Number(src?.stage_count||2)));
    const hyd=multistageHydraulicFor(n,false);
    delete hyd.membrane_coupling;delete hyd.interstage_control_objective;delete hyd.interstage_balance_basis;
    // Plant Design always uses dynamic membrane coupling. Keep the useful global
    // membrane-condition factors in the central Hydraulic Conditions card.
    hyd.fouling_factor={...operating.fouling_factor};
    hyd.salt_passage_factor={...operating.salt_passage_factor};
    const plantFields={design_mode:{...plantDesigner.design_mode},stage_count:{...plantDesigner.stage_count},max_design_flux_lmh:{...plantDesigner.max_design_flux_lmh},operating_trains:{...plantDesigner.operating_trains},standby_trains:{...plantDesigner.standby_trains},required_capacity_m3d:{...plantDesigner.required_capacity_m3d}};
    const out=[['Plant / array configuration',plantFields],['Hydraulic conditions',hyd],stageMembraneSection(1,false,src,false)];
    if(n>=2)out.push(stageMembraneSection(2,false,src,false));if(n>=3)out.push(stageMembraneSection(3,false,src,false));if(n>=4)out.push(stageMembraneSection(4,false,src,false));
    out.push(['Pretreatment & high-pressure pump',plantPumpEnergy]);return out;
  }
  const stage1Mem=stageMembraneSection(1,false,values);
  if(mode==='dweer'||mode==='pelton'){
    const src=values||modeStates[mode]||defaults[mode];const n=Math.max(1,Math.min(4,Number(src?.stage_count||1)));const hyd=multistageHydraulicFor(n,false);const out=[memBasis,stage1Mem];if(n>=2)out.push(stageMembraneSection(2,false,src));if(n>=3)out.push(stageMembraneSection(3,false,src));if(n>=4)out.push(stageMembraneSection(4,false,src));out.push(['Hydraulic conditions',hyd],[mode==='dweer'?'DWEER work exchanger':'Pelton turbine & common shaft',mode==='dweer'?dweerDevice:peltonDevice],['Pumps & energy',multistageEnergy]);return out;
  }
  if(mode==='biturbo' && (Boolean((values||modeStates.biturbo||defaults.biturbo)?.generalized_biturbo)||Number((values||modeStates.biturbo||defaults.biturbo)?.stage_count||2)>2)){
    const src=values||modeStates.biturbo||defaults.biturbo;const n=Math.max(3,Math.min(4,Number(src.stage_count||3))),hyd=multistageHydraulicFor(n,true);const out=[memBasis,stage1Mem];if(n>=2)out.push(stageMembraneSection(2,true));if(n>=3)out.push(stageMembraneSection(3,true));if(n>=4)out.push(stageMembraneSection(4,true));out.push(['Hydraulic conditions',hyd],['Pumps & multistage BiTurbo energy',multistageEnergy]);return out;
  }
  if(mode==='single') return [memBasis,stage1Mem,['Hydraulic conditions',hydraulic],['Turbine Cv',cvSingle],['Energy & efficiency',energy]];
  if(mode==='interstage'){
    const src=values||modeStates.interstage||defaults.interstage;const generalized=Boolean(src?.generalized_interstage_turbo)||Number(src?.stage_count||2)>2;
    if(generalized){const n=Math.max(3,Math.min(4,Number(src.stage_count||3))),hyd=multistageHydraulicFor(n,false);const out=[memBasis,stage1Mem,stageMembraneSection(2,false)];if(n>=3)out.push(stageMembraneSection(3,false));if(n>=4)out.push(stageMembraneSection(4,false));out.push(['Hydraulic conditions',hyd],['Pumps & multistage interstage-turbo energy',multistageEnergy]);return out;}
    return [memBasis,stage1Mem,['Stage 2 membrane train',{...membrane2}],['Hydraulic conditions',{...hydraulic,...stage2}],['Turbine Cv',cvSingle],['Energy & efficiency',energy]];
  }
  if(mode==='interstage_px'){
    const src=values||modeStates.interstage_px||defaults.interstage_px;const n=Math.max(2,Math.min(4,Number(src?.stage_count||2)));
    const hyd=multistageHydraulicFor(n,false);
    const out=[['Plant design inherited from Base Plant',{...plantDesigner}],memBasis,stage1Mem,stageMembraneSection(2,false)];if(n>=3)out.push(stageMembraneSection(3,false));if(n>=4)out.push(stageMembraneSection(4,false));out.push(['Hydraulic conditions',hyd],['Interstage Isobaric Chamber · final-stage reject recovery',bwpxDevice],['Pumps & energy',{...multistageEnergy,...pxEnergy}]);return out;
  }
  if(mode==='px'){
    const src=values||modeStates.px||defaults.px;const n=Math.max(1,Math.min(4,Number(src?.stage_count||1)));
    if(n>1||src?.plant_solution){const hyd=multistageHydraulicFor(n,false);const out=[['Plant design inherited from Base Plant',{...plantDesigner}],memBasis,stage1Mem];if(n>=2)out.push(stageMembraneSection(2,false));if(n>=3)out.push(stageMembraneSection(3,false));if(n>=4)out.push(stageMembraneSection(4,false));out.push(['Hydraulic conditions',hyd],['Brackish / multistage Isobaric Chamber',bwpxDevice],['Pumps & energy',{...multistageEnergy,...pxEnergy}]);return out;}
    return [memBasis,stage1Mem,['Hydraulic conditions',{feed_flow:{label:'Feed flow',type:'flow'},target_product_flow:{label:'Permeate flow',type:'flow',solveTarget:true,optional:true},target_recovery:{label:'Overall recovery',type:'recoveryPct',suffix:'%',solveRecovery:true,optional:true},membrane_pressure_1:{label:'Membrane feed pressure',type:'pressure',solvePressure:true},reject_flow_1:{label:'Reject flow',type:'flow',manualReject:true},suction_pressure:{label:'HP pump / PX low-pressure inlet pressure',type:'pressure',hint:'Common low-pressure feed header: this value is used for both the HP pump inlet and the PX low-pressure/feed inlet.',info:'Common low-pressure header pressure seen by the HP pump suction and the PX low-pressure/feed inlet.'}}],['Isobaric Chamber',pxDevice],['Pumps & energy',pxEnergy]];
  }
  return [memBasis,stage1Mem,['Stage 2 membrane train',{...membrane2}],['Hydraulic conditions',{...hydraulic,...stage2,target_interstage_boost:{label:'Target interstage turbo boost',type:'pressure',hint:'Typical BiTurbo interstage boost is usually 12–18 bar; 15 bar is a practical starting point.',info:'Pressure boost targeted between RO stages from the interstage turbocharger. It changes Stage 2 feed pressure and therefore the coupled power-transfer balance.'}}],['Interstage turbine Cv',cvInter],['Feed turbine Cv',cvFeed],['Energy & efficiency',energy]];
}
function defn(){return (mode==='water'||mode==='envelope'||mode==='scenario'||mode==='comparison'||mode==='summary'||mode==='economic')?{}:Object.assign({},...sections(modeStates[mode]||defaults[mode]).map(x=>x[1]))}
function unitFor(type){if(type==='flow')return $('#flowUnit').value;if(type==='pressure')return $('#pressureUnit').value;if(type==='flux')return $('#fluxUnit')?.value||'LMH';return ''}
function convert(v,type,oldU,newU){if(v===''||v===null||v===undefined)return v;v=+v;if(type==='flow'){const m3=v*({'m3/h':1,'L/s':3.6,gpm:.227124707}[oldU]);return m3/({'m3/h':1,'L/s':3.6,gpm:.227124707}[newU])}if(type==='pressure'){const bar=oldU==='bar'?v:v/14.5037738;return newU==='bar'?bar:bar*14.5037738}if(type==='flux'){const lmh=String(oldU).toUpperCase()==='GFD'?v/0.589024:v;return String(newU).toUpperCase()==='GFD'?lmh*0.589024:lmh}return v}
function membraneManufacturerLabel(name){const n=String(name||'');return (n==='LG Water Solutions'||n==='LG NanoH2O'||n==='NanoH2O')?'NanoH2O':n;}
function membraneOptions(selected){
  const groups={}; membranes.forEach(m=>{const g=membraneManufacturerLabel(m.manufacturer);(groups[g]??=[]).push(m)});
  return Object.keys(groups).sort().map(manufacturer=>{
    const opts=groups[manufacturer].sort((a,b)=>(a.family||'').localeCompare(b.family||'')||a.model.localeCompare(b.model)).map(m=>{
      const variant=m.test_variant&&m.test_variant!=='A / standard'?` · ${m.test_variant}`:'';
      const ready=!!m.calculation_enabled;
      const flux=ready&&m.test_flux_lmh!=null?` · Jtest ${convert(Number(m.test_flux_lmh),'flux','LMH',unitFor('flux')).toFixed(1)} ${unitFor('flux')}`:'';
      const aapp=ready&&m.specific_flux_A_app_lmh_bar!=null?` · A ${Number(m.specific_flux_A_app_lmh_bar).toFixed(2)}`:'';
      const nfBench=m.nf_rejection_benchmarks||null;
      const nfTag=ready&&nfBench?` · NF selective`:'';
      const rej=ready&&m.rejection_pct!=null&&!nfBench?` · ${Number(m.rejection_pct).toFixed(2)}%`:'';
      const status=ready?'✓':'catalog only';
      const txt=`${m.model}${variant}${nfTag}${rej}${flux}${aapp} · ${status}`;
      return `<option value="${escapeHtml(m.record_id)}" ${selected===m.record_id?'selected':''} ${ready?'':'disabled'} title="${escapeHtml(m.calculation_disabled_reason||m.application||'')}">${escapeHtml(txt)}</option>`;
    }).join('');
    return `<optgroup label="${escapeHtml(manufacturer)}">${opts}</optgroup>`;
  }).join('');
}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function infoTip(text){if(!text)return '';return `<span class="info-tip" tabindex="0" role="button" data-help-text="${escapeHtml(text)}" aria-label="Open engineering explanation">i<span class="info-popover">${escapeHtml(text)}<em>Click for detailed movable help</em></span></span>`}
function fieldLabelHtml(f){return `${escapeHtml(f.label)}${f.info?infoTip(f.info):''}`}
const contextualHelpCatalog={
  calculateBtn:{title:'Calculate / Run',body:'Runs the active Total RO Design process model using the current inputs. Resolve mandatory-field warnings first. Auto-controlled pressures, recoveries and coupled ERD duties are solved during this run.'},
  runBackgroundOptimizer:{title:'Background Design Optimizer',body:'Screens many nearby plant designs, using the GPU for the large vector screening pass when OpenCL is available. The best candidates are then rigorously recalculated with the multicore CPU engineering model before ranking.'},
  populateSolutionsBtn:{title:'Populate selected solutions',body:'Copies the current successfully calculated Plant Design Basis into the selected ERD alternatives. Recalculate the Plant Design Basis after changing topology, membranes, flows or chemistry before populating again.'},
  printResultsBtn:{title:'Print results',body:'Builds a print-ready engineering summary of the current calculated case. Review warnings, solver diagnostics and active units before issuing a report.'},
  runAllBtn:{title:'Run all scenarios',body:'Runs the configured Scenario Matrix across populated technologies, N and N−1, and the hydraulic-envelope conditions. This can be compute intensive.'},
  optimizeFluxBtn:{title:'Optimize flux balance',body:'Searches a coupled membrane/turbo operating point that brings the locked turbo duty back inside its usable Cv window while respecting the selected production/recovery adjustment limits.'}
};
let contextualHelpState={dragging:false,dx:0,dy:0};
function helpTextForElement(el){
  if(!el)return null;
  if(el.classList?.contains('info-tip'))return {title:'Engineering guidance',body:el.dataset.helpText||el.querySelector('.info-popover')?.textContent||''};
  const rec=contextualHelpCatalog[el.id];if(rec)return rec;
  const txt=(el.textContent||'').replace(/\s+/g,' ').trim();
  if(!txt)return null;
  if(el.matches('button,[role="button"]'))return {title:txt,body:`Use “${txt}” to perform this action in the current Total RO Design workspace. Inputs and calculated results are not changed until the action is explicitly run or applied.`};
  return null;
}
function ensureContextHelpPanel(){
  let panel=document.getElementById('contextHelpPanel');if(panel)return panel;
  panel=document.createElement('aside');panel.id='contextHelpPanel';panel.className='context-help-panel';panel.hidden=true;
  panel.innerHTML=`<div class="context-help-head"><div><span>TOTAL RO DESIGN ENGINEERING HELP</span><strong id="contextHelpTitle">Engineering guidance</strong></div><div class="context-help-tools"><button type="button" id="contextHelpPin" aria-label="Pin help">⌖</button><button type="button" id="contextHelpClose" aria-label="Close help">×</button></div></div><div id="contextHelpBody" class="context-help-body"></div><div class="context-help-foot">Drag this panel by its header. Hover the ⓘ icon for a quick explanation.</div>`;
  document.body.appendChild(panel);
  panel.querySelector('#contextHelpClose').addEventListener('click',()=>panel.hidden=true);
  panel.querySelector('#contextHelpPin').addEventListener('click',()=>panel.classList.toggle('pinned'));
  const head=panel.querySelector('.context-help-head');
  head.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;const r=panel.getBoundingClientRect();contextualHelpState={dragging:true,dx:e.clientX-r.left,dy:e.clientY-r.top};head.setPointerCapture?.(e.pointerId);panel.classList.add('dragging')});
  head.addEventListener('pointermove',e=>{if(!contextualHelpState.dragging)return;const w=panel.offsetWidth,h=panel.offsetHeight;const x=Math.max(8,Math.min(window.innerWidth-w-8,e.clientX-contextualHelpState.dx));const y=Math.max(8,Math.min(window.innerHeight-h-8,e.clientY-contextualHelpState.dy));panel.style.left=`${x}px`;panel.style.top=`${y}px`;panel.style.right='auto';panel.style.bottom='auto'});
  const stop=e=>{contextualHelpState.dragging=false;panel.classList.remove('dragging');try{head.releasePointerCapture?.(e.pointerId)}catch(_){}};head.addEventListener('pointerup',stop);head.addEventListener('pointercancel',stop);
  return panel;
}
function openContextHelp(el){const rec=helpTextForElement(el);if(!rec?.body)return;const panel=ensureContextHelpPanel();panel.querySelector('#contextHelpTitle').textContent=rec.title;panel.querySelector('#contextHelpBody').textContent=rec.body.replace(/Click for detailed movable help\s*$/,'').trim();panel.hidden=false;if(!panel.style.left){panel.style.right='18px';panel.style.top='120px'} }
function bindContextualHelp(){
  document.addEventListener('click',e=>{const t=e.target.closest('.info-tip');if(t){e.preventDefault();e.stopPropagation();openContextHelp(t);return}const b=e.target.closest('button');if(b&&!b.dataset.noContextHelp&&e.altKey){openContextHelp(b)}});
  document.addEventListener('pointerover',e=>{const b=e.target.closest('button');if(!b||b.title||b.closest('.context-help-panel'))return;const rec=helpTextForElement(b);if(rec)b.title=`${rec.body}  Alt+click for detailed movable help.`});
}
function membraneSpecNoteHtml(mm,key=''){
  if(!mm)return `<div class="membrane-spec-note warning" data-membrane-note="${escapeHtml(key)}">Membrane data not found.</div>`;
  if(mm.calculation_enabled){
    const test=`${mm.tds_ppm??'—'} ppm ${mm.test_solute||'salt'} @ ${mm.pressure_psi??'—'} psi · ${mm.recovery_pct??'—'}% recovery`;
    const flux=Number(mm.test_flux_lmh);const aapp=Number(mm.specific_flux_A_app_lmh_bar);const fluxShown=convert(flux,'flux','LMH',unitFor('flux'));
    const nb=mm.nf_rejection_benchmarks||null;
    let nfLine='';
    if(nb){
      const pieces=[];
      for(const k of ['mono_mono','mixed_valence','divalent_divalent','divalent_divivalent']){const b=nb[k];if(!b)continue;const rel=b.published_relation?b.published_relation:`${Number(b.rejection_pct).toFixed(1)}%`;pieces.push(`${b.salt||k} ${rel}`)}
      nfLine=`<br><strong>NF salt selectivity:</strong> ${escapeHtml(pieces.join(' · '))}<br><span class="muted">Charge-balanced salt-pair transport; Full Water Analysis required.</span>`;
    }
    return `<div class="membrane-spec-note" data-membrane-note="${escapeHtml(key)}"><strong>${escapeHtml(membraneManufacturerLabel(mm.manufacturer))} · ${escapeHtml(mm.model)}</strong> · ${escapeHtml(mm.application||'RO')}<br>Manufacturer test: ${escapeHtml(test)} · Jtest ${Number.isFinite(fluxShown)?fluxShown.toFixed(2):'—'} ${unitFor('flux')} · A<sub>app</sub> ${Number.isFinite(aapp)?aapp.toFixed(3):'—'} LMH/bar · spacer ${mm.spacer_mil??'—'} mil${nfLine}</div>`;
  }
  return `<div class="membrane-spec-note warning" data-membrane-note="${escapeHtml(key)}"><strong>${escapeHtml(membraneManufacturerLabel(mm.manufacturer))} · ${escapeHtml(mm.model)}</strong><br>Catalog-only: ${escapeHtml(mm.calculation_disabled_reason||'test point not yet verified')}</div>`;
}
function refreshMembraneDescription(select){
  if(!select)return;const mm=membranes.find(m=>m.record_id===select.value);const wrap=select.closest('.wrap');if(!wrap)return;
  const current=wrap.querySelector('.membrane-spec-note');
  const html=membraneSpecNoteHtml(mm,select.name);
  if(current)current.outerHTML=html;else select.insertAdjacentHTML('afterend',html);
}
function numericInputSize(k,f){
  if(f.type==='integer'||/(stage_count|vessels_|elements_per_vessel_|operating_trains|standby_trains|qty$)/.test(k))return 'input-xs';
  if(['pressure','flux','percent','recoveryPct'].includes(f.type)||/(temperature|ph$|factor|eff|frequency|hz$)/i.test(k))return 'input-sm';
  if(f.type==='flow'||/(capacity|flow|power|area|tds)/i.test(k))return 'input-md';
  return 'input-sm';
}
function inputHtml(k,f,val){
  if(f.type==='toggle')return `<label class="toggle"><input name="${k}" type="checkbox" value="1" ${val?'checked':''}><span class="toggle-ui"></span><em>${escapeHtml(f.toggleText||'No VFD → ηVFD = 100%')}</em></label>`;
  if(f.type==='select'){const opts=(k==='design_mode'&&!tierAllows('auto_design'))?f.options.filter(o=>String(o[0])!=='auto'):f.options;return `<select class="engineering-select" name="${k}" ${f.readOnly?'disabled':''}>${opts.map(o=>`<option value="${o[0]}" ${String(val)===String(o[0])?'selected':''} ${o[2]?'disabled':''}>${o[1]}</option>`).join('')}</select>`;}
  if(f.type==='membrane'){const mm=membranes.find(m=>m.record_id===val);return `<select class="engineering-select membrane-select" name="${k}" data-membrane-select="1">${membraneOptions(val)}</select>${membraneSpecNoteHtml(mm,k)}`;}
  if(f.type==='integer')return `<input class="${numericInputSize(k,f)}" name="${k}" type="number" min="1" max="8" step="1" value="${val??''}" required>`;
  const req=(k.endsWith('cvc')||k==='cvc'||f.optional||f.readOnly)?'':'required';let min=f.minPressureBar!==undefined?(unitFor('pressure')==='psi'?f.minPressureBar*14.5037738:f.minPressureBar):f.min;let max=f.max;if(f.type==='flux'){if(min!=null)min=convert(min,'flux','LMH',unitFor('flux'));if(max!=null)max=convert(max,'flux','LMH',unitFor('flux'));}
  return `<input class="${numericInputSize(k,f)}" name="${k}" type="number" step="any" value="${val??''}" placeholder="${f.placeholder||''}" ${min!==undefined?`min="${min}"`:''} ${max!==undefined?`max="${max}"`:''} ${f.readOnly?'readonly':''} ${req}>`;
}
function needsManualEntry(k,f){if(f.optional||f.readOnly)return false;return ['flow','pressure','recoveryPct','integer'].includes(f.type)||k.startsWith('vessels_')||k.startsWith('elements_per_vessel_')||['operating_trains','fouling_factor','salt_passage_factor'].includes(k);}
function updateRequiredFieldStates(){document.querySelectorAll('#fields .field').forEach(field=>{const input=field.querySelector('input,select,textarea');const note=field.querySelector('.mandatory-note');const missing=field.dataset.manualEntry==='1'&&!!input&&input.required&&!input.readOnly&&!input.disabled&&String(input.value??'').trim()==='';field.classList.toggle('missing-required',missing);if(note)note.hidden=!missing;});}
function calculateButton(){return document.querySelector('#calculateBtn')}
function calculateButtonLabel(){return calculateButton()?.querySelector('.calc-btn-label')}
function workspaceCalculateLabel(modeKey=mode,fallback='Calculate'){
  if(modeKey==='water')return 'Calculate water chemistry';
  if(modeKey==='multistage')return 'Calculate Plant Design';
  return fallback||'Calculate';
}
function setPrimaryLabel(text=''){
  const button=calculateButton(),label=calculateButtonLabel();if(!button||!label)return;
  const resolved=workspaceCalculateLabel(mode,text||button.dataset.twdsIdleLabel||'Calculate');
  label.textContent=resolved;button.dataset.twdsIdleLabel=resolved;
}
function solveArrowHtml(){return `<span class="solve-arrows"><button type="button" class="solve-arrow" data-solve="pressure" title="Pressure setpoint: calculate permeate flow and overall recovery">P→Q</button><button type="button" class="solve-arrow" data-solve="product" title="Permeate-flow setpoint: solve required membrane feed pressure and recovery">Q→P</button><button type="button" class="solve-arrow" data-solve="recovery" title="Overall-recovery setpoint: calculate permeate flow from feed flow and solve required membrane feed pressure">R→P</button></span>`}
const STANDARD_SW={ammonium:0,sodium:10783.7,potassium:399.1,magnesium:1283.7,calcium:412.1,strontium:7.9,barium:0,iron_ii:0,iron_iii:0,manganese_ii:0,fluoride:1.3,chloride:19352.4,sulfate:2712.3,nitrate:0,carbonate:15.6,bicarbonate:108,phosphate:0,boron:4.5,bromide:67.3,silica:2};
const CASPIAN_SW={ammonium:0,sodium:2990,potassium:90,magnesium:700,calcium:340,strontium:0,barium:0,iron_ii:0,iron_iii:0,manganese_ii:0,fluoride:0,chloride:5180,sulfate:2980,nitrate:0,carbonate:0,bicarbonate:0,phosphate:0,boron:0,bromide:0,silica:0};
function roundTdsFromPsu(psu){return Math.round(Number(psu||0))*1000}
function scaledChemistry(kind,tds){const base=kind==='caspian'?CASPIAN_SW:STANDARD_SW;const total=Object.values(base).reduce((a,b)=>a+b,0)||1;const f=Number(tds||0)/total;const out={};Object.keys(base).forEach(k=>out['ion_'+k]=base[k]*f);return out}
function presetById(id){return seawaterPresets.find(p=>p.id===id)||null}

function blankWaterProfile(){
  const out={
    water_region:'',
    water_region_name:'',
    water_mode:'full',
    feed_tds:'',
    analysis_tds:'',
    temperature_c:'',
    temperature_min_c:'',
    temperature_max_c:'',
    temperature_source_name:'Project input',
    temperature_source_url:'',
    feed_ph:'',
    salinity_psu:'',
    fouling_factor:'',
    new_membrane_fouling_factor:'',
    old_membrane_fouling_factor:'',
    salt_passage_factor:'',
    envelope_label:'Base design',
    source_water_type:'',
    acid_enabled:false,
    acid_type:'none',
    acid_target_ph:7.0,
    acid_solution_strength_pct:32,
    acid_solution_density_kg_l:1.16,
    acid_reference_flow_m3h:'',
    acid_last_result:null
  };
  Object.keys(chemistry)
    .filter(k=>k.startsWith('ion_'))
    .forEach(k=>out[k]='');
  return out;
}

function waterProfileHasAnalyticalBasis(w=waterProfile){
  if(String(w?.water_region||'').trim())return true;
  if(Number(w?.analysis_tds||0)>0)return true;
  return Object.keys(chemistry)
    .filter(k=>k.startsWith('ion_'))
    .some(k=>Number(w?.[k]||0)>0);
}
function makeWaterProfile(p){const tds=roundTdsFromPsu(p.salinity_psu);return {water_region:p.id,water_region_name:p.name,water_mode:'full',feed_tds:tds,analysis_tds:tds,temperature_c:p.temperature_c,temperature_min_c:p.temperature_min_c??p.temperature_c,temperature_max_c:p.temperature_max_c??p.temperature_c,temperature_source_name:p.temperature_source_name||'Project input',temperature_source_url:p.temperature_source_url||'',feed_ph:p.ph??8.1,salinity_psu:p.salinity_psu,fouling_factor:p.fouling_factor??0.85,new_membrane_fouling_factor:p.new_membrane_fouling_factor??0.95,old_membrane_fouling_factor:p.old_membrane_fouling_factor??0.70,salt_passage_factor:p.salt_passage_factor??1.0,envelope_label:'Base design',source_water_type:'seawater',acid_enabled:false,acid_type:'none',acid_target_ph:7.0,acid_solution_strength_pct:32,acid_solution_density_kg_l:1.16,acid_reference_flow_m3h:1500,acid_last_result:null,...scaledChemistry(p.chemistry,tds)}}

function deepClone(o){if(o===null||o===undefined)return o;return JSON.parse(JSON.stringify(o))}
function activeCaseData(){return caseStore[activeCase]||null}
function caseWaterIsValid(c=activeCaseData()){return Boolean(c?.chemistryResult?.analysis||c?.chemistryResult?.water_state||c?.chemistryResult?.tds_mg_l||c?.chemistryResult?.analysis_tds||lastChemistryResult);}
function caseBaseSeed(c=activeCaseData()){const seed=c?.baseDesignSeed;return seed&&!seed.stale?seed:null;}
function casePlantIsValid(c=activeCaseData()){return Boolean(c?.caseResults?.multistage&&caseBaseSeed(c));}
function updateWorkflowGates(){
  const waterOk=caseWaterIsValid(),plantOk=casePlantIsValid();
  document.querySelectorAll('.gated-plant').forEach(b=>{const entitled=tierAllows('manual_plant_design');b.disabled=!entitled||!waterOk;b.classList.toggle('workflow-locked',b.disabled);b.title=!entitled?featureLockMessage('manual_plant_design'):(waterOk?'Manual Plant Design':'Calculate valid Water Quality first.');});
  document.querySelectorAll('.gated-envelope').forEach(b=>{const entitled=tierAllows('hydraulic_envelope');b.disabled=!entitled||!plantOk;b.classList.toggle('workflow-locked',b.disabled);b.title=!entitled?featureLockMessage('hydraulic_envelope'):(plantOk?'Hydraulic Envelope':'Calculate a valid Plant Design first.');});
  document.querySelectorAll('.gated-advanced').forEach(b=>{const entitled=tierAllows('advanced_design');b.disabled=!entitled||!plantOk;b.classList.toggle('workflow-locked',b.disabled);b.title=!entitled?featureLockMessage('advanced_design'):(plantOk?'Advance Design':'Calculate a valid Plant Design first.');});
  updateErdNavAccess();
}
function makeBaseDesignSeed(input,result){
  const n=Math.max(1,Math.min(4,Number(result?.stage_count||input?.stage_count||1)));
  const stages=[];for(let i=1;i<=n;i++)stages.push({stage:i,feed_pressure_bar:Number(result?.[`stage${i}_feed_pressure_bar`]??result?.[`membrane_pressure_${i}`]??(i===1?result?.membrane_pressure_1:null)),concentrate_pressure_bar:Number(result?.[`stage${i}_concentrate_pressure_bar`]??result?.[`concentrate_pressure_${i}`]??0),dp_bar:Number(result?.[`stage${i}_dp_bar`]??result?.[`stage_dp_${i}`]??0),feed_flow:Number(result?.[`stage${i}_feed_flow`]??result?.[`feed_flow_${i}`]??(i===1?result?.feed_flow:0)),permeate_flow:Number(result?.[`stage${i}_permeate_flow`]??result?.[`product_flow_${i}`]??0),concentrate_flow:Number(result?.[`reject_flow_${i}`]??0),recovery:Number(result?.[`stage${i}_recovery`]??0)});
  const elements=Array.isArray(result?.element_results)?deepClone(result.element_results):Array.isArray(result?.elements)?deepClone(result.elements):[];
  return {schema:'ROSeed-v0.2',case_id:activeCase,created_at:new Date().toISOString(),stale:false,source:'Plant Design',water_signature:{tds:Number(waterProfile.analysis_tds||waterProfile.feed_tds||0),ph:Number(waterProfile.feed_ph||0),temperature_c:Number(waterProfile.temperature_c||0)},stage_count:n,membranes:Array.from({length:n},(_,j)=>input?.[`membrane_${j+1}`]||null),vessels:Array.from({length:n},(_,j)=>Number(input?.[`vessels_${j+1}`]||0)),elements_per_vessel:Array.from({length:n},(_,j)=>Number(input?.[`elements_per_vessel_${j+1}`]||0)),feed_pressure_bar:Number(result?.membrane_pressure_1||result?.solved_feed_pressure||0),feed_flow:Number(result?.feed_flow||input?.feed_flow||0),product_flow:Number(result?.product_flow||0),recovery:Number(result?.recovery||0),stages,elements,input_snapshot:deepClone(input),result_snapshot:deepClone(result),solver_metadata:{iterations:Number(result?.pressure_solve_iterations||0),evaluations:Number(result?.pressure_solve_evaluations||0),method:result?.solver_method||'',fallback:!!result?.solver_fallback_used,seed_source:result?.pressure_seed_source||'',runtime_s:Number(result?.calculation_time_s||result?.elapsed_seconds||0)}};
}
function markBaseSeedStale(reason='Plant Design inputs changed'){const c=activeCaseData();if(c?.baseDesignSeed){c.baseDesignSeed.stale=true;c.baseDesignSeed.stale_reason=reason;}if(c){c.advancedDesignResult=null;c.hydraulicEnvelope=null;c.scenarioMatrixResult=null;}advancedDesignResult=null;updateWorkflowGates();}
function baseSeedStatusHtml(){const seed=caseBaseSeed();if(!seed)return `<section class="input-section seed-card"><h3>BASE DESIGN SEED</h3><p class="muted">Calculate this manual Plant Design to create the converged seed used by Advance Design and ERD calculations.</p></section>`;return `<section class="input-section seed-card seed-ready"><h3>BASE DESIGN SEED · READY</h3><p><strong>Case ${activeCase}</strong> · ${seed.stage_count} stage${seed.stage_count===1?'':'s'} · feed pressure ${fmt(seed.feed_pressure_bar,2)} bar · product ${fmt(seed.product_flow,2)} ${currentUnits.flow}</p><p class="micro-note">Saved converged RO vector · seed source: ${escapeHtml(seed.solver_metadata?.seed_source||'Plant Design')} · iterations ${seed.solver_metadata?.iterations??'—'}.</p></section>`;}
function advancedResultHtml(){const r=activeCaseData()?.advancedDesignResult;if(!r)return '<p class="muted">No advanced calculation has been run. Plant Design remains the authoritative reference state.</p>';return `<section class="report-section"><h3>ADVANCED DESIGN RESULT</h3><p><strong>Seeded from Plant Design · Case ${activeCase}</strong></p><div class="result-grid"><div><span>Feed pressure</span><strong>${fmt(r.membrane_pressure_1||r.solved_feed_pressure,2)} bar</strong></div><div><span>Product flow</span><strong>${fmt(r.product_flow,2)} ${currentUnits.flow}</strong></div><div><span>Recovery</span><strong>${fmt(Number(r.recovery||0)*100,2)}%</strong></div><div><span>Solver</span><strong>${escapeHtml(r.pressure_seed_source||'Base Design warm start')}</strong></div></div></section>`;}
function renderAdvancedDesignTab(){
  const root=$('#fields');if(!root)return;const seed=caseBaseSeed();$('#modeLabel').textContent=`Advance Design · Case ${activeCase}`;
  if(!seed){root.innerHTML='<section class="input-section"><h3>ADVANCE DESIGN LOCKED</h3><p>Calculate a valid manual Plant Design first.</p></section>';$('#results').innerHTML='';return;}
  const base=seed.input_snapshot||{},rec=(Number(base.target_recovery||Number(seed.recovery||0)*100)||45),cap=Number(base.required_capacity_m3d||((Number(seed.product_flow)||0)*24*(Number(base.operating_trains)||1))||0);
  const optimizer=tierAllows('design_optimizer')?`<section class="input-section" data-tier-field-feature="design_optimizer"><h3>DESIGN OPTIMIZER · PLATINUM</h3><p class="micro-note">The numerical optimizer searches around the converged Base Design and runs only when requested.</p><button type="button" class="envelope-btn" id="runAdvancedOptimizer">Run Design Optimizer</button></section>`:`<section class="tier-upgrade-card"><strong>Design Optimizer · Platinum</strong><span>Platinum adds large candidate screening and rigorous validation around the Gold Base Design.</span></section>`;
  const scenario=tierAllows('scenario_matrix')?`<section class="input-section" data-tier-field-feature="scenario_matrix"><h3>SCENARIO MATRIX · PLATINUM INTERNAL PREVIEW</h3><p class="micro-note">Run N/N−1 and condition combinations from the current solved design. This module remains an internal administrator preview until its v0.2 case-isolation migration is complete.</p><button type="button" class="envelope-btn" id="openScenarioMatrixFromAdvanced">Open Scenario Matrix</button><span class="tier-internal-pill">Internal preview</span></section>`:'';
  root.innerHTML=`${baseSeedStatusHtml()}<section class="input-section"><h3>AUTO DESIGN · GOLD WARM START</h3><p class="micro-note">Optimize around the converged manual design. The Base Design is not overwritten.</p><div class="grid"><div class="field"><label>Required plant product capacity</label><div class="wrap"><input name="adv_capacity" type="number" step="any" value="${cap||''}"><span class="suffix">m³/d</span></div></div><div class="field"><label>Target recovery</label><div class="wrap"><input name="adv_recovery" type="number" step="any" value="${rec}"><span class="suffix">%</span></div></div><div class="field"><label>Maximum average stage flux</label><div class="wrap"><input name="adv_flux" type="number" step="any" value="${Number(base.max_design_flux_lmh||14)}"><span class="suffix">LMH</span></div></div><div class="field"><label>Operating trains</label><div class="wrap"><input name="adv_trains" type="number" min="1" step="1" value="${Number(base.operating_trains||1)}"></div></div></div><button type="button" class="envelope-btn" id="runAdvancedAutoDesign">Optimize from Base Design</button></section>${optimizer}${scenario}`;
  $('#results').innerHTML=advancedResultHtml();const cb=$('#calculateBtn');if(cb)cb.hidden=true;bindAdvancedDesign();applyTierEntitlements();
}
async function runAdvancedAutoDesign(){const c=activeCaseData(),seed=caseBaseSeed(c);if(!seed)throw new Error('Calculate Plant Design first.');if(!tierAllows('auto_design'))throw new Error(featureLockMessage('auto_design'));const base=deepClone(seed.input_snapshot||{}),q=n=>Number(document.querySelector(`[name="${n}"]`)?.value||0);const data={...waterProfile,...base,design_mode:'auto',required_capacity_m3d:q('adv_capacity'),target_recovery:q('adv_recovery'),max_design_flux_lmh:q('adv_flux'),operating_trains:Math.max(1,q('adv_trains')||1),_base_design_seed:deepClone(seed),_warm_start_seed:deepClone(seed),flow_unit:currentUnits.flow,pressure_unit:currentUnits.pressure};const r=await requestJson('/api/calculate/multistage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)},'Advanced Auto Design failed');c.advancedDesignInput=deepClone(data);c.advancedDesignResult=deepClone(r);advancedDesignInput=deepClone(data);advancedDesignResult=deepClone(r);syncActiveCaseStore();$('#results').innerHTML=advancedResultHtml();}
function bindAdvancedDesign(){$('#runAdvancedAutoDesign')?.addEventListener('click',async()=>{setCalculating(true);try{await runAdvancedAutoDesign()}catch(e){showCalcError(e,'Advance Design')}finally{setCalculating(false)}});$('#runAdvancedOptimizer')?.addEventListener('click',async()=>{if(!tierAllows('design_optimizer')){showCalcError(new Error(featureLockMessage('design_optimizer')),'subscription tier');return;}const seed=caseBaseSeed();if(!seed)return;const data={...waterProfile,...deepClone(seed.input_snapshot||{}),_base_design_seed:deepClone(seed),_warm_start_seed:deepClone(seed)};setCalculating(true);try{const j=await requestJson('/api/optimize/plant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data,mode:'multistage',objective:'min_sec',screen_candidates:2048,validate_candidates:24})},'Design optimization failed');lastDesignOptimization=j;$('#results').innerHTML=`<section class="report-section"><h3>DESIGN OPTIMIZER</h3><p>${j.screened||0} screened · ${j.validated||0} fully validated from the Base Design neighborhood.</p></section>`;}catch(e){showCalcError(e,'Design Optimizer')}finally{setCalculating(false)}});$('#openScenarioMatrixFromAdvanced')?.addEventListener('click',()=>changeMode('scenario'));}
function syncActiveCaseStore(){
  const existing=caseStore[activeCase]||{};
  caseStore[activeCase]={...existing,waterProfile:deepClone(waterProfile),modeStates:deepClone(modeStates),caseResults:deepClone(caseResults),economicState:deepClone(economicState),lastEconomicResult:deepClone(lastEconomicResult),chemistryResult:deepClone(lastChemistryResult),baseDesignSeed:deepClone(existing.baseDesignSeed||null),advancedDesignInput:deepClone(advancedDesignInput),advancedDesignResult:deepClone(advancedDesignResult)};
}
function persistActiveCase(){
  if(mode==='water'&&document.querySelector('[name="water_region"]'))waterProfile=captureWater();
  else if(!['water','chemistry','comparison','summary','economic'].includes(mode)&&document.querySelector('[name="feed_flow"]')){
    const captured=capture(),previous=modeStates[mode]||{};
    // Preserve non-form workflow metadata when leaving a calculated workspace.
    // These fields are intentionally not DOM inputs, so a raw capture() must not erase them.
    const workflowMeta={};
    Object.entries(previous).forEach(([k,v])=>{if(k.startsWith('_')||['generated_from_base_plant','solution_enabled','generalized_biturbo','plant_solution'].includes(k))workflowMeta[k]=v;});
    modeStates[mode]={...captured,...workflowMeta};
  }
  else if(mode==='economic'&&document.querySelector('[name="product_capacity_m3d"]'))economicState=captureEconomic();
  syncActiveCaseStore();
}
function caseLimitForTier(){return tierAllows('multi_case')?MAX_CASES:1;}
function renderCaseBar(){
  const root=$('#caseTabs');if(!root)return;const allIds=Object.keys(caseStore).map(Number).sort((a,b)=>a-b),multi=tierAllows('multi_case'),ids=multi?allIds:allIds.slice(0,1),limit=caseLimitForTier();
  const chips=ids.map(id=>{const c=caseStore[id]||{},wp=c.waterProfile||{},label=escapeHtml(wp.envelope_label||`Case ${id}`),status=c.baseDesignSeed&&!c.baseDesignSeed.stale?'✓':(c.baseDesignSeed?.stale?'!':'—');return `<button type="button" class="case-chip case-tab ${id===activeCase?'active':''}" data-case="${id}" title="${label}"><strong>${id}</strong><span>${label}</span><em>${status}</em></button>`}).join('');
  const controls=multi?((allIds.length<limit?`<button type="button" class="case-chip case-tab add-case" data-add-case="1" title="Add case">+</button>`:'')+(allIds.length>1?`<button type="button" class="case-chip case-tab remove-case" data-remove-case="1" title="Delete selected case">−</button>`:'')):`<button type="button" class="case-chip tier-case-lock" disabled title="Silver unlocks up to 10 independent cases">1 case · Silver+</button>`;
  const preserved=!multi&&allIds.length>1?`<span class="tier-preserved-note">${allIds.length-1} higher-tier case${allIds.length===2?'':'s'} preserved</span>`:'';
  root.innerHTML=chips+controls+preserved;updateWorkspaceChrome();updateWorkflowGates();}
function removeActiveCase(){if(!tierAllows('multi_case')){showCalcError(new Error(featureLockMessage('multi_case')),'subscription tier');return;}const ids=Object.keys(caseStore).map(Number).sort((a,b)=>a-b);if(ids.length<=1)return;const c=activeCaseData(),hasData=Object.keys(c?.caseResults||{}).length||Object.keys(c?.modeStates||{}).length||c?.chemistryResult;if(hasData&&!window.confirm(`Delete Case ${activeCase} and its stored inputs, results and seeds?`))return;delete caseStore[activeCase];const next=Object.keys(caseStore).map(Number).sort((a,b)=>a-b)[0];loadCaseGlobals(next);mode='water';renderCaseBar();renderWaterTab();$('#results').innerHTML='';}
function loadCaseGlobals(id){
  const c=caseStore[id]; if(!c)return false;
  activeCase=id; waterProfile=deepClone(c.waterProfile); modeStates=deepClone(c.modeStates||{}); caseResults=deepClone(c.caseResults||{}); economicState=deepClone(c.economicState||economicDefaults); lastEconomicResult=deepClone(c.lastEconomicResult||null); lastChemistryResult=deepClone(c.chemistryResult||null); advancedDesignInput=deepClone(c.advancedDesignInput||{}); advancedDesignResult=deepClone(c.advancedDesignResult||null); lastResult=caseResults[mode]||null; updateWorkflowGates(); return true;
}
function switchCase(id){
  id=Number(id);if(!tierAllows('multi_case')){const first=Object.keys(caseStore).map(Number).sort((a,b)=>a-b)[0];if(id!==first)return;}if(!caseStore[id]||id===activeCase)return;
  persistActiveCase(); loadCaseGlobals(id); caseSetupNotice=''; renderCaseBar();
  const vals=modeStates[mode]||convertedDefaults(); renderFields(vals); $('#warnings').innerHTML='';
  if(mode==='water')renderCurrentWaterChemistry();
  else if(mode==='advanced'){$('#results').innerHTML=advancedResultHtml();}
    else if(mode==='envelope')$('#results').innerHTML=hydraulicEnvelopeStatusHtml();
  else if(mode==='scenario')$('#results').innerHTML=scenarioMatrixResults();
  else if(mode==='comparison')$('#results').innerHTML=comparisonResults();
  else if(mode==='summary')$('#results').innerHTML=summaryResults();
  else if(mode==='economic')$('#results').innerHTML=lastEconomicResult?economicResults(lastEconomicResult):'<p class="muted">Run the comparison after calculating the technology cases you want to evaluate.</p>';
  else if(caseResults[mode]){lastResult=caseResults[mode];syncSolveResult(lastResult);show(lastResult)}else $('#results').innerHTML='<p class="muted">Enter required inputs and calculate.</p>';
}
function nextCaseId(){for(let i=1;i<=MAX_CASES;i++)if(!caseStore[i])return i;return null}
function addCase(){
  if(!tierAllows('multi_case')){showCalcError(new Error(featureLockMessage('multi_case')),'subscription tier');return;}
  const id=nextCaseId(); if(!id){alert('Maximum of 10 cases reached.');return;}
  persistActiveCase(); markAllTurboDesignStale(); const src=caseStore[activeCase];
  caseStore[id]={waterProfile:deepClone(src.waterProfile),modeStates:deepClone(src.modeStates||{}),caseResults:{},economicState:deepClone(src.economicState||economicDefaults),lastEconomicResult:null,chemistryResult:deepClone(src.chemistryResult||null),baseDesignSeed:null,advancedDesignInput:{},advancedDesignResult:null};
  caseStore[id].waterProfile.envelope_label=`Case ${id}`;
  caseSetupNotice=`Case ${id} created. Water quality is copied from Case ${activeCase} as a starting point, and the hydraulic/design inputs are retained so you can change chemistry/temperature/fouling and recalculate quickly.`;
  loadCaseGlobals(id); mode='water'; updateWaterWorkspaceTabs(); renderCaseBar(); renderWaterTab(); $('#results').innerHTML=waterSummary(); $('#warnings').innerHTML='';
}
function processModeConfigured(tech,s){
  if(!s||!Object.keys(s).length)return false;
  if(s.solution_enabled===false)return false;
  if(tech==='multistage'&&String(s.energy_recovery_mode||'with')==='with'&&s.solution_conventional===false)return false;
  const positive=k=>Number.isFinite(Number(s[k]))&&Number(s[k])>0, finite=k=>Number.isFinite(Number(s[k]));
  if(!positive('feed_flow')||!positive('vessels_1')||!positive('elements_per_vessel_1')||!finite('suction_pressure')||!finite('pretreatment_discharge_pressure'))return false;
  const generalizedInterstage=tech==='interstage'&&(Boolean(s.generalized_interstage_turbo)||Number(s.stage_count||2)>2);
  if(tech==='multistage'||tech==='interstage_px'||tech==='dweer'||tech==='pelton'||generalizedInterstage){
    const n=Math.max(tech==='interstage_px'?2:(generalizedInterstage?3:1),Math.min(4,Number(s.stage_count)||1));
    for(let i=2;i<=n;i++)if(!positive(`vessels_${i}`)||!positive(`elements_per_vessel_${i}`))return false;
  }else if(!['px','interstage_px','multistage','dweer','pelton'].includes(tech)&&!finite('pex'))return false;
  if(tech==='px'&&!(Number(s.stage_count||1)>1||s.plant_solution)&&(!finite('px_lp_outlet_pressure')||Number(s.px_lp_outlet_pressure)<1.5))return false;
  if(((tech==='interstage'&&!generalizedInterstage)||tech==='biturbo')&&(!positive('vessels_2')||!positive('elements_per_vessel_2')))return false;
  if(tech==='biturbo'&&!positive('target_interstage_boost')&&!Boolean(s.generalized_biturbo))return false;
  const basis=s.solve_basis||'recovery';
  if(basis==='recovery'&&!positive('target_recovery'))return false;
  if(basis==='product'&&!positive('target_product_flow'))return false;
  if(basis==='pressure'&&!positive('membrane_pressure_1'))return false;
  if(basis==='pressure'&&((tech==='interstage'&&!generalizedInterstage)||tech==='biturbo')&&!positive('membrane_pressure_2'))return false;
  return true;
}
function configuredProcessModes(state){return ['multistage','single','px','interstage_px','interstage','biturbo','dweer','pelton'].filter(k=>processModeConfigured(k,state?.[k]))}
function processPayload(caseData,tech,useLock=true){
  // v16.8: the case water profile is the authoritative source for every shared
  // water-quality/transport input. Process modeStates can contain mirrored UI
  // controls (notably fouling_factor and salt_passage_factor); those values must
  // never override the case-specific hydraulic-envelope condition.
  const state=deepClone(caseData.modeStates?.[tech]||{});
  const water=deepClone(caseData.waterProfile||{});
  const data={...state,...water,...(useLock?activeTurboLockFields(tech):{}),flow_unit:currentUnits.flow,pressure_unit:currentUnits.pressure};if(data.pretreatment_discharge_pressure===undefined||data.pretreatment_discharge_pressure==='')data.pretreatment_discharge_pressure=6;if(data.max_design_flux_lmh!==undefined&&data.max_design_flux_lmh!=='')data.max_design_flux_lmh=convert(data.max_design_flux_lmh,'flux',currentUnits.flux||'LMH','LMH');
  if(tech==='px'){data.px_lp_inlet_pressure=data.suction_pressure;data.mpe_hp_dp=.66;data.mpe_lp_dp=.74;data.mpe_mixing=.02;data.mpe_motor_power=.8;}
  return data;
}
function resultMatchesCaseWaterBasis(c,r){
  if(!c?.waterProfile||!r)return true;
  const w=c.waterProfile;
  const checks=[
    [r.stage1_temperature_c,w.temperature_c],
    [r.stage1_fouling_factor,w.fouling_factor],
    [r.stage1_salt_passage_factor,w.salt_passage_factor],
  ];
  return checks.every(([actual,expected])=>actual===undefined||expected===undefined||Math.abs(Number(actual)-Number(expected))<=1e-7);
}
function invalidateMismatchedCaseResults(store=caseStore){
  let removed=0;
  Object.values(store||{}).forEach(c=>{
    Object.keys(c?.caseResults||{}).forEach(k=>{
      const r=c.caseResults[k];
      if(!resultMatchesCaseWaterBasis(c,r)){delete c.caseResults[k];removed++;}
    });
  });
  return removed;
}
function envelopeDefaults(c=activeCaseData()){
  const p=c?.waterProfile||waterProfile||{},saved=c?.hydraulicEnvelope?.conditions;
  if(Array.isArray(saved)&&saved.length===4)return deepClone(saved);
  const cold=Number(p.temperature_min_c??p.temperature_c??15),warm=Number(p.temperature_max_c??p.temperature_c??30),newFF=Number(p.new_membrane_fouling_factor??p.fouling_factor??0.95),oldFF=Number(p.old_membrane_fouling_factor??p.fouling_factor??0.70),sp=Number(p.salt_passage_factor??1);
  return [
    {id:'new_cold',label:'New membrane · cold water',temperature_c:cold,fouling_factor:newFF,salt_passage_factor:sp},
    {id:'new_warm',label:'New membrane · warm water',temperature_c:warm,fouling_factor:newFF,salt_passage_factor:sp},
    {id:'aged_cold',label:'Aged membrane · cold water',temperature_c:cold,fouling_factor:oldFF,salt_passage_factor:sp},
    {id:'aged_warm',label:'Aged membrane · warm water',temperature_c:warm,fouling_factor:oldFF,salt_passage_factor:sp}
  ];
}
function captureEnvelopeConditions(){return Array.from(document.querySelectorAll('[data-envelope-card]')).map(card=>({id:card.dataset.envelopeCard,label:card.dataset.envelopeLabel||card.querySelector('h4')?.textContent||'',temperature_c:Number(card.querySelector('[name$="_temperature_c"]')?.value),fouling_factor:Number(card.querySelector('[name$="_fouling_factor"]')?.value),salt_passage_factor:Number(card.querySelector('[name$="_salt_passage_factor"]')?.value)}));}
async function calculateHydraulicEnvelope(){
  const c=activeCaseData(),seed=caseBaseSeed(c);if(!seed)throw new Error('Calculate a valid Plant Design first.');const wp=deepClone(c.waterProfile||waterProfile),base=deepClone(seed.input_snapshot||{}),defs=captureEnvelopeConditions();
  if(defs.length!==4||defs.some(x=>![x.temperature_c,x.fouling_factor,x.salt_passage_factor].every(Number.isFinite)))throw new Error('Hydraulic Envelope conditions contain invalid temperature, fouling or salt-passage values.');
  const baseT=Number(wp.temperature_c||defs[0].temperature_c),baseF=Number(wp.fouling_factor||defs[0].fouling_factor),baseS=Number(wp.salt_passage_factor||1);const ordered=defs.slice().sort((a,b)=>(Math.abs(a.temperature_c-baseT)+12*Math.abs(a.fouling_factor-baseF)+3*Math.abs(a.salt_passage_factor-baseS))-(Math.abs(b.temperature_c-baseT)+12*Math.abs(b.fouling_factor-baseF)+3*Math.abs(b.salt_passage_factor-baseS)));
  const rows=[];let warmSeed=deepClone(seed);for(const cond of ordered){if(calculationCancelRequested)throw Object.assign(new Error('Calculation cancelled'),{cancelled:true});const data={...wp,...base,temperature_c:cond.temperature_c,fouling_factor:cond.fouling_factor,salt_passage_factor:cond.salt_passage_factor,design_mode:'manual',_entitlement_feature:'hydraulic_envelope',_base_design_seed:deepClone(seed),_warm_start_seed:deepClone(warmSeed),flow_unit:currentUnits.flow,pressure_unit:currentUnits.pressure};const r=await requestJson('/api/calculate/multistage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)},`Hydraulic Envelope failed at ${cond.label}`);rows.push({...cond,result:r});warmSeed=makeBaseDesignSeed(data,r);}
  const byId=Object.fromEntries(rows.map(x=>[x.id,x]));const display=defs.map(d=>byId[d.id]||d);c.hydraulicEnvelope={generated_at:new Date().toISOString(),base_seed_created_at:seed.created_at,conditions:deepClone(defs),rows:display};syncActiveCaseStore();$('#results').innerHTML=hydraulicEnvelopeResultsHtml(c.hydraulicEnvelope);
}
function hydraulicEnvelopeResultsHtml(env){const rows=env?.rows||[];if(!rows.length)return '<p class="muted">Configure the four study cards and calculate when ready.</p>';return `<section class="report-section"><h3>HYDRAULIC ENVELOPE RESULTS</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Condition</th><th>Temperature</th><th>Fouling factor</th><th>Salt passage</th><th>Feed pressure</th><th>Product flow</th><th>Iterations</th></tr>${rows.map(x=>`<tr><td>${escapeHtml(x.label)}</td><td>${fmt(x.temperature_c,1)} °C</td><td>${fmt(x.fouling_factor,3)}</td><td>${fmt(x.salt_passage_factor,3)}</td><td>${fmt(x.result?.membrane_pressure_1,2)} bar</td><td>${fmt(x.result?.product_flow,2)} ${currentUnits.flow}</td><td>${x.result?.pressure_solve_iterations??'—'}</td></tr>`).join('')}</table></div><p class="micro-note">Inputs and converged results are stored under Case ${activeCase} and reused as warm starts for future calculations.</p></section>`;}
function captureEnvelopeSettings(){const defs=captureEnvelopeConditions();const c=activeCaseData();if(c)c.hydraulicEnvelope={...(c.hydraulicEnvelope||{}),conditions:deepClone(defs)};return waterProfile;}
function renderEnvelopeTab(){const c=activeCaseData(),conds=envelopeDefaults(c),region=(c?.waterProfile||waterProfile)?.water_region_name||'Water Quality reference';$('#fields').innerHTML=`<section class="input-section"><div class="section-inline-title"><div><h3>HYDRAULIC ENVELOPE</h3><p class="micro-note">Initial temperatures are taken from the selected NOAA/Copernicus regional water-quality preset where available. Every condition remains editable before calculation.</p></div></div><div class="envelope-condition-cards">${conds.map((x,i)=>`<article class="envelope-condition-card" data-envelope-card="${escapeHtml(x.id)}" data-envelope-label="${escapeHtml(x.label)}"><div class="envelope-card-head"><span class="envelope-card-icon">${i<2?'◉':'◌'}</span><div><h4>${escapeHtml(x.label)}</h4><small>${escapeHtml(region)}</small></div></div><div class="grid"><div class="field"><label>Temperature</label><div class="wrap"><input name="env${i}_temperature_c" type="number" step="any" value="${x.temperature_c}"><span class="suffix">°C</span></div></div><div class="field"><label>Fouling factor</label><div class="wrap"><input name="env${i}_fouling_factor" type="number" min="0.3" max="1.2" step="0.01" value="${x.fouling_factor}"><span class="suffix">A multiplier</span></div></div><div class="field"><label>Salt passage factor</label><div class="wrap"><input name="env${i}_salt_passage_factor" type="number" min="0.1" max="5" step="0.01" value="${x.salt_passage_factor}"><span class="suffix">B multiplier</span></div></div></div>${c?.hydraulicEnvelope?.rows?.find(r=>r.id===x.id)?.result?'<span class="status-chip ok">Calculated · stored</span>':'<span class="status-chip review">Ready to calculate</span>'}</article>`).join('')}</div></section>`;$('#modeLabel').textContent=`Hydraulic Envelope · Case ${activeCase}`;setPrimaryLabel('Calculate Hydraulic Envelope');$('.solve-hint').textContent='Calculates the four editable operating conditions from the current Plant Design Base Seed and stores each converged state.';const b=$('#calculateBtn');if(b)b.hidden=false;}
function hydraulicEnvelopeStatusHtml(){return hydraulicEnvelopeResultsHtml(activeCaseData()?.hydraulicEnvelope);}
function scenarioTechLabel(k){return ({multistage:'RO Plant Designer',px:'Single Stage Isobaric Chamber',interstage_px:'Interstage Isobaric Chamber',single:'Turbocharger',interstage:'Interstage Turbo',biturbo:'BiTurbo™',dweer:'DWEER',pelton:'Pelton Turbine'})[k]||k}
function scenarioTechIcon(k){return ({multistage:'plant',px:'isobaric',interstage_px:'interstage_isobaric',single:'turbo',interstage:'interstage',biturbo:'biturbo',dweer:'dweer',pelton:'pelton'})[k]||'solutions'}
function captureScenarioMatrixState(){
  const fd=new FormData($('#calcForm'));const next={...scenarioMatrixState};if(mode==='multistage'){const v=capture();next.normal_trains=Math.max(2,Math.round(Number(v.operating_trains||2)));next.required_capacity_m3d=Math.max(0,Number(v.required_capacity_m3d||0));next.maintain_capacity_nminus1=v.scenario_maintain_capacity_nminus1!==false;scenarioMatrixState=next;return next;}
  if(fd.has('normal_trains'))next.normal_trains=Math.max(2,Math.round(Number(fd.get('normal_trains'))||2));
  if(fd.has('required_capacity_m3d'))next.required_capacity_m3d=Math.max(0,Number(fd.get('required_capacity_m3d'))||0);
  next.maintain_capacity_nminus1=fd.get('maintain_capacity_nminus1')==='on';
  scenarioMatrixState=next;return next;
}
function renderScenarioMatrixTab(){
  const st=scenarioMatrixState;const src=caseStore[activeCase]||{};const techs=configuredProcessModes(src.modeStates||{});
  const solutions=techs.length?techs.map(k=>`<div class="case-ready"><span class="solution-icon-card"><img src="/static/icons_v18/${scenarioTechIcon(k)}.svg" alt=""><strong>${escapeHtml(scenarioTechLabel(k))}</strong></span><span>Populated and eligible for Run All</span></div>`).join(''):'<div class="case-ready missing"><strong>No populated solution yet</strong><span>Configure at least one active solution before Run All.</span></div>';
  $('#fields').innerHTML=`<section class="input-section"><h3>PLANT AVAILABILITY MATRIX</h3><div class="v18-scenario-config">
    <div class="field"><label>N · operating trains</label><div class="wrap"><input name="normal_trains" type="number" min="2" max="50" step="1" value="${st.normal_trains}"><span class="suffix">trains</span></div></div>
    <div class="field"><label>Required plant product capacity</label><div class="wrap"><input name="required_capacity_m3d" type="number" min="1" step="any" value="${st.required_capacity_m3d||''}" required><span class="suffix">m³/d</span></div></div>
    <div class="field"><label>Normal per-train product</label><div class="wrap"><input type="text" value="${st.required_capacity_m3d?fmt(st.required_capacity_m3d/st.normal_trains,0):'—'}" readonly><span class="suffix">m³/d</span></div></div>
    <div class="field"><label>N−1 per-train product</label><div class="wrap"><input type="text" value="${st.required_capacity_m3d?fmt(st.required_capacity_m3d/(st.normal_trains-1),0):'—'}" readonly><span class="suffix">m³/d</span></div></div>
  </div><label class="scenario-maintain"><input name="maintain_capacity_nminus1" type="checkbox" ${st.maintain_capacity_nminus1?'checked':''}> Maintain required plant production at N−1 by reloading the remaining trains.</label><p class="micro-note">N−1 is a true membrane / hydraulic recalculation. Total RO Design changes the per-train duty and reruns pressure, flux, product quality, ERD duty, pumps and SEC rather than multiplying the N result algebraically.</p></section>
  <section class="input-section"><h3>POPULATED SOLUTIONS</h3><div class="case-readiness">${solutions}</div><p class="micro-note">Each populated solution is run across New/Cold, New/Warm, Aged/Cold and Aged/Warm at N and N−1. One solution = 8 calculations; two solutions = 16; five solutions = 40.</p></section>`;
  $('#modeLabel').textContent='Scenario Matrix';setPrimaryLabel('Run all configurations');$('.solve-hint').textContent='Solutions × availability states × hydraulic-envelope conditions.';
}
function scenarioResultStatus(r){
  if(!r)return ['fail','Fail'];
  const review=Boolean(r.backpressure_active||r.bypass_active||r.n_minus_one_meets_required===false||String(r.pump_operating_status||'').toLowerCase().includes('review')||String(r.pump_operating_status||'').toLowerCase().includes('outside'));
  return review?['review','Review']:['ok','OK'];
}
function scenarioProductTds(r){return Number(r?.composite_permeate_tds_ppm??r?.permeate_tds_ppm??r?.stage1_permeate_tds_ppm??NaN)}
function scenarioFlux(r){
  const vals=[r?.stage1_flux_lmh,r?.stage2_flux_lmh,r?.stage3_flux_lmh,r?.stage4_flux_lmh].map(Number).filter(Number.isFinite);
  if(vals.length)return vals.reduce((a,b)=>a+b,0)/vals.length;
  return Number(r?.flux_lmh??r?.actual_flux_lmh??NaN);
}
function scenarioMatrixResults(){
  const ids=Object.keys(caseStore||{}).map(Number).sort((a,b)=>a-b).filter(id=>caseStore[id]?.scenarioMeta);
  const rows=[];let ok=0,review=0,fail=0,total=0;const techSet=new Set();
  ids.forEach(id=>{const c=caseStore[id];Object.entries(c.caseResults||{}).forEach(([tech,r])=>{if(!['multistage','single','px','interstage_px','interstage','biturbo','dweer','pelton'].includes(tech))return;techSet.add(tech);total++;const [cls,label]=scenarioResultStatus(r);if(cls==='ok')ok++;else if(cls==='review')review++;else fail++;const m=c.scenarioMeta||{};const p=Number(r?.membrane_pressure_1);const tds=scenarioProductTds(r);const flux=scenarioFlux(r);const acidDose=Number(r?.acid_dose_mg_l),acidKgD=Number(r?.acid_pure_kg_d);rows.push(`<tr class="${m.availability==='N'?'availability-n':'availability-n1'}"><td><span class="solution-icon-card"><img src="/static/icons_v18/${scenarioTechIcon(tech)}.svg" alt=""><strong>${escapeHtml(scenarioTechLabel(tech))}</strong></span></td><td><strong>${escapeHtml(m.availability||'')}</strong><br><span class="tbl-unit">${m.available_trains||'—'} trains</span></td><td>${escapeHtml(m.condition||'')}</td><td>${fmt(c.waterProfile?.temperature_c,1)} °C</td><td>${fmt(c.waterProfile?.fouling_factor,2)}</td><td>${Number.isFinite(p)?fmt(p,2):'—'} ${r?.pressure_unit||''}</td><td>${Number.isFinite(flux)?fmt(fluxValue(flux),2):'—'}</td><td>${Number.isFinite(Number(r?.total_sec))?fmt(r.total_sec,3):'—'}</td><td>${Number.isFinite(tds)?fmt(tds,0):'—'}</td><td>${Number.isFinite(acidDose)?fmt(acidDose,2):'—'}</td><td>${Number.isFinite(acidKgD)?fmt(acidKgD,1):'—'}</td><td><span class="status-chip ${cls}">${label}</span></td></tr>`)});});
  if(!rows.length)return `<section class="report-section"><h3>SCENARIO MATRIX</h3><p class="muted">No v18 N / N−1 matrix has been run yet. Configure at least one solution and click <strong>Run all configurations</strong>.</p></section>`;
  return `<div class="scenario-summary-strip"><div><span>Calculated combinations</span><strong>${total}</strong></div><div><span>Solutions</span><strong>${techSet.size}</strong></div><div><span>OK</span><strong>${ok}</strong></div><div><span>Review / Fail</span><strong>${review} / ${fail}</strong></div></div><section class="report-section"><div class="chart-title-row"><h3>ALL SOLUTIONS · N + N−1 HYDRAULIC ENVELOPE</h3><span>${scenarioMatrixState.normal_trains} → ${scenarioMatrixState.normal_trains-1} trains</span></div><div class="table-wrap"><table class="fedco-table scenario-table"><tr><th>Solution</th><th>Availability</th><th>Condition</th><th>Feed T</th><th>Fouling</th><th>RO pressure</th><th>Avg flux<br><span>${fluxUnit()}</span></th><th>Total SEC<br><span>kWh/m³</span></th><th>Product TDS<br><span>mg/L</span></th><th>Acid dose<br><span>mg/L</span></th><th>Acid<br><span>kg/day</span></th><th>Status</th></tr>${rows.join('')}</table></div><p class="micro-note">The N−1 rows are independent solver runs at the reloaded per-train capacity. Turbo solutions use one design-lock/off-design calculation across all matrix cases.</p></section>`;
}
function scenarioStudyInsights(){
  const entries=[];Object.keys(caseStore||{}).map(Number).sort((a,b)=>a-b).forEach(id=>{const c=caseStore[id];if(!c?.scenarioMeta)return;Object.entries(c.caseResults||{}).forEach(([tech,r])=>{if(!['multistage','single','px','interstage_px','interstage','biturbo','dweer','pelton'].includes(tech)||!r)return;entries.push({id,tech,r,m:c.scenarioMeta,w:c.waterProfile||{}});});});
  if(!entries.length)return '';
  const num=(x,k)=>Number(x?.r?.[k]);const valid=(a)=>a.filter(Number.isFinite);const avg=a=>{a=valid(a);return a.length?a.reduce((x,y)=>x+y,0)/a.length:NaN};const maxBy=(arr,fn)=>arr.reduce((best,x)=>!best||fn(x)>fn(best)?x:best,null);
  const techs=[...new Set(entries.map(x=>x.tech))];
  const compareRows=techs.map(tech=>{const a=entries.filter(x=>x.tech===tech),n=a.filter(x=>x.m.availability==='N'),n1=a.filter(x=>x.m.availability==='N−1');const sec=avg(a.map(x=>num(x,'total_sec'))),secN=avg(n.map(x=>num(x,'total_sec'))),secN1=avg(n1.map(x=>num(x,'total_sec'))),pmax=Math.max(...valid(a.map(x=>num(x,'membrane_pressure_1'))),NaN),tdsmax=Math.max(...valid(a.map(x=>scenarioProductTds(x.r))),NaN),bad=a.filter(x=>scenarioResultStatus(x.r)[0]!=='ok').length;return `<tr><td><span class="solution-icon-card"><img src="/static/icons_v18/${scenarioTechIcon(tech)}.svg" alt=""><strong>${escapeHtml(scenarioTechLabel(tech))}</strong></span></td><td>${fmt(secN,3)}</td><td>${fmt(secN1,3)}</td><td><strong>${fmt(sec,3)}</strong></td><td>${fmt(pmax,2)}</td><td>${fmt(tdsmax,0)}</td><td>${bad?a.length-bad+'/'+a.length+' OK':'All OK'}</td></tr>`;}).join('');
  const worstSec=maxBy(entries,x=>Number(x.r.total_sec)||-Infinity),worstP=maxBy(entries,x=>Number(x.r.membrane_pressure_1)||-Infinity),worstTds=maxBy(entries,x=>scenarioProductTds(x.r)||-Infinity),worstFlux=maxBy(entries,x=>scenarioFlux(x.r)||-Infinity);
  const crit=(title,x,val,unit)=>x?`<div class="check-card"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(scenarioTechLabel(x.tech))} · ${escapeHtml(x.m.availability)} · ${escapeHtml(x.m.condition)}</span><b>${fmt(val(x),2)} ${escapeHtml(unit)}</b></div>`:'';
  const equipmentRows=techs.map(tech=>{const a=entries.filter(x=>x.tech===tech);const h=maxBy(a,x=>Number(x.r.hpp_kw??x.r.electric_kw)||0),b=maxBy(a,x=>Number(x.r.booster_kw??x.r.circ_kw)||0),th=maxBy(a,x=>Number(x.r.px_throttle_dissipation_kw)||0);return `<tr><td>${escapeHtml(scenarioTechLabel(tech))}</td><td>${h?fmt(Number(h.r.hpp_kw??h.r.electric_kw)||0,1):'—'}</td><td>${b?fmt(Number(b.r.booster_kw??b.r.circ_kw)||0,1):'—'}</td><td>${th?fmt(Number(th.r.px_throttle_dissipation_kw)||0,1):'—'}</td><td>${h?escapeHtml(h.m.availability+' · '+h.m.condition):'—'}</td></tr>`;}).join('');
  const avgSecs=techs.map(t=>({t,v:avg(entries.filter(x=>x.tech===t).map(x=>Number(x.r.total_sec)))})).filter(x=>Number.isFinite(x.v)).sort((a,b)=>a.v-b.v),best=avgSecs[0];
  const pxRows=['px','interstage_px'].filter(t=>techs.includes(t)).map(t=>{const a=entries.filter(x=>x.tech===t&&Number.isFinite(Number(x.r.px_installed_qty_per_train)));if(!a.length)return '';const g=a.find(x=>Number(x.r.px_bank_governing_case_id)===x.id)||maxBy(a,x=>Number(x.r.px_operating_qty||x.r.px_qty)||0);const inst=Math.max(...a.map(x=>Number(x.r.px_installed_qty_per_train)||0));const minOp=Math.min(...a.map(x=>Number(x.r.px_operating_qty||x.r.px_qty)||Infinity)),maxOp=Math.max(...a.map(x=>Number(x.r.px_operating_qty||x.r.px_qty)||0));return `<tr><td>${escapeHtml(scenarioTechLabel(t))}</td><td>${fmt(inst,0)}</td><td>${fmt(minOp,0)}–${fmt(maxOp,0)}</td><td>${escapeHtml(g?.r?.px_bank_governing_case||'—')}</td><td>${g?.r?.px_bank_sized_for_nminus1?'Yes':'No'}</td></tr>`;}).join('');
  const pxBankSection=pxRows?`<section class="report-section"><h3>ISOBARIC CHAMBER BANK · N / N−1 SIZING</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Solution</th><th>Installed units / train</th><th>Operating units across envelope</th><th>Governing condition</th><th>N−1 governs?</th></tr>${pxRows}</table></div><p class="micro-note">Installed IC/PX quantity is fixed to the maximum unit count required by the eight independently solved N/N−1 envelope cases. Lower-flow conditions may operate fewer units with the remaining units standby/bypassed, subject to the selected unit-flow envelope.</p></section>`:'';
  return `<section class="report-section"><div class="chart-title-row"><h3>N vs N−1 · TECHNOLOGY COMPARISON</h3><span>${entries.length} solved operating conditions</span></div><div class="table-wrap"><table class="fedco-table"><tr><th>Solution</th><th>Avg SEC · N</th><th>Avg SEC · N−1</th><th>All-condition avg SEC</th><th>Max feed pressure</th><th>Max product TDS</th><th>Envelope status</th></tr>${compareRows}</table></div>${best?`<p class="micro-note"><strong>Lowest all-condition average SEC:</strong> ${escapeHtml(scenarioTechLabel(best.t))} at ${fmt(best.v,3)} kWh/m³. Selection still requires review of design limits, CAPEX and the critical operating condition.</p>`:''}</section>
  <section class="report-section"><h3>CRITICAL / WORST-CASE CONDITIONS</h3><div class="check-grid">${crit('Highest total SEC',worstSec,x=>Number(x.r.total_sec),'kWh/m³')}${crit('Highest Stage-1 pressure',worstP,x=>Number(x.r.membrane_pressure_1),worstP?.r?.pressure_unit||'')}${crit('Highest product TDS',worstTds,x=>scenarioProductTds(x.r),'mg/L')}${crit('Highest average flux',worstFlux,x=>fluxValue(scenarioFlux(x.r)),fluxUnit())}</div></section>
  <section class="report-section"><h3>EQUIPMENT DUTIES · ENVELOPE MAXIMA</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Solution</th><th>Max HPP / main power<br><span>kW</span></th><th>Max booster duty<br><span>kW</span></th><th>Max throttle dissipation<br><span>kW</span></th><th>Governing HPP condition</th></tr>${equipmentRows}</table></div><p class="micro-note">Equipment maxima are extracted from the independently solved N/N−1 hydraulic-envelope cases. Isobaric throttling is reported as dissipated inherited hydraulic energy, never as additional ERD efficiency.</p></section>${pxBankSection}`;
}

function _baseRecoveryForScenario(source,tech,state){
  const rr=Number(source?.caseResults?.[tech]?.recovery);if(Number.isFinite(rr)&&rr>0&&rr<.95)return rr;
  const tr=Number(state?.target_recovery);if(Number.isFinite(tr)&&tr>0)return tr>1?tr/100:tr;
  const q=Number(state?.target_product_flow),f=Number(state?.feed_flow);if(q>0&&f>q)return q/f;
  return .45;
}
function _scenarioStateForTech(source,tech,targetProductM3h,availableTrains){
  const st=deepClone(source.modeStates?.[tech]||{});const rec=Math.max(.05,Math.min(.92,_baseRecoveryForScenario(source,tech,st)));
  const flowInCurrent=convert(targetProductM3h/rec,'flow','m3/h',currentUnits.flow);const productInCurrent=convert(targetProductM3h,'flow','m3/h',currentUnits.flow);
  st.feed_flow=flowInCurrent;st.solve_basis='product';st.target_product_flow=productInCurrent;st.target_recovery=rec*100;
  if(tech==='multistage'){st.operating_trains=availableTrains;st.standby_trains=0;st.required_capacity_m3d=scenarioMatrixState.required_capacity_m3d;}
  return st;
}
function applyScenarioPxBankSizing(techs){
  ['px','interstage_px'].filter(t=>techs.includes(t)).forEach(tech=>{
    const rows=[];for(let i=1;i<=8;i++){const r=caseStore[i]?.caseResults?.[tech];if(!r)continue;const qty=Math.max(1,Math.round(Number(r.px_qty||1))),unit=Number(r.px_unit_flow),total=Number.isFinite(unit)?qty*unit:Number(r.px_lp_flow||r.circ_flow||0);rows.push({i,r,qty,total,meta:caseStore[i].scenarioMeta||{}});}
    if(!rows.length)return;const installed=Math.max(...rows.map(x=>x.qty));const governing=rows.slice().sort((a,b)=>b.qty-a.qty||b.total-a.total)[0];
    rows.forEach(x=>{x.r.px_operating_qty=x.qty;x.r.px_installed_qty_per_train=installed;x.r.px_standby_or_bypassed_qty=Math.max(0,installed-x.qty);x.r.px_bank_governing_case=`${governing.meta.availability||''} · ${governing.meta.condition||''}`;x.r.px_bank_governing_case_id=governing.i;x.r.px_bank_sized_for_nminus1=String(governing.meta.availability||'').includes('N−1');});
  });
}

async function calculateScenarioMatrix(){
  scenarioRunCancelled=false;const st=captureScenarioMatrixState();
  if(st.normal_trains<2)throw new Error('Scenario Matrix requires N of at least 2 trains.');
  if(!(st.required_capacity_m3d>0))throw new Error('Enter the required plant product capacity before running the Scenario Matrix.');
  persistActiveCase();const source=deepClone(caseStore[activeCase]);const techs=configuredProcessModes(source.modeStates||{});
  if(!techs.length)throw new Error('No populated solution is ready. Configure and calculate or fully populate at least one RO/ERD solution first.');
  const occupied=Object.keys(caseStore).map(Number).filter(id=>id<=8&&id!==activeCase&&(Object.keys(caseStore[id]?.caseResults||{}).length||Object.keys(caseStore[id]?.modeStates||{}).length));
  if(occupied.length&&!window.confirm(`Scenario Matrix uses Cases 1–8 and will replace their current setup/results. Continue?`))return;
  const p=source.waterProfile||{};const cold=Number(p.temperature_min_c??p.temperature_c),warm=Number(p.temperature_max_c??p.temperature_c),newFF=Number(p.new_membrane_fouling_factor??0.95),oldFF=Number(p.old_membrane_fouling_factor??0.70);
  if(![cold,warm,newFF,oldFF].every(Number.isFinite)||cold>warm)throw new Error('Hydraulic Envelope temperatures or membrane-condition factors are invalid.');
  const defs=[['New / Cold',cold,newFF],['New / Warm',warm,newFF],['Aged / Cold',cold,oldFF],['Aged / Warm',warm,oldFF]];
  const n=st.normal_trains,n1=n-1;const states=[['N',n],['N−1',n1]];let cid=1;
  for(const [availability,trains] of states){for(const [condition,temp,ff] of defs){
    const wp=deepClone(source.waterProfile);wp.temperature_c=temp;wp.fouling_factor=ff;wp.envelope_label=`${availability} · ${condition}`;
    const targetM3h=st.maintain_capacity_nminus1?st.required_capacity_m3d/trains/24:st.required_capacity_m3d/n/24;
    const modes={};techs.forEach(tech=>modes[tech]=_scenarioStateForTech(source,tech,targetM3h,trains));
    caseStore[cid]={waterProfile:wp,modeStates:modes,caseResults:{},economicState:deepClone(source.economicState||economicDefaults),lastEconomicResult:null,chemistryResult:null,scenarioMeta:{availability,available_trains:trains,condition,target_product_m3d:targetM3h*24}};cid++;
  }}
  renderCaseBar();setCalculating(true);clearCalcError();const errors=[];
  const stop=$('#stopRunBtn');if(stop)stop.disabled=false;
  try{
    const independent=techs.filter(t=>t==='px'||t==='interstage_px'||t==='multistage'||(t==='interstage'&&Boolean(source.modeStates?.interstage?.generalized_interstage_turbo))||(t==='biturbo'&&Boolean(source.modeStates?.biturbo?.generalized_biturbo)));
    if(independent.length&&!scenarioRunCancelled){const tasks=[];for(const tech of independent)for(let i=1;i<=8;i++)tasks.push({id:`${i}:${tech}`,mode:tech,data:processPayload(caseStore[i],tech,false)});const j=await requestJson('/api/calculate-batch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tasks})},'Scenario Matrix batch calculation failed');(j.results||[]).forEach(item=>{const [idRaw,tech]=String(item.id||'').split(':'),id=Number(idRaw);if(item.ok&&caseStore[id])caseStore[id].caseResults[tech]=item.result;else errors.push(`Case ${id} ${tech}: ${item.error||'failed'}`)});lastComputeRun={backend:j.backend,workers:j.workers,fallback:j.fallback,jobs_total:j.jobs_total,jobs_completed:j.jobs_completed,elapsed_seconds:j.elapsed_seconds};}
    for(const tech of techs.filter(t=>['single','interstage','biturbo'].includes(t)&&!(t==='interstage'&&Boolean(source.modeStates?.interstage?.generalized_interstage_turbo))&&!(t==='biturbo'&&Boolean(source.modeStates?.biturbo?.generalized_biturbo)))){if(scenarioRunCancelled)break;const lock=turboDesignLocks[tech]||{};const cases=[];for(let i=1;i<=8;i++)cases.push({case_id:i,data:processPayload(caseStore[i],tech,false)});const body={mode:tech,cases};if(tech==='biturbo'){body.inter_design_case=lock.inter_case||'auto';body.feed_design_case=lock.feed_case||'auto'}else body.design_case=lock.case||'auto';const j=await requestJson('/api/turbo/design-cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},`${scenarioTechLabel(tech)} matrix calculation failed`);turboDesignLocks[tech]={...lock,stale:false,design:deepClone(j.design),locked_fields:deepClone(j.locked_fields||{})};(j.results||[]).forEach(item=>{const id=Number(item.id);if(item.ok&&caseStore[id])caseStore[id].caseResults[tech]=item.result;else errors.push(`Case ${id} ${tech}: ${item.error||'failed'}`)});lastComputeRun={backend:j.backend,workers:j.workers,fallback:j.fallback,elapsed_seconds:j.elapsed_seconds};}
    applyScenarioPxBankSizing(techs);
    scenarioMatrixLastRun={at:new Date().toISOString(),solutions:techs.slice(),normal_trains:n,required_capacity_m3d:st.required_capacity_m3d,cases:8,combinations:techs.length*8};updateComputeStatus();renderComputePanel();
  }finally{setCalculating(false);if(stop)stop.disabled=true;loadCaseGlobals(1);mode='multistage';updateWaterWorkspaceTabs();renderFields(modeStates.multistage||defaults.multistage);$('#warnings').innerHTML='';$('#results').innerHTML=scenarioMatrixResults()+scenarioStudyInsights();}
  if(scenarioRunCancelled)showCalcError(new Error('Scenario Matrix stopped after the current calculation batch. Results already completed are retained.'),'scenario matrix');
  else if(errors.length)showCalcError(new Error(`Scenario Matrix completed with ${errors.length} skipped/failed combination(s): ${errors.slice(0,4).join(' · ')}${errors.length>4?' …':''}`),'scenario matrix');
}

function sourceWaterTypeOptions(selected){
  const rows=[['surface','Surface water'],['well','Well water'],['seawater_well','Seawater well'],['municipal_secondary','Municipal secondary effluent'],['seawater','Seawater'],['custom','Custom / manually entered water quality']];
  const blank=`<option value="" ${!selected?'selected':''} disabled>Select source-water type…</option>`;
  return blank+rows.map(([v,l])=>`<option value="${v}" ${String(selected||'')===v?'selected':''}>${l}</option>`).join('');
}

function plantSolutionSelectorHtml(values){
  const withErd=String(values?.energy_recovery_mode||'with')!=='none';
  const checked=k=>values?.[k]===true||String(values?.[k]).toLowerCase()==='true';
  const btScreen=biturboTdsScreen();
  const card=(name,label,icon,desc,planned=false,disabled=false,disabledReason='')=>`<label class="solution-choice-card ${checked(name)&&!disabled?'selected':''} ${planned?'planned':''} ${disabled?'blocked':''}" ${disabledReason?`title="${escapeHtml(disabledReason)}"`:''}><input type="checkbox" name="${name}" ${checked(name)&&!disabled?'checked':''} ${(planned||disabled)?'disabled':''}><span class="solution-choice-check">✓</span><img src="/static/icons_v18/${icon}.svg" alt=""><span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(disabled?disabledReason:desc)}</small></span>${planned?'<b>PLANNED</b>':disabled?'<b>BLOCKED</b>':''}</label>`;
  return `<section class="input-section plant-solution-picker"><div class="section-inline-title"><div><h3>ENERGY RECOVERY SOLUTIONS</h3><p class="micro-note">The Base Plant Design is the parent. Every checked technology is generated as an independent sibling solution from the same water, capacity, membrane and hydraulic basis; no ERD solution inherits another ERD's assumptions.</p></div><button type="button" class="envelope-btn" id="populateSolutionsBtn">Populate selected solutions</button></div>
    <div class="erd-mode-switch"><label class="erd-mode-card ${!withErd?'selected':''}"><input type="radio" name="energy_recovery_mode" value="none" ${!withErd?'checked':''}><img src="/static/icons_v18/conventional.svg" alt=""><span><strong>Without ERD</strong><small>Conventional pump-only baseline.</small></span></label><label class="erd-mode-card ${withErd?'selected':''}"><input type="radio" name="energy_recovery_mode" value="with" ${withErd?'checked':''}><img src="/static/icons_v18/solutions.svg" alt=""><span><strong>Evaluate ERD solutions</strong><small>Create parallel technology alternatives from this base plant.</small></span></label></div>
    <div class="solution-choice-grid ${withErd?'':'disabled'}" id="erdSolutionCards">
      ${card('solution_conventional','Conventional baseline','conventional','Keep a no-ERD reference solution for energy comparison.')}
      ${card('solution_px','Single Stage Isobaric Chamber','isobaric','Direct single-stage SWRO/BWRO pressure-exchange alternative.')}
      ${card('solution_interstage_px','Interstage Isobaric Chamber','interstage_isobaric','Dedicated 2–4 stage isobaric solution; final-stage reject supplies the pressure exchanger.')}
      ${card('solution_single','Turbocharger','turbo','Feed-side turbo for a single-stage base; multistage turbo placements are configured between stages.')}
      ${card('solution_interstage','Interstage Turbo','interstage','Dedicated 2–4 stage interstage-turbo solution inherited from the Base Plant; Total RO Design selects a hydraulically eligible turbo location as the starting configuration.')}
      ${card('solution_biturbo','BiTurbo™','biturbo','Supports legacy feed + interstage BiTurbo and multistage BiTurbo placements inherited from the Base Plant.',false,!btScreen.eligible,btScreen.reason||`Requires at least two hydraulically eligible turbo positions with local TDS ≥ 30,000 mg/L and Qtr/Qpf > 0.20.`)}
      ${card('solution_pelton','Pelton Turbine','pelton','Common-shaft Pelton recovery using final-stage brine pressure, shaft-power balance, torque and runner/nozzle screening.')}
      ${card('solution_dweer','DWEER','dweer','Positive-displacement work exchanger using final-stage brine, mixing/overflush and HP/LP loss screening from the attached calculator.')}
    </div>
    <div id="solutionPopulateStatus" class="solution-populate-status">${withErd?'Select the alternatives to evaluate, then calculate the Base Plant or click Populate selected solutions.':'Without ERD selected: the Plant Designer acts as the conventional baseline.'}</div>
  </section>`;
}
function _copyPlantCommon(base){
  const keys=['solve_basis','target_product_flow','target_recovery','membrane_coupling','permeate_pressure','feed_flow','membrane_pressure_1','suction_pressure','pretreatment_discharge_pressure','pretreatment_recovery','pretreatment_pump_eff','pretreatment_motor_eff','pretreatment_vfd_eff','pretreatment_no_vfd','pump_eff','motor_eff','vfd_eff','pump_no_vfd','curve'];
  const out={};keys.forEach(k=>{if(base[k]!==undefined)out[k]=base[k]});return out;
}
function _copyStages(base,n,out){
  out.stage_count=n;out.interstage_control_objective=base.interstage_control_objective??'manual';out.interstage_balance_basis=base.interstage_balance_basis??'average';for(let i=1;i<=n;i++){['membrane','vessels','elements_per_vessel','membrane_design_mode','membrane_recipe'].forEach(k=>{const key=`${k}_${i}`;if(base[key]!==undefined)out[key]=base[key]});if(i>1){out[`interstage_equipment_${i}`]=base[`interstage_equipment_${i}`]??'pump';out[`interstage_boost_${i}`]=base[`interstage_boost_${i}`]??0;out[`interstage_target_recovery_${i}`]=base[`interstage_target_recovery_${i}`]??'';out[`interstage_maximize_turbo_energy_${i}`]=base[`interstage_maximize_turbo_energy_${i}`]!==false;}}return out;
}
function populateSelectedSolutions(base,showStatus=true){
  base={...(base||capture())};const n=Math.max(1,Math.min(4,Number(base.stage_count||1)));const source=base.source_water_type||waterProfile.source_water_type||'custom';waterProfile.source_water_type=source;
  const withErd=String(base.energy_recovery_mode||'with')!=='none';
  if(!withErd){base.solution_conventional=true;base.solution_px=false;base.solution_interstage_px=false;base.solution_single=false;base.solution_interstage=false;base.solution_biturbo=false;base.solution_dweer=false;base.solution_pelton=false;}
  // Mark previously generated solution states inactive unless selected again. Their manual values are retained.
  [['px','solution_px'],['interstage_px','solution_interstage_px'],['single','solution_single'],['interstage','solution_interstage'],['biturbo','solution_biturbo'],['dweer','solution_dweer'],['pelton','solution_pelton']].forEach(([tech,key])=>{if(modeStates[tech])modeStates[tech].solution_enabled=withErd&&Boolean(base[key]);});
  const common=_copyPlantCommon(base);const notes=[];const baseSig=base._last_calculated_signature||basePlantSignature(base);const btScreen=biturboTdsScreen(caseResults.multistage);
  if(withErd&&base.solution_px){
    if(n===1){
      const px={...defaults.px,...common,solution_enabled:true,generated_from_base_plant:true,source_water_type:source,plant_solution:false};
      _copyStages(base,1,px);px.operating_trains=base.operating_trains;px.standby_trains=base.standby_trains;px.required_capacity_m3d=base.required_capacity_m3d;px.reject_flow_1='';px.px_lp_outlet_pressure=modeStates.px?.px_lp_outlet_pressure??1.5;
      px._base_plant_signature=baseSig;modeStates.px={...px,...(modeStates.px?.generated_from_base_plant===false?modeStates.px:{})};notes.push('Single Stage Isobaric Chamber');
    } else {
      if(modeStates.px)modeStates.px.solution_enabled=false;
      notes.push('Single Stage Isobaric skipped · use the dedicated Interstage Isobaric Chamber for 2–4 stages');
    }
  }
  if(withErd&&base.solution_interstage_px){
    if(n>=2){const ix={...defaults.interstage_px,...common,solution_enabled:true,generated_from_base_plant:true,source_water_type:source,plant_solution:true};_copyStages(base,n,ix);ix.operating_trains=base.operating_trains;ix.standby_trains=base.standby_trains;ix.required_capacity_m3d=base.required_capacity_m3d;['bwpx_pressure_transfer_eff','bwpx_flow_balance_eff','bwpx_mixing_fraction','bwpx_brine_backpressure','bwpx_model'].forEach(k=>ix[k]=modeStates.interstage_px?.[k]??defaults.interstage_px[k]);ix._base_plant_signature=baseSig;modeStates.interstage_px=ix;notes.push('Interstage Isobaric Chamber');}
    else notes.push('Interstage Isobaric Chamber requires at least two stages');
  }
  if(withErd&&base.solution_single){
    if(n===1){const st={...defaults.single,...common,solution_enabled:true,generated_from_base_plant:true,membrane_1:base.membrane_1,vessels_1:base.vessels_1,elements_per_vessel_1:base.elements_per_vessel_1,membrane_design_mode_1:base.membrane_design_mode_1,membrane_recipe_1:base.membrane_recipe_1,pex:modeStates.single?.pex??1.5};st.stage_count=1;st._base_plant_signature=baseSig;modeStates.single=st;notes.push('Turbocharger');}
    else notes.push('Turbocharger: multistage feed/interstage duties stay in Plant Designer; dedicated single-stage solution not generated');
  }
  if(withErd&&base.solution_interstage){
    if(n===2){const st={...defaults.interstage,...common,solution_enabled:true,generated_from_base_plant:true,stage_count:2,membrane_1:base.membrane_1,vessels_1:base.vessels_1,elements_per_vessel_1:base.elements_per_vessel_1,membrane_2:base.membrane_2,vessels_2:base.vessels_2,elements_per_vessel_2:base.elements_per_vessel_2,membrane_design_mode_1:base.membrane_design_mode_1,membrane_recipe_1:base.membrane_recipe_1,membrane_design_mode_2:base.membrane_design_mode_2,membrane_recipe_2:base.membrane_recipe_2,pex:modeStates.interstage?.pex??1.5,_base_plant_signature:baseSig};modeStates.interstage=st;notes.push('Interstage Turbo');}
    else if(n>2){
      const st={...defaults.multistage,...common,solution_enabled:true,generated_from_base_plant:true,generalized_interstage_turbo:true,stage_count:n,source_water_type:source,_base_plant_signature:baseSig};_copyStages(base,n,st);
      const candidates=[];for(let i=2;i<=n;i++){const scr=turboPlacementScreen(i,false,caseResults.multistage);if(scr.allow)candidates.push({position:i,ratio:Number(scr.ratio)||0});}
      if(!candidates.length){st.solution_enabled=false;modeStates.interstage=st;notes.push('Interstage Turbo blocked · no interstage location has Qtr/Qpf > 0.20');}
      else{
        const existing=candidates.filter(x=>['turbo','turbo_pump'].includes(String(base[`interstage_equipment_${x.position}`]||'')));
        const pick=(existing.length?existing:candidates).slice().sort((a,b)=>Math.abs(a.ratio-.675)-Math.abs(b.ratio-.675))[0];
        const req=Number(caseResults.multistage?.[`stage${pick.position}_interstage_required_hydraulic_kw`]||0),avail=Number(caseResults.multistage?.multistage_turbo_available_hydraulic_kw||0);
        st[`interstage_equipment_${pick.position}`]=(req>0&&avail+1e-9>=req)?'turbo':'turbo_pump';st.interstage_turbo_position=pick.position;st.interstage_turbo_reject_ratio=pick.ratio;
        modeStates.interstage=st;notes.push(`Interstage Turbo · ${n}-stage topology inherited · Stage ${pick.position-1}→${pick.position} · Qtr/Qpf ${pick.ratio.toFixed(3)}`);
      }
    }
    else notes.push('Interstage Turbo requires at least two stages');
  }
  if(withErd&&base.solution_biturbo){
    if(!btScreen.eligible){if(modeStates.biturbo)modeStates.biturbo.solution_enabled=false;notes.push(`BiTurbo blocked · ${btScreen.reason||'current hydraulic/TDS screen is not eligible'}`);}
    else if(n<=2){let v1=Math.max(1,Math.round(Number(base.vessels_1||1))),v2=Math.max(1,Number(base.vessels_2||0));if(n===1){const total=v1;v1=Math.max(1,Math.round(total*2/3));v2=Math.max(1,total-v1);}const bt={...defaults.biturbo,...common,solution_enabled:true,generated_from_base_plant:true,stage_count:n,membrane_1:base.membrane_1,vessels_1:v1,elements_per_vessel_1:base.elements_per_vessel_1,membrane_2:base.membrane_2||base.membrane_1,vessels_2:v2,elements_per_vessel_2:base.elements_per_vessel_2||base.elements_per_vessel_1,membrane_design_mode_1:base.membrane_design_mode_1,membrane_recipe_1:base.membrane_recipe_1,membrane_design_mode_2:base.membrane_design_mode_2||base.membrane_design_mode_1,membrane_recipe_2:base.membrane_recipe_2||base.membrane_recipe_1,target_interstage_boost:modeStates.biturbo?.target_interstage_boost??15,pex:modeStates.biturbo?.pex??1.5,_base_plant_signature:baseSig};bt.biturbo_energy_screen_tds_mg_l=btScreen.min_tds;modeStates.biturbo=bt;notes.push(`BiTurbo${n===1?' · initial 2/3 + 1/3 membrane split':''}`);}
    else {
      const bt={...defaults.multistage,...common,solution_enabled:true,generated_from_base_plant:true,generalized_biturbo:true,stage_count:n,source_water_type:source,_base_plant_signature:baseSig};_copyStages(base,n,bt);
      const eligible=(btScreen.eligible_candidates||[]).map(x=>Number(x.position)).filter(Number.isFinite).sort((a,b)=>b-a);
      const already=[];for(let i=2;i<=n;i++)if(['turbo','turbo_pump'].includes(String(bt[`interstage_equipment_${i}`]||''))&&eligible.includes(i))already.push(i);
      const chosen=already.slice();for(const i of eligible)if(chosen.length<2&&!chosen.includes(i))chosen.push(i);
      chosen.slice(0,2).forEach((i,idx)=>{bt[`interstage_equipment_${i}`]=idx===0?'turbo':'turbo_pump';});
      bt.biturbo_energy_screen_tds_mg_l=Math.min(...chosen.slice(0,2).map(i=>Number(caseResults.multistage?.[`stage${i}_feed_tds_ppm`]||30000)));
      modeStates.biturbo=bt;notes.push(`BiTurbo · ${n}-stage topology inherited · turbo positions ${chosen.slice(0,2).sort((a,b)=>a-b).map(i=>`Stage ${i-1}→${i}`).join(' + ')}`);
    }
  }
  if(withErd&&base.solution_dweer){const dw={...defaults.dweer,...common,solution_enabled:true,generated_from_base_plant:true,source_water_type:source,_base_plant_signature:baseSig,_base_plant_result:deepClone(caseResults.multistage)};_copyStages(base,n,dw);['operating_trains','standby_trains','required_capacity_m3d'].forEach(k=>dw[k]=base[k]);Object.keys(dweerDevice).forEach(k=>dw[k]=modeStates.dweer?.[k]??defaults.dweer[k]);modeStates.dweer=dw;notes.push('DWEER');}
  if(withErd&&base.solution_pelton){const pe={...defaults.pelton,...common,solution_enabled:true,generated_from_base_plant:true,source_water_type:source,_base_plant_signature:baseSig,_base_plant_result:deepClone(caseResults.multistage)};_copyStages(base,n,pe);['operating_trains','standby_trains','required_capacity_m3d'].forEach(k=>pe[k]=base[k]);Object.keys(peltonDevice).forEach(k=>pe[k]=modeStates.pelton?.[k]??defaults.pelton[k]);modeStates.pelton=pe;notes.push('Pelton Turbine');}
  const inheritedSeed=deepClone(caseBaseSeed());ERD_MODES.forEach(k=>{if(modeStates[k]?.generated_from_base_plant){modeStates[k]._base_design_seed=inheritedSeed;modeStates[k]._warm_start_seed=inheritedSeed;modeStates[k]._inherited_from=`Plant Design · Case ${activeCase}`;}});base.solution_conventional=!withErd?true:Boolean(base.solution_conventional);base._erd_populated_signature=baseSig;modeStates.multistage={...base};syncActiveCaseStore();updateSolutionNavState();updateErdNavAccess();
  const host=$('#solutionPopulateStatus');if(showStatus&&host)host.textContent=notes.length?`Populated from Base Plant: ${notes.join(' · ')}`:'No ERD alternatives selected; conventional Base Plant retained.';
  return notes;
}
function bindPlantSolutionPicker(){
  const syncCards=()=>{const withErd=document.querySelector('[name="energy_recovery_mode"]:checked')?.value!=='none';const grid=$('#erdSolutionCards');if(grid)grid.classList.toggle('disabled',!withErd);document.querySelectorAll('.solution-choice-card input').forEach(x=>{if(!x.disabled)x.disabled=!withErd;});document.querySelectorAll('.erd-mode-card').forEach(x=>x.classList.toggle('selected',x.querySelector('input')?.checked));};
  document.querySelectorAll('[name="energy_recovery_mode"]').forEach(x=>x.addEventListener('change',syncCards));document.querySelectorAll('.solution-choice-card input').forEach(x=>x.addEventListener('change',()=>x.closest('.solution-choice-card')?.classList.toggle('selected',x.checked)));syncCards();
  $('#populateSolutionsBtn')?.addEventListener('click',()=>{const vals=capture();modeStates.multistage={...vals,_last_calculated_signature:modeStates.multistage?._last_calculated_signature};if(!basePlantIsCurrent()){showCalcError(new Error('Calculate the current Plant Design Basis before populating ERD solutions.'),'input');return;}populateSelectedSolutions({...vals,_last_calculated_signature:modeStates.multistage._last_calculated_signature},true);renderCaseBar();});
}

const WATER_CATION_FIELDS=['ion_ammonium','ion_sodium','ion_potassium','ion_magnesium','ion_calcium','ion_strontium','ion_barium','ion_iron_ii','ion_iron_iii','ion_manganese_ii'];
const WATER_ANION_FIELDS=['ion_fluoride','ion_chloride','ion_sulfate','ion_nitrate','ion_bicarbonate','ion_phosphate','ion_bromide'];
const WATER_NEUTRAL_FIELDS=['ion_boron','ion_silica'];
function waterIonEditorRow(k){
  const f=chemistry[k],key=k.slice(4),label=f.label,suffix=f.suffix||'mg/L';
  const tip=k==='ion_bicarbonate'?infoTip('Total alkalinity is the master carbonate-system input together with pH. Total RO Design derives free HCO₃⁻, CO₃²⁻ and dissolved CO₂ from equilibrium. The charge table below reports the resulting equilibrium ionic charge contribution.') : '';
  const raw=waterProfile[k];
  const value=(raw===null||raw===undefined||raw==='')?'':Number(raw).toFixed(2);
  return `<div class="water-ion-row" data-ion-row="${key}"><label>${escapeHtml(label)}${tip}</label><div class="wrap"><input name="${k}" type="number" step="any" value="${value}"><span class="suffix">${escapeHtml(suffix)}</span></div><span class="water-ion-meq" data-water-meq="${key}">—</span></div>`;
}
function waterIonColumn(title,fields,totalId,kind){
  const calculatedCarbonate=kind==='anion'?`<div class="water-ion-row calculated-ion-row" data-ion-row="carbonate"><label>Calculated carbonate CO₃²⁻ ${infoTip('Read-only equilibrium carbonate derived from pH + total alkalinity. It contributes to the displayed anion charge balance but is never an independent input.')}</label><div class="wrap"><input id="calculatedCarbonate" type="text" value="Calculating…" readonly><span class="suffix">mg/L</span></div><span class="water-ion-meq" data-water-meq="carbonate">—</span></div>`:'';
  return `<div class="water-ion-column ${kind}"><div class="water-ion-column-title"><h4>${title}</h4><span>Concentration</span><span>meq/L</span></div>${fields.map(waterIonEditorRow).join('')}${calculatedCarbonate}<div class="water-ion-total"><span>Total ${kind==='cation'?'cations':'anions'}</span><strong id="${totalId}">Calculating…</strong><span>meq/L</span></div></div>`;
}
function waterBalanceSelectHtml(){return `<select id="waterBalanceIon"><option value="">Choose balancing ion…</option><optgroup label="Add anion"><option value="chloride">Chloride · Cl⁻</option><option value="alkalinity">Bicarbonate / alkalinity · HCO₃⁻ equivalent</option><option value="sulfate">Sulfate · SO₄²⁻</option></optgroup><optgroup label="Add cation"><option value="magnesium">Magnesium · Mg²⁺</option><option value="sodium">Sodium · Na⁺</option><option value="calcium">Calcium · Ca²⁺</option></optgroup></select>`}

function renderWaterTab(){
  const root=$('#fields'); const p=waterProfile;
  const opts=`<option value="" ${!p.water_region?'selected':''} disabled>Select region / water preset…</option>`+
    seawaterPresets.map(x=>`<option value="${x.id}" ${p.water_region===x.id?'selected':''}>${escapeHtml(x.name)}</option>`).join('');
  const caseOpts=Object.keys(caseStore).map(Number).sort((a,b)=>a-b).map(id=>`<option value="${id}" ${id===activeCase?'selected':''}>Case ${id}</option>`).join('');
  const neutralFields=WATER_NEUTRAL_FIELDS.map(k=>{const f=chemistry[k],raw=p[k],value=(raw===null||raw===undefined||raw==='')?'':Number(raw).toFixed(2);return `<div class="field"><label>${escapeHtml(f.label)}</label><div class="wrap"><input name="${k}" type="number" step="any" value="${value}"><span class="suffix">${escapeHtml(f.suffix||'mg/L')}</span></div></div>`}).join('');
  const labCarbonate=`<div class="field"><label>Lab-reported carbonate · optional QC ${infoTip('Optional laboratory CO₃²⁻ value. It is compared against the equilibrium carbonate calculated from pH + total alkalinity, but it is not counted as a second carbonate input and does not drive the charge-balance adjustment.')}</label><div class="wrap"><input name="ion_carbonate" type="number" step="any" value="${Number(p.ion_carbonate??0).toFixed(2)}"><span class="suffix">mg/L</span></div><div id="carbonateQcNote" class="micro-note"></div></div>`;
  const notice=caseSetupNotice?`<div class="case-setup-banner"><strong>Case ${activeCase} water-quality setup</strong><span>${escapeHtml(caseSetupNotice)}</span></div>`:'';
  root.innerHTML=`${notice}<section class="input-section water-profile"><h3>CASE & SOURCE WATER</h3><div class="grid water-basic-grid">
    <div class="field compact-field"><label>Case number</label><div class="wrap"><select name="case_selector">${caseOpts}</select></div></div>
    <div class="field compact-field"><label>Source-water type ${infoTip('Source-water type provides process context and design defaults. The analytical ion composition and TDS remain the governing calculation inputs.')}</label><div class="wrap"><select name="source_water_type">${sourceWaterTypeOptions(p.source_water_type)}</select></div></div>
    <div class="field source-water-field"><label>Region / water preset ${infoTip('Select a regional water preset as a starting composition. All analytical values remain editable and should be verified against project-specific laboratory data.')}</label><div class="wrap"><select name="water_region">${opts}</select></div></div>
    <div class="field compact-field"><label>Reference temperature ${infoTip('Reference/design-case water temperature. The cold/warm operating envelope is configured only in the Hydraulic Envelope workspace.')}</label><div class="wrap"><input name="temperature_c" type="number" step="any" value="${p.temperature_c}"><span class="suffix">°C</span></div></div>
    <div class="field compact-field"><label>Salinity</label><div class="wrap"><input name="salinity_psu" type="number" step="any" value="${p.salinity_psu}"><span class="suffix">PSU</span></div></div>
    <div class="field compact-field"><label>Target / reported TDS ${infoTip('Reported analytical TDS. Changing this value proportionally rescales the current analytical ion composition before subsequent speciation calculations.')}</label><div class="wrap"><input name="analysis_tds" type="number" step="1000" value="${p.analysis_tds}"><span class="suffix">mg/L</span></div></div>
    <div class="field compact-field"><label>pH ${infoTip('Analytical feed pH. Acid-conditioning target pH is a separate calculation setting below.')}</label><div class="wrap"><input name="feed_ph" type="number" step="any" value="${p.feed_ph}"></div></div>
  </div><p class="micro-note">The Water Quality workspace defines the reference analytical water only. Cold/warm and new/aged cases are configured in the separate Hydraulic Envelope tab after Plant Design.</p><p class="micro-note source-disclaimer"><strong>Geographic seawater preset disclaimer:</strong> regional seawater composition and temperature references, including NOAA NCEI World Ocean Atlas / Copernicus-derived screening values where identified, are engineering starting points only. Use site-specific laboratory water analysis for final engineering.</p></section>
  <section class="input-section acid-dosing-section"><div class="section-inline-title"><div><h3>FEED ACID CONDITIONING · HCl / H₂SO₄</h3><p class="micro-note">Acid is configured here but is not applied to the source-water analysis. The actual dose is solved only when a process calculation is run.</p></div></div>
    <label class="acid-enable-card"><input name="acid_enabled" type="checkbox" ${p.acid_enabled?'checked':''}><span class="acid-checkmark">✓</span><span><strong>Apply acid dosing during calculation</strong><small>Calculate dose, counter-ion addition, resulting pH/alkalinity, kg/h and kg/day for every operating case.</small></span></label>
    <div class="grid acid-config-grid"><div class="field"><label>Acid</label><div class="wrap"><select name="acid_type"><option value="hcl" ${p.acid_type==='hcl'?'selected':''}>Hydrochloric acid · HCl</option><option value="h2so4" ${p.acid_type==='h2so4'?'selected':''}>Sulfuric acid · H₂SO₄</option></select></div></div><div class="field"><label>Target feed pH</label><div class="wrap"><input name="acid_target_ph" type="number" min="2" max="12" step="0.05" value="${p.acid_target_ph??7}"></div></div><div class="field"><label>Commercial solution strength</label><div class="wrap"><input name="acid_solution_strength_pct" type="number" min="1" max="100" step="0.1" value="${p.acid_solution_strength_pct??32}"><span class="suffix">wt%</span></div></div><div class="field"><label>Commercial solution density</label><div class="wrap"><input name="acid_solution_density_kg_l" type="number" min="0.5" max="2.5" step="0.01" value="${p.acid_solution_density_kg_l??1.16}"><span class="suffix">kg/L</span></div></div></div>
    <div class="acid-pending-note ${p.acid_enabled?'active':''}">${p.acid_enabled?`Configured: ${p.acid_type==='h2so4'?'H₂SO₄':'HCl'} to target pH ${fmt(p.acid_target_ph,2)}. Dose will be calculated at RUN using each case's actual RO feed flow.`:'Acid conditioning is OFF.'}</div>
  </section>
  <section class="input-section ionic-composition-section"><div class="section-inline-title"><div><h3>IONIC COMPOSITION & CHARGE BALANCE</h3><p class="micro-note">Cations and anions are grouped by electrical charge. meq/L values and charge imbalance are calculated from the current analysis at the entered pH and temperature.</p></div></div>
    <div class="water-ion-editor">${waterIonColumn('CATIONS (+)',WATER_CATION_FIELDS,'waterCationMeq','cation')}${waterIonColumn('ANIONS (−)',WATER_ANION_FIELDS,'waterAnionMeq','anion')}</div>
    <div class="water-charge-summary"><div class="water-charge-kpis"><div><span>Cation charge</span><strong id="waterCationMeqKpi">—</strong><small>meq/L</small></div><div><span>Anion charge</span><strong id="waterAnionMeqKpi">—</strong><small>meq/L</small></div><div><span>Charge imbalance</span><strong id="waterChargeImbalance">—</strong><small id="waterChargeStatus">Calculating…</small></div></div><div class="water-balance-controls"><strong>Balance analysis by selected ion</strong>${waterBalanceSelectHtml()}<button type="button" id="waterBalanceBtn" class="ghost">Balance charge</button><span id="waterBalanceMessage">${escapeHtml(waterBalanceNotice||'')}</span></div><p class="micro-note">Balancing is never automatic. If cation charge is high, add Cl⁻, SO₄²⁻ or bicarbonate-equivalent alkalinity. If anion charge is high, add Na⁺, Ca²⁺ or Mg²⁺. When alkalinity is selected, pH is held constant and carbonate equilibrium is re-solved before the final charge balance is reported.</p></div>
    <div class="water-neutral-qc"><h4>UNCHARGED / QC ANALYTICAL INPUTS</h4><div class="grid chemistry-neutral-grid">${neutralFields}${labCarbonate}</div></div>
    <p class="micro-note">Standard-ocean presets preserve representative major-ion ratios. Calculated carbonate is derived from pH + total alkalinity; lab-reported carbonate is QC only.</p>
  </section>`;
  $('#modeLabel').textContent=`Water Quality · Case ${activeCase}`; setPrimaryLabel('Calculate water chemistry'); $('.solve-hint').textContent=`Case ${activeCase}: reference water and chemistry. Configure operating extremes in Hydraulic Envelope.`; bindWaterTab();renderCurrentWaterChemistry();
}
function captureWater(){
  let o={...waterProfile};const fd=new FormData($('#calcForm'));
  fd.forEach((v,k)=>{if(k==='case_selector')return;o[k]=(v===''?'':(isNaN(v)?v:+v))});
  o.acid_enabled=fd.get('acid_enabled')==='on';o.feed_tds=Number(o.analysis_tds||0);o.water_mode='full';
  const pr=presetById(o.water_region);o.water_region_name=pr?.name||'Custom';o.temperature_source_name=pr?.temperature_source_name||o.temperature_source_name||'Project input';o.temperature_source_url=pr?.temperature_source_url||o.temperature_source_url||'';return o;
}
function profileChemPayload(w=waterProfile,comp=null,phOverride=null,alkOverride=null){const o={temperature_c:Number(w.temperature_c||25),feed_ph:Number(phOverride??w.feed_ph??8),reported_tds:Number(w.analysis_tds||w.feed_tds||0)};Object.keys(chemistry).filter(k=>k.startsWith('ion_')).forEach(k=>{const ion=k.slice(4);o[k]=comp&&comp[ion]!==undefined?comp[ion]:Number(w[k]||0)});if(alkOverride!=null)o.ion_bicarbonate=Number(alkOverride);return o}
function applyCompositionToProfile(w,comp){Object.entries(comp||{}).forEach(([k,v])=>{if(('ion_'+k) in chemistry)w['ion_'+k]=Number(v||0)});return w}
async function rescaleWaterTds(target){let w=captureWater();const payload={...profileChemPayload(w),target_tds:Number(target||0)};const j=await requestJson('/api/chemistry/scale-tds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},'TDS scaling failed');applyCompositionToProfile(w,j.composition);w.analysis_tds=Number(target||0);w.feed_tds=w.analysis_tds;w._tds_scale_factor=j.factor;waterProfile=w;lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();renderWaterTab();if($('#results'))$('#results').innerHTML=''}
async function refreshCalculatedCarbonate(){const el=$('#calculatedCarbonate'),note=$('#carbonateQcNote');if(!el)return;try{const w=captureWater();const j=await requestJson('/api/chemistry/speciate-ph',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(profileChemPayload(w))},'Carbonate speciation failed');el.value=fmt(j.co3_mg_l,3);const reported=Number(w.ion_carbonate||0),calc=Number(j.co3_mg_l||0);if(note){if(reported>0&&calc>0){const d=100*(reported-calc)/calc;note.textContent=`Lab QC: ${fmt(reported,3)} mg/L · difference ${fmt(d,1)}%${Math.abs(d)>20?' · REVIEW ANALYSIS':''}`;note.classList.toggle('chem-qc-warning',Math.abs(d)>20)}else{note.textContent='Optional QC only; equilibrium carbonate is used by the model.';note.classList.remove('chem-qc-warning')}}}catch(e){el.value='Unavailable';if(note)note.textContent=e.message||'Carbonate speciation failed'}}
function markWaterChargePending(message='Calculate water chemistry to evaluate charge balance.'){
  document.querySelectorAll('[data-water-meq]').forEach(el=>{el.textContent='—'});
  for(const id of ['waterCationMeq','waterAnionMeq','waterCationMeqKpi','waterAnionMeqKpi','waterChargeImbalance']){const el=$('#'+id);if(el)el.textContent='—';}
  const status=$('#waterChargeStatus');if(status)status.textContent=message;
  const box=document.querySelector('.water-charge-summary');if(box)box.classList.remove('charge-good','charge-review','charge-bad');
  const sel=$('#waterBalanceIon');if(sel){sel.value='';Array.from(sel.options).forEach(option=>{if(option.value)option.disabled=true});sel.title='Calculate water chemistry before balancing the analysis.';}
}
function applyWaterChargeAnalysis(result){
  const cat=$('#waterCationMeq'),an=$('#waterAnionMeq'),imb=$('#waterChargeImbalance');if(!cat||!an||!imb)return;
  const ch=result?.charge||{};if(!Array.isArray(ch.rows)){markWaterChargePending('Charge balance is unavailable for this result.');return;}
  const rows=Object.fromEntries(ch.rows.map(row=>[row.key,row]));document.querySelectorAll('[data-water-meq]').forEach(el=>{const row=rows[el.dataset.waterMeq];el.textContent=row?fmt(row.meq_l,3):'—'});
  cat.textContent=fmt(ch.cations_meq_l,3);an.textContent=fmt(ch.anions_meq_l,3);const ck=$('#waterCationMeqKpi'),ak=$('#waterAnionMeqKpi');if(ck)ck.textContent=fmt(ch.cations_meq_l,3);if(ak)ak.textContent=fmt(ch.anions_meq_l,3);
  const value=Number(ch.imbalance_pct||0);imb.textContent=`${value>=0?'+':''}${fmt(value,2)}%`;const status=$('#waterChargeStatus');if(status)status.innerHTML=chemStatusText(value);
  const sel=$('#waterBalanceIon');if(sel){const excessCations=Number(ch.cations_meq_l)>Number(ch.anions_meq_l)+1e-9,excessAnions=Number(ch.anions_meq_l)>Number(ch.cations_meq_l)+1e-9;Array.from(sel.options).forEach(option=>{if(!option.value)return;option.disabled=(excessCations&&!['chloride','sulfate','alkalinity'].includes(option.value))||(excessAnions&&!['sodium','calcium','magnesium'].includes(option.value))||(!excessCations&&!excessAnions)});if(sel.selectedOptions[0]?.disabled)sel.value='';sel.title=excessCations?'Excess cation charge: add an anion.':excessAnions?'Excess anion charge: add a cation.':'Charge is already balanced.';}
  const box=document.querySelector('.water-charge-summary');if(box){box.classList.toggle('charge-good',Math.abs(value)<2);box.classList.toggle('charge-review',Math.abs(value)>=2&&Math.abs(value)<5);box.classList.toggle('charge-bad',Math.abs(value)>=5);}
}
async function refreshWaterChargeBalance(){
  const cat=$('#waterCationMeq'),an=$('#waterAnionMeq'),imb=$('#waterChargeImbalance');if(!cat||!an||!imb)return null;
  try{const water=captureWater();const result=await requestJson('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(profileChemPayload(water))},'Charge balance calculation failed');applyWaterChargeAnalysis(result);return result;}
  catch(error){markWaterChargePending(error?.message||'Charge calculation failed');return null;}
}
async function balanceWaterFromInput(){
  const sel=$('#waterBalanceIon'),ion=sel?.value;if(!ion)return;
  try{
    waterProfile=captureWater();const before=await requestJson('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(profileChemPayload(waterProfile))},'Charge balance calculation failed');const payload={...profileChemPayload(waterProfile),ion};const j=await requestJson('/api/chemistry/balance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},'Balancing failed');applyCompositionToProfile(waterProfile,j.composition);waterProfile.analysis_tds=Object.values(j.composition).reduce((a,b)=>a+Number(b||0),0);waterProfile.feed_tds=waterProfile.analysis_tds;lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();const beforeRow=(before.charge?.rows||[]).find(r=>r.key===(ion==='alkalinity'?'bicarbonate':ion));const afterValue=Number(j.composition?.[ion==='alkalinity'?'bicarbonate':ion]||0);const action=Number(j.adjustment_mg_l)>=0?'Added':'Removed';waterBalanceNotice=`${action} ${fmt(Math.abs(j.adjustment_mg_l),2)} mg/L ${ion==='alkalinity'?'bicarbonate-equivalent alkalinity':ion}. ${beforeRow?`New analytical value ${fmt(afterValue,2)} mg/L. `:''}Final imbalance ${fmt(j.charge_after?.imbalance_pct,3)}%.`;renderWaterTab();const msg=$('#waterBalanceMessage');if(msg)msg.textContent=waterBalanceNotice;
  }catch(e){showCalcError(e,'water chemistry')}
}
function updateAcidDefaults(){
  const acidSelect=document.querySelector('[name="acid_type"]');
  const acid=String(acidSelect?.value||waterProfile.acid_type||'hcl').toLowerCase();
  const profile=ACID_PROPERTY_PROFILES[acid]||ACID_PROPERTY_PROFILES.hcl;
  const strength=document.querySelector('[name="acid_solution_strength_pct"]');
  const density=document.querySelector('[name="acid_solution_density_kg_l"]');
  if(strength)strength.value=String(profile.solution_strength_pct);
  if(density)density.value=String(profile.solution_density_kg_l);
  waterProfile.acid_type=profile.acid_type;
  waterProfile.acid_solution_strength_pct=profile.solution_strength_pct;
  waterProfile.acid_solution_density_kg_l=profile.solution_density_kg_l;
  waterProfile.acid_molecular_weight_g_mol=profile.molecular_weight_g_mol;
  waterProfile.acid_equivalents_per_mole=profile.equivalents_per_mole;
}
function bindWaterTab(){
  document.querySelector('[name="acid_type"]')?.addEventListener('change',()=>{updateAcidDefaults();waterProfile=captureWater();syncActiveCaseStore();renderWaterTab()});
  document.querySelector('[name="acid_enabled"]')?.addEventListener('change',()=>{waterProfile=captureWater();syncActiveCaseStore();renderWaterTab()});
  const cs=document.querySelector('[name="case_selector"]');if(cs)cs.addEventListener('change',()=>switchCase(Number(cs.value)));
  const sel=document.querySelector('[name="water_region"]');if(sel)sel.addEventListener('change',()=>{const pr=presetById(sel.value);const preserved={envelope_label:waterProfile.envelope_label,source_water_type:waterProfile.source_water_type,acid_enabled:waterProfile.acid_enabled,acid_type:waterProfile.acid_type,acid_target_ph:waterProfile.acid_target_ph,acid_solution_strength_pct:waterProfile.acid_solution_strength_pct,acid_solution_density_kg_l:waterProfile.acid_solution_density_kg_l,temperature_min_c:waterProfile.temperature_min_c,temperature_max_c:waterProfile.temperature_max_c,new_membrane_fouling_factor:waterProfile.new_membrane_fouling_factor,old_membrane_fouling_factor:waterProfile.old_membrane_fouling_factor};waterProfile={...makeWaterProfile(pr),...preserved,_last_speciated_ph:pr.ph??8.1};caseSetupNotice='';lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();renderWaterTab()});
  const sal=document.querySelector('[name="salinity_psu"]');if(sal)sal.addEventListener('change',()=>{let w=captureWater();w.analysis_tds=roundTdsFromPsu(w.salinity_psu);const pr=presetById(w.water_region);if(pr)Object.assign(w,scaledChemistry(pr.chemistry||'standard',w.analysis_tds));waterProfile=w;lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();renderWaterTab()});
  const tds=document.querySelector('[name="analysis_tds"]');if(tds)tds.addEventListener('change',async()=>{try{await rescaleWaterTds(tds.value)}catch(e){showCalcError(e,'startup')}});
  const ph=document.querySelector('[name="feed_ph"]');if(ph)ph.addEventListener('change',async()=>{waterProfile=captureWater();lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();markWaterChargePending();await refreshCalculatedCarbonate()});
  document.querySelectorAll('#fields input,#fields select').forEach(el=>{if(['case_selector','water_region','salinity_psu','analysis_tds','feed_ph','acid_type','acid_enabled'].includes(el.name)||['waterBalanceIon'].includes(el.id))return;el.addEventListener('change',async()=>{waterProfile=captureWater();lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();if(el.name?.startsWith('ion_')||el.name==='temperature_c'){markWaterChargePending();await refreshCalculatedCarbonate()}})});$('#waterBalanceBtn')?.addEventListener('click',balanceWaterFromInput);refreshCalculatedCarbonate();if(lastChemistryResult)applyWaterChargeAnalysis(lastChemistryResult);else markWaterChargePending();
}
function saveWaterFromTab(){if(mode==='water'){waterProfile=captureWater();syncActiveCaseStore()}}
function availableChemistryTechnology(){if(chemistryTechnology!=='auto'&&caseResults[chemistryTechnology])return chemistryTechnology;return comparisonOrder?.find(([k])=>caseResults[k])?.[0]||null}
function chemistryStreamBasis(){const tech=availableChemistryTechnology(),r=tech?caseResults[tech]:null;if(chemistryStream==='feed'||!r)return {comp:Object.fromEntries(summarySpecies.map(([k])=>[k,Number(waterProfile['ion_'+k]||0)])),ph:Number(waterProfile.feed_ph||8),alk:Number(waterProfile.ion_bicarbonate||0)};const streams=waterStreamsForResult({waterProfile},r),n=resultStageCount(r);if(chemistryStream==='concentrate')return {comp:streams.conc||streams.feed,ph:Number(r[`stage${n}_concentrate_ph`]??r.stage1_concentrate_ph??waterProfile.feed_ph),alk:Number(r[`stage${n}_concentrate_alkalinity_mg_l_as_hco3`]??r.stage1_concentrate_alkalinity_mg_l_as_hco3??0)};const comp=r.composite_permeate_composition_mg_l||streams.perm||streams.feed;return {comp,ph:Number(r.composite_permeate_ph??r[`stage${n}_permeate_ph`]??r.stage1_permeate_ph??waterProfile.feed_ph),alk:Number(r.composite_permeate_alkalinity_mg_l_as_hco3??r[`stage${n}_permeate_alkalinity_mg_l_as_hco3`]??r.stage1_permeate_alkalinity_mg_l_as_hco3??0)}}
function renderChemistryTab(){
  // Legacy project files may reference the retired chemistry workspace.
  // Result chemistry now belongs to the selected calculated case.
  const target=caseResults?.multistage?'multistage':'water';
  mode=target;
  if(target==='water')renderWaterTab();
  else{renderFields(modeStates.multistage||defaults.multistage);const r=caseResults.multistage;if(r)show(r);}
}
function chemStatusText(v){const a=Math.abs(Number(v||0));return a<2?'Balanced · <2%':a<5?'Review · 2–5%':'CHECK ANALYSIS · >5%'}
function chemistryResultsHtml(j){if(!j)return '<p class="muted">Run chemistry analysis.</p>';const ch=j.charge||{},rows=ch.rows||[];const cats=rows.filter(x=>x.charge>0),ans=rows.filter(x=>x.charge<0),neut=rows.filter(x=>x.charge===0);const ionRows=a=>a.map(x=>`<tr><td>${escapeHtml(x.label)}</td><td class="value">${fmt(x.mg_l,2)}</td><td class="value">${fmt(x.mmol_l,3)}</td><td class="value">${x.charge>0?'+':''}${x.charge}</td><td class="value">${fmt(x.meq_l,3)}</td></tr>`).join('');const indexRows=(j.indices||[]).map(x=>`<tr><td>${escapeHtml(x.name)}</td><td>${escapeHtml(x.track)}</td><td class="value">${fmt(x.value,3)}</td><td>${escapeHtml(x.definition)}</td></tr>`).join('');const mineralRows=(j.minerals||[]).slice().sort((a,b)=>String(a.formula||'').localeCompare(String(b.formula||''))||String(a.name||'').localeCompare(String(b.name||''))).map(x=>{const pct=x.concentration_saturation_pct;const cls=Number(pct)>=100?'chem-warn':'';return `<tr class="${cls}"><td><strong>${escapeHtml(x.formula)}</strong></td><td>${escapeHtml(x.name)}</td><td>${escapeHtml(x.governing_track)}</td><td class="value">${fmt(x.si_track_a,3)}</td><td class="value">${x.si_track_b==null?'—':fmt(x.si_track_b,3)}</td><td class="value">${Number.isFinite(pct)?fmt(pct,1)+'%':'∞'}</td></tr>`}).join('');const f=j.speciation?.free_mol_kg||{},specRows=['calcium','magnesium','sodium','potassium','strontium','barium','iron_ii','manganese_ii','bicarbonate','carbonate','sulfate','fluoride'].map(k=>`<tr><td>${escapeHtml(summarySpecies.find(x=>x[0]===k)?.[1]||k)}</td><td class="value">${fmt(f[k],7)}</td><td class="value">${fmt(j.speciation?.activities?.[k],7)}</td></tr>`).join('');const ws=j.speciation?.weak_systems||{};const weakRows=Object.entries(ws).flatMap(([system,parts])=>Object.entries(parts||{}).filter(([k])=>k!=='total').map(([k,v])=>`<tr><td>${escapeHtml(system)}</td><td>${escapeHtml(k)}</td><td class="value">${fmt(v,8)}</td><td class="value">${Number(parts.total)>0?fmt(100*Number(v)/Number(parts.total),2)+'%':'—'}</td></tr>`)).join('');return `<div class="chemistry-dashboard"><div class="kpi-strip seven"><div><span>Reported TDS</span><strong>${fmt(j.reported_tds_mg_l,1)} mg/L</strong></div><div><span>Temperature</span><strong>${fmt(j.temperature_c??waterProfile.temperature_c,1)} °C</strong></div><div><span>pH</span><strong>${fmt(j.ph??waterProfile.feed_ph,2)}</strong></div><div><span>Constituent sum</span><strong>${fmt(j.tds_sum_mg_l,1)} mg/L</strong><small>${fmt(j.tds_difference_pct,2)}% difference</small></div><div><span>Ionic strength</span><strong>${fmt(j.ionic_strength_mol_kg,3)} mol/kg</strong></div><div><span>Charge balance</span><strong>${fmt(ch.imbalance_pct,2)}%</strong></div><div><span>Osmotic pressure</span><strong>${fmt(j.osmotic?.osmotic_bar,2)} bar</strong></div></div>${chemistryVisualizations(j)}<section class="report-section"><div class="chart-title-row"><h3>Electroneutrality / ion balance</h3><span>${chemStatusText(ch.imbalance_pct)}</span></div><div class="chem-ion-columns"><div><h4>Cations</h4><table class="report-table"><tr><th>Constituent</th><th>mg/L</th><th>mmol/L</th><th>z</th><th>meq/L</th></tr>${ionRows(cats)}<tr><td><b>Total cations</b></td><td></td><td></td><td></td><td class="value"><b>${fmt(ch.cations_meq_l,3)}</b></td></tr></table></div><div><h4>Anions</h4><table class="report-table"><tr><th>Constituent</th><th>mg/L</th><th>mmol/L</th><th>z</th><th>meq/L</th></tr>${ionRows(ans)}<tr><td><b>Total anions</b></td><td></td><td></td><td></td><td class="value"><b>${fmt(ch.anions_meq_l,3)}</b></td></tr></table></div></div>${Math.abs(ch.imbalance_pct)>=0.05?`<div class="charge-balance-box"><strong>Balance this analysis</strong><select id="balanceIon"><option value="">Choose balancing ion…</option>${Number(ch.cations_meq_l)>Number(ch.anions_meq_l)?'<option value="chloride">Chloride (Cl⁻)</option><option value="sulfate">Sulfate (SO₄²⁻)</option><option value="alkalinity">Alkalinity (HCO₃-equivalent)</option>':'<option value="sodium">Sodium (Na⁺)</option><option value="calcium">Calcium (Ca²⁺)</option><option value="magnesium">Magnesium (Mg²⁺)</option><option value="alkalinity">Reduce alkalinity (HCO₃-equivalent)</option>'}</select><button type="button" id="balanceWaterBtn" class="ghost">Balance</button><span id="balanceMessage"></span><div class="micro-note">Balancing is never automatic. When alkalinity is selected, pH is held constant and carbonate equilibrium is re-solved after every trial; the final charge balance is reported after re-speciation.</div></div>`:''}${neut.length?`<p class="micro-note">Neutral analytical constituents: ${neut.map(x=>`${escapeHtml(x.label)} ${fmt(x.mg_l,2)} mg/L`).join(' · ')}</p>`:''}</section><section class="report-section"><h3>pH-dependent speciation / free-ion activity</h3><table class="report-table"><tr><th>Component</th><th>Free molality (mol/kg)</th><th>Activity</th></tr>${specRows}</table><p class="micro-note">Carbonate system at pH ${fmt(j.ph,2)}: CT ${fmt(j.speciation?.total_inorganic_carbon_mol_kg,7)} mol/kg · CO₂(aq) ${fmt(j.speciation?.co2_mol_kg,7)} · HCO₃⁻ ${fmt(j.speciation?.hco3_mol_kg,7)} · CO₃²⁻ ${fmt(j.speciation?.co3_mol_kg,7)}.</p><h4>Weak-acid / base equilibrium distribution</h4><div class="table-wrap"><table class="report-table"><tr><th>System</th><th>Species</th><th>mol/kg</th><th>Fraction of analytical total</th></tr>${weakRows}</table></div><p class="micro-note">Boron, silica, phosphate, ammonium/ammonia and fluoride/HF distributions are recalculated whenever case pH or temperature changes. Analytical component totals are preserved.</p></section><section class="report-section"><h3>Scaling & corrosion indices</h3><table class="report-table"><tr><th>Index</th><th>Track</th><th>Value</th><th>Definition</th></tr>${indexRows}</table></section><section class="report-section"><h3>Mineral saturation</h3><div class="table-wrap"><table class="report-table"><tr><th>Formula</th><th>Mineral</th><th>Governing track</th><th>SI Track A</th><th>SI Track B</th><th>Conc. saturation</th></tr>${mineralRows}</table></div><p class="micro-note">Concentration-basis saturation follows the workbook convention: 100 × (IAP/Ksp)^(1/ν), where ν is ions per mineral formula unit.</p></section><p class="micro-note chemistry-basis">${escapeHtml(j.basis_note||'')}</p></div>`}
async function loadChemistryResults(){try{clearCalcError();$('#results').innerHTML='<p class="muted">Calculating water chemistry…</p>';const b=chemistryStreamBasis(),comp={...(b.comp||{})};comp.bicarbonate=Number(b.alk||0);if(chemistryStream!=='feed')comp.carbonate=0;const payload=profileChemPayload(waterProfile,comp,b.ph,b.alk);const j=await requestJson('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},'Chemistry calculation failed');lastChemistryResult=j;syncActiveCaseStore();$('#results').innerHTML=chemistryResultsHtml(j);$('#balanceWaterBtn')?.addEventListener('click',balanceActiveWater)}catch(e){showCalcError(e,'chemistry');$('#results').innerHTML='<p class="muted">Chemistry calculation could not be completed.</p>'}}
async function balanceActiveWater(){const ion=$('#balanceIon')?.value;if(!ion)return;try{const payload={...profileChemPayload(waterProfile),ion};const j=await requestJson('/api/chemistry/balance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},'Balancing failed');applyCompositionToProfile(waterProfile,j.composition);waterProfile.analysis_tds=Object.values(j.composition).reduce((a,b)=>a+Number(b||0),0);waterProfile.feed_tds=waterProfile.analysis_tds;lastChemistryResult=null;markAllTurboDesignStale();syncActiveCaseStore();const action=Number(j.adjustment_mg_l)>=0?'Added':'Removed';const msg=`${action} ${fmt(Math.abs(j.adjustment_mg_l),2)} mg/L ${ion==='alkalinity'?'alkalinity as HCO₃-equivalent':ion}; pH held at ${fmt(j.ph_held_constant??waterProfile.feed_ph,2)}; new imbalance ${fmt(j.charge_after?.imbalance_pct,3)}%.`;await loadChemistryResults();const m=$('#balanceMessage');if(m)m.textContent=msg}catch(e){showCalcError(e,'water chemistry')}}
function embeddedChemistryComposition(r,stream){
  const streams=waterStreamsForResult({waterProfile},r);
  if(stream==='feed')return streams.feed;
  const m=String(stream||'').match(/^stage(\d+)_concentrate$/);
  if(m){const i=Number(m[1]);return r?.[`stage${i}_concentrate_composition_mg_l`]||streams.conc||streams.feed;}
  if(stream==='permeate')return r?.composite_permeate_composition_mg_l||streams.perm||streams.feed;
  return streams.conc||streams.feed;
}

function resultChemistryBasis(r,stream){
  const n=resultStageCount(r);let comp,ph,alk;
  if(stream==='feed'){comp=r?.stage1_feed_composition_mg_l;ph=r?.stage1_feed_ph;alk=r?.stage1_feed_alkalinity_mg_l_as_hco3;}
  else {const m=String(stream||'').match(/^stage(\d+)_concentrate$/);if(m){const i=Number(m[1]);comp=r?.[`stage${i}_concentrate_composition_mg_l`];ph=r?.[`stage${i}_concentrate_ph`];alk=r?.[`stage${i}_concentrate_alkalinity_mg_l_as_hco3`];}else if(stream==='permeate'){comp=r?.composite_permeate_composition_mg_l||r?.[`stage${n}_permeate_composition_mg_l`];ph=r?.composite_permeate_ph??r?.[`stage${n}_permeate_ph`];alk=r?.composite_permeate_alkalinity_mg_l_as_hco3??r?.[`stage${n}_permeate_alkalinity_mg_l_as_hco3`];}else{comp=r?.[`stage${n}_concentrate_composition_mg_l`];ph=r?.[`stage${n}_concentrate_ph`];alk=r?.[`stage${n}_concentrate_alkalinity_mg_l_as_hco3`];}}
  return {comp:comp||embeddedChemistryComposition(r,stream),ph:Number(ph??waterProfile.feed_ph),alk:Number((alk??waterProfile.ion_bicarbonate)||0)};
}
function embeddedChemistrySection(r){return '';}
function embeddedChemistryCacheKey(tech,stream,r=caseResults[tech]){const basis=resultChemistryBasis(r,stream),comp=basis.comp||{};const sig=summarySpecies.map(([k])=>Number(comp[k]||0).toFixed(4)).join(',');const temp=Number(r?.stage1_temperature_c??waterProfile.temperature_c??25);return `${activeCase}:${tech}:${stream}:${temp.toFixed(2)}:${Number(basis.ph??waterProfile.feed_ph??8).toFixed(3)}:${sig}`}
async function loadEmbeddedChemistry(r,force=false){
  const host=$('#embeddedChemistryBody'); if(!host||!r)return;
  const stream=embeddedChemistryStreamByMode[mode]||'concentrate'; const key=embeddedChemistryCacheKey(mode,stream,r);
  if(embeddedChemistryCache[key]&&!force){host.innerHTML=chemistryResultsHtml(embeddedChemistryCache[key]);return;}
  host.innerHTML=`<p class="muted">Calculating ${escapeHtml(stream.replaceAll('_',' '))} chemistry…</p>`;
  try{
    const basis=resultChemistryBasis(r,stream),comp=basis.comp; const payload={...profileChemPayload(waterProfile,comp,basis.ph,basis.alk),reported_tds:compositionTds(comp),source_ph:basis.ph};
    const resp=await totalroFetch('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const j=await resp.json();
    if(!resp.ok)throw new Error(j.error||'Chemistry calculation failed'); embeddedChemistryCache[key]=j; host.innerHTML=chemistryResultsHtml(j);
  }catch(e){host.innerHTML=`<p class="muted">Water chemistry could not be calculated: ${escapeHtml(e.message||String(e))}</p>`;}
}
function bindEmbeddedChemistry(r){
  const sel=$('#embeddedChemStream');if(sel)sel.addEventListener('change',()=>{embeddedChemistryStreamByMode[mode]=sel.value;loadEmbeddedChemistry(r)});
  loadEmbeddedChemistry(r);
}
function embeddedChemistryPrintHtml(key){const stream=embeddedChemistryStreamByMode[key]||'concentrate',j=embeddedChemistryCache[embeddedChemistryCacheKey(key,stream,caseResults[key])];return j?`<section class="print-section"><h3>Water Chemistry · ${escapeHtml(stream.replaceAll('_',' '))}</h3>${chemistryResultsHtml(j)}</section>`:'<p class="print-no-data">Contextual water chemistry is still being calculated. Reprint after the chemistry section is populated.</p>'}

function turboCaseOptions(selected){
  const ids=Object.keys(caseStore).map(Number).sort((a,b)=>a-b);
  return `<option value="auto" ${String(selected)==='auto'?'selected':''}>Auto · lowest required Cvt</option>`+ids.map(id=>`<option value="${id}" ${String(selected)===String(id)?'selected':''}>Case ${id}</option>`).join('');
}
function turboDesignDutyHtml(){
  if(!['single','interstage','biturbo'].includes(mode))return '';
  const lock=turboDesignLocks[mode]||{};
  const status=lock.stale?'Design envelope needs recalculation':(lock.design?'Design duty locked':'No design envelope calculated');
  if(mode==='biturbo')return `<section class="input-section turbo-design-duty ${lock.stale?'stale':''}"><div class="section-inline-title"><h3>TURBO DESIGN DUTY · MULTI-CASE LOCK</h3><button type="button" class="envelope-btn" id="turboDesignBtn">Lock / recalculate design envelope</button></div><div class="grid"><div class="field span2"><label>Interstage turbo design case</label><div class="wrap"><select id="interDesignCase">${turboCaseOptions(lock.inter_case??'auto')}</select></div></div><div class="field span2"><label>Feed turbo design case</label><div class="wrap"><select id="feedDesignCase">${turboCaseOptions(lock.feed_case??'auto')}</select></div></div></div><p class="micro-note"><strong>${escapeHtml(status)}.</strong> Auto selects the case with the lowest required Cvt for each turbine. Total RO Design then fixes that turbine Cvc at the selected design duty and recalculates all cases with the workbook off-design turbine/pump efficiency equations. A higher-Cvt design case may be selected manually if the user prefers; the lower-Cvt case will then require backpressure, which reduces energy recovery (energy-transfer efficiency). Bypass/backpressure remain explicit in every off-design result.</p></section>`;
  return `<section class="input-section turbo-design-duty ${lock.stale?'stale':''}"><div class="section-inline-title"><h3>TURBO DESIGN DUTY · MULTI-CASE LOCK</h3><button type="button" class="envelope-btn" id="turboDesignBtn">Lock / recalculate design envelope</button></div><div class="grid"><div class="field span2"><label>Design duty case</label><div class="wrap"><select id="designCase">${turboCaseOptions(lock.case??'auto')}</select></div></div></div><p class="micro-note"><strong>${escapeHtml(status)}.</strong> Auto selects the case with the lowest required Cvt, fixes Cvc at that design duty, then recalculates the remaining cases from the locked turbine using the supplied workbook off-design method. A higher-Cvt design case may be selected manually if the user prefers; however, the case with the lowest required Cvt will then require backpressure, reducing energy recovery (energy-transfer efficiency).</p></section>`;
}
function activeTurboLockFields(tech){if(tech==='interstage'&&(Boolean(modeStates.interstage?.generalized_interstage_turbo)||Number(modeStates.interstage?.stage_count||2)>2))return {};const l=turboDesignLocks[tech];return l&&!l.stale&&l.locked_fields?deepClone(l.locked_fields):{};}
function markTurboDesignStale(tech=mode){if(!['single','interstage','biturbo'].includes(tech))return;const l=turboDesignLocks[tech]||(turboDesignLocks[tech]={});if(!l.stale){l.stale=true;l.locked_fields=null;}const sec=document.querySelector('.turbo-design-duty');if(sec)sec.classList.add('stale');}
function markAllTurboDesignStale(){['single','interstage','biturbo'].forEach(markTurboDesignStale);}
async function runTurboDesignEnvelope(tech=mode){
  if(!['single','interstage','biturbo'].includes(tech))return;
  persistActiveCase();
  const lock=turboDesignLocks[tech]||(turboDesignLocks[tech]={stale:true});
  if(tech==='biturbo'){lock.inter_case=$('#interDesignCase')?.value||lock.inter_case||'auto';lock.feed_case=$('#feedDesignCase')?.value||lock.feed_case||'auto';}
  else lock.case=$('#designCase')?.value||lock.case||'auto';
  const cases=[];
  Object.keys(caseStore).map(Number).sort((a,b)=>a-b).forEach(cid=>{const c=caseStore[cid];if(processModeConfigured(tech,c?.modeStates?.[tech]))cases.push({case_id:cid,data:processPayload(c,tech,false)});});
  if(!cases.length)throw new Error(`No configured ${tech} cases are available for design locking.`);
  setCalculating(true);clearCalcError();
  try{
    const body={mode:tech,cases};if(tech==='biturbo'){body.inter_design_case=lock.inter_case;body.feed_design_case=lock.feed_case}else body.design_case=lock.case;
    const j=await requestJson('/api/turbo/design-cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},'Turbo design-envelope calculation failed');
    lock.design=deepClone(j.design);lock.locked_fields=deepClone(j.locked_fields||{});lock.stale=false;
    (j.results||[]).forEach(item=>{const cid=Number(item.id);if(item.ok&&caseStore[cid])caseStore[cid].caseResults[tech]=item.result;});
    lastComputeRun={backend:j.backend,workers:j.workers,fallback:j.fallback,elapsed_seconds:j.elapsed_seconds};
    loadCaseGlobals(activeCase);mode=tech;renderFields(modeStates[tech]||convertedDefaults());if(caseResults[tech]){lastResult=caseResults[tech];show(lastResult)}
  } finally {setCalculating(false)}
}

function stageRecipeArray(values,stage){
  const n=Math.max(1,Math.min(8,Number(values?.[`elements_per_vessel_${stage}`]||7))),fallback=values?.[`membrane_${stage}`]||defaultMembrane,raw=values?.[`membrane_recipe_${stage}`];let arr=[];
  if(Array.isArray(raw))arr=raw.slice();else if(typeof raw==='string'&&raw.trim()){try{const j=JSON.parse(raw);arr=Array.isArray(j)?j:raw.split(',')}catch(e){arr=raw.split(',')}}
  arr=arr.map(x=>String(x||'').trim()).filter(Boolean);while(arr.length<n)arr.push(fallback);return arr.slice(0,n);
}
function hybridRecipeEditorHtml(stage,values){
  const recipe=stageRecipeArray(values,stage),representative=recipe[0]||defaultMembrane;
  const uniform=new Set(recipe).size<=1,mm=membranes.find(x=>x.record_id===representative);
  const slots=recipe.map((id,i)=>{const m=membranes.find(x=>x.record_id===id),short=(m?.model||id||'—').replace(/^SW30/i,'').slice(0,13);return `<button type="button" class="hybrid-slot" data-stage="${stage}" data-slot="${i}" title="${escapeHtml(m?`${membraneManufacturerLabel(m.manufacturer)} ${m.model}`:id)}"><b>${i+1}</b><span>${escapeHtml(short)}</span></button>`}).join('');
  return `<div class="hybrid-editor membrane-design-editor" data-hybrid-stage="${stage}"><div class="hybrid-head"><div><strong>MEMBRANE DESIGN</strong><small>Select one or more element positions, choose a membrane, and apply it. Use Apply to all for a uniform vessel.</small></div></div><input type="hidden" name="membrane_${stage}" value="${escapeHtml(representative)}"><input type="hidden" name="membrane_design_mode_${stage}" value="${uniform?'uniform':'hybrid'}"><input type="hidden" name="membrane_recipe_${stage}" value='${escapeHtml(JSON.stringify(recipe))}'><div class="hybrid-body"><div class="hybrid-select-label">Select element positions:</div><div class="hybrid-slots">${slots}</div><div class="hybrid-selected">Selected: <strong data-selected-label>None</strong></div><div class="hybrid-apply-row"><label>Membrane:<div class="membrane-design-select-wrap"><select data-hybrid-membrane>${membraneOptions(representative)}</select>${membraneSpecNoteHtml(mm,`membrane_design_${stage}`)}</div></label><button type="button" class="envelope-btn" data-apply-hybrid>Apply to selected</button></div><div class="hybrid-actions"><button type="button" class="ghost" data-select-all>Select all</button><button type="button" class="ghost" data-apply-all>Apply to all</button></div></div><div class="hybrid-recipe-summary">Current vessel recipe: ${recipe.map((id,i)=>{const m=membranes.find(x=>x.record_id===id);return `<span>${i+1}. ${escapeHtml(m?.model||id)}</span>`}).join('')}</div></div>`;
}
function bindHybridRecipeEditors(){
  document.querySelectorAll('[data-hybrid-stage]').forEach(ed=>{
    const stage=Number(ed.dataset.hybridStage);
    const modeInput=ed.querySelector(`[name="membrane_design_mode_${stage}"]`);
    const recipeInput=ed.querySelector(`[name="membrane_recipe_${stage}"]`);
    const representativeInput=ed.querySelector(`[name="membrane_${stage}"]`);
    const membraneSelect=ed.querySelector('[data-hybrid-membrane]');
    const selected=new Set();
    const readRecipe=()=>{let arr=[];try{arr=JSON.parse(recipeInput.value)}catch(e){};return Array.isArray(arr)?arr:[]};
    const normalizeState=arr=>{
      const clean=arr.map(x=>String(x||'').trim()).filter(Boolean);
      if(clean.length){representativeInput.value=clean[0];modeInput.value=new Set(clean).size<=1?'uniform':'hybrid';}
      recipeInput.value=JSON.stringify(clean);
    };
    const persistAndRender=arr=>{normalizeState(arr);const vals=capture();modeStates[mode]={...vals};renderFields(vals)};
    const refreshSel=()=>{
      ed.querySelectorAll('.hybrid-slot').forEach((b,i)=>b.classList.toggle('selected',selected.has(i)));
      const a=[...selected].sort((a,b)=>a-b).map(i=>i+1),lab=ed.querySelector('[data-selected-label]');
      if(lab){const consecutive=a.length>1&&a.every((v,i)=>i===0||v===a[i-1]+1);lab.textContent=!a.length?'None':(consecutive?`${a[0]}–${a[a.length-1]}`:a.join(', '));}
    };
    membraneSelect?.addEventListener('change',()=>{const mm=membranes.find(m=>m.record_id===membraneSelect.value);const wrap=membraneSelect.closest('.membrane-design-select-wrap');const current=wrap?.querySelector('.membrane-spec-note');const html=membraneSpecNoteHtml(mm,`membrane_design_${stage}`);if(current)current.outerHTML=html;else membraneSelect.insertAdjacentHTML('afterend',html)});
    ed.querySelectorAll('.hybrid-slot').forEach((b,i)=>b.addEventListener('click',()=>{selected.has(i)?selected.delete(i):selected.add(i);refreshSel()}));
    ed.querySelector('[data-select-all]')?.addEventListener('click',()=>{ed.querySelectorAll('.hybrid-slot').forEach((_,i)=>selected.add(i));refreshSel()});
    ed.querySelector('[data-apply-hybrid]')?.addEventListener('click',()=>{if(!selected.size)return;const arr=readRecipe();const id=membraneSelect?.value||defaultMembrane;selected.forEach(i=>arr[i]=id);persistAndRender(arr)});
    ed.querySelector('[data-apply-all]')?.addEventListener('click',()=>{const id=membraneSelect?.value||defaultMembrane,n=Math.max(1,Math.min(8,Number(document.querySelector(`[name="elements_per_vessel_${stage}"]`)?.value||7)));persistAndRender(Array(n).fill(id))});
    refreshSel();
  });
}
function averageDesignFluxState(values){
  const src=values||{};const n=Math.max(1,Math.min(4,Number(src.stage_count||1)));let area=0,elements=0;const missing=[];
  for(let stage=1;stage<=n;stage++){
    const vessels=Number(src[`vessels_${stage}`]),epv=Number(src[`elements_per_vessel_${stage}`]);
    if(!(vessels>0))missing.push(`Stage ${stage} vessel count`);if(!(epv>0))missing.push(`Stage ${stage} elements/vessel`);
    if(!(vessels>0&&epv>0))continue;
    const recipe=stageRecipeArray(src,stage);let vesselArea=0;
    for(let pos=0;pos<epv;pos++){
      const id=recipe[pos]||src[`membrane_${stage}`];const membrane=membranes.find(m=>m.record_id===id);const a=Number(membrane?.area_m2);
      if(!(a>0)){missing.push(`Stage ${stage} membrane position ${pos+1}`);continue;}vesselArea+=a;
    }
    area+=vessels*vesselArea;elements+=vessels*epv;
  }
  let product=Number(src.target_product_flow);
  if(!(product>0)){
    const feed=Number(src.feed_flow);let recovery=Number(src.target_recovery);if(recovery>1)recovery/=100;
    if(feed>0&&recovery>0&&recovery<1)product=feed*recovery;
  }
  if(!(product>0)){const cap=Number(src.required_capacity_m3d),trains=Number(src.operating_trains);if(cap>0&&trains>0)product=convert(cap/(24*trains),'flow','m3/h',currentUnits.flow);}
  if(!(product>0))missing.push('permeate flow');
  if(!(area>0))missing.push('active membrane area');
  if(missing.length)return {ready:false,missing:[...new Set(missing)],area,elements};
  const productM3h=convert(product,'flow',currentUnits.flow,'m3/h');const lmh=productM3h*1000/area;const shown=convert(lmh,'flux','LMH',currentUnits.flux||'LMH');
  return {ready:Number.isFinite(shown)&&shown>0,value:shown,lmh,area,elements,productM3h,missing:[]};
}
function averageDesignFluxHtml(values){const state=averageDesignFluxState(values);if(!state.ready)return `<div id="averageDesignFluxIndicator" class="average-flux-indicator pending"><span>AVERAGE DESIGN FLUX</span><strong>Average flux pending</strong><small>Complete permeate flow, vessel count, elements per vessel and membrane selection.</small></div>`;return `<div id="averageDesignFluxIndicator" class="average-flux-indicator ready"><span>AVERAGE DESIGN FLUX · PRELIMINARY</span><strong>${fmt(state.value,2)} ${escapeHtml(currentUnits.flux||'LMH')}</strong><small>${fmt(state.productM3h,2)} m³/h ÷ ${fmt(state.area,0)} m² · ${fmt(state.elements,0)} membrane elements</small></div>`;}
function updateAverageDesignFluxIndicator(){if(mode!=='multistage')return;const target=document.getElementById('averageDesignFluxIndicator');if(!target)return;const wrap=document.createElement('div');wrap.innerHTML=averageDesignFluxHtml(capture());target.replaceWith(wrap.firstElementChild);}

function plantOptimizerHtml(values){const on=!!values?.background_optimizer_enabled,obj=values?.optimizer_objective||'min_sec';return `<section class="input-section optimizer-card"><div class="section-inline-title"><div><h3>BACKGROUND DESIGN OPTIMIZER</h3><p class="micro-note">Optional numerical search around the current stage topology. Large candidate arrays are screened using the configured CPU vector path; shortlisted designs are always re-solved with the full CPU engineering model.</p></div></div><label class="acid-enable-card"><input name="background_optimizer_enabled" type="checkbox" ${on?'checked':''}><span class="acid-checkmark">✓</span><span><strong>Run background design optimization</strong><small>Search vessel counts and nearby recovery values without changing membrane/process physics.</small></span></label><div class="optimizer-controls"><label>Objective <select name="optimizer_objective"><option value="min_sec" ${obj==='min_sec'?'selected':''}>Minimum SEC</option><option value="min_membranes" ${obj==='min_membranes'?'selected':''}>Minimum membrane count</option><option value="min_pressure" ${obj==='min_pressure'?'selected':''}>Minimum feed pressure</option><option value="balanced" ${obj==='balanced'?'selected':''}>Balanced design</option></select></label><label>Screen candidates <input name="optimizer_screen_candidates" type="number" min="32" max="20000" step="32" value="${Number(values?.optimizer_screen_candidates||4096)}"></label><label>Full CPU validations <input name="optimizer_validate_candidates" type="number" min="4" max="64" step="1" value="${Number(values?.optimizer_validate_candidates||24)}"></label></div><button type="button" class="envelope-btn" id="runBackgroundOptimizer" ${on?'':'disabled'}>${designOptimizationRunning?'Optimizing…':'Run Background Optimizer'}</button><div id="optimizerStatus" class="micro-note">${lastDesignOptimization?`Last search: ${lastDesignOptimization.screened||0} screened · ${lastDesignOptimization.validated||0} fully validated.`:'No optimization run yet.'}</div></section>`}
function bindPlantOptimizer(){const cb=document.querySelector('[name="background_optimizer_enabled"]'),btn=$('#runBackgroundOptimizer');if(cb)cb.addEventListener('change',()=>{if(btn)btn.disabled=!cb.checked});btn?.addEventListener('click',runBackgroundDesignOptimizer)}
async function runBackgroundDesignOptimizer(){if(mode!=='multistage'||designOptimizationRunning)return;const values=capture();if(!values.background_optimizer_enabled)return;designOptimizationRunning=true;renderFields(values);clearCalcError();try{const data={...waterProfile,...values,flow_unit:currentUnits.flow,pressure_unit:currentUnits.pressure};if(data.max_design_flux_lmh!==undefined&&data.max_design_flux_lmh!=='')data.max_design_flux_lmh=convert(data.max_design_flux_lmh,'flux',currentUnits.flux||'LMH','LMH');const j=await requestJson('/api/optimize/plant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data,mode:'multistage',objective:values.optimizer_objective||'min_sec',screen_candidates:Number(values.optimizer_screen_candidates||4096),validate_candidates:Number(values.optimizer_validate_candidates||24)})},'Background design optimization failed');lastDesignOptimization=j;const rows=(j.top||[]).map(x=>`<tr><td>${x.rank}</td><td>${fmt(x.total_sec,3)}</td><td>${fmt(x.feed_pressure,2)} ${currentUnits.pressure}</td><td>${fmt(x.target_recovery,2)}%</td><td>${(x.vessels||[]).join(' / ')}</td></tr>`).join('');$('#results').insertAdjacentHTML('afterbegin',`<section class="report-section optimizer-results"><div class="chart-title-row"><h3>BACKGROUND DESIGN OPTIMIZER</h3><span>${j.screened} screened · ${j.validated} CPU-validated</span></div><div class="table-wrap"><table class="fedco-table"><tr><th>Rank</th><th>Total SEC<br><span>kWh/m³</span></th><th>Stage 1 pressure</th><th>Target recovery</th><th>Vessels by stage</th></tr>${rows}</table></div><p class="micro-note">GPU screening: ${escapeHtml(j.gpu_screen?.backend||'not applicable')}${j.gpu_screen?.device?` · ${escapeHtml(j.gpu_screen.device)}`:''} · ${j.gpu_screen?.points||0} candidates${j.gpu_screen?.kernel_ms!=null?` · kernel ${fmt(j.gpu_screen.kernel_ms,2)} ms`:''}. Final recommendations are full CPU Total RO Design solves.${j.gpu_screen?.fallback_reason?` GPU fallback: ${escapeHtml(j.gpu_screen.fallback_reason)}`:''}</p></section>`);lastComputeRun={backend:j.cpu_backend,workers:j.workers,elapsed_seconds:j.elapsed_seconds};updateComputeStatus();}catch(e){showCalcError(e,'background design optimizer')}finally{designOptimizationRunning=false;renderFields({...values,background_optimizer_enabled:true});}}

function plantScenarioMatrixHtml(values){const on=!!values?.scenario_matrix_enabled,n=Math.max(1,Number(values?.operating_trains||1)),nm=Math.max(1,n-1);return `<section class="input-section scenario-plant-card"><div class="section-inline-title"><div><h3>SCENARIO MATRIX</h3><p class="micro-note">Optional study mode: run every selected solution at N and N−1 across New/Cold, New/Warm, Aged/Cold and Aged/Warm conditions.</p></div></div><label class="acid-enable-card"><input name="scenario_matrix_enabled" type="checkbox" ${on?'checked':''}><span class="acid-checkmark">✓</span><span><strong>Run this plant as a Scenario Matrix</strong><small>${n} trains at N · ${nm} trains at N−1 · 4 hydraulic-envelope conditions per availability state.</small></span></label><label class="scenario-maintain"><input name="scenario_maintain_capacity_nminus1" type="checkbox" ${values?.scenario_maintain_capacity_nminus1!==false?'checked':''}> Maintain required plant production at N−1 by re-solving the remaining trains at higher loading</label><button type="button" class="envelope-btn" id="runScenarioFromPlant" ${on?'':'disabled'}>Run Scenario Matrix</button><div class="micro-note">${scenarioMatrixLastRun?`Last run: ${scenarioMatrixLastRun.combinations} solution/condition calculations.`:'No Scenario Matrix run yet.'}</div></section>`}
function bindPlantScenarioMatrix(){const toggle=document.querySelector('[name="scenario_matrix_enabled"]'),btn=$('#runScenarioFromPlant');toggle?.addEventListener('change',()=>{if(btn)btn.disabled=!toggle.checked;const v=capture();modeStates.multistage={...v};syncActiveCaseStore()});$('#runScenarioFromPlant')?.addEventListener('click',async()=>{const vals=capture();modeStates.multistage={...vals};scenarioMatrixState.normal_trains=Number(vals.operating_trains||1);scenarioMatrixState.required_capacity_m3d=Number(vals.required_capacity_m3d||0);scenarioMatrixState.maintain_capacity_nminus1=vals.scenario_maintain_capacity_nminus1!==false;await calculateScenarioMatrix();});}

// ============================================================================
// Total RO Design v0.25 Hotfix 1B
// Multi-pass / multistage / recycle user interface
// ============================================================================

function multiPassMaxPasses(){
  // Entry permits 3 passes. Silver+ permits 8.
  return tierAllows('multi_case') ? 8 : 3;
}

function defaultMultiPassStage(){
  return {
    membrane_id:'',
    vessels:'',
    elements_per_vessel:7,
    permeate_pressure:'',
    interstage_boost:''
  };
}

function defaultDownstreamPass(index){
  return {
    pass_id:`P${index+1}`,
    feed_basis:'pressure',
    feed_pressure:'',
    target_recovery_pct:'',
    pump_efficiency:0.85,
    motor_efficiency:0.97,
    vfd_efficiency:0.97,
    fouling_factor:1.0,
    salt_passage_factor:1.0,
    permeate_to_next_fraction:1.0,
    stages:[defaultMultiPassStage()]
  };
}

function activeMultiPassConfig(){
  const c=activeCaseData();

  if(!c)return {
    passes:[{pass_id:'P1',permeate_to_next_fraction:1.0}],
    recycles:[]
  };

  if(!c.multiPassConfig || typeof c.multiPassConfig!=='object'){
    c.multiPassConfig={
      passes:[
        {
          pass_id:'P1',
          permeate_to_next_fraction:1.0
        }
      ],
      recycles:[]
    };
  }

  if(!Array.isArray(c.multiPassConfig.passes) ||
     !c.multiPassConfig.passes.length){
    c.multiPassConfig.passes=[
      {
        pass_id:'P1',
        permeate_to_next_fraction:1.0
      }
    ];
  }

  if(!Array.isArray(c.multiPassConfig.recycles)){
    c.multiPassConfig.recycles=[];
  }

  c.multiPassConfig.passes.forEach((pass,i)=>{
    pass.pass_id=`P${i+1}`;

    if(pass.permeate_to_next_fraction===undefined){
      pass.permeate_to_next_fraction=1.0;
    }

    if(i>0){
      if(!Array.isArray(pass.stages)||!pass.stages.length){
        pass.stages=[defaultMultiPassStage()];
      }
    }
  });

  return c.multiPassConfig;
}

function markMultiPassStale(){
  const c=activeCaseData();
  if(c)c.multiPassResult=null;
}

function multiPassBaseState(){
  return modeStates.multistage||defaults.multistage||{};
}

function multiPassBaseResult(){
  return caseResults.multistage||null;
}

function multiPassPressureToBar(value){
  const n=Number(value);
  if(!Number.isFinite(n))return null;
  return Number(convert(n,'pressure',currentUnits.pressure,'bar'));
}

function multiPassFlowToM3h(value){
  const n=Number(value);
  if(!Number.isFinite(n))return null;
  return Number(convert(n,'flow',currentUnits.flow,'m3/h'));
}

function multiPassBaseStageCount(){
  const r=multiPassBaseResult();
  const s=multiPassBaseState();

  return Math.max(
    1,
    Math.min(
      4,
      Number(
        r?.stage_count||
        s?.stage_count||
        1
      )
    )
  );
}

function multiPassBaseStages(){
  const state=multiPassBaseState();
  const n=multiPassBaseStageCount();

  const out=[];

  for(let i=1;i<=n;i++){
    out.push({
      membrane_id:String(state[`membrane_${i}`]||''),
      vessels:Number(state[`vessels_${i}`]||0),
      elements_per_vessel:Number(
        state[`elements_per_vessel_${i}`]||7
      ),
      permeate_pressure_bar:
        multiPassPressureToBar(
          state[`permeate_pressure_${i}`] ??
          state.permeate_pressure ??
          0
        ) || 0,
      interstage_boost_bar:
        i===1 ? 0 :
        (
          multiPassPressureToBar(
            state[`interstage_boost_${i}`]||0
          ) || 0
        )
    });
  }

  return out;
}

function multiPassBasePassPayload(){
  const state=multiPassBaseState();
  const result=multiPassBaseResult();
  const cfg=activeMultiPassConfig();

  if(!result){
    throw new Error(
      'Calculate the current Plant Design first. '+
      'The converged Plant Design becomes Pass 1 of the multi-pass system.'
    );
  }

  const pressureRaw=
    result.membrane_pressure_1 ??
    result.solved_feed_pressure ??
    state.membrane_pressure_1;

  const pressureBar=multiPassPressureToBar(pressureRaw);

  if(!(pressureBar>0)){
    throw new Error(
      'Pass 1 does not have a valid converged membrane feed pressure.'
    );
  }

  return {
    pass_id:'P1',
    feed_pressure_bar:pressureBar,
    target_recovery:null,

    pump_efficiency:Number(
      result.pump_operating_efficiency ??
      result.pump_efficiency ??
      state.pump_eff ??
      0.85
    ),

    motor_efficiency:Number(
      result.motor_efficiency ??
      state.motor_eff ??
      0.97
    ),

    vfd_efficiency:Number(
      result.vfd_efficiency ??
      state.vfd_eff ??
      0.97
    ),

    fouling_factor:Number(
      state.fouling_factor||1
    ),

    salt_passage_factor:Number(
      state.salt_passage_factor||1
    ),

    permeate_to_next_fraction:Number(
      cfg.passes[0]?.permeate_to_next_fraction ?? 1
    ),

    stages:multiPassBaseStages()
  };
}

function multiPassExternalFeedPayload(){
  const result=multiPassBaseResult();
  const state=multiPassBaseState();

  if(!result){
    throw new Error(
      'Calculate Plant Design before calculating the multi-pass flowsheet.'
    );
  }

  const flowRaw=
    result.feed_flow ??
    state.feed_flow;

  const flow=multiPassFlowToM3h(flowRaw);

  if(!(flow>0)){
    throw new Error(
      'The converged Pass-1 external feed flow is unavailable.'
    );
  }

  const suctionBar=
    multiPassPressureToBar(
      state.suction_pressure ?? 1
    ) || 1;

  const composition=
    result.stage1_feed_composition_mg_l ||
    Object.fromEntries(
      Object.keys(chemistry)
        .filter(k=>k.startsWith('ion_'))
        .map(k=>[
          k.slice(4),
          Number(waterProfile[k]||0)
        ])
        .filter(([,v])=>v>0)
    );

  const hasComposition=
    composition &&
    Object.keys(composition).length>0;

  return {
    flow_m3h:flow,
    pressure_bar:suctionBar,
    temperature_c:Number(
      result.temperature_c ??
      waterProfile.temperature_c ??
      25
    ),
    tds_mg_l:Number(
      result.stage1_feed_tds_ppm ??
      waterProfile.analysis_tds ??
      waterProfile.feed_tds ??
      0
    ),
    ph:Number(
      result.stage1_feed_ph ??
      waterProfile.feed_ph ??
      7
    ),
    composition_mg_l:
      hasComposition ? composition : undefined
  };
}

function multiPassResizeStages(pass,count){
  const n=Math.max(
    1,
    Math.min(4,Number(count)||1)
  );

  if(!Array.isArray(pass.stages)){
    pass.stages=[];
  }

  while(pass.stages.length<n){
    pass.stages.push(defaultMultiPassStage());
  }

  if(pass.stages.length>n){
    pass.stages=pass.stages.slice(0,n);
  }
}

function multiPassBuildDownstreamPayload(pass,index){
  if(!Array.isArray(pass.stages)||!pass.stages.length){
    throw new Error(
      `Pass ${index+1} must contain at least one RO stage.`
    );
  }

  const stages=pass.stages.map((stage,j)=>{
    if(!stage.membrane_id){
      throw new Error(
        `Pass ${index+1} Stage ${j+1}: select a membrane.`
      );
    }

    const vessels=Number(stage.vessels);
    const epv=Number(stage.elements_per_vessel);

    if(!(vessels>0)){
      throw new Error(
        `Pass ${index+1} Stage ${j+1}: enter pressure vessels.`
      );
    }

    if(!(epv>=1&&epv<=8)){
      throw new Error(
        `Pass ${index+1} Stage ${j+1}: elements/vessel must be 1–8.`
      );
    }

    return {
      membrane_id:stage.membrane_id,
      vessels,
      elements_per_vessel:epv,

      permeate_pressure_bar:
        multiPassPressureToBar(
          stage.permeate_pressure||0
        ) || 0,

      interstage_boost_bar:
        j===0 ? 0 :
        (
          multiPassPressureToBar(
            stage.interstage_boost||0
          ) || 0
        )
    };
  });

  const basis=String(
    pass.feed_basis||'pressure'
  );

  let feedPressure=null;
  let targetRecovery=null;

  if(basis==='recovery'){
    const pct=Number(pass.target_recovery_pct);

    if(!(pct>0&&pct<98)){
      throw new Error(
        `Pass ${index+1}: target recovery must be between 0 and 98%.`
      );
    }

    targetRecovery=pct/100;

  }else{
    feedPressure=multiPassPressureToBar(
      pass.feed_pressure
    );

    if(!(feedPressure>0)){
      throw new Error(
        `Pass ${index+1}: enter a valid membrane feed pressure.`
      );
    }
  }

  return {
    pass_id:`P${index+1}`,
    feed_pressure_bar:feedPressure,
    target_recovery:targetRecovery,

    pump_efficiency:Number(
      pass.pump_efficiency||0.85
    ),

    motor_efficiency:Number(
      pass.motor_efficiency||0.97
    ),

    vfd_efficiency:Number(
      pass.vfd_efficiency||0.97
    ),

    fouling_factor:Number(
      pass.fouling_factor||1
    ),

    salt_passage_factor:Number(
      pass.salt_passage_factor||1
    ),

    permeate_to_next_fraction:Number(
      pass.permeate_to_next_fraction ?? 1
    ),

    stages
  };
}

function multiPassValidateSourceAllocations(recycles){
  const totals={};

  recycles.forEach(r=>{
    if(r.mode!=='fraction')return;

    const key=`${r.source_pass}:concentrate`;
    totals[key]=(totals[key]||0)+Number(r.fraction_pct||0);
  });

  Object.entries(totals).forEach(([key,total])=>{
    if(total>100.000001){
      throw new Error(
        `${key} recycle allocation is ${total.toFixed(1)}%. `+
        'Total source allocation cannot exceed 100%.'
      );
    }
  });
}

function multiPassBuildPayload(){
  const cfg=activeMultiPassConfig();

  if(cfg.passes.length<2){
    throw new Error(
      'Add at least one downstream RO pass before calculating a multi-pass system.'
    );
  }

  const passes=[
    multiPassBasePassPayload(),
    ...cfg.passes.slice(1).map(
      (p,i)=>multiPassBuildDownstreamPayload(p,i+1)
    )
  ];

  multiPassValidateSourceAllocations(
    cfg.recycles
  );

  const recycles=cfg.recycles.map((r,i)=>{
    const source=String(r.source_pass||'');
    const destination=String(r.destination_pass||'');

    const sourceIndex=
      passes.findIndex(p=>p.pass_id===source);

    const destinationIndex=
      passes.findIndex(p=>p.pass_id===destination);

    if(sourceIndex<=0){
      throw new Error(
        `Recycle R${i+1}: select a downstream source pass.`
      );
    }

    if(destinationIndex<0||
       destinationIndex>=sourceIndex){
      throw new Error(
        `Recycle R${i+1}: destination must be an upstream pass.`
      );
    }

    const row={
      link_id:`R${i+1}`,
      source_pass:source,
      source_port:'concentrate',
      destination_pass:destination,
      destination:'suction',
      enabled:true
    };

    if(r.mode==='absolute'){
      const q=Number(r.absolute_flow_m3h);

      if(!(q>=0)){
        throw new Error(
          `Recycle R${i+1}: enter a valid absolute recycle flow.`
        );
      }

      row.absolute_flow_m3h=q;

    }else{
      const pct=Number(r.fraction_pct);

      if(!(pct>=0&&pct<=100)){
        throw new Error(
          `Recycle R${i+1}: source fraction must be 0–100%.`
        );
      }

      row.fraction=pct/100;
    }

    return row;
  });

  return {
    external_feed:multiPassExternalFeedPayload(),
    passes,
    recycles,
    solver:'auto',
    max_iterations:40
  };
}

function multiPassStageEditorHtml(passIndex,stageIndex,stage){
  const n=stageIndex+1;

  return `
    <div class="mp-stage-card">
      <div class="mp-stage-title">
        <strong>Stage ${n}</strong>
        <span>Pass ${passIndex+1}</span>
      </div>

      <div class="grid mp-stage-grid">

        <div class="field">
          <label>Membrane</label>
          <div class="wrap">
            <select
              class="engineering-select membrane-select"
              data-mp-pass="${passIndex}"
              data-mp-stage="${stageIndex}"
              data-mp-stage-field="membrane_id">
              ${membraneOptions(stage.membrane_id)}
            </select>
          </div>
        </div>

        <div class="field">
          <label>Pressure vessels</label>
          <div class="wrap">
            <input
              type="number"
              min="1"
              step="1"
              value="${escapeHtml(String(stage.vessels??''))}"
              data-mp-pass="${passIndex}"
              data-mp-stage="${stageIndex}"
              data-mp-stage-field="vessels">
          </div>
        </div>

        <div class="field">
          <label>Elements / vessel</label>
          <div class="wrap">
            <input
              type="number"
              min="1"
              max="8"
              step="1"
              value="${escapeHtml(String(stage.elements_per_vessel??7))}"
              data-mp-pass="${passIndex}"
              data-mp-stage="${stageIndex}"
              data-mp-stage-field="elements_per_vessel">
          </div>
        </div>

        <div class="field">
          <label>Permeate backpressure</label>
          <div class="wrap">
            <input
              type="number"
              step="any"
              value="${escapeHtml(String(stage.permeate_pressure??0))}"
              data-mp-pass="${passIndex}"
              data-mp-stage="${stageIndex}"
              data-mp-stage-field="permeate_pressure">
            <span class="suffix">${escapeHtml(currentUnits.pressure)}</span>
          </div>
        </div>

        ${stageIndex>0 ? `
          <div class="field">
            <label>Interstage boost</label>
            <div class="wrap">
              <input
                type="number"
                min="0"
                step="any"
                value="${escapeHtml(String(stage.interstage_boost??0))}"
                data-mp-pass="${passIndex}"
                data-mp-stage="${stageIndex}"
                data-mp-stage-field="interstage_boost">
              <span class="suffix">${escapeHtml(currentUnits.pressure)}</span>
            </div>
          </div>
        `:''}

      </div>
    </div>
  `;
}

function multiPassDownstreamPassHtml(pass,index,totalPasses){
  const basis=String(pass.feed_basis||'pressure');

  return `
    <article class="mp-pass-card">
      <div class="mp-pass-header">
        <div>
          <span class="mp-pass-number">PASS ${index+1}</span>
          <strong>Downstream RO array</strong>
          <small>
            Feed: routed permeate from Pass ${index}
          </small>
        </div>

        ${index===totalPasses-1 ? `
          <button
            type="button"
            class="ghost"
            data-mp-remove-pass="1">
            − Remove pass
          </button>
        `:''}
      </div>

      <div class="grid mp-pass-basis-grid">

        <div class="field">
          <label>Number of RO stages</label>
          <div class="wrap">
            <select
              class="engineering-select"
              data-mp-pass="${index}"
              data-mp-field="stage_count">
              ${[1,2,3,4].map(n=>`
                <option value="${n}"
                  ${pass.stages?.length===n?'selected':''}>
                  ${n} stage${n===1?'':'s'}
                </option>
              `).join('')}
            </select>
          </div>
        </div>

        <div class="field">
          <label>Operating basis</label>
          <div class="wrap">
            <select
              class="engineering-select"
              data-mp-pass="${index}"
              data-mp-field="feed_basis">
              <option value="pressure"
                ${basis==='pressure'?'selected':''}>
                Feed pressure
              </option>
              <option value="recovery"
                ${basis==='recovery'?'selected':''}>
                Target recovery
              </option>
            </select>
          </div>
        </div>

        ${basis==='recovery' ? `
          <div class="field">
            <label>Target pass recovery</label>
            <div class="wrap">
              <input
                type="number"
                min="0.1"
                max="97.9"
                step="0.1"
                value="${escapeHtml(String(pass.target_recovery_pct??''))}"
                data-mp-pass="${index}"
                data-mp-field="target_recovery_pct">
              <span class="suffix">%</span>
            </div>
          </div>
        ` : `
          <div class="field">
            <label>Membrane feed pressure</label>
            <div class="wrap">
              <input
                type="number"
                step="any"
                value="${escapeHtml(String(pass.feed_pressure??''))}"
                data-mp-pass="${index}"
                data-mp-field="feed_pressure">
              <span class="suffix">${escapeHtml(currentUnits.pressure)}</span>
            </div>
          </div>
        `}

        ${index<totalPasses-1 ? `
          <div class="field">
            <label>Permeate sent to next pass</label>
            <div class="wrap">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value="${escapeHtml(String(
                  100*Number(pass.permeate_to_next_fraction??1)
                ))}"
                data-mp-pass="${index}"
                data-mp-field="route_fraction_pct">
              <span class="suffix">%</span>
            </div>
          </div>
        `:''}

        <div class="field">
          <label>Pump efficiency</label>
          <div class="wrap">
            <input
              type="number"
              min="0.1"
              max="1"
              step="0.001"
              value="${escapeHtml(String(pass.pump_efficiency??0.85))}"
              data-mp-pass="${index}"
              data-mp-field="pump_efficiency">
            <span class="suffix">fraction</span>
          </div>
        </div>

        <div class="field">
          <label>Motor efficiency</label>
          <div class="wrap">
            <input
              type="number"
              min="0.1"
              max="1"
              step="0.001"
              value="${escapeHtml(String(pass.motor_efficiency??0.97))}"
              data-mp-pass="${index}"
              data-mp-field="motor_efficiency">
            <span class="suffix">fraction</span>
          </div>
        </div>

        <div class="field">
          <label>Fouling factor · A</label>
          <div class="wrap">
            <input
              type="number"
              min="0.3"
              max="1.2"
              step="0.01"
              value="${escapeHtml(String(pass.fouling_factor??1))}"
              data-mp-pass="${index}"
              data-mp-field="fouling_factor">
          </div>
        </div>

        <div class="field">
          <label>Salt passage factor · B</label>
          <div class="wrap">
            <input
              type="number"
              min="0.1"
              max="5"
              step="0.01"
              value="${escapeHtml(String(pass.salt_passage_factor??1))}"
              data-mp-pass="${index}"
              data-mp-field="salt_passage_factor">
          </div>
        </div>

      </div>

      <div class="mp-stage-list">
        ${(pass.stages||[]).map(
          (stage,j)=>multiPassStageEditorHtml(index,j,stage)
        ).join('')}
      </div>

    </article>
  `;
}

function multiPassRecycleHtml(cfg){
  if(cfg.passes.length<2){
    return `
      <div class="mp-empty-state">
        Add a downstream pass before configuring recycle.
      </div>
    `;
  }

  if(!tierAllows('advanced_recycle')){
    return `
      <div class="mp-tier-note">
        Recycle connections are available from the Silver tier.
        Multi-pass RO without recycle remains available.
      </div>
    `;
  }

  const rows=cfg.recycles.map((r,i)=>{
    const sourceIndex=Math.max(
      1,
      cfg.passes.findIndex(
        p=>p.pass_id===r.source_pass
      )
    );

    const sourceOptions=
      cfg.passes.slice(1).map((p,j)=>{
        const idx=j+1;
        return `
          <option value="P${idx+1}"
            ${r.source_pass===`P${idx+1}`?'selected':''}>
            Pass ${idx+1} concentrate
          </option>
        `;
      }).join('');

    const destinationOptions=
      cfg.passes.slice(0,Math.max(1,sourceIndex))
        .map((p,j)=>`
          <option value="P${j+1}"
            ${r.destination_pass===`P${j+1}`?'selected':''}>
            Pass ${j+1} HPP suction / feed mixer
          </option>
        `).join('');

    return `
      <article class="mp-recycle-row">
        <div class="mp-recycle-name">
          <strong>R${i+1}</strong>
          <span>Recycle connection</span>
        </div>

        <div class="grid mp-recycle-grid">

          <div class="field">
            <label>Source</label>
            <div class="wrap">
              <select
                class="engineering-select"
                data-mp-recycle="${i}"
                data-mp-recycle-field="source_pass">
                ${sourceOptions}
              </select>
            </div>
          </div>

          <div class="field">
            <label>Destination</label>
            <div class="wrap">
              <select
                class="engineering-select"
                data-mp-recycle="${i}"
                data-mp-recycle-field="destination_pass">
                ${destinationOptions}
              </select>
            </div>
          </div>

          <div class="field">
            <label>Specification</label>
            <div class="wrap">
              <select
                class="engineering-select"
                data-mp-recycle="${i}"
                data-mp-recycle-field="mode">
                <option value="fraction"
                  ${r.mode!=='absolute'?'selected':''}>
                  Fraction of source
                </option>
                <option value="absolute"
                  ${r.mode==='absolute'?'selected':''}>
                  Absolute flow
                </option>
              </select>
            </div>
          </div>

          ${r.mode==='absolute' ? `
            <div class="field">
              <label>Recycle flow</label>
              <div class="wrap">
                <input
                  type="number"
                  min="0"
                  step="any"
                  value="${escapeHtml(String(r.absolute_flow_m3h??''))}"
                  data-mp-recycle="${i}"
                  data-mp-recycle-field="absolute_flow_m3h">
                <span class="suffix">m³/h</span>
              </div>
            </div>
          ` : `
            <div class="field">
              <label>Source recycled</label>
              <div class="wrap">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value="${escapeHtml(String(r.fraction_pct??100))}"
                  data-mp-recycle="${i}"
                  data-mp-recycle-field="fraction_pct">
                <span class="suffix">%</span>
              </div>
            </div>
          `}

        </div>

        <div class="mp-recycle-footer">
          <span>
            Pressure handling:
            <strong>throttle to receiving HPP suction pressure</strong>
          </span>

          <button
            type="button"
            class="ghost"
            data-mp-remove-recycle="${i}">
            Remove
          </button>
        </div>
      </article>
    `;
  }).join('');

  return `
    ${rows || `
      <div class="mp-empty-state">
        No recycle connections configured.
      </div>
    `}

    <button
      type="button"
      class="ghost mp-add-recycle"
      data-mp-add-recycle="1">
      + Add recycle
    </button>

    <p class="micro-note">
      v0.25 Hotfix 1B currently validates recycle to an upstream
      pass HPP suction / feed mixer. Interstage recycle destinations
      remain disabled until their hydraulic implementation is qualified.
    </p>
  `;
}

function multiPassResultHtml(result){
  if(!result)return '';

  const passes=result.passes||{};
  const recycles=result.recycles||{};

  const passRows=Object.entries(passes).map(([id,p])=>`
    <tr>
      <td><strong>${escapeHtml(id)}</strong></td>
      <td>${fmt(p.suction?.flow_m3h,2)}</td>
      <td>${fmt(p.membrane_feed?.pressure_bar,2)}</td>
      <td>${fmt(p.permeate?.flow_m3h,2)}</td>
      <td>${fmt(p.permeate?.tds_mg_l,2)}</td>
      <td>${fmt(p.concentrate?.flow_m3h,2)}</td>
      <td>${fmt(p.concentrate?.tds_mg_l,2)}</td>
      <td>${fmt(p.hpp_power_kw,2)}</td>
    </tr>
  `).join('');

  const recycleRows=Object.entries(recycles).map(([id,r])=>`
    <tr>
      <td><strong>${escapeHtml(id)}</strong></td>
      <td>${fmt(r.flow_m3h,2)}</td>
      <td>${fmt(r.tds_mg_l,2)}</td>
      <td>${fmt(r.pressure_bar,2)}</td>
    </tr>
  `).join('');

  return `
    <div class="mp-result-panel">
      <div class="kpi-strip five">
        <div>
          <span>Status</span>
          <strong>${result.converged?'Converged':'Not converged'}</strong>
        </div>
        <div>
          <span>Iterations</span>
          <strong>${result.iterations??'—'}</strong>
        </div>
        <div>
          <span>Residual</span>
          <strong>${Number(result.residual_norm||0).toExponential(2)}</strong>
        </div>
        <div>
          <span>Overall recovery</span>
          <strong>${fmt(100*Number(result.overall_recovery||0),2)}%</strong>
        </div>
        <div>
          <span>Water closure</span>
          <strong>${fmt(result.water_closure_m3h,6)} m³/h</strong>
        </div>
      </div>

      <div class="table-wrap">
        <table class="fedco-table">
          <thead>
            <tr>
              <th>Pass</th>
              <th>HPP suction<br>m³/h</th>
              <th>Feed pressure<br>bar</th>
              <th>Permeate<br>m³/h</th>
              <th>Permeate TDS<br>mg/L</th>
              <th>Concentrate<br>m³/h</th>
              <th>Concentrate TDS<br>mg/L</th>
              <th>Pump power<br>kW</th>
            </tr>
          </thead>
          <tbody>${passRows}</tbody>
        </table>
      </div>

      ${recycleRows ? `
        <div class="table-wrap">
          <table class="fedco-table">
            <thead>
              <tr>
                <th>Recycle</th>
                <th>Flow<br>m³/h</th>
                <th>TDS<br>mg/L</th>
                <th>Pressure<br>bar</th>
              </tr>
            </thead>
            <tbody>${recycleRows}</tbody>
          </table>
        </div>
      `:''}
    </div>
  `;
}

function multiPassEditorHtml(){
  const cfg=activeMultiPassConfig();
  const base=multiPassBaseResult();
  const n=multiPassBaseStageCount();
  const max=multiPassMaxPasses();
  const c=activeCaseData();

  const p1=cfg.passes[0];

  return `
    <section class="input-section multipass-section">

      <div class="section-inline-title">
        <div>
          <h3>MULTI-PASS RO & RECYCLE</h3>
          <p class="micro-note">
            A pass is an independent RO array. Each pass may contain
            1–4 serial RO stages. Pass 1 is the current converged Plant
            Design; downstream passes are configured here.
          </p>
        </div>

        <div class="mp-toolbar">
          <span>
            ${cfg.passes.length} / ${max} passes
          </span>

          <button
            type="button"
            class="ghost"
            data-mp-add-pass="1"
            ${cfg.passes.length>=max?'disabled':''}>
            + Add pass
          </button>
        </div>
      </div>

      <article class="mp-pass-card mp-pass-primary">
        <div class="mp-pass-header">
          <div>
            <span class="mp-pass-number">PASS 1</span>
            <strong>Current Plant Design</strong>
            <small>
              ${n} RO stage${n===1?'':'s'} ·
              ${base?'converged':'calculate Plant Design first'}
            </small>
          </div>

          <span class="status-chip ${base?'ok':'review'}">
            ${base?'Ready':'Not calculated'}
          </span>
        </div>

        ${cfg.passes.length>1 ? `
          <div class="grid mp-pass-basis-grid">
            <div class="field">
              <label>Pass-1 permeate sent to Pass 2</label>
              <div class="wrap">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value="${escapeHtml(String(
                    100*Number(p1.permeate_to_next_fraction??1)
                  ))}"
                  data-mp-pass="0"
                  data-mp-field="route_fraction_pct">
                <span class="suffix">%</span>
              </div>
              <div class="field-hint">
                The balance bypasses downstream treatment and remains
                an exported product/blend stream.
              </div>
            </div>
          </div>
        `:''}
      </article>

      ${cfg.passes.slice(1).map(
        (p,i)=>multiPassDownstreamPassHtml(
          p,
          i+1,
          cfg.passes.length
        )
      ).join('')}

      <div class="mp-subsection">
        <div class="section-inline-title">
          <div>
            <h3>RECYCLE CONNECTIONS</h3>
            <p class="micro-note">
              Select where the recycle originates, where it returns,
              and how much of the source stream is recycled.
            </p>
          </div>
        </div>

        ${multiPassRecycleHtml(cfg)}
      </div>

      <div class="mp-feature-boundary">
        <strong>Engineering boundary</strong>
        <span>
          Split-partial permeate hydraulic zones and arbitrary
          interstage recycle destinations remain disabled until
          their coupled hydraulic models complete qualification.
        </span>
      </div>

      <div class="mp-calc-row">
        <button
          type="button"
          id="multiPassCalculateBtn"
          class="ghost mp-calculate-secondary"
          data-mp-calculate="1"
          ${cfg.passes.length<2?'disabled hidden aria-hidden="true"':'aria-hidden="false"'}>
          <span class="calc-btn-label">
            Calculate multi-pass flowsheet
          </span>
          <span class="button-arrow">→</span>
        </button>
      </div>

      <div id="multiPassResult">
        ${multiPassResultHtml(c?.multiPassResult)}
      </div>

    </section>
  `;
}

function bindMultiPassEditor(){
  const cfg=activeMultiPassConfig();
  const root=document.querySelector('.multipass-section');

  if(!root)return;

  root.querySelector('[data-mp-add-pass]')?.addEventListener(
    'click',
    ()=>{
      if(cfg.passes.length>=multiPassMaxPasses())return;

      cfg.passes.push(
        defaultDownstreamPass(cfg.passes.length)
      );

      markMultiPassStale();
      renderFields(
        modeStates.multistage||defaults.multistage
      );
    }
  );

  root.querySelector('[data-mp-remove-pass]')?.addEventListener(
    'click',
    ()=>{
      if(cfg.passes.length<=1)return;

      const removed=cfg.passes.pop()?.pass_id;

      cfg.recycles=cfg.recycles.filter(
        r=>
          r.source_pass!==removed &&
          r.destination_pass!==removed
      );

      markMultiPassStale();

      renderFields(
        modeStates.multistage||defaults.multistage
      );
    }
  );

  root.querySelectorAll('[data-mp-field]').forEach(el=>{
    const eventName=
      el.tagName==='SELECT' ? 'change' : 'change';

    el.addEventListener(eventName,()=>{
      const i=Number(el.dataset.mpPass);
      const field=el.dataset.mpField;
      const pass=cfg.passes[i];

      if(!pass)return;

      if(field==='stage_count'){
        multiPassResizeStages(
          pass,
          Number(el.value)
        );

        markMultiPassStale();

        renderFields(
          modeStates.multistage||defaults.multistage
        );

        return;
      }

      if(field==='feed_basis'){
        pass.feed_basis=el.value;

        markMultiPassStale();

        renderFields(
          modeStates.multistage||defaults.multistage
        );

        return;
      }

      if(field==='route_fraction_pct'){
        pass.permeate_to_next_fraction=
          Number(el.value||0)/100;

      }else{
        pass[field]=el.value;
      }

      markMultiPassStale();
    });
  });

  root.querySelectorAll('[data-mp-stage-field]').forEach(el=>{
    el.addEventListener('change',()=>{
      const i=Number(el.dataset.mpPass);
      const j=Number(el.dataset.mpStage);
      const field=el.dataset.mpStageField;

      const stage=cfg.passes[i]?.stages?.[j];

      if(!stage)return;

      stage[field]=el.value;
      markMultiPassStale();
    });
  });

  root.querySelector('[data-mp-add-recycle]')?.addEventListener(
    'click',
    ()=>{
      if(!tierAllows('advanced_recycle'))return;
      if(cfg.passes.length<2)return;

      const source=`P${cfg.passes.length}`;

      cfg.recycles.push({
        source_pass:source,
        destination_pass:'P1',
        mode:'fraction',
        fraction_pct:100,
        absolute_flow_m3h:''
      });

      markMultiPassStale();

      renderFields(
        modeStates.multistage||defaults.multistage
      );
    }
  );

  root.querySelectorAll('[data-mp-remove-recycle]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      cfg.recycles.splice(
        Number(btn.dataset.mpRemoveRecycle),
        1
      );

      markMultiPassStale();

      renderFields(
        modeStates.multistage||defaults.multistage
      );
    });
  });

  root.querySelectorAll('[data-mp-recycle-field]').forEach(el=>{
    el.addEventListener('change',()=>{
      const i=Number(el.dataset.mpRecycle);
      const field=el.dataset.mpRecycleField;
      const row=cfg.recycles[i];

      if(!row)return;

      row[field]=el.value;

      if(field==='source_pass'){
        const srcIndex=
          cfg.passes.findIndex(
            p=>p.pass_id===el.value
          );

        if(
          cfg.passes.findIndex(
            p=>p.pass_id===row.destination_pass
          ) >= srcIndex
        ){
          row.destination_pass='P1';
        }
      }

      markMultiPassStale();

      if(
        field==='source_pass' ||
        field==='mode'
      ){
        renderFields(
          modeStates.multistage||defaults.multistage
        );
      }
    });
  });

  root.querySelector('[data-mp-calculate]')?.addEventListener(
    'click',
    runMultiPassFlowsheet
  );
}

async function runMultiPassFlowsheet(){
  if(!casePlantIsValid()){
    showCalcError(
      new Error(
        'Calculate the current Plant Design first. '+
        'Pass 1 must be a valid converged Plant Design.'
      ),
      'multi-pass'
    );
    return;
  }

  const button=document.querySelector(
    '[data-mp-calculate]'
  );

  try{
    if(button){
      button.disabled=true;
      button.querySelector('.calc-btn-label').textContent=
        'Solving multi-pass flowsheet…';
    }

    const payload=multiPassBuildPayload();

    const result=await requestJson(
      '/api/flowsheet/solve',
      {
        method:'POST',
        headers:{
          'Content-Type':'application/json'
        },
        body:JSON.stringify(payload)
      },
      'Multi-pass flowsheet calculation failed'
    );

    const c=activeCaseData();

    if(c){
      c.multiPassResult=deepClone(result);
    }

    const host=$('#multiPassResult');

    if(host){
      host.innerHTML=multiPassResultHtml(result);
    }

  }catch(err){
    showCalcError(
      err,
      'multi-pass flowsheet'
    );

  }finally{
    if(button){
      button.disabled=false;
      button.querySelector('.calc-btn-label').textContent=
        'Calculate multi-pass flowsheet';
    }
  }
}


function renderFields(values=defaults[mode]){const cb=$('#calculateBtn');if(cb)cb.hidden=(mode==='advanced');if(mode==='water'){renderWaterTab();return;}if(mode==='advanced'){renderAdvancedDesignTab();return;}if(mode==='envelope'){renderEnvelopeTab();return;}if(mode==='scenario'){renderScenarioMatrixTab();return;}if(mode==='comparison'){renderComparisonTab();return;}if(mode==='summary'){renderSummaryTab();return;}if(mode==='economic'){renderEconomicTab();return;}const root=$('#fields');const generalizedBt=mode==='biturbo'&&(Boolean(values?.generalized_biturbo)||Number(values?.stage_count||2)>2);const generalizedInterstage=mode==='interstage'&&(Boolean(values?.generalized_interstage_turbo)||Number(values?.stage_count||2)>2);root.innerHTML=`<input type="hidden" name="solve_basis" value="${values.solve_basis||defaults[mode].solve_basis||'recovery'}">${mode==='multistage'?'<input type="hidden" name="membrane_coupling" value="on">':''}${generalizedBt?`<input type="hidden" name="stage_count" value="${Number(values.stage_count||3)}"><input type="hidden" name="generalized_biturbo" value="1">`:''}${generalizedInterstage?`<input type="hidden" name="stage_count" value="${Number(values.stage_count||3)}"><input type="hidden" name="generalized_interstage_turbo" value="1">`:''}${(generalizedBt||generalizedInterstage)?'':turboDesignDutyHtml()}`;sections(values).forEach(([title,fields])=>{const section=document.createElement('section');section.className='input-section'+(title.startsWith('Full water')?' chemistry-section':'')+(title.includes('membrane train')?' stage-membrane-section':'');if(title.startsWith('Full water'))section.dataset.chemistrySection='1';section.innerHTML=`<h3>${title}</h3><div class="grid"></div>`;const grid=section.querySelector('.grid');Object.entries(fields).forEach(([k,f])=>{const el=document.createElement('div');el.className='field '+numericInputSize(k,f);if(SILVER_PUMP_FIELDS.has(k))el.dataset.tierFieldFeature='vcmp_pump_selection';if(['max_design_flux_lmh','required_capacity_m3d'].includes(k))el.dataset.tierFieldFeature='auto_design';let val=f.linkedWater?(waterProfile[k]??values[k]??''):(f.linkedHppInlet?(values.suction_pressure??''):(values[k]??''));let suffix=f.type==='toggle'?'':(f.suffix|| (f.type==='percent'?'fraction':unitFor(f.type)));const arrows=f.solveTarget?solveArrowHtml():'';const mandatory=needsManualEntry(k,f)?'<div class="mandatory-note" hidden>Mandatory field</div>':'';const hint=f.hint?`<div class="field-hint">${escapeHtml(f.hint)}</div>`:'';el.innerHTML=`<label>${fieldLabelHtml(f)}${arrows}</label>${mandatory}<div class="wrap">${inputHtml(k,f,val)}${suffix?`<span class="suffix">${suffix}</span>`:''}</div>${hint}`;if(needsManualEntry(k,f))el.dataset.manualEntry='1';if(f.manualReject)el.dataset.manualReject='1';if(f.motorOnly)el.dataset.motorOnly='1';if(f.solveTarget)el.dataset.solveTarget='1';if(f.solvePressure)el.dataset.solvePressure='1';if(f.solveRecovery)el.dataset.solveRecovery='1';if(f.chemistryOnly)el.dataset.chemistryOnly='1';if(f.tdsOnly)el.dataset.tdsOnly='1';if(k==='px_model')el.dataset.passiveOnly='1';if(f.linkedWater)el.dataset.linkedWater='1';if(f.type==='membrane')el.classList.add('membrane-field');grid.appendChild(el)});if(mode==='multistage'&&title==='Hydraulic conditions')section.insertAdjacentHTML('beforeend',averageDesignFluxHtml(values));const sm=title.match(/^Stage (\d+) membrane train/);if(sm)section.insertAdjacentHTML('beforeend',hybridRecipeEditorHtml(Number(sm[1]),values));root.appendChild(section)});if(['multistage','interstage_px','interstage','biturbo','px','dweer','pelton'].includes(mode))root.insertAdjacentHTML('beforeend',interstageTurboPreviewHtml(values));if(mode==='multistage'){
  root.insertAdjacentHTML(
    'beforeend',
    baseSeedStatusHtml()
  );

  root.insertAdjacentHTML(
    'beforeend',
    multiPassEditorHtml(values)
  );

  bindMultiPassEditor();
}const modeName={multistage:'RO Plant Designer',single:'Single Stage Turbo Charger',px:'Single Stage Isobaric Chamber',interstage_px:'Interstage Isobaric Chamber',interstage:'Interstage Turbocharger',biturbo:'BiTurbo™',dweer:'DWEER',pelton:'Pelton Turbine'}[mode];$('#modeLabel').textContent=`${modeName} · Case ${activeCase}`;bindDynamic();bindHybridRecipeEditors();$('#turboDesignBtn')?.addEventListener('click',async()=>{try{await runTurboDesignEnvelope(mode)}catch(e){showCalcError(e,mode)}});updateCouplingVisibility();updateWaterModeVisibility();updatePxVisibility();syncBwpxHeaderTolerance();updateBwpxBankVisibility();updateInterstageControlVisibility();updateSolveUI();updateRequiredFieldStates();applyTierEntitlements();updateAutoDesignFieldVisibility()}
function syncBwpxHeaderTolerance(){
  const suction=document.querySelector('[name="suction_pressure"]'),tol=document.querySelector('[name="bwpx_header_tolerance_bar"]');
  if(suction&&tol)tol.value=suction.value;
}
function updateBwpxBankVisibility(){
  const auto=document.querySelector('[name="bwpx_auto_size"]'),qty=document.querySelector('[name="bwpx_qty"]');
  if(!auto||!qty)return;const isAuto=!!auto.checked;qty.readOnly=isAuto;qty.setAttribute('aria-readonly',String(isAuto));qty.closest('.field')?.classList.toggle('dimmed',isAuto);
}
function updatePumpCurveVisibility(){
  if(mode!=='multistage')return;const manual=document.querySelector('[name="pump_curve_basis"]')?.value==='manual';
  ['pump_bep_flow','pump_bep_dp'].forEach(k=>{const f=document.querySelector(`[name="${k}"]`)?.closest('.field');if(f)f.style.display=manual?'':'none';});
}
function updateInterstageControlVisibility(){
  const objective=document.querySelector('[name="interstage_control_objective"]')?.value||'manual';
  const balance=document.querySelector('[name="interstage_balance_basis"]')?.closest('.field');
  if(balance)balance.style.display=(objective==='balance_flux'||objective==='balance_polarization')?'':'none';
  for(let i=2;i<=4;i++){
    const eq=document.querySelector(`[name="interstage_equipment_${i}"]`)?.value||'none';
    const boost=document.querySelector(`[name="interstage_boost_${i}"]`),bf=boost?.closest('.field');
    const target=document.querySelector(`[name="interstage_target_recovery_${i}"]`),tf=target?.closest('.field');
    const maxe=document.querySelector(`[name="interstage_maximize_turbo_energy_${i}"]`),mf=maxe?.closest('.field');
    if(tf)tf.style.display=(objective==='target_recovery'&&eq!=='none')?'':'none';
    if(mf)mf.style.display=(eq==='turbo'||eq==='turbo_pump')?'':'none';
    if(boost){boost.readOnly=objective!=='manual';boost.setAttribute('aria-readonly',String(objective!=='manual'));if(bf)bf.classList.toggle('dimmed',objective!=='manual');if(objective!=='manual')boost.placeholder='Calculated on Run';}
  }
}
function interstageTurboPreviewHtml(values){
  const src=caseResults.multistage;if(!src)return '';const n=Math.max(1,Math.min(4,Number(values?.stage_count||src.stage_count||1)));if(n<2)return '';
  const qtrRaw=Number(src.reject_flow_final??src[`reject_flow_${n}`]),pRaw=Number(src[`reject_pressure_${n}`]);if(!Number.isFinite(qtrRaw)||!Number.isFinite(pRaw))return '';
  const qtr=convert(qtrRaw,'flow',src.flow_unit||currentUnits.flow,'m3/h'),pfin=convert(pRaw,'pressure',src.pressure_unit||currentUnits.pressure,'bar'),back=convert(Number(values?.multistage_turbo_backpressure??src.multistage_turbo_backpressure??1.5),'pressure',currentUnits.pressure,'bar'),eta=Number(values?.multistage_turbo_efficiency??src.multistage_turbo_efficiency_assumed??0.80);
  const cards=[];let turboCount=0;
  for(let i=2;i<=n;i++){const eq=String(values?.[`interstage_equipment_${i}`]||'none');if(!['turbo','turbo_pump'].includes(eq))continue;turboCount++;const qpfRaw=Number(src[`reject_flow_${i-1}`]);if(!(qpfRaw>0))continue;const qpf=convert(qpfRaw,'flow',src.flow_unit||currentUnits.flow,'m3/h'),rr=qtr/qpf,hyd=qtr*Math.max(0,pfin-back)/36*eta,boost=hyd*36/Math.max(qpf,1e-12),status=rr<=.20?'NOT AVAILABLE':(rr>=.65&&rr<=.70?'PEAK MATCH':rr<.50?'POOR MATCH':'AVAILABLE');const cls=rr<=.20?'bad':(rr>=.65&&rr<=.70?'ok':'');cards.push(`<div class="check-card"><strong>Stage ${i-1} → ${i} turbo preview</strong><span>Qpf ${fmt(convert(qpf,'flow','m3/h',currentUnits.flow),1)} ${currentUnits.flow} · Qtr ${fmt(convert(qtr,'flow','m3/h',currentUnits.flow),1)} ${currentUnits.flow}</span><span>Reject ratio <b>${fmt(rr,3)}</b> · <b class="${cls}">${status}</b></span><span>Recoverable hydraulic power ≈ ${fmt(hyd,1)} kW</span><span>Estimated maximum boost ≈ <b>${fmt(convert(boost,'pressure','bar',currentUnits.pressure),2)} ${currentUnits.pressure}</b></span></div>`);}
  if(!cards.length)return '';return `<section class="input-section turbo-preview-section"><h3>PRE-CALCULATION TURBO HYDRAULIC AVAILABILITY</h3><div class="check-grid">${cards.join('')}</div><p class="micro-note">Preview uses the last converged Base Plant final-reject flow/pressure and the current turbo efficiency assumption. ${turboCount>1?'Multiple turbochargers share the same final-reject hydraulic-energy pool; the individual maximum-boost values above are stand-alone availability indicators and are not additive. ':''}The final coupled calculation remains authoritative because boost changes membrane recovery, reject flow and available turbine power.</p></section>`;}
function bindDynamic(){
  const c=document.querySelector('[name="membrane_coupling"]');if(c)c.addEventListener('change',()=>{updateCouplingVisibility();updateWaterModeVisibility();updateSolveUI();updateRejectFlowMode();updateMassBalancePreview();updateRequiredFieldStates()});
  const p=document.querySelector('[name="px_architecture"]');if(p)p.addEventListener('change',()=>{updatePxVisibility();updateRequiredFieldStates()});const ba=document.querySelector('[name="bwpx_auto_size"]');if(ba)ba.addEventListener('change',()=>{updateBwpxBankVisibility();updateRequiredFieldStates()});const sp=document.querySelector('[name="suction_pressure"]');if(sp){['input','change'].forEach(evt=>sp.addEventListener(evt,syncBwpxHeaderTolerance));}
  const pc=document.querySelector('[name="pump_curve_basis"]');if(pc)pc.addEventListener('change',updatePumpCurveVisibility);const ico=document.querySelector('[name="interstage_control_objective"]');if(ico)ico.addEventListener('change',updateInterstageControlVisibility);document.querySelectorAll('[name^="interstage_equipment_"]').forEach(x=>x.addEventListener('change',updateInterstageControlVisibility));
  const w=document.querySelector('[name="water_mode"]');if(w)w.addEventListener('change',updateWaterModeVisibility);const dm=document.querySelector('[name="design_mode"]');if(dm)dm.addEventListener('change',()=>{updateAutoDesignFieldVisibility();updateSolveUI();updateRequiredFieldStates();});
  document.querySelectorAll('.solve-arrow').forEach(b=>b.addEventListener('click',()=>setSolveBasis(b.dataset.solve)));
  document.querySelectorAll('input[type=checkbox]').forEach(b=>b.addEventListener('change',()=>{updateVfdToggles();updateRequiredFieldStates()}));
  document.querySelectorAll('[data-membrane-select="1"]').forEach(sel=>sel.addEventListener('change',()=>refreshMembraneDescription(sel)));
  document.querySelectorAll('#fields input,#fields select').forEach(el=>{
    if(el.type==='checkbox')return;
    ['input','change','blur'].forEach(evt=>el.addEventListener(evt,()=>{
      if(mode==='multistage'&&evt==='change')markBaseSeedStale('Plant Design input changed');
      if(el.closest('[data-linked-water="1"]')){
        const raw=String(el.value??'').trim();const n=Number(raw);waterProfile[el.name]=raw===''?'':(Number.isFinite(n)?n:el.value);lastChemistryResult=null;syncActiveCaseStore();
      }
      if(isAutoPlantDesign())updateAutoDesignHydraulics();updateMassBalancePreview();updateAverageDesignFluxIndicator();updateRequiredFieldStates();if(evt==='change')markTurboDesignStale();
      if(isAutoPlantDesign()&&evt==='change'&&el.name!=='membrane_pressure_1'){const ap=document.querySelector('[name="membrane_pressure_1"]');if(ap)ap.value='';}if((mode==='multistage'&&(el.name==='stage_count'||el.name==='design_mode')||el.name?.startsWith('elements_per_vessel_'))&&evt==='change'){const vals=capture();if(el.name==='design_mode'&&el.value==='auto'){vals.solve_basis='recovery';vals.membrane_pressure_1='';vals.feed_flow='';vals.target_product_flow='';}modeStates.multistage={...vals};renderFields(vals);}
    }));
  });
  updateVfdToggles();updateRejectFlowMode();updateMassBalancePreview();updateAverageDesignFluxIndicator();updatePumpCurveVisibility();updateInterstageControlVisibility();updateRequiredFieldStates();
}
function updateVfdToggles(){
  const pairs=[['pretreatment_no_vfd','pretreatment_vfd_eff'],['pump_no_vfd','vfd_eff'],['booster_no_vfd','booster_vfd_eff'],['circ_no_vfd','circ_vfd_eff']];
  pairs.forEach(([toggleName,effName])=>{const t=document.querySelector(`[name="${toggleName}"]`),e=document.querySelector(`[name="${effName}"]`);if(!t||!e)return;const off=!!t.checked;e.disabled=off;e.closest('.field')?.classList.toggle('dimmed',off);e.setAttribute('aria-disabled',String(off));});
}
function setSolveBasis(basis){
  if(isAutoPlantDesign()){updateSolveUI();return;}
  const hidden=document.querySelector('[name="solve_basis"]');
  if(!hidden)return;
  const coupled=mode==='multistage'||document.querySelector('[name="membrane_coupling"]')?.value==='on';
  if((basis==='product'||basis==='recovery')&&!coupled)return;
  const q=document.querySelector('[name="target_product_flow"]');
  const p=document.querySelector('[name="membrane_pressure_1"]');
  const r=document.querySelector('[name="target_recovery"]');
  // Seed the newly selected setpoint from the last converged duty point.
  if(basis==='product' && q && lastResult?.product_flow!==undefined) q.value=Number(lastResult.product_flow).toFixed(1);
  if(basis==='pressure' && p && lastResult?.membrane_pressure_1!==undefined) p.value=Number(lastResult.membrane_pressure_1).toFixed(1);
  if(basis==='recovery' && r && lastResult?.recovery!==undefined) r.value=(Number(lastResult.recovery)*100).toFixed(1);
  hidden.value=basis;
  updateSolveUI();
  updateRejectFlowMode();
  updateMassBalancePreview();
  updateRequiredFieldStates();
}
function updateRejectFlowMode(){
  const basis=document.querySelector('[name="solve_basis"]')?.value||'pressure';
  const coupled=mode==='multistage'||document.querySelector('[name="membrane_coupling"]')?.value==='on';
  // Reject is an input only in true manual pressure-basis mode. In coupled
  // membrane calculations, Q→P and R→P modes it is always a calculated output.
  const calculated=coupled||basis==='product'||basis==='recovery';
  document.querySelectorAll('[data-manual-reject="1"]').forEach(field=>{
    const input=field.querySelector('input');
    if(!input)return;
    input.disabled=calculated;
    input.required=!calculated;
    input.readOnly=calculated;
    input.setAttribute('aria-readonly',String(calculated));
    field.classList.remove('dimmed');
    field.classList.toggle('calculated-field',calculated);
    field.classList.toggle('setpoint-field',!calculated);
    const note=field.querySelector('.mandatory-note');
    if(note&&calculated)note.hidden=true;
  });
}
function updateMassBalancePreview(){
  const basis=document.querySelector('[name="solve_basis"]')?.value||'pressure';
  if(basis!=='product'&&basis!=='recovery')return;
  const qfEl=document.querySelector('[name="feed_flow"]');
  const qpEl=document.querySelector('[name="target_product_flow"]');
  const recEl=document.querySelector('[name="target_recovery"]');
  if(!qfEl||!qpEl||!recEl)return;
  const qf=Number(qfEl.value);
  if(!Number.isFinite(qf)||qf<=0)return;
  let qp;
  if(basis==='recovery'){
    let rec=Number(recEl.value);
    if(!Number.isFinite(rec)||rec<=0)return;
    if(rec>1)rec/=100;
    if(rec<=0||rec>=1)return;
    qp=qf*rec;
    qpEl.value=Number(qp.toFixed(6));
  }else{
    qp=Number(qpEl.value);
    if(!Number.isFinite(qp)||qp<0||qp>=qf)return;
    recEl.value=Number(((qp/qf)*100).toFixed(6));
  }
  const qr=Math.max(0,qf-qp);
  // Single-stage Turbo / IC: Stage 1 reject is the system reject. For two-stage
  // trains, Stage 2 reject is the system reject; Stage 1 reject comes from the
  // coupled membrane solver and remains a calculated output.
  const finalRejectName=(mode==='interstage'||mode==='biturbo')?'reject_flow_2':'reject_flow_1';
  const finalReject=document.querySelector(`[name="${finalRejectName}"]`);
  if(finalReject)finalReject.value=Number(qr.toFixed(6));
}
function isAutoPlantDesign(){return mode==='multistage'&&document.querySelector('[name="design_mode"]')?.value==='auto';}
function updateAutoDesignHydraulics(){
  if(!isAutoPlantDesign())return;
  const cap=document.querySelector('[name="required_capacity_m3d"]'),trains=document.querySelector('[name="operating_trains"]'),rec=document.querySelector('[name="target_recovery"]');
  const feed=document.querySelector('[name="feed_flow"]'),product=document.querySelector('[name="target_product_flow"]'),pressure=document.querySelector('[name="membrane_pressure_1"]');
  if(cap){cap.required=true;cap.setAttribute('aria-required','true');cap.closest('.field')?.classList.add('setpoint-field');}
  if(feed){feed.readOnly=true;feed.setAttribute('aria-readonly','true');feed.closest('.field')?.classList.add('calculated-field');feed.closest('.field')?.classList.remove('setpoint-field');}
  if(product){product.readOnly=true;product.setAttribute('aria-readonly','true');product.closest('.field')?.classList.add('calculated-field');product.closest('.field')?.classList.remove('setpoint-field');}
  if(pressure){pressure.readOnly=true;pressure.setAttribute('aria-readonly','true');pressure.closest('.field')?.classList.add('calculated-field');pressure.closest('.field')?.classList.remove('setpoint-field');if(!String(pressure.value||'').trim())pressure.placeholder='Calculated by Auto Design';}
  const c=Number(cap?.value),n=Math.max(1,Math.round(Number(trains?.value)||0));let r=Number(rec?.value);if(r>1)r/=100;
  if(Number.isFinite(c)&&c>0&&n>0&&Number.isFinite(r)&&r>0&&r<=.95){
    const qpM3h=c/(24*n),qfM3h=qpM3h/r;
    if(product)product.value=Number(convert(qpM3h,'flow','m3/h',currentUnits.flow).toFixed(6));
    if(feed)feed.value=Number(convert(qfM3h,'flow','m3/h',currentUnits.flow).toFixed(6));
  }else{if(product)product.value='';if(feed)feed.value='';}
}
function updateAutoDesignFieldVisibility(){
  if(mode!=='multistage')return;
  const allowed=tierAllows('auto_design');
  const autoSelected=document.querySelector('[name="design_mode"]')?.value==='auto';
  ['max_design_flux_lmh','required_capacity_m3d'].forEach(k=>{
    const field=document.querySelector(`[name="${k}"]`)?.closest('.field');if(!field)return;
    field.style.display=(allowed&&autoSelected)?'':'none';
    const ctl=field.querySelector('input,select');if(!ctl)return;
    ctl.disabled=!(allowed&&autoSelected);
    if(k==='required_capacity_m3d'){
      ctl.required=Boolean(allowed&&autoSelected);
      if(ctl.required)ctl.setAttribute('aria-required','true');else ctl.removeAttribute('aria-required');
    }
  });
}
function updateSolveUI(){
  let basis=document.querySelector('[name="solve_basis"]')?.value||'pressure';
  let couplingEl=document.querySelector('[name="membrane_coupling"]');
  let coupled=mode==='multistage'||couplingEl?.value==='on';
  const autoPlant=isAutoPlantDesign();
  if(autoPlant){basis='recovery';const hidden=document.querySelector('[name="solve_basis"]');if(hidden)hidden.value='recovery';if(couplingEl){couplingEl.value='on';coupled=true;}}
  if((basis==='product'||basis==='recovery')&&!coupled&&couplingEl){couplingEl.value='on';coupled=true;}
  const p=document.querySelector('[name="membrane_pressure_1"]');
  const q=document.querySelector('[name="target_product_flow"]');
  const r=document.querySelector('[name="target_recovery"]');
  const p2=document.querySelector('[name="membrane_pressure_2"]');
  const pf=p?.closest('.field'),qf=q?.closest('.field'),rf=r?.closest('.field'),p2f=p2?.closest('.field');
  if(!p||!q||!r)return;
  const pressureInput=basis==='pressure',productInput=basis==='product',recoveryInput=basis==='recovery';
  p.readOnly=!pressureInput;q.readOnly=!productInput;r.readOnly=!recoveryInput;
  if(p2){p2.readOnly=!pressureInput;p2.required=pressureInput;p2.setAttribute('aria-readonly',String(!pressureInput));p2f?.classList.toggle('calculated-field',!pressureInput);p2f?.classList.toggle('setpoint-field',pressureInput);}
  const calcPlaceholder=el=>{if(!el)return;if(el.readOnly&&!String(el.value||'').trim())el.placeholder='Calculated on Run';else if(!el.readOnly&&el.placeholder==='Calculated on Run')el.placeholder='';};
  [p,q,r,p2].forEach(calcPlaceholder);
  document.querySelectorAll('[data-manual-reject="1"] input').forEach(el=>{if((coupled||basis==='product'||basis==='recovery')&&!String(el.value||'').trim())el.placeholder='Calculated on Run';});
  p.required=pressureInput;q.required=productInput;r.required=recoveryInput;
  p.setAttribute('aria-readonly',String(!pressureInput));q.setAttribute('aria-readonly',String(!productInput));r.setAttribute('aria-readonly',String(!recoveryInput));
  [[pf,pressureInput],[qf,productInput],[rf,recoveryInput]].forEach(([field,isInput])=>{field?.classList.toggle('calculated-field',!isInput);field?.classList.toggle('setpoint-field',isInput);});
  document.querySelectorAll('.solve-arrow').forEach(b=>{b.classList.toggle('active',b.dataset.solve===basis);b.disabled=autoPlant||(!coupled&&b.dataset.solve!=='pressure');});
  if(autoPlant)updateAutoDesignHydraulics();
  else {const feed=document.querySelector('[name="feed_flow"]'),cap=document.querySelector('[name="required_capacity_m3d"]');if(feed){feed.readOnly=false;feed.setAttribute('aria-readonly','false');feed.closest('.field')?.classList.remove('calculated-field');}if(cap){cap.required=false;cap.removeAttribute('aria-required');}}
  updateRejectFlowMode();updateMassBalancePreview();updateRequiredFieldStates();
  const btn=calculateButton();if(btn)setPrimaryLabel(autoPlant?'Auto Design · size array & solve pressure':pressureInput?'Calculate permeate & recovery':productInput?'Solve feed pressure & recovery':'Solve feed pressure & permeate');
  const hint=document.querySelector('.solve-hint');
  if(!hint)return;
  if(mode==='multistage'){
    hint.textContent=autoPlant?'AUTO DESIGN SETPOINTS: required plant product capacity + operating trains + overall recovery + maximum design flux. OUTPUTS: train permeate/feed flow, membrane area, integer tree/funnel vessel array, interstage boosts and minimum required Stage 1 membrane feed pressure.':pressureInput?'SETPOINTS: Stage 1 membrane feed pressure and optional interstage booster ΔP. OUTPUTS: stage-by-stage permeate, final reject and overall recovery.':productInput?'SETPOINT: total permeate flow. OUTPUTS: required Stage 1 pressure; downstream stage pressures follow calculated reject pressure + booster ΔP.':'SETPOINT: overall recovery. OUTPUTS: permeate flow and required Stage 1 pressure; downstream stage pressures follow reject pressure + booster ΔP.';
    return;
  }
  const multi=!!p2;
  hint.textContent=pressureInput?(multi?'SETPOINTS: Stage 1 and Stage 2 membrane feed pressures. OUTPUTS: permeate flow, reject flows and overall recovery.':'SETPOINT: membrane feed pressure. OUTPUTS: permeate flow, reject flow and overall recovery.'):productInput?(multi?'SETPOINT: total permeate flow. OUTPUTS: reject flows, coupled Stage 1 and Stage 2 membrane feed pressures and overall recovery.':'SETPOINT: permeate flow. OUTPUTS: reject flow, required membrane feed pressure and overall recovery.'):(multi?'SETPOINT: overall recovery. OUTPUTS: permeate flow, reject flows and coupled Stage 1 and Stage 2 membrane feed pressures.':'SETPOINT: overall recovery. OUTPUTS: permeate flow, reject flow and required membrane feed pressure.');
}
function updatePxVisibility(){if(mode!=='px')return;const motor=document.querySelector('[name="px_architecture"]')?.value==='motorized';document.querySelectorAll('[data-passive-only="1"]').forEach(el=>{el.hidden=motor;const ctl=el.querySelector('select,input');if(ctl)ctl.disabled=motor;});updateRequiredFieldStates()}
function updateWaterModeVisibility(){if(mode==='water')return;const coupled=mode==='multistage'||document.querySelector('[name="membrane_coupling"]')?.value==='on';const full=true;document.querySelectorAll('[data-chemistry-only="1"]').forEach(el=>{el.classList.toggle('dimmed',!full);const input=el.querySelector('input');if(input)input.disabled=!full});document.querySelectorAll('[data-tds-only="1"]').forEach(el=>{const active=coupled&&!full;el.classList.toggle('dimmed',!active);const input=el.querySelector('input');if(input)input.disabled=!active});document.querySelectorAll('[data-chemistry-section="1"]').forEach(el=>el.classList.toggle('hidden-section',!full));}
function updateCouplingVisibility(){const on=mode==='multistage'||document.querySelector('[name="membrane_coupling"]')?.value==='on';const pp=document.querySelector('[name="permeate_pressure"]');if(pp){pp.disabled=false;pp.closest('.field')?.classList.remove('dimmed')}updateRejectFlowMode();updateMassBalancePreview();updateRequiredFieldStates()}
function capture(){let o={};document.querySelectorAll('#calcForm input[type=checkbox]').forEach(el=>o[el.name]=el.checked);new FormData($('#calcForm')).forEach((v,k)=>{if(document.querySelector(`[name="${k}"]`)?.type==='checkbox')return;o[k]=(v===''?'':(isNaN(v)?v:+v))});return o}
function changeUnits(kind,newUnit){if(mode==='water'){waterProfile=captureWater();syncActiveCaseStore();currentUnits[kind]=newUnit;renderWaterTab();return;}if(mode==='comparison'){currentUnits[kind]=newUnit;renderComparisonTab();$('#results').innerHTML=comparisonResults();return;}if(mode==='summary'){currentUnits[kind]=newUnit;renderSummaryTab();$('#results').innerHTML=summaryResults();return;}if(mode==='economic'){economicState=captureEconomic();currentUnits[kind]=newUnit;renderEconomicTab();return;}const d=defn(),old=currentUnits[kind],vals=capture();Object.keys(vals).forEach(k=>{if(d[k]?.type===kind){const converted=convert(vals[k],kind,old,newUnit);vals[k]=(converted===''||converted===null||converted===undefined)?converted:+Number(converted).toFixed(6);}}); // preserve disabled/manual fields from defaults/current DOM
  document.querySelectorAll('#calcForm input:disabled,#calcForm select:disabled').forEach(el=>{let v=el.value;if(d[el.name]?.type===kind){const converted=convert(v,kind,old,newUnit);v=(converted===''||converted===null||converted===undefined)?converted:+Number(converted).toFixed(6);}vals[el.name]=v});currentUnits[kind]=newUnit;renderFields(vals)}
function fmt(v,n=1){if(v===null||v===undefined||Number.isNaN(Number(v)))return '—';return Number(v).toLocaleString(undefined,{minimumFractionDigits:n,maximumFractionDigits:n})}

const labels={
 base_turbo_eff:['Base turbo efficiency','%'],turbo_eff:['Corrected turbo efficiency','%'],feed_turbo_eff:['Feed turbo corrected efficiency','%'],
 recovery:['Overall recovery','%'],stage1_recovery:['Stage 1 recovery','%'],stage2_recovery:['Stage 2 recovery','%'],
 product_flow:['Product flow','FLOW'],product_m3d:['Product water','m³/d'],turbine_flow:['Turbine brine flow','FLOW'],interstage_turbine_flow:['Interstage turbine flow','FLOW'],feed_turbine_flow:['Feed turbine flow','FLOW'],
 turbine_dp:['Turbine ΔP','PRESS'],interstage_turbine_dp:['Interstage turbine ΔP','PRESS'],feed_turbine_dp:['Feed turbine ΔP','PRESS'],turbo_boost:['Turbo pressure boost','PRESS'],interstage_boost:['Interstage boost','PRESS'],feed_turbo_boost:['Feed turbo boost','PRESS'],brine_discharge_pressure:['Brine discharge pressure','PRESS'],interstage_discharge_pressure:['Interstage discharge pressure','PRESS'],feed_pump_dp:['Feed pump ΔP','PRESS'],
 hydraulic_kw:['Hydraulic power','kW'],electric_kw:['Feed pump electric power','kW'],pretreatment_kw:['Pretreatment electric power','kW'],pump_sec:['Feed pump SEC','kWh/m³'],ro_sec:['RO SEC','kWh/m³'],pretreatment_sec:['Pretreatment SEC','kWh/m³'],total_sec:['Total plant SEC','kWh/m³'],
 cv_required:['Required turbine Cv','Cv'],cvc:['Cvc · aux closed','Cv'],cvo:['Cvo · aux fully open','Cv'],kv_required:['Required Kv','Kv'],aux_opening:['Auxiliary valve opening','%'],efficiency_loss:['Turbo efficiency penalty','%'],
 inter_cv_required:['Interstage required Cv','Cv'],inter_cvc:['Interstage Cvc','Cv'],inter_cvo:['Interstage Cvo','Cv'],inter_aux_opening:['Interstage aux opening','%'],inter_efficiency_loss:['Interstage efficiency penalty','%'],feed_cv_required:['Feed turbo required Cv','Cv'],feed_cvc:['Feed turbo Cvc','Cv'],feed_cvo:['Feed turbo Cvo','Cv'],feed_aux_opening:['Feed turbo aux opening','%'],feed_efficiency_loss:['Feed turbo efficiency penalty','%'],
 stage1_flux_lmh:['Stage 1 average flux','LMH'],stage1_polarization_factor:['Stage 1 polarization factor',''],stage1_a_app_lmh_bar:['Stage 1 Aapp','LMH/bar'],stage1_b_app_lmh:['Stage 1 B(T)','LMH'],stage1_salt_temperature_factor:['Stage 1 B temperature factor',''],stage1_observed_salt_rejection_pct:['Stage 1 observed rejection','%'],stage1_observed_salt_passage_pct:['Stage 1 observed salt passage','%'],stage1_salt_rejection:['Stage 1 salt rejection','%'],stage1_salt_passage:['Stage 1 salt passage','%'],stage1_permeate_tds_ppm:['Stage 1 permeate TDS','ppm'],stage1_concentrate_tds_ppm:['Stage 1 concentrate TDS','ppm'],stage1_ndp:['Stage 1 NDP','PRESS'],stage1_feed_osmotic:['Stage 1 feed osmotic pressure','PRESS'],stage1_concentrate_osmotic:['Stage 1 concentrate osmotic pressure','PRESS'],stage1_feed_osmotic_coefficient:['Stage 1 feed osmotic coefficient φ',''],stage1_concentrate_osmotic_coefficient:['Stage 1 concentrate osmotic coefficient φ',''],stage1_feed_ionic_strength:['Stage 1 feed ionic strength','mol/kg'],stage1_concentrate_ionic_strength:['Stage 1 concentrate ionic strength','mol/kg'],
 stage2_flux_lmh:['Stage 2 average flux','LMH'],stage2_polarization_factor:['Stage 2 polarization factor',''],stage2_a_app_lmh_bar:['Stage 2 Aapp','LMH/bar'],stage2_b_app_lmh:['Stage 2 B(T)','LMH'],stage2_salt_temperature_factor:['Stage 2 B temperature factor',''],stage2_observed_salt_rejection_pct:['Stage 2 observed rejection','%'],stage2_observed_salt_passage_pct:['Stage 2 observed salt passage','%'],stage2_salt_rejection:['Stage 2 salt rejection','%'],stage2_salt_passage:['Stage 2 salt passage','%'],stage2_permeate_tds_ppm:['Stage 2 permeate TDS','ppm'],stage2_concentrate_tds_ppm:['Stage 2 concentrate TDS','ppm'],stage2_ndp:['Stage 2 NDP','PRESS'],stage2_feed_osmotic:['Stage 2 feed osmotic pressure','PRESS'],stage2_concentrate_osmotic:['Stage 2 concentrate osmotic pressure','PRESS'],stage2_feed_osmotic_coefficient:['Stage 2 feed osmotic coefficient φ',''],stage2_concentrate_osmotic_coefficient:['Stage 2 concentrate osmotic coefficient φ',''],stage2_feed_ionic_strength:['Stage 2 feed ionic strength','mol/kg'],stage2_concentrate_ionic_strength:['Stage 2 concentrate ionic strength','mol/kg']
};
function showWarnings(r){const warns=[];const coupled=!!r.membrane_coupling;const fu=r.flow_unit,pu=r.pressure_unit;const collect=(prefix,name)=>{const status=r[prefix+'duty_status']||r[prefix+'cv_status'];if(!status||status==='in_range')return;const msg=r[prefix+'cv_message']||'';if(status==='bypass_required'||status==='above_cvo'){warns.push(`<div class="warning warning-bypass"><div class="warning-head"><strong>${name}: BYPASS REQUIRED</strong><details class="why"><summary>?</summary><div class="why-box"><strong>Why?</strong> Cv required is above Cvo, so even at full auxiliary opening the nozzle cannot pass all of the concentrate at the present turbine ΔP.${coupled?'<br><br><strong>Membrane coupling is active.</strong> Increasing RO pressure also increases membrane flux, changes permeate flow, recovery, concentrate TDS and concentrate flow. Therefore the hydraulic ΔP shown below is only a reference—not the final equilibrium correction. Recalculate the coupled duty after changing pressure.':''}<br><br><strong>Ways to move away from bypass:</strong> increase available turbine ΔP, or reduce concentrate flow through the nozzle. With RO coupling active, both occur together when pressure is changed, so the duty point must be solved iteratively.</div></details></div><div class="warning-text">${msg}</div><div class="duty-actions"><div><span>Max turbine flow at current ΔP</span><strong>${fmt(r[prefix+'flow_at_cvo_current_dp'])} ${fu}</strong></div><div><span>Hydraulic-only bypass estimate</span><strong>${fmt(r[prefix+'bypass_flow_required'])} ${fu}</strong></div><div><span>Hydraulic-only ΔP at Cvo</span><strong>${fmt(r[prefix+'required_dp_at_cvo'])} ${pu}</strong></div><div><span>Hydraulic-only ΔP increase</span><strong>${fmt(r[prefix+'pressure_increase_to_avoid_bypass'])} ${pu}</strong></div></div></div>`)}else{warns.push(`<div class="warning warning-backpressure"><div class="warning-head"><strong>${name}: BACKPRESSURE REQUIRED</strong><details class="why"><summary>?</summary><div class="why-box"><strong>Why?</strong> Cv required is below Cvc. With the auxiliary path closed, the nozzle is too open for the requested flow/ΔP point.${coupled?'<br><br><strong>Membrane coupling is active.</strong> Decreasing RO pressure lowers flux and permeate production, which raises concentrate flow and changes TDS/osmotic pressure. Increasing feed flow also changes recovery. The backpressure value below is therefore a hydraulic reference only.':''}<br><br><strong>Ways to move away from backpressure:</strong> increase turbine/concentrate flow or decrease available turbine ΔP/pressure, then recalculate the coupled membrane/turbo duty.</div></details></div><div class="warning-text">${msg}</div><div class="duty-actions"><div><span>Flow needed at current ΔP</span><strong>${fmt(r[prefix+'flow_at_cvc_current_dp'])} ${fu}</strong></div><div><span>Hydraulic-only flow increase</span><strong>${fmt(r[prefix+'flow_increase_to_avoid_backpressure'])} ${fu}</strong></div><div><span>Hydraulic-only ΔP at Cvc</span><strong>${fmt(r[prefix+'required_dp_at_cvc'])} ${pu}</strong></div><div><span>Hydraulic-only backpressure</span><strong>${fmt(r[prefix+'backpressure_required'])} ${pu}</strong></div></div></div>`)}};if(mode==='biturbo'){collect('inter_','Interstage turbo');collect('feed_','Feed turbo')}else collect('','Turbo');Array.from({length:resultStageCount(r)},(_,j)=>j+1).forEach(i=>{const frac=Number(r[`stage${i}_dp_limit_fraction`]);if(!Number.isFinite(frac)||frac<=1)return;warns.push(`<div class="warning warning-limit"><div class="warning-head"><strong>Stage ${i}: membrane ΔP limit exceeded</strong></div><div class="warning-text">Maximum element pressure drop is ${fmt(r[`stage${i}_max_actual_dp_per_element`])} ${pu} versus an allowed datasheet limit of ${fmt(r[`stage${i}_datasheet_max_dp_per_element`])} ${pu} per element. Change the inputs so the duty is within the accepted membrane hydraulic limit.</div><div class="duty-actions"><div><span>Calculated max ΔP / element</span><strong>${fmt(r[`stage${i}_max_actual_dp_per_element`])} ${pu}</strong></div><div><span>Datasheet limit</span><strong>${fmt(r[`stage${i}_datasheet_max_dp_per_element`])} ${pu}</strong></div><div><span>Suggested changes</span><strong>More vessels · less flow/vessel</strong></div><div><span>Also consider</span><strong>Lower pressure or recovery</strong></div></div></div>`);});if((mode==='px'||mode==='interstage_px')&&r.px_within_flow_range===false){const lo=Number(r.px_min_unit_flow),hi=Number(r.px_max_unit_flow),range=Number.isFinite(hi)&&hi>0?`${Number.isFinite(lo)&&lo>0?fmt(lo)+'–':''}${fmt(hi)} ${fu}`:'the entered unit-flow envelope';warns.push(`<div class="warning warning-limit"><div class="warning-head"><strong>Isobaric Chamber: unit flow outside preferred range</strong></div><div class="warning-text">The calculated PX unit flow is ${fmt(r.px_unit_flow)} ${fu}, outside ${range}. Adjust feed flow, recovery, PX quantity or PX model to bring the design back within range.</div><div class="duty-actions"><div><span>Current unit flow</span><strong>${fmt(r.px_unit_flow)} ${fu}</strong></div><div><span>Preferred range</span><strong>${escapeHtml(range)}</strong></div><div><span>Suggested changes</span><strong>Adjust PX qty / model</strong></div><div><span>Or modify</span><strong>Feed flow / recovery</strong></div></div></div>`);}if(mode==='multistage'&&r.pump_operating_status==='no_intersection'){warns.push(`<div class="warning warning-limit"><div class="warning-head"><strong>HPP pump/system curve: no operating-point intersection</strong></div><div class="warning-text">The selected typical pump BEP and the calculated RO system curve do not intersect within the screening range.</div><div class="duty-actions"><div><span>Suggested changes</span><strong>Choose a higher-head / different-BEP pump</strong></div><div><span>Or modify</span><strong>RO pressure / train flow</strong></div></div></div>`);}else if(mode==='multistage'&&r.pump_operating_status==='ok'&&r.pump_operating_zone&&r.pump_operating_zone!=='preferred'){const right=r.pump_operating_zone==='right_of_bep';warns.push(`<div class="warning ${right?'warning-limit':'dynamic-note'}"><div class="warning-head"><strong>HPP operating point ${right?'right':'left'} of preferred BEP range</strong></div><div class="warning-text">The preliminary pump/system intersection is ${fmt(100*r.pump_operating_bep_flow_ratio,1)}% of BEP flow. ${right?'Right-of-BEP operation should be checked for runout, vibration, NPSH and motor loading against the vendor curve.':'Left-of-BEP operation should be checked for minimum continuous stable flow, recirculation and vibration against the vendor curve.'}</div><div class="duty-actions"><div><span>Calculated flow / BEP</span><strong>${fmt(100*r.pump_operating_bep_flow_ratio,1)}%</strong></div><div><span>Screening efficiency</span><strong>${fmt(100*r.pump_operating_efficiency,1)}%</strong></div></div></div>`);}if(coupled&&mode==='single'&&r.plus1_cv_required!==undefined){warns.push(`<div class="warning dynamic-note"><div class="warning-head"><strong>Coupled pressure sensitivity</strong><details class="why"><summary>?</summary><div class="why-box">This is a local ±1 bar sensitivity, with stage feed and reject pressure moved together. It demonstrates the coupled response: membrane flux changes first, which changes permeate/reject flow and therefore the turbine Cv requirement. It is not a vendor membrane projection.</div></details></div><div class="duty-actions"><div><span>At +1 bar · product</span><strong>${fmt(r.plus1_product_flow)} ${fu}</strong></div><div><span>At +1 bar · Cv required</span><strong>${fmt(r.plus1_cv_required)} Cv</strong></div><div><span>At −1 bar · product</span><strong>${fmt(r.minus1_product_flow)} ${fu}</strong></div><div><span>At −1 bar · Cv required</span><strong>${fmt(r.minus1_cv_required)} Cv</strong></div></div></div>`)}$('#warnings').innerHTML=warns.join('')}
function showMembraneHeader(r){
  let s=`<div class="membrane-summary"><strong>${r.membrane_coupling?'RO coupling active':'Manual permeate/reject · clean ΔP active'}</strong><span>Water: ${escapeHtml(waterProfile.water_region_name||'Custom')} · ${fmt(waterProfile.salinity_psu)} PSU · ${fmt(waterProfile.analysis_tds)} mg/L</span><span>Reject pressure: automatically calculated element-by-element</span>`;
  if(r.membrane_coupling)s+=`<span>Osmotic model: ${r.stage1_osmotic_method||'TDS quick mode'}</span><span>Temperature: ${fmt(r.stage1_temperature_c??25)} °C</span>`;
  const n=resultStageCount(r);
  for(let i=1;i<=n;i++)if(r[`stage${i}_membrane_model`])s+=`<span>Stage ${i}: ${escapeHtml(r[`stage${i}_membrane_manufacturer`]||'')} ${escapeHtml(r[`stage${i}_membrane_model`]||'')}</span>`;
  if(r.stage1_fouling_factor!==undefined)s+=`<span>Flow/Fouling factor: ${fmt(r.stage1_fouling_factor)} · Salt passage factor: ${fmt(r.stage1_salt_passage_factor??1)}</span>`;
  if(r.stage1_salt_temperature_factor!==undefined)s+=`<span>Temperature transport: A ×${fmt(r.stage1_water_temperature_factor,3)} · B ×${fmt(r.stage1_salt_temperature_factor,3)} vs ${fmt(r.stage1_transport_reference_temperature_c??25)} °C datasheet test</span>`;
  for(let i=1;i<=n;i++)if(r[`stage${i}_membrane_transport_note`])s+=`<span class="estimate-note">⚠ Stage ${i}: ${escapeHtml(r[`stage${i}_membrane_transport_note`])}</span>`;
  if(r.stage1_osmotic_warning)s+=`<span class="estimate-note">⚠ Osmotic backend fallback: ${escapeHtml(r.stage1_osmotic_warning)}</span>`;
  return s+'</div>';
}
function cell(v,unit='',digits=1){return `<td>${fmt(v,digits)}${unit?` <span class="tbl-unit">${unit}</span>`:''}</td>`}
function pct(v,d=1){return fmt((v??0)*100,d)}
function fluxValue(v){return convert(v,'flux','LMH',currentUnits.flux||$('#fluxUnit')?.value||'LMH')}
function fluxUnit(){return currentUnits.flux||$('#fluxUnit')?.value||'LMH'}
function stageReport(r){
  const fu=r.flow_unit,pu=r.pressure_unit,n=resultStageCount(r),fl=fluxUnit(),rows=[];
  rows.push(`<tr><th>Stage</th><th>Qpf<br><span>${fu}</span></th><th>Pf<br><span>${pu}</span></th><th>Qp<br><span>${fu}</span></th><th>Qr<br><span>${fu}</span></th><th>Pr · calc<br><span>${pu}</span></th><th>Recovery</th><th>Vessels</th><th>Elements / vessel</th><th>Total elements</th><th>Avg. flux<br><span>${fl}</span></th><th>Feed TDS<br><span>mg/L</span></th><th>Conc. TDS<br><span>mg/L</span></th><th>CP mono</th><th>CP divalent</th><th>Stage ΔP<br><span>${pu}</span></th><th>ΔP / element<br><span>${pu}</span></th></tr>`);
  for(let i=1;i<=n;i++){if(r[`stage${i}_pressure_vessels`]===undefined)continue;const qf=i===1?r.feed_flow:r[`reject_flow_${i-1}`];rows.push(`<tr><td>${i}</td>${cell(qf)}${cell(r[`membrane_pressure_${i}`])}${cell(r[`stage${i}_permeate_flow`])}${cell(r[`reject_flow_${i}`])}${cell(r[`reject_pressure_${i}`])}<td>${pct(r[`stage${i}_recovery`]??(i===1?r.recovery:null))}%</td><td>${fmt(r[`stage${i}_pressure_vessels`],1)}</td><td>${fmt(r[`stage${i}_elements_per_vessel`],1)}</td><td>${fmt(r[`stage${i}_total_elements`],1)}</td>${cell(fluxValue(r[`stage${i}_flux_lmh`]))}${cell(r[`stage${i}_feed_tds_ppm`])}${cell(r[`stage${i}_concentrate_tds_ppm`])}${cell(r[`stage${i}_polarization_factor_monovalent`]??r[`stage${i}_polarization_factor`],'',2)}${cell(r[`stage${i}_polarization_factor_divalent`]??r[`stage${i}_polarization_factor`],'',2)}${cell(r[`stage${i}_stage_dp`]??(r[`membrane_pressure_${i}`]-r[`reject_pressure_${i}`]))}${cell(r[`stage${i}_dp_per_element`])}</tr>`)}
  return `<section class="report-section"><h3>RO STAGE PERFORMANCE</h3><div class="table-wrap"><table class="fedco-table">${rows.join('')}</table></div><p class="micro-note">Each downstream stage is fed by the actual calculated concentrate from the preceding stage. Hybrid recipes are solved element-position by element-position.</p></section>`;
}
function multistageSeries(r,field){
  const pts=[];let pos=0,n=resultStageCount(r);
  for(let stage=1;stage<=n;stage++){
    const arr=Array.isArray(r[`stage${stage}_element_profile`])?r[`stage${stage}_element_profile`]:[];
    arr.forEach((e,i)=>pts.push({pos:++pos,v:Number(e[field]),stage,local:i+1}));
  }
  return pts;
}
function stageBoundariesSvg(points,x,T,H,B,L,W,R){
  if(!points.length)return '';
  const groups=[];for(const p of points){let g=groups.find(x=>x.stage===p.stage);if(!g){g={stage:p.stage,start:p.pos,end:p.pos};groups.push(g)}else g.end=p.pos;}
  let out='';for(let i=0;i<groups.length;i++){const g=groups[i],x1=i===0?L:(x({pos:g.start-1})+x({pos:g.start}))/2,x2=i===groups.length-1?W-R:(x({pos:g.end})+x({pos:g.end+1}))/2;out+=`<text x="${(x1+x2)/2}" y="${T+10}" text-anchor="middle" class="stage-label">STAGE ${g.stage}</text>`;if(i<groups.length-1){const bx=x2;out+=`<line x1="${bx}" y1="${T}" x2="${bx}" y2="${H-B}" class="stage-boundary"/>`;}}
  return out;
}
function fluxProfileChart(r){
  const points=multistageSeries(r,'flux_lmh').map(p=>({...p,v:fluxValue(p.v)})).filter(p=>Number.isFinite(p.v));if(!points.length)return '';
  const W=820,H=255,L=54,R=20,T=22,B=42,vals=points.map(p=>p.v);let ymin=Math.min(...vals),ymax=Math.max(...vals);const spread=Math.max(ymax-ymin,Math.max(1,ymax)*.08);ymin=Math.max(0,ymin-spread*.18);ymax+=spread*.18;
  const n=Math.max(1,points.length-1),x=p=>L+(p.pos-1)*(W-L-R)/n,y=v=>T+(ymax-v)*(H-T-B)/(ymax-ymin||1),grid=[];
  for(let i=0;i<=4;i++){const v=ymax-(ymax-ymin)*i/4,yy=T+(H-T-B)*i/4;grid.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="flux-grid"/><text x="${L-8}" y="${yy+3}" text-anchor="end" class="flux-axis-text">${fmt(v,1)}</text>`)}
  const path=points.map((p,i)=>`${i?'L':'M'} ${x(p).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' '),dots=points.map(p=>`<g class="flux-point"><circle cx="${x(p)}" cy="${y(p.v)}" r="4.2"/><text x="${x(p)}" y="${y(p.v)-9}" text-anchor="middle" class="flux-value">${fmt(p.v,1)}</text><title>Position ${p.pos} · Stage ${p.stage}, element ${p.local}: ${fmt(p.v,1)} ${fluxUnit()}</title></g>`).join(''),ticks=points.map(p=>`<text x="${x(p)}" y="${H-B+18}" text-anchor="middle" class="flux-axis-text">${p.pos}</text>`).join('');
  return `<section class="report-section flux-chart-section"><div class="chart-title-row"><h3>FLUX vs. MEMBRANE POSITION</h3><span>Representative pressure vessels · ${points.length} element positions</span></div><div class="flux-chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Membrane flux versus element position">${grid.join('')}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/>${stageBoundariesSvg(points,x,T,H,B,L,W,R)}<path d="${path}" class="flux-line"/>${dots}${ticks}<text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" class="flux-axis-title">Membrane position</text><text x="15" y="${(T+H-B)/2}" transform="rotate(-90 15 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Flux (${fluxUnit()})</text></svg></div></section>`;
}
function polarizationProfileChart(r){
  const base=multistageSeries(r,'polarization_factor_monovalent');if(!base.length)return '';
  const points=[];let pos=0;for(let stage=1;stage<=resultStageCount(r);stage++){const arr=Array.isArray(r[`stage${stage}_element_profile`])?r[`stage${stage}_element_profile`]:[];arr.forEach((e,i)=>points.push({pos:++pos,mono:Number(e.polarization_factor_monovalent??e.polarization_factor),di:Number(e.polarization_factor_divalent??e.polarization_factor),stage,local:i+1}))}if(!points.length)return '';
  const vals=points.flatMap(p=>[p.mono,p.di]).filter(Number.isFinite);if(!vals.length)return '';const W=820,H=255,L=54,R=20,T=22,B=42;let ymin=Math.min(...vals),ymax=Math.max(...vals),spread=Math.max(ymax-ymin,.08);ymin=Math.max(1,ymin-spread*.18);ymax+=spread*.18;const n=Math.max(1,points.length-1),x=p=>L+(p.pos-1)*(W-L-R)/n,y=v=>T+(ymax-v)*(H-T-B)/(ymax-ymin||1),grid=[];
  for(let i=0;i<=4;i++){const v=ymax-(ymax-ymin)*i/4,yy=T+(H-T-B)*i/4;grid.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="flux-grid"/><text x="${L-8}" y="${yy+3}" text-anchor="end" class="flux-axis-text">${fmt(v,2)}</text>`)}
  const path=k=>points.map((p,i)=>`${i?'L':'M'} ${x(p).toFixed(1)} ${y(p[k]).toFixed(1)}`).join(' '),dots=k=>points.map(p=>{const yy=y(p[k]),labelY=k==='mono'?yy-8:yy+13;return `<g class="cp-marker ${k==='mono'?'cp-mono':'cp-di'}"><circle cx="${x(p)}" cy="${yy}" r="3.6" class="cp-point ${k==='mono'?'cp-point-mono':'cp-point-di'}"/><text x="${x(p)}" y="${labelY}" text-anchor="middle" class="cp-value ${k==='mono'?'cp-value-mono':'cp-value-di'}">${fmt(p[k],2)}</text><title>Stage ${p.stage}, element ${p.local}: ${fmt(p[k],2)}</title></g>`}).join(''),ticks=points.map(p=>`<text x="${x(p)}" y="${H-B+18}" text-anchor="middle" class="flux-axis-text">${p.pos}</text>`).join('');
  return `<section class="report-section suite-polarization-section"><div class="chart-title-row"><h3>POLARIZATION FACTOR vs. MEMBRANE POSITION</h3><span>Monovalent and divalent screening</span></div><div class="cp-legend suite-cp-legend"><span class="legend-mono">Monovalent / neutral</span><span class="legend-di">Divalent</span></div><div class="suite-chart-card full-chart-card"><svg class="suite-polarization-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Polarization factors versus membrane position">${grid.join('')}${stageBoundariesSvg(points,x,T,H,B,L,W,R)}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/><path d="${path('mono')}" class="cp-line cp-line-mono"/><path d="${path('di')}" class="cp-line cp-line-di"/>${dots('mono')}${dots('di')}${ticks}<text x="${(L+W-R)/2}" y="${H-5}" text-anchor="middle" class="axis-label">Membrane position</text><text x="15" y="${(T+H-B)/2}" text-anchor="middle" transform="rotate(-90 15 ${(T+H-B)/2})" class="axis-label">Polarization factor</text></svg></div><p class="micro-note">The divalent curve is a conservative screening enhancement reflecting lower effective mass transfer of multivalent species. It is not a substitute for a species-specific diffusion model.</p></section>`;
}

function osmoticProfileChart(r){
  const factor=r.pressure_unit==='psi'?14.5037738:1,points=multistageSeries(r,'membrane_surface_osmotic_bar').map(p=>({...p,v:p.v*factor})).filter(p=>Number.isFinite(p.v));if(!points.length)return '';
  const W=820,H=255,L=54,R=20,T=22,B=42,vals=points.map(p=>p.v);let ymin=Math.min(...vals),ymax=Math.max(...vals);const spread=Math.max(ymax-ymin,Math.max(1,ymax)*.08);ymin=Math.max(0,ymin-spread*.18);ymax+=spread*.18;const n=Math.max(1,points.length-1),x=p=>L+(p.pos-1)*(W-L-R)/n,y=v=>T+(ymax-v)*(H-T-B)/(ymax-ymin||1),grid=[];
  for(let i=0;i<=4;i++){const v=ymax-(ymax-ymin)*i/4,yy=T+(H-T-B)*i/4;grid.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="flux-grid"/><text x="${L-8}" y="${yy+3}" text-anchor="end" class="flux-axis-text">${fmt(v)}</text>`)}
  const path=points.map((p,i)=>`${i?'L':'M'} ${x(p).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' '),dots=points.map(p=>`<g class="flux-point"><circle cx="${x(p)}" cy="${y(p.v)}" r="4.2"/><text x="${x(p)}" y="${y(p.v)-9}" text-anchor="middle" class="flux-value">${fmt(p.v)}</text><title>Position ${p.pos} · Stage ${p.stage}, element ${p.local}: ${fmt(p.v)} ${r.pressure_unit}</title></g>`).join(''),ticks=points.map(p=>`<text x="${x(p)}" y="${H-B+18}" text-anchor="middle" class="flux-axis-text">${p.pos}</text>`).join('');
  return `<section class="report-section flux-chart-section"><div class="chart-title-row"><h3>OSMOTIC PRESSURE vs. MEMBRANE POSITION</h3><span>Membrane-surface osmotic pressure</span></div><div class="flux-chart-wrap"><svg viewBox="0 0 ${W} ${H}">${grid.join('')}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/>${stageBoundariesSvg(points,x,T,H,B,L,W,R)}<path d="${path}" class="flux-line"/>${dots}${ticks}<text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" class="flux-axis-title">Membrane position</text><text x="15" y="${(T+H-B)/2}" transform="rotate(-90 15 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Osmotic pressure (${r.pressure_unit})</text></svg></div></section>`;
}

function turboRows(r){
  const pu=r.pressure_unit, fu=r.flow_unit; let rows=[];
  const biturboExtra=mode==='biturbo'?'<th>BiTurbo feed derate</th>':'';
  const hdr=`<tr><th>Turbo</th><th>Pfin<br><span>${pu}</span></th><th>Boost Pressure<br><span>${pu}</span></th><th>Qpf<br><span>${fu}</span></th><th>ΔPr<br><span>${pu}</span></th><th>Qtr<br><span>${fu}</span></th><th>Pex<br><span>${pu}</span></th><th>Neff</th>${biturboExtra}<th>Kvt</th><th>Aux</th><th>Qbyp<br><span>${fu}</span></th></tr>`;
  if(mode==='biturbo'){
    const pre=Number(r.feed_turbo_eff_before_biturbo_derate),pen=Number(r.feed_turbo_biturbo_derate_percentage_points);
    const derate=Number.isFinite(pre)&&Number.isFinite(pen)?`${pct(pre)}% − ${fmt(pen,1)} pt = <strong>${pct(r.feed_turbo_eff)}%</strong>`:`<strong>${pct(r.feed_turbo_eff)}%</strong>`;
    rows.push(`<tr><td>Feed</td>${cell(r.feed_turbo_pfin)}${cell(r.feed_turbo_boost)}${cell(r.feed_flow)}${cell(r.feed_turbine_dp)}${cell(r.feed_turbine_flow)}${cell(r.pex)}<td>${pct(r.feed_turbo_eff)}%</td><td>${derate}</td><td>${fmt(r.feed_kv_required,1)}</td><td>${pct(r.feed_aux_opening,1)}%</td>${cell(r.feed_bypass_flow_required)}</tr>`);
    rows.push(`<tr><td>Interstage</td>${cell(r.inter_turbo_pfin)}${cell(r.interstage_boost)}${cell(r.reject_flow_1)}${cell(r.interstage_turbine_dp)}${cell(r.interstage_turbine_flow)}${cell(r.brine_discharge_pressure)}<td>${pct(r.turbo_eff)}%</td><td>No extra feed-turbo derate</td><td>${fmt(r.inter_kv_required,1)}</td><td>${pct(r.inter_aux_opening,1)}%</td>${cell(r.inter_bypass_flow_required)}</tr>`);
  } else {
    const boost=mode==='single'?r.turbo_boost:r.interstage_boost;
    rows.push(`<tr><td>${mode==='single'?'Feed':'Interstage'}</td>${cell(r.turbo_pfin)}${cell(boost)}${cell(mode==='single'?r.feed_flow:r.reject_flow_1)}${cell(r.turbine_dp)}${cell(r.turbine_flow)}${cell(mode==='single'?r.pex:r.pex)}<td>${pct(r.turbo_eff)}%</td><td>${fmt(r.kv_required,1)}</td><td>${pct(r.aux_opening,1)}%</td>${cell(r.bypass_flow_required)}</tr>`);
  }
  return `<section class="report-section"><h3>TURBO CASE ANALYSIS</h3><div class="table-wrap"><table class="fedco-table">${hdr}${rows.join('')}</table></div></section>`;
}
function dutyCards(r){
  let cards=[];
  const mk=(title,prefix,eff,flow,dp,pex)=>{
    const isFeedBiTurbo=mode==='biturbo'&&prefix==='feed_';
    const preT=Number(r.feed_turbine_component_eff_before_biturbo_derate),preP=Number(r.feed_pump_component_eff_before_biturbo_derate),preO=Number(r.feed_turbo_eff_before_biturbo_derate),pen=Number(r.feed_turbo_biturbo_derate_percentage_points);
    const derateAudit=isFeedBiTurbo&&Number.isFinite(preT)&&Number.isFinite(preP)&&Number.isFinite(preO)&&Number.isFinite(pen)?`<dt>Turbine η · base</dt><dd>${pct(preT)}%</dd><dt>Pump η · base</dt><dd>${pct(preP)}%</dd><dt>Overall η · base</dt><dd>${pct(preO)}%</dd><dt>BiTurbo feed derate</dt><dd>−${fmt(pen,1)} %-points</dd>`:'';
    const netLabel=isFeedBiTurbo?' · net':'';
    return `<div class="duty-card"><h4>${title}</h4><dl><dt>SG</dt><dd>${fmt(r[prefix+'sg']??1.025,3)}</dd><dt>Turbine flow</dt><dd>${fmt(flow)} ${r.flow_unit}</dd><dt>ΔP turbine</dt><dd>${fmt(dp)} ${r.pressure_unit}</dd><dt>Pex</dt><dd>${fmt(pex)} ${r.pressure_unit}</dd>${derateAudit}<dt>Turbine η${netLabel}</dt><dd>${pct(r[prefix+'turbine_component_eff']??r.turbine_component_eff)}%</dd><dt>Pump η${netLabel}</dt><dd>${pct(r[prefix+'pump_component_eff']??r.pump_component_eff)}%</dd><dt>Overall η${netLabel}</dt><dd>${pct(eff)}%</dd><dt>Cvt · required</dt><dd>${fmt(r[prefix+'cv_required'],2)}</dd><dt>Cvt · aux closed</dt><dd>${fmt(r[prefix+'cvc'],2)}</dd><dt>Cvt · aux open</dt><dd>${fmt(r[prefix+'cvo'],2)}</dd><dt>Auxiliary valve</dt><dd>${pct(r[prefix+'aux_opening'])}%</dd><dt>Backpressure</dt><dd>${fmt(r[prefix+'backpressure_required'])} ${r.pressure_unit}</dd><dt>Bypass</dt><dd>${fmt(r[prefix+'bypass_flow_required'])} ${r.flow_unit}</dd></dl><p class="micro-note">${escapeHtml(r[prefix+'turbo_efficiency_method']||r.turbo_efficiency_method||'')}</p></div>`;
  };
  if(mode==='biturbo'){
    cards.push(mk('FEED TURBO DUTY PT','feed_',r.feed_turbo_eff,r.feed_turbine_flow,r.feed_turbine_dp,r.pex));
    cards.push(mk('INTERSTAGE TURBO DUTY PT','inter_',r.turbo_eff,r.interstage_turbine_flow,r.interstage_turbine_dp,r.brine_discharge_pressure));
  } else cards.push(mk(`${mode==='single'?'FEED':'INTERSTAGE'} TURBO DUTY PT`,'',r.turbo_eff,r.turbine_flow,r.turbine_dp,r.pex));
  return `<section class="report-section duty-grid">${cards.join('')}<div class="duty-card terminology"><h4>TERMINOLOGY</h4><dl><dt>Pfin</dt><dd>Feed pressure to turbo</dd><dt>Qpf</dt><dd>Flow through turbocharger pump side</dd><dt>Pf</dt><dd>Membrane pressure</dd><dt>Boost Pressure</dt><dd>Pressure increase produced by the turbocharger; not RO vessel pressure drop</dd><dt>Qtr</dt><dd>Reject/brine flow through turbocharger turbine side</dd><dt>RR</dt><dd>Reject Ratio = Qtr/Qpf; must be > 0.20, peak match about 0.65–0.70</dd><dt>ΔPr</dt><dd>Brine pressure drop through turbo</dd><dt>Pex</dt><dd>Brine pressure at turbo outlet</dd><dt>Neff</dt><dd>Turbo transfer efficiency</dd><dt>Kvt</dt><dd>Brine flow coefficient through turbo</dd><dt>Qbyp</dt><dd>Brine bypass flow around turbo</dd></dl></div></section>`;
}
function membraneChecks(r){let html='<section class="report-section"><h3>MEMBRANE HYDRAULIC / OSMOTIC CHECK</h3><div class="check-grid">';Array.from({length:resultStageCount(r)},(_,j)=>j+1).forEach(i=>{if(r[`stage${i}_pressure_vessels`]===undefined)return;const frac=r[`stage${i}_dp_limit_fraction`];const osm=r.membrane_coupling?`<span>Feed osmotic pressure: ${fmt(r[`stage${i}_feed_osmotic`])} ${r.pressure_unit}</span><span>Concentrate osmotic pressure: ${fmt(r[`stage${i}_concentrate_osmotic`])} ${r.pressure_unit}</span><span>Feed φ: ${fmt(r[`stage${i}_feed_osmotic_coefficient`])} · I: ${fmt(r[`stage${i}_feed_ionic_strength`])} mol/kg</span><span>Concentrate φ: ${fmt(r[`stage${i}_concentrate_osmotic_coefficient`])} · I: ${fmt(r[`stage${i}_concentrate_ionic_strength`])} mol/kg</span>${r[`stage${i}_feed_charge_imbalance_pct`]!==undefined?`<span>Feed charge imbalance: ${fmt(r[`stage${i}_feed_charge_imbalance_pct`])}%</span>${r[`stage${i}_reported_tds_ppm`]!==undefined?`<span>Reported TDS: ${fmt(r[`stage${i}_reported_tds_ppm`])} mg/L · species sum: ${fmt(r[`stage${i}_feed_tds_ppm`])} mg/L</span>`:''}`:''}`:'';html+=`<div class="check-card"><strong>Stage ${i}</strong><span>${fmt(r[`stage${i}_vessel_feed_flow`])} ${r.flow_unit} feed / vessel</span><span>${fmt(r[`stage${i}_vessel_reject_flow`])} ${r.flow_unit} reject / vessel</span><span>${fmt(r[`stage${i}_stage_dp`])} ${r.pressure_unit} calculated clean vessel ΔP</span><span>${fmt(r[`stage${i}_max_actual_dp_per_element`])} ${r.pressure_unit} maximum element ΔP</span><span>Datasheet limit: ${fmt(r[`stage${i}_datasheet_max_dp_per_element`])} ${r.pressure_unit} / element</span>${osm}<b class="${frac>1?'bad':'ok'}">${frac>1?'EXCEEDS DATASHEET LIMIT':'Within datasheet ΔP limit'}</b></div>`});return html+'</div><p class="micro-note">Reject pressure is calculated automatically from the clean element-by-element pressure drop. With RO coupling active, full-analysis mode calculates osmotic pressure from the entered multi-ion composition using a pyEQL-calibrated effective-Pitzer osmotic surrogate when available; direct pyEQL is retained as the reference path, and TDS quick mode retains the NaCl-equivalent φ(T,I) model.</p></section>';}

function acidDosingReport(r){
  const d=r?.acid_dosing;if(!r?.acid_dosing_enabled||!d)return '';
  const acid=String(d.acid_type||r.acid_type||'').toLowerCase()==='h2so4'?'H₂SO₄':'HCl';const added=acid==='H₂SO₄'?['SO₄²⁻ added',d.sulfate_added_mg_l]:['Cl⁻ added',d.chloride_added_mg_l];
  return `<section class="report-section acid-result-section"><div class="chart-title-row"><h3>CHEMICAL DOSING · ${acid}</h3><span>Calculated with this operating case</span></div><div class="kpi-strip five"><div><span>Pure acid dose</span><strong>${fmt(d.pure_acid_mg_l,2)} mg/L</strong></div><div><span>Commercial solution</span><strong>${fmt(d.commercial_solution_l_m3,4)} L/m³</strong></div><div><span>Pure acid mass</span><strong>${fmt(d.pure_acid_kg_h,2)} kg/h</strong><small>${fmt(d.pure_acid_kg_d,1)} kg/day</small></div><div><span>Commercial solution</span><strong>${fmt(d.commercial_solution_l_h,2)} L/h</strong><small>${fmt(Number(d.commercial_solution_l_h||0)*24,1)} L/day</small></div><div><span>pH</span><strong>${fmt(d.feed_ph,2)} → ${fmt(d.resulting_ph,2)}</strong><small>Target ${fmt(d.target_ph,2)}</small></div></div><div class="check-grid"><div class="check-card"><strong>Alkalinity</strong><span>Before: ${fmt(d.feed_alkalinity_mg_l_as_hco3,2)} mg/L as HCO₃⁻</span><span>After: ${fmt(d.resulting_alkalinity_mg_l_as_hco3,2)} mg/L as HCO₃⁻</span></div><div class="check-card"><strong>Counter-ion addition</strong><span>${added[0]}: ${fmt(added[1],2)} mg/L</span><span>Water chemistry is re-solved before the membrane calculation.</span></div></div><p class="micro-note">The untreated source-water analysis remains stored in Water Quality. Acid consumption is recalculated independently for every N/N−1 and hydraulic-envelope case using that case's actual RO feed flow.</p></section>`;
}
function biturboFeasibilityReport(r){
  if(!r||mode!=='biturbo')return '';
  if(r.generalized_biturbo){
    const pos=Array.isArray(r.biturbo_turbo_positions)?r.biturbo_turbo_positions:[];const rows=pos.map(x=>`<tr><td>Stage ${x.from_stage} → ${x.to_stage}</td><td>${escapeHtml(String(x.equipment||'').replaceAll('_',' + '))}</td><td>${fmt(x.pump_side_feed_tds_mg_l,0)}</td><td>${fmt(x.qpf,1)}</td><td>${fmt(x.qtr,1)}</td><td><strong>${fmt(x.reject_ratio,3)}</strong></td><td>${escapeHtml(x.reject_ratio_status||'')}</td></tr>`).join('');
    return `<section class="report-section"><div class="chart-title-row"><h3>MULTISTAGE BITURBO FEASIBILITY</h3><span class="status-chip ok">${pos.length} turbochargers · Candidate</span></div><div class="table-wrap"><table class="fedco-table"><tr><th>Hydraulic position</th><th>Equipment</th><th>Pump-side feed TDS<br><span>mg/L</span></th><th>Qpf · pump side<br><span>${r.flow_unit}</span></th><th>Qtr · turbine side<br><span>${r.flow_unit}</span></th><th>Reject Ratio<br><span>Qtr/Qpf</span></th><th>Match</th></tr>${rows}</table></div><p class="micro-note">Hard gates: local pump-side feed TDS ≥ 30,000 mg/L for each BiTurbo position and Qtr/Qpf &gt; 0.20 for every turbocharger. Peak hydraulic matching is approximately Qtr/Qpf = 0.65–0.70. Hydraulic-energy availability still governs whether Turbo alone or Turbo + Booster Pump can provide the requested boost.</p></section>`;
  }
  const tds=Number(r.biturbo_screen_tds_mg_l);const feedRR=Number(r.feed_turbo_reject_ratio),interRR=Number(r.inter_turbo_reject_ratio);
  const feedSrc=Number(r.biturbo_feed_source_hydraulic_kw),feedUse=Number(r.biturbo_feed_boost_hydraulic_kw),interSrc=Number(r.biturbo_interstage_source_hydraulic_kw),interUse=Number(r.biturbo_interstage_boost_hydraulic_kw);
  const feedPre=Number(r.feed_turbo_eff_before_biturbo_derate),feedPenalty=Number(r.feed_turbo_biturbo_derate_percentage_points),feedNet=Number(r.feed_turbo_eff);
  return `<section class="report-section"><div class="chart-title-row"><h3>BITURBO HYDRAULIC-ENERGY SCREEN</h3><span class="status-chip ok">Candidate</span></div><div class="kpi-strip five"><div><span>TDS screening</span><strong>${Number.isFinite(tds)?fmt(tds,0)+' mg/L':'—'}</strong><small>30,000 mg/L hard local screen</small></div><div><span>Feed turbo RR</span><strong>${Number.isFinite(feedRR)?fmt(feedRR,3):'—'}</strong><small>Qtr/Qpf</small></div><div><span>Interstage turbo RR</span><strong>${Number.isFinite(interRR)?fmt(interRR,3):'—'}</strong><small>Qtr/Qpf</small></div><div><span>Feed turbo η</span><strong>${Number.isFinite(feedNet)?pct(feedNet)+'%':'—'}</strong><small>${Number.isFinite(feedPre)&&Number.isFinite(feedPenalty)?pct(feedPre)+'% base − '+fmt(feedPenalty,1)+' pt':'net BiTurbo feed efficiency'}</small></div><div><span>Interstage boost</span><strong>${Number.isFinite(interUse)?fmt(interUse,1)+' kW':'—'}</strong></div></div><p class="micro-note">${escapeHtml(r.biturbo_tds_screen_note||'The actual reject-flow and pressure energy balance governs BiTurbo feasibility.')} Each turbocharger is prohibited at Qtr/Qpf ≤ 0.20; the preferred peak-efficiency flow-match region is approximately 0.65–0.70.</p></section>`;
}

function multistageTurboAssessment(r){
  if(!r?.plant_designer)return '';const n=resultStageCount(r);const rows=[];
  for(let i=2;i<=n;i++){const eq=r[`stage${i}_interstage_equipment`];if(!eq)continue;const rr=Number(r[`stage${i}_interstage_reject_ratio`]),qpf=Number(r[`stage${i}_interstage_turbo_pump_flow`]),qtr=Number(r[`stage${i}_interstage_turbo_turbine_flow`]),tds=Number(r[`stage${i}_interstage_turbo_pump_side_tds_mg_l`]);const suit=String(r[`stage${i}_interstage_turbo_suitability`]||'');const need=Number(r[`stage${i}_interstage_required_hydraulic_kw`]||0),turbo=Number(r[`stage${i}_interstage_turbo_hydraulic_kw`]||0),pump=Number(r[`stage${i}_interstage_booster_hydraulic_kw`]||0);const cls=suit==='peak'||suit==='good'?'ok':suit==='not_allowed'||suit==='poor'?'bad':'';rows.push(`<tr><td>Stage ${i-1} → ${i}</td><td>${escapeHtml(String(eq).replaceAll('_',' + '))}</td><td>${fmt(tds,0)}</td><td>${fmt(qpf,1)}</td><td>${fmt(qtr,1)}</td><td><strong>${Number.isFinite(rr)?fmt(rr,3):'—'}</strong></td><td class="${cls}">${escapeHtml(suit||'—')}</td><td>${fmt(need,1)}</td><td>${fmt(turbo,1)}</td><td>${fmt(pump,1)}</td></tr>`)}
  const control=String(r.interstage_control_objective||'manual');let controlHtml='';
  if(control!=='manual'){
    const label={balance_flux:'Balance flux',balance_polarization:'Balance polarization factor',target_recovery:'Target downstream-stage recovery'}[control]||control;
    const basis=String(r.interstage_control_balance_basis||'average');const metrics=Array.isArray(r.interstage_control_stage_metrics)?r.interstage_control_stage_metrics:[];
    const unit=control==='balance_flux'?fluxUnit():control==='balance_polarization'?'CP':'fraction';
    const metricText=metrics.length?metrics.map((v,i)=>`Stage ${i+1}: ${control==='balance_flux'?fmt(fluxValue(v),2):fmt(v,3)} ${unit}`).join(' · '):'';
    const seeds=r.interstage_control_seed_boost_bar||{};const seedText=Object.keys(seeds).length?Object.entries(seeds).map(([st,v])=>`S${Number(st)-1}→S${st}: ${fmt(convert(Number(v),'pressure','bar',r.pressure_unit||currentUnits.pressure),2)} ${r.pressure_unit||currentUnits.pressure}`).join(' · '):'';
    controlHtml=`<div class="engineering-callout"><strong>Automatic interstage pressure control · ${escapeHtml(label)}</strong><span>${control.startsWith('balance_')?`Basis: ${basis==='lead'?'lead element in every stage':'stage average'}. `:''}${metricText}</span>${seedText?`<span>Physics seed: ΔP ≈ osmotic-pressure rise since last hydraulic-energy input · ${escapeHtml(seedText)}</span>`:''}<span>Method: ${escapeHtml(r.interstage_control_method||'bounded nonlinear solve')} · ${r.interstage_control_iterations||0} iterations · residual ${fmt(r.interstage_control_residual,4)}</span></div>`;
  } else if(r.interstage_manual_max_turbo_stage){const tb=Number(r.interstage_manual_max_turbo_boost_bar),tot=Number(r.interstage_manual_total_boost_bar??tb),req=Number(r.interstage_manual_requested_boost_bar??tot);controlHtml=`<div class="engineering-callout"><strong>Maximum available hydraulic energy</strong><span>Stage ${Number(r.interstage_manual_max_turbo_stage)-1} → ${r.interstage_manual_max_turbo_stage}: self-consistent maximum turbo contribution ${fmt(tb,2)} bar · total interstage boost ${fmt(tot,2)} bar${tot>tb+0.01?` · booster remainder ${fmt(tot-tb,2)} bar`:''}.</span><span>Original manual pressure target: ${fmt(req,2)} bar.</span></div>`;}
  if(!rows.length&&!controlHtml)return '';
  return `${controlHtml}${rows.length?`<section class="report-section"><div class="chart-title-row"><h3>TURBOCHARGER HYDRAULIC-ENERGY ASSESSMENT</h3><span>Final-reject recoverable pool ${fmt(r.multistage_turbo_available_hydraulic_kw,1)} kW</span></div><div class="table-wrap"><table class="fedco-table"><tr><th>Interstage</th><th>Equipment</th><th>Pump-side feed TDS<br><span>mg/L</span></th><th>Qpf<br><span>${r.flow_unit}</span></th><th>Qtr<br><span>${r.flow_unit}</span></th><th>Reject Ratio<br><span>Qtr/Qpf</span></th><th>Hydraulic match</th><th>Required hydraulic<br><span>kW</span></th><th>Turbo contribution<br><span>kW</span></th><th>Pump contribution<br><span>kW</span></th></tr>${rows.join('')}</table></div><p class="micro-note">Qpf is the flow through the pump side of that turbocharger; Qtr is the reject/brine flow through its turbine side. Qtr/Qpf ≤ 0.20 is prohibited because turbocharger efficiency is expected to be very low. Peak efficiency is normally reached around Qtr/Qpf = 0.65–0.70. Remaining unused recoverable pool: ${fmt(r.multistage_turbo_unused_hydraulic_kw,1)} kW.</p></section>`:''}`;
}
function multistagePxReport(r){
  const fu=r.flow_unit,pu=r.pressure_unit,control=String(r.px_hydraulic_control||'direct');const ctl=control==='booster'?'Booster / recirculation pump':control==='throttle'?'Throttling / control valve':'Direct pressure match';const note=control==='throttle'?'The excess IC outlet pressure comes from upstream/interstage pumping retained in final brine. It is not additional isobaric efficiency.':'';
  const op=Number(r.px_operating_qty??r.px_qty),inst=Number(r.px_installed_qty_per_train??r.px_qty),standby=Number(r.px_standby_or_bypassed_qty??Math.max(0,inst-op));const lo=Number(r.px_min_unit_flow),hi=Number(r.px_max_unit_flow),range=hi>0?`${lo>0?fmt(lo)+'–':''}${fmt(hi)} ${fu}`:'Not defined for generic device';
  return `<section class="report-section"><div class="chart-title-row"><h3>MULTISTAGE BWRO / SWRO ISOBARIC HYDRAULIC BALANCE</h3><span>${escapeHtml(ctl)}</span></div><div class="kpi-strip five"><div><span>Final brine → IC</span><strong>${fmt(r.px_hp_in_pressure,2)} ${pu}</strong><small>${fmt(r.reject_flow_final,1)} ${fu}</small></div><div><span>IC feed outlet</span><strong>${fmt(r.px_lp_out_pressure,2)} ${pu}</strong></div><div><span>Required Stage 1 header</span><strong>${fmt(r.px_header_pressure_required,2)} ${pu}</strong></div><div><span>Pressure balance</span><strong>${fmt(r.px_pressure_balance,2)} ${pu}</strong><small>${escapeHtml(control)}</small></div><div><span>Recovered hydraulic power</span><strong>${fmt(r.px_recovered_kw,1)} kW</strong></div></div><div class="duty-grid"><div class="duty-card"><h4>FLOW SPLIT & PUMPING</h4><dl><dt>Total membrane feed</dt><dd>${fmt(r.feed_flow)} ${fu}</dd><dt>IC / PX feed branch</dt><dd>${fmt(r.px_lp_flow)} ${fu}</dd><dt>HPP branch</dt><dd>${fmt(r.hpp_flow)} ${fu}</dd><dt>HPP wire power</dt><dd>${fmt(r.hpp_kw)} kW</dd><dt>IC booster ΔP</dt><dd>${fmt(r.circ_dp)} ${pu}</dd><dt>IC booster power</dt><dd>${fmt(r.circ_kw)} kW</dd></dl></div><div class="duty-card"><h4>PX / IC BANK SIZING</h4><dl><dt>Model</dt><dd>${escapeHtml(r.px_model||'Generic')}</dd><dt>Operating units</dt><dd>${fmt(op,0)}</dd><dt>Installed units / train</dt><dd>${fmt(inst,0)}</dd><dt>Standby / bypassed units</dt><dd>${fmt(standby,0)}</dd><dt>Flow / operating unit</dt><dd>${fmt(r.px_unit_flow)} ${fu}</dd><dt>Unit-flow envelope</dt><dd>${escapeHtml(range)}</dd><dt>Flow status</dt><dd class="${r.px_within_flow_range===false?'bad':'ok'}">${r.px_within_flow_range===false?'Outside range':'Within / no range defined'}</dd><dt>Auto sizing</dt><dd>${r.px_bank_auto_size?'On':'Off'}</dd>${r.px_bank_governing_case?`<dt>Governing bank case</dt><dd>${escapeHtml(r.px_bank_governing_case)}</dd>`:''}</dl><p class="micro-note">${escapeHtml(r.px_bank_sizing_basis||'Current duty-point sizing')}${r.px_bank_sized_for_nminus1?' · N−1 governs installed quantity.':''}${r.px_bank_sizing_reason?` · ${escapeHtml(r.px_bank_sizing_reason)}`:''}</p></div><div class="duty-card"><h4>PRESSURE TRANSFER & CONTROL</h4><dl><dt>IC HP inlet</dt><dd>${fmt(r.px_hp_in_pressure)} ${pu}</dd><dt>IC HP outlet</dt><dd>${fmt(r.px_hp_out_pressure)} ${pu}</dd><dt>IC LP inlet</dt><dd>${fmt(r.px_lp_in_pressure)} ${pu}</dd><dt>IC LP outlet</dt><dd>${fmt(r.px_lp_out_pressure)} ${pu}</dd><dt>Control action</dt><dd><strong>${escapeHtml(ctl)}</strong></dd><dt>Header match tolerance</dt><dd>${fmt(r.px_header_tolerance)} ${pu} · HPP inlet linked</dd><dt>Throttle ΔP</dt><dd>${fmt(r.px_throttle_dp)} ${pu}</dd><dt>Throttle dissipation</dt><dd>${fmt(r.px_throttle_dissipation_kw)} kW</dd></dl></div></div><div class="check-grid"><div class="check-card"><strong>Pressure-transfer basis</strong><span>Net transfer efficiency: ${pct(r.px_pressure_transfer_efficiency)}%</span><span>Flow-balance factor: ${pct(r.px_flow_balance_efficiency)}%</span><span>Mixing: ${pct(r.px_mixing)}%</span></div><div class="check-card"><strong>Salinity feedback</strong><span>Raw feed TDS: ${fmt(r.raw_feed_tds,0)} mg/L</span><span>Effective membrane feed TDS: ${fmt(r.effective_membrane_feed_tds,0)} mg/L</span><span>${r.px_coupling_iterations||1} chemistry/hydraulic coupling iterations</span></div></div>${note?`<div class="engineering-callout warning"><strong>Why the throttling valve appears</strong><span>${escapeHtml(note)}</span></div>`:''}<p class="micro-note">Without interstage boosting, final-brine pressure normally leaves the IC feed branch below the Stage-1 header and a booster/recirculation pump is calculated. With sufficient interstage boost, the final brine can be above the Stage-1 requirement; Total RO Design then replaces the IC booster duty with throttling and reports the dissipated pressure energy.</p></section>`;
}
function pxKpis(r){return `<div class="kpi-strip five"><div><span>Product flow</span><strong>${fmt(r.product_flow)} ${r.flow_unit}</strong></div><div><span>Overall system recovery</span><strong>${pct(r.recovery)}%</strong></div><div><span>RO SEC</span><strong>${fmt(r.ro_sec)} kWh/m³</strong></div><div><span>Pretreatment SEC</span><strong>${fmt(r.pretreatment_sec)} kWh/m³</strong></div><div><span>Total plant SEC</span><strong>${fmt(r.total_sec)} kWh/m³</strong></div></div>`}
function pxReport(r){const fu=r.flow_unit,pu=r.pressure_unit;const motor=r.px_architecture==='motorized';const op=Number(r.px_operating_qty??r.px_qty),inst=Number(r.px_installed_qty_per_train??r.px_qty),standby=Number(r.px_standby_or_bypassed_qty??Math.max(0,inst-op));const lo=Number(r.px_min_unit_flow),hi=Number(r.px_max_unit_flow),range=hi>0?`${lo>0?fmt(lo)+'–':''}${fmt(hi)} ${fu}`:'Not defined';return `<section class="report-section"><h3>ISOBARIC CHAMBER DUTY POINT</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Architecture</th><th>Model</th><th>Operating Qty</th><th>Installed / train</th><th>Unit flow<br><span>${fu}</span></th><th>HP IN<br><span>${pu}</span></th><th>HP OUT<br><span>${pu}</span></th><th>HP ΔP<br><span>${pu}</span></th><th>LP / feed IN<br><span>${pu}</span></th><th>Brine OUT<br><span>${pu}</span></th><th>LP ΔP<br><span>${pu}</span></th><th>Mixing</th><th>Efficiency</th></tr><tr><td>${motor?'Motorized active':'Passive'}</td><td>${escapeHtml(r.px_model)}</td><td>${fmt(op,0)}</td><td>${fmt(inst,0)}${standby>0?` <small>(${fmt(standby,0)} standby)</small>`:''}</td>${cell(r.px_unit_flow)}${cell(r.px_hp_in_pressure)}${cell(r.px_hp_out_pressure)}${cell(r.px_hp_dp)}${cell(r.px_lp_in_pressure)}${cell(r.px_lp_out_pressure)}${cell(r.px_lp_dp)}<td>${pct(r.px_mixing)}%</td><td>${pct(r.px_overall_eff)}%</td></tr></table></div>${r.px_bank_governing_case?`<p class="micro-note"><strong>Governing installed IC bank:</strong> ${escapeHtml(r.px_bank_governing_case)}${r.px_bank_sized_for_nminus1?' · N−1 governs.':''}</p>`:''}</section><section class="report-section duty-grid"><div class="duty-card"><h4>ISOBARIC CHAMBER SYSTEM POWER RESULTS</h4><dl><dt>HP pump flow</dt><dd>${fmt(r.hpp_flow)} ${fu}</dd><dt>HP pump power</dt><dd>${fmt(r.electric_kw)} kW</dd><dt>Circulation / booster flow</dt><dd>${fmt(r.circ_flow)} ${fu}</dd><dt>Circulation / booster ΔP</dt><dd>${fmt(r.circ_dp)} ${pu}</dd><dt>Circulation / booster power</dt><dd>${fmt(r.circ_kw)} kW</dd><dt>ERD motor power</dt><dd>${fmt(r.px_motor_kw)} kW</dd><dt>Recovered hydraulic power</dt><dd>${fmt(r.px_recovered_kw)} kW</dd><dt>IC auxiliary SEC</dt><dd>${fmt(r.px_aux_sec)} kWh/m³</dd></dl></div><div class="duty-card"><h4>ISOBARIC CHAMBER HYDRAULIC / SALINITY CHECK</h4><dl><dt>IC LP/feed inlet pressure</dt><dd>${fmt(r.px_lp_in_pressure)} ${pu} · same as HP pump inlet</dd><dt>IC brine exit backpressure</dt><dd>${fmt(r.px_lp_out_pressure)} ${pu}</dd><dt>Unit flow range</dt><dd>${escapeHtml(range)}</dd><dt>Flow status</dt><dd class="${r.px_within_flow_range===false?'bad':'ok'}">${r.px_within_flow_range===false?'Outside preferred range':'Within range'}</dd><dt>Lubrication flow</dt><dd>${fmt(r.px_lubrication_flow)} ${fu}</dd><dt>Base feed TDS</dt><dd>${fmt(r.raw_feed_tds??0)} ppm</dd><dt>IC HP-out TDS</dt><dd>${fmt(r.px_feed_tds_after_mixing)} ppm</dd><dt>Effective membrane feed TDS</dt><dd>${fmt(r.effective_membrane_feed_tds)} ppm</dd></dl>${motor&&r.px_motor_power_is_estimate?'<p class="micro-note">Active/motorized Isobaric Chamber motor power and internal losses are calculated automatically from the embedded engineering model and the converged duty point. The displayed values are screening estimates; verify final selection with vendor data.</p>':'<p class="micro-note">Passive Isobaric Chamber losses, lubrication and mixing use the embedded legacy reference correlations.</p>'}</div></section>`}
function mechanicalErdReport(r){
  if(mode==='dweer')return `<section class="report-section"><div class="chart-title-row"><h3>DWEER WORK-EXCHANGER DUTY</h3><span>${escapeHtml(r.dweer_model_basis||'')}</span></div><div class="kpi-strip five"><div><span>DWEER modules</span><strong>${fmt(r.dweer_modules_required,0)}</strong><small>${fmt(r.dweer_module_design_flow,1)} ${r.flow_unit}/module</small></div><div><span>Device efficiency</span><strong>${pct(r.dweer_device_efficiency)}%</strong></div><div><span>HPP make-up flow</span><strong>${fmt(r.dweer_hpp_makeup_flow,1)} ${r.flow_unit}</strong></div><div><span>HP booster ΔP</span><strong>${fmt(r.dweer_hp_booster_dp,2)} ${r.pressure_unit}</strong></div><div><span>Mixing osmotic penalty</span><strong>${fmt(r.dweer_mixing_osmotic_penalty_dp,2)} ${r.pressure_unit}</strong></div></div><div class="table-wrap"><table class="fedco-table"><tr><th>Quantity</th><th>Value</th></tr><tr><td>Final brine into HP end</td><td>${fmt(r.dweer_brine_in_flow,1)} ${r.flow_unit}</td></tr><tr><td>Pressure-exchanged feed</td><td>${fmt(r.dweer_hp_feed_out_flow,1)} ${r.flow_unit}</td></tr><tr><td>Overflush</td><td>${fmt(r.dweer_overflush_flow,1)} ${r.flow_unit}</td></tr><tr><td>HP feed outlet pressure</td><td>${fmt(r.dweer_hp_feed_out_pressure,2)} ${r.pressure_unit}</td></tr><tr><td>HPP electrical input</td><td>${fmt(r.dweer_hpp_electric_kw,1)} kW</td></tr><tr><td>DWEER booster electrical input</td><td>${fmt(r.dweer_booster_electric_kw,1)} kW</td></tr><tr><td>LP increment</td><td>${fmt(r.dweer_lp_increment_electric_kw,1)} kW</td></tr></table></div><p class="micro-note">${escapeHtml(r.dweer_note||'')}</p></section>`;
  if(mode==='pelton')return `<section class="report-section"><div class="chart-title-row"><h3>PELTON COMMON-SHAFT DUTY</h3><span>${escapeHtml(r.pelton_model_basis||'')}</span></div><div class="kpi-strip five"><div><span>Recovered shaft power</span><strong>${fmt(r.pelton_shaft_delivered_kw,1)} kW</strong></div><div><span>Energy recovery</span><strong>${pct(r.pelton_recovered_fraction)}%</strong></div><div><span>Runner diameter</span><strong>${fmt(r.pelton_runner_diameter_m,3)} m</strong></div><div><span>Jet diameter</span><strong>${fmt(r.pelton_jet_diameter_mm,1)} mm</strong></div><div><span>Jet ratio D/d</span><strong>${fmt(r.pelton_jet_ratio,2)}</strong><small>${escapeHtml(r.pelton_jet_ratio_status||'')}</small></div></div><div class="table-wrap"><table class="fedco-table"><tr><th>Quantity</th><th>Value</th></tr><tr><td>Final brine flow</td><td>${fmt(r.pelton_brine_flow,1)} ${r.flow_unit}</td></tr><tr><td>Pelton ΔP</td><td>${fmt(r.pelton_turbine_dp,2)} ${r.pressure_unit}</td></tr><tr><td>HP pump shaft power</td><td>${fmt(r.pelton_hpp_shaft_kw,1)} kW</td></tr><tr><td>Net motor shaft power</td><td>${fmt(r.pelton_net_motor_shaft_kw,1)} kW</td></tr><tr><td>Motor nameplate</td><td>${fmt(r.pelton_motor_nameplate_kw,0)} kW</td></tr><tr><td>Full pump-side shaft torque</td><td>${fmt(r.pelton_pump_side_shaft_torque_nm,0)} N·m</td></tr><tr><td>Specific speed</td><td>${fmt(r.pelton_specific_speed,2)} · ${escapeHtml(r.pelton_specific_speed_status||'')}</td></tr><tr><td>Runaway speed</td><td>${fmt(r.pelton_runaway_speed_rpm,0)} rpm</td></tr></table></div><p class="micro-note">${escapeHtml(r.pelton_note||'')}</p></section>`;
  return '';
}
function kpis(r){return `<div class="kpi-strip five"><div><span>Product flow</span><strong>${fmt(r.product_flow)} ${r.flow_unit}</strong></div><div><span>Overall recovery</span><strong>${pct(r.recovery)}%</strong></div><div><span>RO SEC</span><strong>${fmt(r.ro_sec)} kWh/m³</strong></div><div><span>Pretreatment SEC</span><strong>${fmt(r.pretreatment_sec)} kWh/m³</strong></div><div><span>Total plant SEC</span><strong>${fmt(r.total_sec)} kWh/m³</strong></div></div>`}
function solveStatus(r){
  let text,strong;const n=resultStageCount(r),multi=n>1,pressures=Array.from({length:n},(_,j)=>j+1).filter(i=>r[`membrane_pressure_${i}`]!==undefined).map(i=>`P<sub>f,${i}</sub>: ${fmt(r[`membrane_pressure_${i}`])} ${r.pressure_unit}`).join(' · ');
  if(r.solve_basis==='product'){text=multi?'Permeate setpoint → coupled multistage pressure solution':'Permeate setpoint → required pressure';strong=`${pressures} · Recovery: ${pct(r.recovery)}%`;}
  else if(r.solve_basis==='recovery'){text=multi?'Recovery setpoint → permeate + coupled multistage pressure solution':'Recovery setpoint → permeate + required pressure';strong=`Q<sub>p</sub>: ${fmt(r.product_flow)} ${r.flow_unit} · ${pressures}`;}
  else{text=multi?'Stage 1 pressure + booster setpoints → calculated multistage permeate & recovery':'Feed pressure setpoint → calculated permeate + recovery';strong=`Q<sub>p</sub>: ${fmt(r.product_flow)} ${r.flow_unit} · Recovery: ${pct(r.recovery)}%`;}
  return `<div class="solve-status"><span>${text}</span><strong>${strong}</strong></div>`;
}
function convergencePlotHtml(diag){const h=diag?.history||[];if(h.length<2)return '';const vals=h.map(x=>Math.max(Number(x.residual)||1e-16,1e-16)),logs=vals.map(v=>Math.log10(v)),min=Math.min(...logs),max=Math.max(...logs),W=430,H=120,L=34,R=10,T=12,B=24,x=i=>L+i*(W-L-R)/Math.max(1,h.length-1),y=v=>T+(max-v)*(H-T-B)/Math.max(1e-9,max-min);const pts=logs.map((v,i)=>`${x(i)},${y(v)}`).join(' '),dots=h.map((row,i)=>`<circle cx="${x(i)}" cy="${y(logs[i])}" r="${row.accepted===false?3.5:2.5}" class="${row.accepted===false?'solver-reject-point':'solver-accept-point'}"><title>Iteration ${row.iteration}: residual ${Number(row.residual).toExponential(3)} · ${escapeHtml(row.method||'')}</title></circle>`).join('');return `<svg class="solver-convergence-plot" viewBox="0 0 ${W} ${H}" role="img" aria-label="Solver residual convergence"><polyline points="${pts}" class="solver-residual-line"/>${dots}<text x="${L}" y="${H-6}" class="suite-chart-label">Iteration</text><text x="4" y="${T+8}" class="suite-chart-label">log residual</text></svg>`}
function solverDiagnostics(r){const items=[];if(r.pressure_solve_evaluations!==undefined)items.push(`<span><b>Stage 1 / overall solver</b> ${r.pressure_solve_evaluations} evaluations / ${r.pressure_solve_iterations||0} iterations</span>`);if(r.stage2_pressure_solve_evaluations){items.push(`<span><b>Stage 2 coupled solver</b> ${r.stage2_pressure_solve_evaluations} evaluations / ${r.stage2_pressure_solve_iterations||0} iterations · ${r.stage2_solver_method||'converged'}</span>`);if(r.stage2_pressure_search_backend)items.push(`<span><b>Interstage acceleration</b> ${escapeHtml(r.stage2_pressure_search_backend)} · ${r.stage2_pressure_search_workers||1} CPU worker(s)${r.stage2_gpu_screen_backend==='opencl-gpu'?` · GPU ${escapeHtml(r.stage2_gpu_screen_device||'OpenCL')}`:''}</span>`)}if(r.px_coupling_iterations!==undefined)items.push(`<span><b>Isobaric coupling</b> ${r.px_coupling_iterations} iterations · ${r.px_coupling_method||'converged'}${r.px_warm_start_used?' · thermodynamic warm start':''}</span>`);if(r.compute_backend)items.push(`<span><b>Compute</b> ${escapeHtml(String(r.compute_backend).replace('cpu-worker','multicore CPU worker').replace('cpu-main','CPU'))}</span>`);if(!items.length)return '';const fb=r.solver_fallback_used||r.stage2_solver_fallback_used||r.px_coupling_fallback,diag=r.solver_diagnostics,plot=convergencePlotHtml(diag);const audit=diag?`<details class="solver-audit"><summary>View Solver Diagnostics</summary>${plot}<div class="solver-audit-grid"><span>Final residual <b>${Number(diag.residual||0).toExponential(3)}</b></span><span>Tolerance <b>${diag.tolerance??'—'}</b></span><span>Rejected steps <b>${diag.rejected_steps||0}</b></span><span>Fallbacks <b>${escapeHtml((diag.fallbacks||[]).join(' → ')||'None')}</b></span><span>Solver time <b>${fmt(Number(diag.elapsed_ms||0),2)} ms</b></span></div></details>`:'';return `<div class="solver-diagnostics ${fb?'solver-fallback':''}"><strong>${fb?'Converged with safeguarded fallback':'Converged'}</strong>${items.join('')} ${r.solver_method?`<span><b>Method</b> ${r.solver_method}</span>`:''}${audit}</div>`}
function offDesignEquationNote(){return `<details class="offdesign-equations"><summary>Off-design efficiency equations</summary><div><span>η<sub>t</sub> = η<sub>t,d</sub> − η<sub>t,d</sub>(Q<sub>r</sub>−Q<sub>r,d</sub>)²/Q<sub>r,d</sub>² − η<sub>t,d</sub>(P<sub>r</sub>−P<sub>r,d</sub>)²/P<sub>r,d</sub>²</span><span>η<sub>p</sub> = η<sub>p,d</sub> − η<sub>p,d</sub>(Q<sub>f</sub>−Q<sub>f,d</sub>)²/Q<sub>f,d</sub>² − η<sub>p,d</sub>(P<sub>m</sub>−P<sub>m,d</sub>)²/P<sub>m,d</sub>²</span><span>η<sub>overall</sub> = η<sub>t</sub>η<sub>p</sub>, with η<sub>p,d</sub> = η<sub>t,d</sub> + 0.01 and η<sub>t,d</sub>η<sub>p,d</sub> = η<sub>design</sub>.</span></div></details>`}
function turboDesignStatus(r){
  if(!r?.turbo_design_locked)return '';
  if(mode==='biturbo'){
    const i=r.is_inter_design_case?`<b>Interstage design · Case ${r.inter_design_case_id}</b>`:`Interstage off-design vs Case ${r.inter_design_case_id}`;
    const f=r.is_feed_design_case?`<b>Feed design · Case ${r.feed_design_case_id}</b>`:`Feed off-design vs Case ${r.feed_design_case_id}`;
    return `<div class="turbo-design-status"><strong>LOCKED MULTI-CASE TURBO DESIGN</strong><span>${i}</span><span>${f}</span><span>Workbook quadratic off-design turbine/pump efficiency model</span>${offDesignEquationNote()}</div>`;
  }
  const text=r.is_design_case?`Design duty · Case ${r.design_case_id}`:`Off-design duty vs Case ${r.design_case_id}`;
  return `<div class="turbo-design-status"><strong>LOCKED MULTI-CASE TURBO DESIGN</strong><span>${text}</span><span>Workbook quadratic off-design turbine/pump efficiency model</span>${offDesignEquationNote()}</div>`;
}

function turboNeedsFluxOptimization(r){
  if(!r||!r.turbo_design_locked||!['single','interstage','biturbo'].includes(mode))return false;
  const bad=x=>['backpressure_required','bypass_required','below_cvc','above_cvo'].includes(String(x||''));
  return mode==='biturbo'?(bad(r.inter_duty_status||r.inter_cv_status)||bad(r.feed_duty_status||r.feed_cv_status)):bad(r.duty_status||r.cv_status);
}
function hasFluxUndo(){return !!caseStore[activeCase]?.fluxOptimizationUndo?.[mode]}
function fluxOptimizationPanel(r){
  if(!['single','interstage','biturbo'].includes(mode)||!r?.turbo_design_locked)return '';
  const undo=hasFluxUndo();
  if(!turboNeedsFluxOptimization(r)&&!undo)return `<section class="flux-opt-card success"><div><strong>Flux balance</strong><span>Locked turbo duty is inside the usable Cv window. No bypass/backpressure correction is required.</span></div></section>`;
  const issue=turboNeedsFluxOptimization(r)?'This locked off-design case requires bypass or backpressure. Total RO Design can search for a coupled RO operating point that moves the turbine duty inside its fixed Cv window.':'An optimized flux balance is currently applied.';
  return `<section class="flux-opt-card" id="fluxOptCard"><div class="section-inline-title"><div><h3>OFF-DESIGN FLUX BALANCE</h3><p>${issue}</p></div><div class="flux-opt-actions">${turboNeedsFluxOptimization(r)?'<button type="button" class="envelope-btn" id="optimizeFluxBtn">Optimize Flux Balance</button>':''}${undo?'<button type="button" class="ghost" id="undoFluxBtn">Undo Flux Optimization</button>':''}</div></div>${turboNeedsFluxOptimization(r)?`<div class="flux-opt-options"><label>Strategy <select id="fluxOptStrategy"><option value="maintain_product">Maintain permeate production</option><option value="allow_production">Allow production adjustment</option></select></label><label>Max feed-flow change <input id="fluxMaxFeed" type="number" min="1" max="40" step="1" value="15"><span>%</span></label><label>Max recovery change <input id="fluxMaxRecovery" type="number" min="0.5" max="20" step="0.5" value="5"><span>percentage points</span></label></div><p class="micro-note">Optimization is advisory until you choose Apply. The locked turbo Cvc/Cvo and selected design-duty case are never resized. Every trial reruns the coupled membrane calculation.</p>`:''}<div id="fluxOptPreview"></div></section>`;
}
function cvWindowSummary(r,prefix=''){
  const label=prefix==='inter_'?'Interstage turbo':prefix==='feed_'?'Feed turbo':'Turbo';
  return `${label}: Cvt ${fmt(r?.[prefix+'cv_required'],3)} · window ${fmt(r?.[prefix+'cvc'],3)}–${fmt(r?.[prefix+'cvo'],3)}`;
}
function fluxCompareRows(a,b){
  const rows=[['Feed flow','feed_flow',a?.flow_unit||'',2],['Permeate flow','product_flow',a?.flow_unit||'',2],['Overall recovery','recovery','%',2],['Stage 1 recovery','stage1_recovery','%',2],['Stage 2 recovery','stage2_recovery','%',2],['Stage 1 feed pressure','membrane_pressure_1',a?.pressure_unit||'',2],['Stage 2 feed pressure','membrane_pressure_2',a?.pressure_unit||'',2],['Total SEC','total_sec','kWh/m³',3]];
  return rows.filter(([,k])=>a?.[k]!==undefined||b?.[k]!==undefined).map(([label,k,u,d])=>{let av=a?.[k],bv=b?.[k];if(k.includes('recovery')){av=Number(av)*100;bv=Number(bv)*100;}return `<tr><td>${label}</td><td>${fmt(av,d)} ${u}</td><td>${fmt(bv,d)} ${u}</td></tr>`}).join('');
}
function fluxPreviewHtml(j){
  const a=j.original,b=j.recommended;const cvRows=mode==='biturbo'?`${cvWindowSummary(a,'inter_')} → ${cvWindowSummary(b,'inter_')}<br>${cvWindowSummary(a,'feed_')} → ${cvWindowSummary(b,'feed_')}`:`${cvWindowSummary(a)} → ${cvWindowSummary(b)}`;
  return `<div class="flux-preview ${j.feasible?'success':'warning'}"><div class="warning-head"><strong>${j.feasible?'No-bypass / no-backpressure condition found':'Closest operating point within selected limits'}</strong></div><p>${escapeHtml(j.message||'')}</p><div class="table-wrap"><table class="fedco-table"><tr><th>Parameter</th><th>Original</th><th>Recommended</th></tr>${fluxCompareRows(a,b)}</table></div><p class="micro-note">${cvRows}<br>Coupled solver evaluations: ${j.evaluations||'—'}</p><div class="flux-opt-actions">${j.feasible&&!j.already_in_range?'<button type="button" class="primary-inline" id="applyFluxBtn">Apply Optimized Condition</button>':''}<button type="button" class="ghost" id="closeFluxPreview">Keep Original</button></div></div>`;
}
async function optimizeFluxBalance(){
  const host=$('#fluxOptPreview');if(!host)return;host.innerHTML='<p class="muted">Searching coupled membrane / turbo operating points…</p>';clearCalcError();
  try{persistActiveCase();const data=processPayload(caseStore[activeCase],mode,true);const strategy=$('#fluxOptStrategy')?.value||'maintain_product';const body={mode,data,strategy,max_feed_change_pct:Number($('#fluxMaxFeed')?.value||15),max_recovery_change_pp:Number($('#fluxMaxRecovery')?.value||5)};const j=await requestJson('/api/turbo/optimize-flux',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},'Flux optimization failed');host.innerHTML=fluxPreviewHtml(j);$('#closeFluxPreview')?.addEventListener('click',()=>{host.innerHTML=''});$('#applyFluxBtn')?.addEventListener('click',()=>applyFluxOptimization(j));}catch(e){host.innerHTML='';showCalcError(e,mode)}
}
function applyFluxOptimization(j){
  if(!j?.feasible||!j.recommended)return;persistActiveCase();const c=caseStore[activeCase];c.fluxOptimizationUndo=c.fluxOptimizationUndo||{};c.fluxOptimizationUndo[mode]={modeState:deepClone(c.modeStates?.[mode]||{}),result:deepClone(c.caseResults?.[mode]||null),applied_at:new Date().toISOString()};
  const state=deepClone(c.modeStates?.[mode]||modeStates[mode]||{});Object.assign(state,j.recommended_inputs||{});c.modeStates[mode]=state;c.caseResults[mode]=deepClone(j.recommended);modeStates=deepClone(c.modeStates);caseResults=deepClone(c.caseResults);lastResult=caseResults[mode];renderFields(modeStates[mode]);syncSolveResult(lastResult);show(lastResult);renderCaseBar();
}
function undoFluxOptimization(){
  const c=caseStore[activeCase],u=c?.fluxOptimizationUndo?.[mode];if(!u)return;c.modeStates[mode]=deepClone(u.modeState||{});if(u.result)c.caseResults[mode]=deepClone(u.result);else delete c.caseResults[mode];delete c.fluxOptimizationUndo[mode];modeStates=deepClone(c.modeStates);caseResults=deepClone(c.caseResults);lastResult=caseResults[mode]||null;renderFields(modeStates[mode]||convertedDefaults());if(lastResult){syncSolveResult(lastResult);show(lastResult)}else $('#results').innerHTML='<p class="muted">Optimization undone. Recalculate the original case if needed.</p>';renderCaseBar();
}
function bindFluxOptimizationActions(){
  $('#optimizeFluxBtn')?.addEventListener('click',optimizeFluxBalance);$('#undoFluxBtn')?.addEventListener('click',undoFluxOptimization);const strategy=$('#fluxOptStrategy');if(strategy)strategy.addEventListener('change',()=>{const maintain=strategy.value==='maintain_product';const a=$('#fluxMaxFeed')?.closest('label'),b=$('#fluxMaxRecovery')?.closest('label');if(a)a.classList.toggle('dimmed',!maintain);if(b)b.classList.toggle('dimmed',maintain)});
}


function suiteHydraulicEnvelopeChart(r){
  if(!r)return '';
  const active=caseStore[activeCase]||{},activeFF=Number(active.waterProfile?.fouling_factor),rows=[];
  for(let cid=1;cid<=4;cid++){
    const c=caseStore[cid],rr=c?.caseResults?.[mode];if(!rr||!resultMatchesCaseWaterBasis(c,rr))continue;
    const t=Number(c.waterProfile?.temperature_c),ff=Number(c.waterProfile?.fouling_factor),sec=Number(rr.total_sec),tds=scenarioProductTds(rr);
    if([t,sec,tds].every(Number.isFinite))rows.push({cid,t,ff,sec,tds,label:c.waterProfile?.envelope_label||`Case ${cid}`});
  }
  // The four-condition envelope contains New/Cold, New/Warm, Aged/Cold,
  // Aged/Warm.  Plot the membrane-condition pair matching the active case so
  // temperature is the only changing x-variable.  If the envelope has not yet
  // been run, show the current design point without fabricating a curve.
  let plot=rows.filter(x=>Number.isFinite(activeFF)&&Number.isFinite(x.ff)&&Math.abs(x.ff-activeFF)<1e-8);
  if(plot.length<2){
    const t=Number(active.waterProfile?.temperature_c??waterProfile?.temperature_c),sec=Number(r.total_sec),tds=scenarioProductTds(r);
    plot=([t,sec,tds].every(Number.isFinite))?[{cid:activeCase,t,ff:activeFF,sec,tds,label:'Design point'}]:[];
  }
  if(!plot.length)return '';
  plot.sort((a,b)=>a.t-b.t||a.cid-b.cid);
  const W=620,H=228,L=54,R=58,T=27,B=48;
  let xmin=Math.min(...plot.map(x=>x.t)),xmax=Math.max(...plot.map(x=>x.t));
  if(xmax-xmin<1){const wp=active.waterProfile||waterProfile||{},lo=Number(wp.temperature_min_c),hi=Number(wp.temperature_max_c);if(Number.isFinite(lo)&&Number.isFinite(hi)&&hi>lo){xmin=lo;xmax=hi}else{xmin-=5;xmax+=5}}
  const secVals=plot.map(x=>x.sec),tdsVals=plot.map(x=>x.tds);
  let smin=Math.min(...secVals),smax=Math.max(...secVals),tmin=Math.min(...tdsVals),tmax=Math.max(...tdsVals);
  const sp=Math.max(.05,(smax-smin)*.18,Math.max(Math.abs(smax),1)*.04),tp=Math.max(5,(tmax-tmin)*.18,Math.max(Math.abs(tmax),1)*.04);smin=Math.max(0,smin-sp);smax+=sp;tmin=Math.max(0,tmin-tp);tmax+=tp;
  const x=v=>L+(v-xmin)*(W-L-R)/(xmax-xmin||1),ys=v=>T+(smax-v)*(H-T-B)/(smax-smin||1),yt=v=>T+(tmax-v)*(H-T-B)/(tmax-tmin||1);
  let grid='',leftTicks='',rightTicks='';
  for(let i=0;i<=4;i++){const yy=T+(H-T-B)*i/4,sv=smax-(smax-smin)*i/4,tv=tmax-(tmax-tmin)*i/4;grid+=`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="suite-chart-grid"/>`;leftTicks+=`<text x="${L-8}" y="${yy+3}" text-anchor="end" class="suite-chart-label">${fmt(sv,2)}</text>`;rightTicks+=`<text x="${W-R+8}" y="${yy+3}" class="suite-chart-label">${fmt(tv,0)}</text>`}
  const secPts=plot.map(d=>`${x(d.t)},${ys(d.sec)}`).join(' '),tdsPts=plot.map(d=>`${x(d.t)},${yt(d.tds)}`).join(' ');
  const xTicks=[0,.25,.5,.75,1].map(f=>{const v=xmin+(xmax-xmin)*f;return `<text x="${x(v)}" y="${H-20}" text-anchor="middle" class="suite-chart-label">${fmt(v,0)}</text>`}).join('');
  const dots=plot.map(d=>`<g><circle cx="${x(d.t)}" cy="${ys(d.sec)}" r="4" class="suite-envelope-sec-dot"><title>${escapeHtml(d.label)} · SEC ${fmt(d.sec,3)} kWh/m³</title></circle><circle cx="${x(d.t)}" cy="${yt(d.tds)}" r="4" class="suite-envelope-tds-dot"><title>${escapeHtml(d.label)} · Product TDS ${fmt(d.tds,1)} mg/L</title></circle></g>`).join('');
  const lines=plot.length>1?`<polyline points="${secPts}" class="suite-envelope-sec-line"/><polyline points="${tdsPts}" class="suite-envelope-tds-line"/>`:'';
  const condition=plot.length>1?(Number.isFinite(activeFF)&&activeFF>=.9?'New membrane':'Aged membrane'):'Design point only';
  const footer=plot.length>1?`${plot.length} calculated temperature points · ${condition}`:'Run Hydraulic Envelope to populate the temperature curve';
  return `<div class="suite-chart-card suite-chart-premium suite-envelope-card"><div class="suite-chart-card-head"><div><span>HYDRAULIC ENVELOPE</span><h4>Design point</h4></div><strong>${escapeHtml(condition)}</strong></div><div class="suite-envelope-legend"><span class="sec">SEC (kWh/m³)</span><span class="tds">Product TDS (mg/L)</span></div><svg class="suite-modern-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Hydraulic envelope versus feed temperature">${grid}${leftTicks}${rightTicks}${xTicks}${lines}${dots}<text x="${(L+W-R)/2}" y="${H-5}" text-anchor="middle" class="suite-chart-label">Feed temperature (°C)</text></svg><div class="suite-chart-footer"><span>${escapeHtml(footer)}</span><button type="button" class="envelope-btn suite-envelope-btn" id="viewHydraulicEnvelopeBtn">View Full Envelope</button></div></div>`;
}
function suiteSplitEfficiency(overall){const e=Math.max(0,Math.min(.999999,Number(overall)||0)),d=.01,p=(d+Math.sqrt(d*d+4*e))/2;return {t:p-d,p}}
function suiteEfficiencyChart(r,prefix='',title='Turbocharger off-design efficiency'){
  const lock=activeTurboLockFields(mode)||{};
  const pfx=prefix;
  const designEff=Number(lock[`${pfx}design_overall_eff`]??r[`${pfx}design_overall_eff`]??r.design_overall_eff);
  const designQr=Number(lock[`${pfx}design_qr`]);
  const actualQ=Number(prefix==='feed_'?r.feed_turbine_flow:prefix==='inter_'?r.interstage_turbine_flow:r.turbine_flow);
  const actualEff=Number(prefix==='feed_'?r.feed_turbo_eff:prefix==='inter_'?r.turbo_eff:r.turbo_eff);
  if(!Number.isFinite(designEff)||designEff<=0||!Number.isFinite(designQr)||designQr<=0)return '';
  const sp=suiteSplitEfficiency(designEff),W=520,H=175,L=40,R=16,T=18,B=34,xmin=.55,xmax=1.45,ymin=.35,ymax=1.02;
  const x=v=>L+(v-xmin)*(W-L-R)/(xmax-xmin),y=v=>T+(ymax-v)*(H-T-B)/(ymax-ymin),samples=[];
  for(let i=0;i<=36;i++){const q=xmin+(xmax-xmin)*i/36,et=sp.t*(1-(q-1)*(q-1)),ep=sp.p*(1-(q-1)*(q-1)),eff=et*ep;samples.push({q,eff})}
  const pts=samples.map(d=>`${x(d.q)},${y(d.eff)}`).join(' '),ar=actualQ/designQr;
  let grid='';for(let i=0;i<=4;i++){const yy=T+(H-T-B)*i/4,val=(ymax-(ymax-ymin)*i/4)*100;grid+=`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="suite-chart-grid"/><text x="${L-5}" y="${yy+3}" text-anchor="end" class="suite-chart-label">${fmt(val,0)}%</text>`}
  for(let i=0;i<=4;i++){const xx=L+(W-L-R)*i/4,val=xmin+(xmax-xmin)*i/4;grid+=`<text x="${xx}" y="${H-12}" text-anchor="middle" class="suite-chart-label">${fmt(val,2)}×</text>`}
  const actual=Number.isFinite(ar)&&Number.isFinite(actualEff)?`<circle cx="${x(Math.max(xmin,Math.min(xmax,ar)))}" cy="${y(Math.max(ymin,Math.min(ymax,actualEff)))}" r="5" class="suite-actual-point"/><text x="${x(Math.max(xmin,Math.min(xmax,ar)))+8}" y="${y(Math.max(ymin,Math.min(ymax,actualEff)))-7}" class="suite-chart-value">Actual ${pct(actualEff)}%</text>`:'';
  return `<div class="suite-chart-card"><h4>${escapeHtml(title)}</h4><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Off-design efficiency curve">${grid}<polyline points="${pts}" class="suite-eff-line"/>${actual}</svg><p class="micro-note">Normalized flow slice of the locked workbook quadratic off-design equation at design pressure. The actual point uses the fully coupled flow + pressure result.</p></div>`;
}
function suiteEnergyBreakdown(r){
  if(!r)return '';
  const ro=Number(r.ro_sec||0),pret=Number(r.pretreatment_sec||0),total=Number(r.total_sec||ro+pret),max=Math.max(total,ro,pret,.001);
  const row=(name,v,i)=>`<div class="suite-energy-row"><span>${escapeHtml(name)}</span><div class="suite-energy-track"><div class="suite-energy-fill" style="width:${Math.max(1,100*v/max).toFixed(1)}%"></div></div><strong>${fmt(v,3)}</strong></div>`;
  return `<div class="suite-chart-card"><h4>Energy breakdown · kWh/m³</h4><div class="suite-energy-bars">${row('RO system',ro,0)}${row('Pretreatment',pret,1)}${row('Total plant',total,2)}</div><p class="micro-note">Calculated specific energy at the active case duty point.</p></div>`;
}
function performanceVisualizations(r){
  if(!r)return '';
  const charts=[suiteHydraulicEnvelopeChart(r)];
  charts.push(suiteEnergyBreakdown(r));
  const body=charts.filter(Boolean).join('');if(!body)return '';
  return `<section class="report-section suite-visual-section"><div class="chart-title-row"><h3>CHARTS & PERFORMANCE VISUALIZATIONS</h3><span>Case ${activeCase}</span></div><div class="suite-visual-grid">${body}</div></section>`;
}
function chemistryVisualizations(j){
  const minerals=(j?.minerals||[]).filter(x=>Number.isFinite(Number(x.concentration_saturation_pct))).slice().sort((a,b)=>String(a.formula||'').localeCompare(String(b.formula||''))||String(a.name||'').localeCompare(String(b.name||'')));
  if(!minerals.length)return '';
  const rows=minerals.map(x=>{const v=Number(x.concentration_saturation_pct),w=Math.min(100,Math.max(1,v/1.5)),cls=v>=100?'over':'';return `<div class="chem-sat-row ${cls}"><span><b>${escapeHtml(x.formula||'—')}</b> — ${escapeHtml(x.name)}</span><div class="chem-sat-track"><i style="width:${w.toFixed(1)}%"></i><b class="chem-sat-limit"></b></div><strong>${fmt(v,1)}%</strong></div>`}).join('');
  return `<section class="report-section"><div class="chart-title-row"><h3>MINERAL SATURATION SNAPSHOT</h3><span>Sorted by formula · 100% = saturation</span></div><div class="chem-saturation-grid chem-saturation-scroll">${rows}</div></section>`;
}
function economicVisualizations(r){
  const order=['px','single','biturbo'].filter(k=>r?.cases?.[k]);if(!order.length)return '';
  const maxLc=Math.max(...order.map(k=>Number(r.cases[k].lcow_usd_m3)||0),.001),maxCap=Math.max(...order.map(k=>Number(r.cases[k].capex_usd)||0),1);
  const rows=order.map(k=>{const c=r.cases[k],best=k===r.preferred;return `<div class="econ-visual-row ${best?'best':''}"><strong>${escapeHtml(c.label)}</strong><div><span>LCOW</span><i style="width:${(100*Number(c.lcow_usd_m3||0)/maxLc).toFixed(1)}%"></i><b>$${fmt(c.lcow_usd_m3,3)}/m³</b></div><div><span>CAPEX</span><i style="width:${(100*Number(c.capex_usd||0)/maxCap).toFixed(1)}%"></i><b>${money(c.capex_usd)}</b></div></div>`}).join('');
  return `<section class="report-section"><div class="chart-title-row"><h3>ECONOMIC VISUAL COMPARISON</h3><span>${escapeHtml(r.preferred_label||'')}</span></div><div class="econ-visual-grid">${rows}</div></section>`;
}

function multistageKpis(r){
  return `<div class="kpi-strip five"><div><span>Train permeate</span><strong>${fmt(r.product_flow)} ${r.flow_unit}</strong><small>${fmt(r.train_product_capacity_m3d,0)} m³/d</small></div><div><span>Overall recovery</span><strong>${pct(r.recovery)}%</strong><small>${resultStageCount(r)} membrane stage${resultStageCount(r)>1?'s':''}</small></div><div><span>RO gross SEC</span><strong>${fmt(r.ro_sec)} kWh/m³</strong><small>HPP + interstage boosters</small></div><div><span>Total SEC</span><strong>${fmt(r.total_sec)} kWh/m³</strong><small>incl. pretreatment</small></div><div><span>Membrane inventory</span><strong>${fmt(r.total_membrane_elements,0)} elements</strong><small>${fmt(r.total_pressure_vessels,0)} pressure vessels</small></div></div>`;
}
function multistagePlantReport(r){
  const req=Number(r.required_capacity_m3d),hasReq=Number.isFinite(req)&&req>0,ok=r.n_minus_one_meets_required===true;
  return `<section class="report-section"><div class="chart-title-row"><h3>PLANT / TRAIN CONFIGURATION</h3><span>${r.auto_sized?'Auto Design array sizing':'Manual array design'}${r.auto_sized?` · ${r.auto_sizing_iterations} sizing pass${r.auto_sizing_iterations===1?'':'es'}`:''}</span></div><div class="check-grid"><div class="check-card"><strong>Per-train production</strong><span>${fmt(r.train_product_capacity_m3d,0)} m³/d</span><span>${r.operating_trains} operating + ${r.standby_trains} standby</span><span>${r.installed_trains} total installed trains</span></div><div class="check-card"><strong>Plant capacity</strong><span>Normal: ${fmt(r.normal_operating_capacity_m3d,0)} m³/d</span><span>Installed: ${fmt(r.installed_capacity_m3d,0)} m³/d</span><span>N−1 available: ${fmt(r.n_minus_one_capacity_m3d,0)} m³/d</span></div>${hasReq?`<div class="check-card"><strong>N−1 requirement</strong><span>Required: ${fmt(req,0)} m³/d</span><span>Margin: ${fmt(r.n_minus_one_capacity_margin_m3d,0)} m³/d</span><b class="${ok?'ok':'bad'}">${ok?'MEETS REQUIRED CAPACITY':'DOES NOT MEET REQUIRED CAPACITY'}</b></div>`:''}<div class="check-card"><strong>Array inventory</strong><span>${fmt(r.total_pressure_vessels,0)} pressure vessels / train</span><span>${fmt(r.total_membrane_elements,0)} membrane elements / train</span><span>${fmt(r.total_membrane_area_m2,0)} m² active area / train</span></div></div><p class="micro-note">N−1 assumes one installed RO train is unavailable. Auto Design jointly sizes membrane area / whole pressure vessels and automatic interstage boost against the entered maximum average-flux criterion. BWRO selection also prioritizes the scaling-critical tail-element β; the suggested array and solved boosts remain editable.</p></section>`;
}
function autoDesignJointReport(r){
  if(!r?.auto_sized)return '';
  const n=resultStageCount(r),sizing=Array.isArray(r.auto_sizing)?r.auto_sizing:[],rows=[];
  for(let i=1;i<=n;i++){
    const x=sizing.find(a=>Number(a.stage)===i)||{},boost=i>1?Number(r[`auto_interstage_boost_bar_${i}`]??r[`interstage_boost_${i}`]??0):0;
    const ff=Number(x.first_element_feed_m3h),ffmax=Number(x.max_first_element_feed_m3h),tail=Number(x.tail_concentrate_m3h),tailmin=Number(x.min_tail_concentrate_m3h),ef=Number(x.max_element_flux_lmh),dpf=Number(x.dp_limit_fraction);
    const flowPair=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)?`${fmt(convert(a,'flow','m3/h',r.flow_unit||currentUnits.flow),2)} / ${fmt(convert(b,'flow','m3/h',r.flow_unit||currentUnits.flow),2)} ${escapeHtml(r.flow_unit||currentUnits.flow)}`:'—';
    rows.push(`<tr><td>Stage ${i}</td><td>${fmt(r[`auto_vessels_${i}`],0)}</td><td>${fmt(r[`auto_elements_per_vessel_${i}`],0)}</td><td>${fmt(fluxValue(r[`stage${i}_flux_lmh`]),2)} ${fluxUnit()}</td><td>${Number.isFinite(ef)?fmt(fluxValue(ef),2)+' '+fluxUnit():'—'}</td><td>${flowPair(ff,ffmax)}</td><td>${flowPair(tail,tailmin)}</td><td>${fmt(r[`auto_tail_beta_${i}`],4)}</td><td>${Number.isFinite(dpf)?fmt(100*dpf,1)+'%':'—'}</td><td>${i===1?'HPP energy anchor':fmt(convert(boost,'pressure','bar',r.pressure_unit||currentUnits.pressure),2)+' '+(r.pressure_unit||currentUnits.pressure)}</td></tr>`)
  }
  const seed=escapeHtml(r.auto_design_selected_seed||'coupled array seed'),beta=Number(r.auto_design_max_tail_beta),bw=!!r.auto_design_bwro_tail_beta_priority,attempts=Number(r.auto_design_candidates_evaluated||0),converged=Number(r.auto_design_candidates_converged||0),early=Number(r.auto_design_candidates_early_rejected||0),areaRatio=Number(r.auto_design_area_ratio),recovery=!!r.auto_design_recovery_search_used;
  const skids=Number(r.auto_design_operating_skids||r.operating_trains||1),vps=Number(r.auto_design_vessels_per_skid||r.total_pressure_vessels||0),vpall=Number(r.auto_design_total_vessels_operating||vps*skids);
  return `<section class="report-section"><div class="chart-title-row"><h3>AUTO DESIGN · COUPLED ARRAY + BOOST</h3><span>${bw?'BWRO tail-β priority':'Coupled flux / area optimization'}</span></div><div class="check-grid"><div class="check-card"><strong>Selected tree array</strong><span>${seed}</span><span>${converged} converged · ${attempts} candidate${attempts===1?'':'s'} checked</span></div><div class="check-card"><strong>Membrane area</strong><span>${fmt(r.total_membrane_area_m2,0)} m² / skid</span><span>${Number.isFinite(areaRatio)?fmt(areaRatio*100,1)+'% of flux-based minimum area':'—'}</span></div><div class="check-card"><strong>Hydraulic prefilter</strong><span>${early} impossible candidate${early===1?'':'s'} rejected early</span><span>${recovery?'Automatic recovery search was used':'Nominal tree seeds established a solvable array'}</span></div><div class="check-card"><strong>Operating skid distribution</strong><span>${skids} operating skid${skids===1?'':'s'} · ${fmt(vps,0)} vessels / skid</span><span>${fmt(vpall,0)} vessels across operating skids</span></div><div class="check-card"><strong>Tail-element β</strong><span>Maximum ${Number.isFinite(beta)?fmt(beta,4):'—'} / limit ${fmt(r.auto_design_max_tail_beta_limit,3)}</span><span>${bw?'Explicit array-selection objective for BWRO':'Reported as a hydraulic safeguard'}</span></div><div class="check-card"><strong>Joint pressure solve</strong><span>${r.auto_design_joint_array_boost?'Array and automatic boost re-solved together':'Array sizing only'}</span><span>${escapeHtml(r.interstage_control_seed_basis||'')}</span></div></div><div class="table-wrap"><table class="fedco-table"><tr><th>Stage</th><th>Pressure vessels</th><th>Elements / vessel</th><th>Average flux</th><th>Max element flux</th><th>First-element feed / max</th><th>Tail concentrate / min</th><th>Tail β</th><th>Element ΔP limit used</th><th>Interstage hydraulic input</th></tr>${rows.join('')}</table></div><p class="micro-note">Required production → target flux → active membrane area → actual hybrid membrane elements → whole pressure vessels → operating skids → integer tree/funnel distribution → Hydraulic prefilter → detailed membrane / pressure convergence → optimization. Ratios such as 2:1, 3:2:1, 4:2:1 and 4:3:2:1 are starting geometries, not rigid rules. If the starting array cannot solve the requested permeate flow, the recovery search expands membrane area and nearby integer vessel distributions automatically. Manufacturer flow limits are used when cataloged; otherwise the prefilter uses transparent diameter-based screening defaults that must be verified against the selected membrane datasheet.</p></section>`;
}

function multistagePumpCurveChart(r){
  const pts=Array.isArray(r.pump_curve_points)?r.pump_curve_points:[];if(!pts.length)return '';
  const fu=r.flow_unit,pu=r.pressure_unit,isDb=r.pump_curve_source==='vcmp_database',displayPts=!!r.pump_curve_points_are_display_units;
  const data=pts.map(p=>({q:displayPts?Number(p.flow_m3h):convert(p.flow_m3h,'flow','m3/h',fu),pump:displayPts?Number(p.pump_dp_bar):convert(p.pump_dp_bar,'pressure','bar',pu),system:displayPts?Number(p.system_dp_bar):convert(p.system_dp_bar,'pressure','bar',pu)})).filter(p=>Number.isFinite(p.q)&&Number.isFinite(p.pump)&&Number.isFinite(p.system)).sort((a,b)=>a.q-b.q);
  if(!data.length)return '';
  const qop=Number(r.pump_operating_flow),dpop=Number(isDb?(r.pump_generated_dp??r.pump_operating_dp):r.pump_operating_dp),hasOp=Number.isFinite(qop)&&qop>0&&Number.isFinite(dpop);
  const niceStep=raw=>{if(!Number.isFinite(raw)||raw<=0)return 1;const e=Math.floor(Math.log10(raw)),scale=10**e,f=raw/scale,c=[1,2,2.5,5,10];let best=c[0],d=Math.abs(f-best);for(const x of c.slice(1)){const nd=Math.abs(f-x);if(nd<=d){best=x;d=nd}}return best*scale};
  const axisLabel=(v,step)=>fmt(v,step>=10?0:(Math.abs(step-Math.round(step))<1e-9?0:step>=1?1:2));
  const xTarget=Math.max(hasOp?1.4*qop:Math.max(...data.map(p=>p.q),1),1e-9),xStep=niceStep(xTarget/8),xMax=Math.max(xStep,Math.ceil(xTarget/xStep-1e-10)*xStep);
  const shutoff=Number(r.pump_shutoff_dp),pumpShutoff=Number.isFinite(shutoff)&&shutoff>0?shutoff:Math.max(...data.map(p=>p.pump),1);
  const yTarget=Math.max(isDb?1.20*pumpShutoff:Math.max(...data.flatMap(p=>[p.pump,p.system]),1),1e-9),yStep=niceStep(yTarget/8),yMax=Math.max(yStep,Math.ceil(yTarget/yStep-1e-10)*yStep);
  const W=820,H=260,L=62,R=22,T=22,B=48,x=q=>L+Math.max(0,Math.min(q,xMax))*(W-L-R)/xMax,y=v=>T+(yMax-Math.max(0,Math.min(v,yMax)))*(H-T-B)/yMax,grid=[];
  for(let v=0;v<=yMax+yStep*.25;v+=yStep){const yy=y(v);grid.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="flux-grid"/><text x="${L-8}" y="${yy+3}" text-anchor="end" class="flux-axis-text">${axisLabel(v,yStep)}</text>`)}
  for(let q=0;q<=xMax+xStep*.25;q+=xStep){const xx=x(q);grid.push(`<line x1="${xx}" y1="${T}" x2="${xx}" y2="${H-B}" class="flux-grid pump-x-grid"/><text x="${xx}" y="${H-B+18}" text-anchor="middle" class="flux-axis-text">${axisLabel(q,xStep)}</text>`)}
  const pumpSeries=[];if(data[0].q>1e-9)pumpSeries.push({q:0,v:pumpShutoff});for(const p of data){if(p.q<=xMax+1e-9)pumpSeries.push({q:p.q,v:p.pump});else break}if(pumpSeries.length&&pumpSeries[pumpSeries.length-1].q<xMax&&data[data.length-1].q>xMax){let a=null,b=null;for(let i=1;i<data.length;i++){if(data[i-1].q<=xMax&&data[i].q>=xMax){a=data[i-1];b=data[i];break}}if(a&&b&&b.q>a.q){const f=(xMax-a.q)/(b.q-a.q);pumpSeries.push({q:xMax,v:a.pump+f*(b.pump-a.pump)})}}
  let sysStatic=0,sysK=0;if(data.length>1){const a=data[0],b=data[data.length-1],den=b.q*b.q-a.q*a.q;if(Math.abs(den)>1e-12){sysK=(b.system-a.system)/den;sysStatic=a.system-sysK*a.q*a.q}}if(!Number.isFinite(sysStatic)||!Number.isFinite(sysK)||sysK<0){sysStatic=Math.max(0,Math.min(...data.map(p=>p.system)));sysK=hasOp?Math.max(0,(Number(r.pump_duty_dp)-sysStatic)/(qop*qop)):0}
  const sysSeries=[];for(let i=0;i<=48;i++){const q=xMax*i/48,v=sysStatic+sysK*q*q;if(v>yMax){if(sysSeries.length){const prev=sysSeries[sysSeries.length-1],dv=v-prev.v;if(dv>1e-12){const f=(yMax-prev.v)/dv;sysSeries.push({q:prev.q+f*(q-prev.q),v:yMax})}}break}sysSeries.push({q,v})}
  const path=series=>series.map((p,i)=>`${i?'L':'M'} ${x(p.q).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' '),pumpPath=path(pumpSeries),sysPath=path(sysSeries);
  const op=hasOp?`<circle cx="${x(qop)}" cy="${y(dpop)}" r="6" class="suite-actual-point"/><text x="${x(qop)+9}" y="${y(dpop)-8}" class="suite-chart-value">${isDb?'Selected duty':'Operating point'}</text>`:'';
  const zone=r.pump_operating_status!=='ok'?'No pump/system intersection':r.pump_operating_zone==='preferred'?'Preferred BEP zone':r.pump_operating_zone==='left_of_bep'?'Left of BEP · review minimum-flow / recirculation':r.pump_operating_zone==='right_of_bep'?'Right of BEP · review runout / vibration risk':'Database curve';
  if(isDb){
    const opts=(Array.isArray(r.pump_database_top_options)?r.pump_database_top_options:[]).slice(0,5).map((o,i)=>`<tr><td>${i+1}</td><td>${escapeHtml(o.product_family||'VCMP')} ${escapeHtml(o.stage_config||'')}</td><td>${fmt(o.frequency_hz,2)} Hz</td><td>${fmt(100*Number(o.pump_efficiency||0),1)}%</td><td>${fmt(o.wire_kw,2)} kW</td><td>${o.min_speed_limited?'Minimum-speed limited':'VFD duty matched'}</td></tr>`).join('');
    const torqueRaw=r.pump_shaft_torque_nm,rpmRaw=r.pump_operating_speed_rpm,torque=Number(torqueRaw),rpm=Number(rpmRaw),hasTorque=torqueRaw!==null&&torqueRaw!==undefined&&rpmRaw!==null&&rpmRaw!==undefined&&Number.isFinite(torque)&&torque>0&&Number.isFinite(rpm)&&rpm>0,torqueText=hasTorque?`${fmt(torque,0)} N·m @ ${fmt(rpm,0)} rpm`:'—';
    return `<section class="report-section vcmp-report-section"><div class="chart-title-row"><h3>HPP VCMP DATABASE CURVE / DUTY POINT</h3><span>${escapeHtml(zone)}</span></div><div class="cp-legend suite-cp-legend"><span class="legend-mono">Selected VCMP curve</span><span class="legend-di">RO system curve</span></div><div class="flux-chart-wrap vcmp-chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Selected vertical multistage centrifugal pump curve and RO system curve">${grid.join('')}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/><path d="${pumpPath}" class="cp-line cp-line-mono"/><path d="${sysPath}" class="cp-line cp-line-di"/>${op}<text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" class="flux-axis-title">Flow (${escapeHtml(fu)})</text><text x="15" y="${(T+H-B)/2}" transform="rotate(-90 15 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Differential pressure (${escapeHtml(pu)})</text></svg></div><div class="duty-actions vcmp-duty-actions"><div><span>Selected pump</span><strong>${escapeHtml(r.pump_selected_family||'VCMP')} ${escapeHtml(r.pump_selected_stage_config||'')}</strong></div><div><span>VFD operating speed</span><strong>${fmt(r.pump_operating_frequency_hz,2)} Hz · ${fmt(100*r.pump_operating_speed_ratio,1)}%</strong></div><div><span>Pump efficiency</span><strong>${fmt(100*r.pump_operating_efficiency,1)}%</strong></div><div><span>Wire power</span><strong>${fmt(r.pump_operating_wire_kw,2)} kW</strong></div><div><span>Shaft torque</span><strong>${torqueText}</strong></div><div><span>Required / generated ΔP</span><strong>${fmt(r.pump_duty_dp,2)} / ${fmt(r.pump_generated_dp,2)} ${escapeHtml(pu)}</strong></div></div>${opts?`<div class="table-wrap vcmp-options-table"><table class="fedco-table"><tr><th>Rank</th><th>VCMP option</th><th>Speed</th><th>Pump η</th><th>Wire power</th><th>Operating note</th></tr>${opts}</table></div>`:''}<p class="micro-note">Selected from 431 user-supplied vertical multistage centrifugal pump regressions. Pump speed is matched to the required duty and efficiency is evaluated from the source 60 Hz regression. Ranking uses the lowest actual wire power among curves that also cover the design-margin duty. Torque uses the configured 60 Hz shaft-speed basis (3500 rpm default) and the calculated shaft power. Final selection must verify NPSH, minimum continuous flow, motor rating, materials, pressure rating and mechanical seal.</p></section>`;
  }
  /* Legacy report wording retained for old projects and regression compatibility. */
  return `<section class="report-section"><div class="chart-title-row"><h3>HPP TYPICAL PUMP CURVE / OPERATING POINT</h3><span>${escapeHtml(zone)}</span></div><div class="cp-legend suite-cp-legend"><span class="legend-mono">Pump head curve</span><span class="legend-di">RO system curve</span></div><div class="flux-chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Typical high pressure pump and system curve">${grid.join('')}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/><path d="${pumpPath}" class="cp-line cp-line-mono"/><path d="${sysPath}" class="cp-line cp-line-di"/>${op}<text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" class="flux-axis-title">Flow (${escapeHtml(fu)})</text><text x="15" y="${(T+H-B)/2}" transform="rotate(-90 15 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Differential pressure (${escapeHtml(pu)})</text></svg></div><div class="duty-actions"><div><span>Required RO duty</span><strong>${fmt(r.pump_duty_flow)} ${fu} @ ${fmt(r.pump_duty_dp)} ${pu}</strong></div><div><span>Typical pump BEP</span><strong>${fmt(r.pump_bep_flow)} ${fu} @ ${fmt(r.pump_bep_dp)} ${pu}</strong></div><div><span>Calculated intersection</span><strong>${hasOp?`${fmt(qop)} ${fu} @ ${fmt(dpop)} ${pu}`:'No intersection'}</strong></div><div><span>Flow / BEP</span><strong>${hasOp?fmt(100*r.pump_operating_bep_flow_ratio,1)+'%':'—'}</strong></div><div><span>Efficiency at point</span><strong>${hasOp?fmt(100*r.pump_operating_efficiency,1)+'%':'—'}</strong></div><div><span>Screening wire power</span><strong>${hasOp?fmt(r.pump_operating_wire_kw,1)+' kW':'—'}</strong></div></div><p class="micro-note">Normalized centrifugal-pump curve used for preliminary screening only, not a vendor-certified curve. Auto mode anchors BEP at the required duty; Manual mode lets you enter a selected pump's BEP to calculate the intersection with a local RO system curve anchored at the membrane design point.</p></section>`;
}


function multistagePumpReport(r){
  const hppDb=r.pump_curve_source==='vcmp_database';
  const hppSel=hppDb?`${escapeHtml(r.pump_selected_family||'VCMP')} ${escapeHtml(r.pump_selected_stage_config||'')} · ${fmt(r.pump_operating_frequency_hz,1)} Hz · η ${pct(r.pump_operating_efficiency)}%${Number.isFinite(Number(r.pump_shaft_torque_nm))?` · ${fmt(r.pump_shaft_torque_nm,1)} N·m`:''}`:'Fallback entered efficiency / legacy screening';
  let rows=`<tr><td>High-pressure pump</td><td>${fmt(r.hpp_flow)} ${r.flow_unit}</td><td>${fmt(r.hpp_dp)} ${r.pressure_unit}</td><td>${fmt(r.hpp_kw)} kW</td><td>${hppSel}</td><td>Stage 1 feed</td></tr>`;
  let databaseUsed=hppDb;
  for(let i=2;i<=resultStageCount(r);i++){
    const boost=Number(r[`interstage_boost_${i}`]||0),q=r[`reject_flow_${i-1}`];if(boost<=0)continue;
    const src=r[`stage${i}_interstage_booster_pump_source`],db=src==='vcmp_database';databaseUsed=databaseUsed||db;
    const wire=r[`stage${i}_interstage_booster_wire_kw`];
    const sel=db?`${escapeHtml(r[`stage${i}_interstage_booster_pump_family`]||'VCMP')} ${escapeHtml(r[`stage${i}_interstage_booster_pump_stage_config`]||'')} · ${fmt(r[`stage${i}_interstage_booster_pump_frequency_hz`],1)} Hz · η ${pct(r[`stage${i}_interstage_booster_pump_efficiency`])}%${Number.isFinite(Number(r[`stage${i}_interstage_booster_pump_shaft_torque_nm`]))?` · ${fmt(r[`stage${i}_interstage_booster_pump_shaft_torque_nm`],1)} N·m`:''}`:'Fallback entered booster efficiency';
    rows+=`<tr><td>Stage ${i} booster</td><td>${fmt(q)} ${r.flow_unit}</td><td>${fmt(boost)} ${r.pressure_unit}</td><td>${Number.isFinite(Number(wire))?fmt(wire)+' kW':`Included in ${fmt(r.booster_kw)} kW total`}</td><td>${sel}</td><td>Stage ${i} feed</td></tr>`;
  }
  const dbNote=hppDb?`HPP selected automatically from the ${fmt(r.pump_database_records||431,0)}-curve VCMP database using the supplied 60 Hz curve regressions and VFD speed matching.`:(r.pump_database_fallback?`No single VCMP database curve covered the HPP duty; fallback efficiency remains active. ${escapeHtml(r.pump_database_fallback_reason||'')}`:'Legacy pump screening / entered efficiency is active.');
  const sealNote=databaseUsed?' VCMP use for Isobaric Chamber or interstage booster service requires verification of pressure rating and a suitable high-pressure mechanical seal.':'';
  return `<section class="report-section"><h3>PUMP DUTY SUMMARY</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Service</th><th>Flow</th><th>ΔP</th><th>Wire power</th><th>Pump selection / efficiency basis</th><th>Destination</th></tr>${rows}</table></div><p class="micro-note">${dbNote}${sealNote} Final selection must still be checked against vendor-certified NPSH, minimum continuous flow, motor size, pressure rating, materials, temperature, connections, mechanical seal and approved VFD limits.</p></section>`;
}

function vcmpPxPumpSummary(r){
  const hasHpp=!!r.px_hpp_pump_source,hasBooster=!!r.px_booster_pump_source;if(!hasHpp&&!hasBooster)return '';
  const row=(service,source,family,config,hz,eta,power,torque)=>{const db=source==='vcmp_database';const selection=db?`${escapeHtml(family||'VCMP')} ${escapeHtml(config||'')} · ${fmt(hz,1)} Hz · η ${pct(eta)}%${Number.isFinite(Number(torque))?` · ${fmt(torque,1)} N·m`:''}`:'Fallback entered efficiency';return `<tr><td>${service}</td><td>${selection}</td><td>${fmt(power)} kW</td></tr>`};
  const rows=[row('HPP branch',r.px_hpp_pump_source,r.px_hpp_pump_family,r.px_hpp_pump_stage_config,r.px_hpp_pump_frequency_hz,r.px_hpp_pump_efficiency,r.hpp_kw,null)];
  if(Number(r.circ_dp||0)>0||r.px_booster_pump_source==='vcmp_database')rows.push(row('Isobaric Chamber booster',r.px_booster_pump_source,r.px_booster_pump_family,r.px_booster_pump_stage_config,r.px_booster_pump_frequency_hz,r.px_booster_pump_efficiency,r.circ_kw,r.px_booster_pump_shaft_torque_nm));
  return `<section class="report-section"><h3>VCMP PUMP SELECTION</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Service</th><th>Pump selection / efficiency basis</th><th>Wire power</th></tr>${rows.join('')}</table></div><p class="micro-note">The VCMP database is used only when one supplied vertical-multistage curve covers the required flow/head duty within the configured VFD envelope and design margins. Otherwise Total RO Design retains the entered fallback efficiency. ${escapeHtml(r.vcmp_mechanical_seal_note||'Isobaric/interstage booster use requires verification of a suitable high-pressure mechanical seal and pressure rating.')} Final manufacturer NPSH, minimum-flow, materials, motor and VFD checks remain mandatory.</p></section>`;
}

function tieredPumpCurveHtml(r){return tierAllows('vcmp_pump_selection')?multistagePumpCurveChart(r):'';}
function tieredPumpReportHtml(r){return tierAllows('vcmp_pump_selection')?multistagePumpReport(r):'';}
function tieredVcmpPxPumpSummary(r){return tierAllows('vcmp_pump_selection')?vcmpPxPumpSummary(r):'';}
function tierFilteredStateForPrint(key,state){const out=deepClone(state||{});if(key==='multistage'&&!tierAllows('vcmp_pump_selection'))SILVER_PUMP_FIELDS.forEach(k=>delete out[k]);return out;}

function processResultTabsHtml(){const active=resultSubtabByMode[mode]||'performance';return `<div class="result-subtabs"><button type="button" data-result-subtab="performance" class="${active==='performance'?'active':''}">Performance</button><button type="button" data-result-subtab="chemistry" class="${active==='chemistry'?'active':''}">Water Chemistry</button><button type="button" data-result-subtab="tail" class="${active==='tail'?'active':''}">Tail Element Water Chemistry</button></div><div id="processResultSubtabBody"></div>`}
function tailChemistryStreams(r){const n=resultStageCount(r),t=r?.[`stage${n}_tail_element_chemistry`];if(!t)return [];const adjusted={label:r.acid_dosing_enabled?'Acid-adjusted plant feed':'Plant feed',composition_mg_l:r.stage1_feed_composition_mg_l,tds_mg_l:r.stage1_feed_tds_ppm,ph:r.stage1_feed_ph,alkalinity_mg_l_as_hco3:r.stage1_feed_alkalinity_mg_l_as_hco3,flow_m3h:convert(r.feed_flow,'flow',r.flow_unit,'m3/h')/Math.max(1,Number(r.stage1_pressure_vessels||1))};return [['plant_feed',adjusted],['tail_feed',t.tail_feed],['tail_concentrate',t.tail_concentrate],['cumulative_permeate_in',t.cumulative_permeate_in],['tail_local_permeate',t.tail_local_permeate],['cumulative_permeate_out',t.cumulative_permeate_out]]}
function chemistryStreamMiniTable(stream,key=''){if(!stream)return '<p class="muted">Full water chemistry was not available for this stream.</p>';const comp=stream.composition_mg_l||{};const rows=summarySpecies.map(([k,l])=>`<tr><td>${escapeHtml(l)}</td><td class="value">${fmt(comp[k],3)}</td></tr>`).join('');return `<div class="tail-stream-card"><h4>${escapeHtml(stream.label||'Stream')}</h4><div class="tail-kpis"><span>TDS <b>${fmt(stream.tds_mg_l??compositionTds(comp),1)} mg/L</b></span><span>pH <b>${fmt(stream.ph,2)}</b></span><span>Alkalinity <b>${fmt(stream.alkalinity_mg_l_as_hco3,2)} mg/L as HCO₃⁻</b></span><span>Flow / vessel <b>${fmt(stream.flow_m3h,3)} m³/h</b></span></div>${key?`<div class="tail-scale-risk" data-tail-risk="${escapeHtml(key)}"><span>Scaling analysis</span><b>Calculating…</b></div>`:''}<div class="table-wrap"><table class="report-table"><tr><th>Species</th><th>mg/L</th></tr>${rows}</table></div></div>`}
function tailChemistryRiskKey(key,stream,r){const comp=stream?.composition_mg_l||{},sig=summarySpecies.map(([k])=>Number(comp[k]||0).toFixed(4)).join(','),temp=Number(r?.stage1_temperature_c??waterProfile.temperature_c??25);return `${activeCase}:${mode}:${key}:${temp.toFixed(2)}:${Number(stream?.ph??8).toFixed(3)}:${sig}`}
function tailChemistryRiskHtml(j){if(!j)return '<span>Scaling analysis</span><b>Unavailable</b>';const calcite=(j.minerals||[]).find(x=>String(x.name||'').toLowerCase()==='calcite'),lsi=(j.indices||[]).find(x=>String(x.name||'').toLowerCase().startsWith('lsi')),si=Number(calcite?.si_track_a??lsi?.value),sat=Number(calcite?.concentration_saturation_pct),risk=Number.isFinite(si)&&si>=0;return `<span>Scaling snapshot</span><b class="${risk?'risk':'ok'}">Calcite SI ${Number.isFinite(si)?fmt(si,3):'—'}${Number.isFinite(sat)?` · ${fmt(sat,1)}% saturation`:''}</b><small>Ionic strength ${fmt(j.ionic_strength_mol_kg,4)} mol/kg · osmotic ${fmt(j.osmotic?.osmotic_bar,2)} bar</small>`}
async function loadTailChemistryRisks(r){const streams=tailChemistryStreams(r);await Promise.all(streams.map(async([key,stream])=>{const host=document.querySelector(`[data-tail-risk="${key}"]`);if(!host||!stream?.composition_mg_l)return;const ck=tailChemistryRiskKey(key,stream,r);try{let j=tailChemistryCache[ck];if(!j){const comp=stream.composition_mg_l,payload={...profileChemPayload(waterProfile,comp,stream.ph,stream.alkalinity_mg_l_as_hco3),reported_tds:Number(stream.tds_mg_l??compositionTds(comp)),source_ph:Number(stream.ph??waterProfile.feed_ph)};const resp=await totalroFetch('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});j=await resp.json();if(!resp.ok)throw new Error(j.error||'Tail chemistry analysis failed');tailChemistryCache[ck]=j;}host.innerHTML=tailChemistryRiskHtml(j);}catch(e){host.innerHTML='<span>Scaling analysis</span><b>Unavailable</b>';}}))}
function tailElementWaterChemistryHtml(r){const n=resultStageCount(r),t=r?.[`stage${n}_tail_element_chemistry`];if(!t)return `<section class="report-section"><h3>TAIL ELEMENT WATER CHEMISTRY</h3><p class="muted">Tail-element chemistry requires Full water chemistry and a coupled membrane calculation.</p></section>`;const cards=tailChemistryStreams(r).map(([key,stream])=>chemistryStreamMiniTable(stream,key)).join('');return `<section class="report-section tail-chemistry-intro"><div class="chart-title-row"><h3>TAIL ELEMENT WATER CHEMISTRY</h3><span>Stage ${n} · element ${t.tail_element||r[`stage${n}_elements_per_vessel`]} · ${escapeHtml(t.tail_membrane_model||'')}</span></div><p class="micro-note">This tab captures the chemistry entering the system and the final element, plus the interconnected permeate-tube chemistry immediately before and after the tail element. Each stream also runs a thermodynamic scaling snapshot so permeate-side CaCO₃ risk in NF service is visible rather than inferred only from calcium and alkalinity concentrations.</p></section><div class="tail-chem-grid">${cards}</div>`}
function processPerformanceBody(r){if(mode==='dweer'||mode==='pelton')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+stageReport(r)+mechanicalErdReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+membraneChecks(r);if(mode==='multistage')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+autoDesignJointReport(r)+stageReport(r)+multistageTurboAssessment(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);if(mode==='interstage'&&r?.generalized_interstage_turbo)return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+autoDesignJointReport(r)+stageReport(r)+multistageTurboAssessment(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);if(mode==='biturbo'&&r?.generalized_biturbo)return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+biturboFeasibilityReport(r)+performanceVisualizations(r)+stageReport(r)+multistageTurboAssessment(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);if(mode==='px'||mode==='interstage_px')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+pxKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+(r.is_brackish_multistage_px||mode==='interstage_px'?multistagePxReport(r):pxReport(r))+tieredVcmpPxPumpSummary(r)+multistageTurboAssessment(r)+membraneChecks(r);return solveStatus(r)+turboDesignStatus(r)+fluxOptimizationPanel(r)+solverDiagnostics(r)+showMembraneHeader(r)+kpis(r)+acidDosingReport(r)+(mode==='biturbo'?biturboFeasibilityReport(r):'')+performanceVisualizations(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+turboRows(r)+dutyCards(r)+membraneChecks(r)}
function renderProcessResultSubtab(r){const host=$('#processResultSubtabBody');if(!host)return;const tab=resultSubtabByMode[mode]||'performance';if(tab==='chemistry'){host.innerHTML=embeddedChemistrySection(r);bindEmbeddedChemistry(r);}else if(tab==='tail'){host.innerHTML=tailElementWaterChemistryHtml(r);loadTailChemistryRisks(r);}else{const performanceHtml=processPerformanceBody(r);host.innerHTML=performanceHtml;bindFluxOptimizationActions();const envBtn=$('#viewHydraulicEnvelopeBtn');if(envBtn)envBtn.addEventListener('click',()=>changeMode('envelope'));}document.querySelectorAll('[data-result-subtab]').forEach(b=>b.classList.toggle('active',b.dataset.resultSubtab===tab));}
function bindProcessResultTabs(r){document.querySelectorAll('[data-result-subtab]').forEach(b=>b.addEventListener('click',()=>{resultSubtabByMode[mode]=b.dataset.resultSubtab;renderProcessResultSubtab(r)}));renderProcessResultSubtab(r)}
function showMultistage(r){showWarnings(r);$('#results').innerHTML=processResultTabsHtml();bindProcessResultTabs(r)}
function show(r){showWarnings(r);$('#results').innerHTML=processResultTabsHtml();bindProcessResultTabs(r);updateErdNavAccess()}

function syncSolveResult(r){lastResult=r;const autoPlant=isAutoPlantDesign();const basis=autoPlant?'recovery':(document.querySelector('[name="solve_basis"]')?.value||'pressure');const q=document.querySelector('[name="target_product_flow"]');const feed=document.querySelector('[name="feed_flow"]');const p=document.querySelector('[name="membrane_pressure_1"]');const p2=document.querySelector('[name="membrane_pressure_2"]');const rec=document.querySelector('[name="target_recovery"]');const qrej1=document.querySelector('[name="reject_flow_1"]');const qrej2=document.querySelector('[name="reject_flow_2"]');if(autoPlant){if(feed&&r.feed_flow!==undefined)feed.value=Number(r.feed_flow).toFixed(3);if(q&&r.product_flow!==undefined)q.value=Number(r.product_flow).toFixed(3);if(p&&r.membrane_pressure_1!==undefined)p.value=Number(r.membrane_pressure_1).toFixed(2);if(rec&&r.recovery!==undefined)rec.value=(Number(r.recovery)*100).toFixed(2);}else if(basis==='pressure'){if(q)q.value=Number(r.product_flow).toFixed(1);if(rec)rec.value=(Number(r.recovery)*100).toFixed(1);}else if(basis==='product'){if(p)p.value=Number(r.membrane_pressure_1).toFixed(1);if(p2&&r.membrane_pressure_2!==undefined)p2.value=Number(r.membrane_pressure_2).toFixed(1);if(rec)rec.value=(Number(r.recovery)*100).toFixed(1);}else if(basis==='recovery'){if(p)p.value=Number(r.membrane_pressure_1).toFixed(1);if(p2&&r.membrane_pressure_2!==undefined)p2.value=Number(r.membrane_pressure_2).toFixed(1);if(q)q.value=Number(r.product_flow).toFixed(1);}if(r.membrane_coupling){if(qrej1&&r.reject_flow_1!==undefined)qrej1.value=Number(r.reject_flow_1).toFixed(1);if(qrej2&&r.reject_flow_2!==undefined)qrej2.value=Number(r.reject_flow_2).toFixed(1);}updateRequiredFieldStates();}
function renderWaterChemistryResult(result=lastChemistryResult){
  if(!result)return;
  const host=document.querySelector('#results');if(!host)return;
  host.innerHTML=chemistryResultsHtml(result);
  const balanceButton=document.querySelector('#balanceWaterBtn');
  if(balanceButton&&typeof balanceActiveWater==='function')balanceButton.addEventListener('click',balanceActiveWater,{once:true});
  applyWaterChargeAnalysis(result);
  updateWorkspaceChrome();
}
function renderCurrentWaterChemistry(){
  const host=document.querySelector('#results');
  if(lastChemistryResult)renderWaterChemistryResult(lastChemistryResult);
  else{if(host)host.innerHTML='';updateWorkspaceChrome();}
}
function waterSummary(){const w=waterProfile;const ions=Object.keys(chemistry).filter(k=>k.startsWith('ion_')).reduce((a,k)=>a+Number(w[k]||0),0);return `<div class="water-summary-result"><h3>${escapeHtml(w.water_region_name||'Water quality')}</h3><div class="kpi-strip three"><div><span>Temperature</span><strong>${fmt(w.temperature_c)} °C</strong></div><div><span>Salinity</span><strong>${fmt(w.salinity_psu)} PSU</strong></div><div><span>Rounded TDS</span><strong>${fmt(w.analysis_tds)} mg/L</strong></div></div><p class="micro-note">Species sum: ${fmt(ions)} mg/L. Membrane-condition A/B multipliers are configured in Plant Design.</p></div>`}


const comparisonOrder=[['multistage','RO Plant Designer · gross train'],['single','Single Stage Turbo Charger'],['px','Single Stage Isobaric Chamber'],['interstage_px','Interstage Isobaric Chamber'],['interstage','Interstage Turbocharger'],['biturbo','BiTurbo™'],['dweer','DWEER'],['pelton','Pelton Turbine']];
const summarySpecies=[['calcium','Calcium'],['magnesium','Magnesium'],['sodium','Sodium'],['potassium','Potassium'],['strontium','Strontium'],['barium','Barium'],['iron_ii','Iron (II)'],['iron_iii','Iron (III)'],['manganese_ii','Manganese (II)'],['ammonium','Ammonium'],['bicarbonate','Bicarbonate'],['sulfate','Sulfate'],['chloride','Chloride'],['nitrate','Nitrate'],['fluoride','Fluoride'],['phosphate','o-Phosphate'],['carbonate','Carbonate'],['silica','Silica'],['boron','Boron'],['bromide','Bromide']];
function resultFlowInCurrent(r,v){return convert(v,'flow',r.flow_unit||currentUnits.flow,currentUnits.flow)}
function resultPressureInCurrent(r,v){return convert(v,'pressure',r.pressure_unit||currentUnits.pressure,currentUnits.pressure)}
function pressureFlowEnvelopeChart(){
  const techSeries=[];
  comparisonOrder.forEach(([key,label],ti)=>{const pts=[];for(let cid=1;cid<=4;cid++){const c=caseStore[cid],r=c?.caseResults?.[key];if(!r)continue;const qRaw=['px','interstage_px'].includes(key)?(r.hpp_flow??r.feed_flow):r.feed_flow;const pRaw=r.membrane_pressure_1;if(qRaw===undefined||pRaw===undefined)continue;pts.push({cid,q:resultFlowInCurrent(r,qRaw),p:resultPressureInCurrent(r,pRaw),label:c.waterProfile?.envelope_label||`Case ${cid}`});}if(pts.length)techSeries.push({key,label,ti,pts})});
  if(!techSeries.length)return `<section class="report-section"><h3>P vs Q · HYDRAULIC ENVELOPE</h3><p class="muted">Generate the four-case hydraulic envelope, then calculate at least one technology to populate this chart.</p></section>`;
  const all=techSeries.flatMap(s=>s.pts),xs=all.map(x=>x.q),ys=all.map(x=>x.p);let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);const xpad=Math.max((xmax-xmin)*.15,Math.max(Math.abs(xmax),1)*.04),ypad=Math.max((ymax-ymin)*.15,Math.max(Math.abs(ymax),1)*.04);xmin=Math.max(0,xmin-xpad);xmax+=xpad;ymin=Math.max(0,ymin-ypad);ymax+=ypad;
  const W=850,H=310,L=62,R=28,T=28,B=50,x=v=>L+(v-xmin)*(W-L-R)/(xmax-xmin||1),y=v=>T+(ymax-v)*(H-T-B)/(ymax-ymin||1),grid=[];
  for(let i=0;i<=4;i++){const xv=xmin+(xmax-xmin)*i/4,xx=L+(W-L-R)*i/4;grid.push(`<line x1="${xx}" y1="${T}" x2="${xx}" y2="${H-B}" class="flux-grid"/><text x="${xx}" y="${H-B+18}" text-anchor="middle" class="flux-axis-text">${fmt(xv,1)}</text>`);const yv=ymax-(ymax-ymin)*i/4,yy=T+(H-T-B)*i/4;grid.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="flux-grid"/><text x="${L-8}" y="${yy+3}" text-anchor="end" class="flux-axis-text">${fmt(yv,1)}</text>`)}
  const series=techSeries.map(s=>{const path=s.pts.length>1?`<path d="${s.pts.map((p,i)=>`${i?'L':'M'} ${x(p.q).toFixed(1)} ${y(p.p).toFixed(1)}`).join(' ')}" class="pq-line pq-${s.ti}"/>`:'';const dots=s.pts.map(p=>`<g class="pq-point pq-${s.ti}"><circle cx="${x(p.q)}" cy="${y(p.p)}" r="5"/><text x="${x(p.q)+7}" y="${y(p.p)-7}" class="pq-label">C${p.cid}</text><title>Case ${p.cid} · ${p.label} · ${s.label}: Q ${fmt(p.q,2)} ${currentUnits.flow}, P ${fmt(p.p,2)} ${currentUnits.pressure}</title></g>`).join('');return path+dots}).join('');
  const legend=techSeries.map(s=>`<span class="pq-legend pq-${s.ti}">${escapeHtml(s.label)}</span>`).join('');
  return `<section class="report-section"><div class="chart-title-row"><h3>P vs Q · HYDRAULIC ENVELOPE</h3><span>Cases 1–4 · HP pump / membrane operating points</span></div><div class="pq-legend-row">${legend}</div><div class="flux-chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Pressure versus flow hydraulic envelope">${grid.join('')}<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/>${series}<text x="${(L+W-R)/2}" y="${H-8}" text-anchor="middle" class="flux-axis-title">Pump / feed flow (${currentUnits.flow})</text><text x="16" y="${(T+H-B)/2}" transform="rotate(-90 16 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Required membrane feed pressure (${currentUnits.pressure})</text></svg></div><p class="micro-note">C1 new/cold, C2 new/warm, C3 aged/cold, C4 aged/warm when generated by the hydraulic-envelope tool. Isobaric Chamber uses HP-pump flow; turbo configurations use membrane/feed-pump flow.</p></section>`;
}
function summaryResultForCase(c){if(!c)return [null,null];if(summaryTechnology!=='auto'){const r=c.caseResults?.[summaryTechnology]||null;return [summaryTechnology,resultMatchesCaseWaterBasis(c,r)?r:null];}for(const k of ['multistage','px','interstage_px','single','interstage','biturbo','dweer','pelton']){const r=c.caseResults?.[k];if(r&&resultMatchesCaseWaterBasis(c,r))return [k,r];}return [null,null]}
function weightedComposition(a,qa,b,qb){if(!a)return b||null;if(!b)return a;qa=Number(qa)||0;qb=Number(qb)||0;const qt=qa+qb;if(qt<=0)return a;const out={};summarySpecies.forEach(([k])=>out[k]=(qa*Number(a[k]||0)+qb*Number(b[k]||0))/qt);return out}
function resultStageCount(r){let n=Number(r?.stage_count||0);if(n>0)return n;for(let i=4;i>=1;i--)if(r?.[`stage${i}_pressure_vessels`]!==undefined)return i;return 1}
function waterStreamsForResult(c,r){const feed=r?.stage1_feed_composition_mg_l||Object.fromEntries(summarySpecies.map(([k])=>[k,Number(c.waterProfile?.['ion_'+k]||0)]));const n=resultStageCount(r);const conc=r?(r[`stage${n}_concentrate_composition_mg_l`]||r.stage1_concentrate_composition_mg_l):null;let perm=r?.composite_permeate_composition_mg_l||r?.stage1_permeate_composition_mg_l||null;if(!r?.composite_permeate_composition_mg_l){let mixedQ=Number(r?.stage1_permeate_flow||0);for(let i=2;i<=n;i++)if(r?.[`stage${i}_permeate_composition_mg_l`]){const qi=Number(r[`stage${i}_permeate_flow`]||0);perm=weightedComposition(perm,mixedQ,r[`stage${i}_permeate_composition_mg_l`],qi);mixedQ+=qi;}}return {feed,conc,perm}}
function compositionTds(comp){return comp?summarySpecies.reduce((a,[k])=>a+Number(comp[k]||0),0):null}
function renderSummaryTab(){
  const opts=[['auto','Auto · first calculated technology'],...comparisonOrder].map(([k,l])=>`<option value="${k}" ${summaryTechnology===k?'selected':''}>${escapeHtml(l)}</option>`).join('');
  $('#fields').innerHTML=`<section class="input-section"><h3>CASE WATER-QUALITY SUMMARY</h3><div class="grid"><div class="field span2"><label>Technology basis for concentrate / permeate</label><div class="wrap"><select id="summaryTechnology" name="summaryTechnology">${opts}</select></div></div></div><p class="micro-note">Feed water is stored independently for each case. Concentrate and permeate chemistry come from the selected converged membrane calculation. The layout follows the feed / concentrate / permeate reporting philosophy in the supplied scaling workbook and vendor projection reports.</p></section>`;
  $('#modeLabel').textContent='Case Summary';setPrimaryLabel('Refresh case summary');$('.solve-hint').textContent='Review water quality and operating results across all cases.';const sel=$('#summaryTechnology');if(sel)sel.addEventListener('change',()=>{summaryTechnology=sel.value;$('#results').innerHTML=summaryResults()});
}
function summaryResults(includeScenarioMatrix=true){
  syncActiveCaseStore();const ids=Object.keys(caseStore).map(Number).sort((a,b)=>a-b);if(!ids.length)return '<p class="muted">No cases available.</p>';
  const overview=ids.map(id=>{const c=caseStore[id],[key,r]=summaryResultForCase(c);const tech=key?comparisonOrder.find(x=>x[0]===key)?.[1]:'—';return `<tr><td><strong>Case ${id}</strong><br><span class="tbl-unit">${escapeHtml(c.waterProfile?.envelope_label||'')}</span></td><td>${fmt(c.waterProfile?.temperature_c,1)} °C</td><td>${fmt(c.waterProfile?.fouling_factor,2)}</td><td>${fmt(c.waterProfile?.salt_passage_factor,2)}</td><td>${fmt(c.waterProfile?.analysis_tds,0)}</td><td>${escapeHtml(tech||'—')}</td><td>${r?fmt(r.membrane_pressure_1,1):'—'} ${r?escapeHtml(r.pressure_unit):''}</td><td>${r?pct(r.recovery,1)+'%':'—'}</td><td>${r?fmt(r.total_sec,3):'—'}</td></tr>`}).join('');
  const chemistryCards=ids.map(id=>{const c=caseStore[id],[key,r]=summaryResultForCase(c),streams=waterStreamsForResult(c,r);const rows=summarySpecies.map(([k,label])=>`<tr><td>${escapeHtml(label)}</td><td>${fmt(streams.feed?.[k],2)}</td><td>${streams.conc?fmt(streams.conc[k],2):'—'}</td><td>${streams.perm?fmt(streams.perm[k],2):'—'}</td></tr>`).join('');return `<section class="summary-case-card"><div class="summary-case-head"><div><strong>Case ${id}</strong><span>${escapeHtml(c.waterProfile?.envelope_label||'')}</span></div><div>${r?escapeHtml(comparisonOrder.find(x=>x[0]===key)?.[1]||key):'Water quality only'}</div></div><div class="summary-stream-kpis"><span>Feed TDS <b>${fmt(compositionTds(streams.feed),0)} mg/L</b></span><span>Concentrate TDS <b>${streams.conc?fmt(compositionTds(streams.conc),0):'—'} mg/L</b></span><span>Permeate TDS <b>${streams.perm?fmt(compositionTds(streams.perm),1):'—'} mg/L</b></span></div><div class="table-wrap"><table class="fedco-table summary-water-table"><tr><th>Species</th><th>Feed<br><span>mg/L</span></th><th>Concentrate<br><span>mg/L</span></th><th>Permeate<br><span>mg/L</span></th></tr>${rows}</table></div></section>`}).join('');
  const scenarioPrefix=(Object.values(caseStore||{}).some(c=>c?.scenarioMeta)?`${includeScenarioMatrix?scenarioMatrixResults():''}${scenarioStudyInsights()}`:'');
  return `${scenarioPrefix}<section class="report-section"><h3>ALL-CASE OPERATING SUMMARY</h3><div class="table-wrap"><table class="fedco-table"><tr><th>Case</th><th>Temperature</th><th>Fouling factor</th><th>Salt passage factor</th><th>Feed TDS<br><span>mg/L</span></th><th>Technology basis</th><th>Feed pressure</th><th>Recovery</th><th>Total SEC<br><span>kWh/m³</span></th></tr>${overview}</table></div></section><section class="report-section"><h3>FEED · CONCENTRATE · PERMEATE WATER ANALYSIS</h3><p class="micro-note">Species basis is aligned with the shared Scaling Index Calculator, including trace Fe(II), Fe(III), Mn(II) and o-phosphate fields. Scaling/saturation indices from that workbook are not silently substituted in this release; the table reports Total RO Design's membrane mass-balance chemistry.</p><div class="summary-case-grid">${chemistryCards}</div></section>${pressureFlowEnvelopeChart()}`;
}
function comparisonCaseCard(key,label){
  const r=caseResults[key];if(!r)return `<div class="case-ready missing"><strong>${escapeHtml(label)}</strong><span>Not calculated yet</span></div>`;
  if(!resultMatchesCaseWaterBasis(activeCaseData(),r))return `<div class="case-ready stale"><strong>${escapeHtml(label)}</strong><span>Result stale · recalculate</span></div>`;
  return `<div class="case-ready ready"><strong>${escapeHtml(label)}</strong><span>Calculated · Total SEC ${fmt(r.total_sec)} kWh/m³ · Recovery ${pct(r.recovery)}%</span></div>`;
}
function renderComparisonTab(){$('#fields').innerHTML=`<section class="input-section comparison-intro"><h3>SEC VS TECHNOLOGY</h3><p class="comparison-copy">Compare power consumption using the converged duty point from each technology tab. The comparison uses each case's calculated RO SEC plus pretreatment SEC, without changing the process inputs.</p><div class="case-readiness">${comparisonOrder.map(([k,l])=>comparisonCaseCard(k,l)).join('')}</div></section>`;$('#modeLabel').textContent=`Power Consumption Comparison · Case ${activeCase}`;setPrimaryLabel('Refresh SEC comparison');$('.solve-hint').textContent='SEC vs technology · calculate each technology first, then compare total and RO-only specific energy consumption.';}
function secRangePanel(data,key,title){
  const vals=data.map(x=>Number(x[key])).filter(Number.isFinite);if(!vals.length)return '';
  const min=Math.min(...vals),max=Math.max(...vals),avg=vals.reduce((a,b)=>a+b,0)/vals.length;
  const pad=Math.max(0.03,(max-min)*0.08,avg*0.01),scaleMin=Math.max(0,min-pad),scaleMax=max+pad,pos=v=>100*(v-scaleMin)/(scaleMax-scaleMin||1);
  const bars=data.map(x=>{const v=Number(x[key]);return `<div class="sec-range-row ${Math.abs(v-min)<1e-9?'best':''}"><div class="sec-range-heading"><strong>${escapeHtml(x.label)}</strong><span>${fmt(v,3)} kWh/m³</span></div><div class="sec-range-scale"><span>${fmt(scaleMin,2)}</span><div class="sec-range-track"><i class="sec-range-marker" style="left:${Math.max(0,Math.min(100,pos(v))).toFixed(1)}%"></i></div><span>${fmt(scaleMax,2)}</span></div></div>`}).join('');
  return `<section class="report-section sec-half-panel"><div class="chart-title-row"><h3>${escapeHtml(title)}</h3><span>Min ${fmt(min,3)} · Avg ${fmt(avg,3)} · Max ${fmt(max,3)}</span></div><div class="sec-range-chart">${bars}</div></section>`;
}
function comparisonResults(){
  syncActiveCaseStore();
  const available=comparisonOrder.filter(([k])=>caseResults[k]&&resultMatchesCaseWaterBasis(activeCaseData(),caseResults[k]));
  const pq=pressureFlowEnvelopeChart();
  if(!available.length)return `<div class="comparison-empty"><strong>No current technology cases calculated for Case ${activeCase} yet.</strong><span>Calculate one or more technology tabs for this case. Stale results must be recalculated after a water-quality or membrane-condition change.</span></div>${pq}`;
  const data=available.map(([k,label])=>{const r=caseResults[k];const c=resultCaseForEconomics(r);return {key:k,label,r,...c,total_kw:c.total_sec*c.product_flow_m3h,ro_kw:c.ro_sec*c.product_flow_m3h};});
  const totals=data.map(x=>x.total_sec),min=Math.min(...totals),max=Math.max(...totals),avg=totals.reduce((a,b)=>a+b,0)/totals.length;
  const rows=data.map(x=>`<tr class="${Math.abs(x.total_sec-min)<1e-9?'best-row':''}"><td><strong>${escapeHtml(x.label)}</strong></td><td>${fmt(x.ro_sec,3)}</td><td>${fmt(x.pretreatment_sec,3)}</td><td><strong>${fmt(x.total_sec,3)}</strong></td><td>${fmt(x.total_kw,1)}</td><td>${pct(x.recovery)}%</td><td>${fmt(x.product_flow_m3h,1)}</td></tr>`).join('');
  const best=data.find(x=>Math.abs(x.total_sec-min)<1e-9),worst=data.find(x=>Math.abs(x.total_sec-max)<1e-9);
  return `<div class="case-result-banner"><strong>Case ${activeCase}</strong><span>${escapeHtml(waterProfile.envelope_label||waterProfile.water_region_name||'')}</span></div><div class="kpi-strip five"><div><span>Lowest total SEC</span><strong>${escapeHtml(best.label)}</strong></div><div><span>Minimum total SEC</span><strong>${fmt(min,3)} kWh/m³</strong></div><div><span>Average total SEC</span><strong>${fmt(avg,3)} kWh/m³</strong></div><div><span>Maximum total SEC</span><strong>${fmt(max,3)} kWh/m³</strong><small>${escapeHtml(worst.label)}</small></div><div><span>Technologies compared</span><strong>${data.length}</strong></div></div><div class="sec-dual-grid">${secRangePanel(data,'total_sec',`TOTAL PLANT SEC · CASE ${activeCase}`)}${secRangePanel(data,'ro_sec',`RO SEC · CASE ${activeCase}`)}</div><section class="report-section"><h3>POWER CONSUMPTION COMPARISON</h3><div class="table-wrap"><table class="fedco-table comparison-table"><tr><th>Technology</th><th>RO SEC<br><span>kWh/m³</span></th><th>Pretreatment SEC<br><span>kWh/m³</span></th><th>Total SEC<br><span>kWh/m³</span></th><th>Total power<br><span>kW</span></th><th>Recovery</th><th>Product flow<br><span>m³/h</span></th></tr>${rows}</table></div><p class="micro-note">Total-plant and RO-only SEC are shown in separate half-width panels. Each technology has one horizontal range bar and one marker. Each panel reports its own minimum, average and maximum SEC.</p></section>${pq}`;
}

function econField(name,label,value,suffix='',step='any',placeholder='',required=false){return `<div class="field"><label>${label}</label><div class="wrap"><input name="${name}" type="number" step="${step}" value="${value??''}" placeholder="${escapeHtml(placeholder)}" ${required?'required':''}>${suffix?`<span class="suffix">${suffix}</span>`:''}</div></div>`}
function caseReadyCard(key,label){const r=caseResults[key];if(!r)return `<div class="case-ready missing"><strong>${label}</strong><span>Not calculated yet</span></div>`;return `<div class="case-ready"><strong>${label}</strong><span>Recovery ${pct(r.recovery)}% · RO ${fmt(r.ro_sec)} + Pret ${fmt(r.pretreatment_sec)} = ${fmt(r.total_sec)} kWh/m³</span></div>`}
function renderEconomicTab(){
  const e=economicState;
  $('#fields').innerHTML=`<section class="input-section"><h3>PROJECT ECONOMIC BASIS</h3><div class="grid">${econField('product_capacity_m3d','Product capacity',e.product_capacity_m3d,'m³/d','any','e.g. 10,000',true)}${econField('availability','Availability',e.availability,'fraction')}${econField('electricity_price','Electricity price',e.electricity_price,'USD/kWh')}${econField('project_life','Project life',e.project_life,'years')}${econField('discount_rate','Discount / capital recovery rate',e.discount_rate,'fraction')}${econField('base_capex_per_m3d','Baseline installed CAPEX',e.base_capex_per_m3d,'USD/(m³/d)','any','e.g. 2,000',true)}</div><p class="micro-note"><strong>Indicative installed-cost guidance:</strong> a modern seawater desalination plant can commonly fall in the order of <strong>1,500–4,000 USD per m³/day of installed product capacity</strong>, depending strongly on site conditions and project scope. This total-installed-cost range is intended to include the desalination facility together with intake and outfall systems and civil, mechanical, electrical and installation costs. For screening, a user might enter a plant capacity such as 10,000 m³/d and an installed CAPEX basis such as 2,000 USD/(m³/d), but both fields should be replaced with project-specific assumptions.</p></section>
  <section class="input-section"><h3>CAPEX SAVINGS ASSUMPTIONS · EDITABLE</h3><div class="grid">${econField('turbo_ro_equipment_saving','Turbo RO-system equipment saving',e.turbo_ro_equipment_saving,'fraction')}${econField('turbo_electrical_saving','Turbo electrical / I&C saving',e.turbo_electrical_saving,'fraction')}${econField('turbo_building_saving','Turbo fixed building / footprint saving',e.turbo_building_saving,'fraction')}${econField('turbo_startup_saving','Turbo startup / commissioning saving',e.turbo_startup_saving,'fraction')}${econField('turbo_engineering_saving','Turbo engineering saving',e.turbo_engineering_saving,'fraction')}${econField('biturbo_ro_equipment_adder','BiTurbo RO-package CAPEX adder vs Turbo basis',e.biturbo_ro_equipment_adder,'fraction')}${econField('pretreatment_flow_exponent','Pretreatment CAPEX flow-scaling exponent',e.pretreatment_flow_exponent,'')}${econField('building_flow_exponent','Building / footprint flow-scaling exponent',e.building_flow_exponent,'')}</div><p class="micro-note">Workbook defaults: 15% RO equipment, 15% electrical/I&C, 5% buildings, 10% startup and 10% engineering savings for Turbo vs Isobaric Chamber. Pretreatment and building/footprint costs are additionally scaled by each design's calculated feed-per-product ratio, so higher recovery in BiTurbo can create real pretreatment CAPEX and pretreatment-SEC savings. The BiTurbo package adder is left at 0% unless vendor/project pricing supports another value.</p></section>
  <section class="input-section"><h3>OPTIONAL INCREMENTAL FIXED O&M</h3><div class="grid">${econField('fixed_om_px','Isobaric Chamber fixed O&M',e.fixed_om_px,'USD/y')}${econField('fixed_om_single','Single Turbo fixed O&M',e.fixed_om_single,'USD/y')}${econField('fixed_om_biturbo','BiTurbo fixed O&M',e.fixed_om_biturbo,'USD/y')}</div></section>
  <section class="input-section"><h3>CALCULATED CASES USED BY ECONOMIC MODEL</h3><div class="case-readiness">${caseReadyCard('px','Single Stage Isobaric Chamber')}${caseReadyCard('single','Single Stage Turbo Charger')}${caseReadyCard('biturbo','BiTurbo™')}</div><p class="micro-note">Calculate the Isobaric Chamber, Single Turbo and/or BiTurbo tabs with the desired membrane configuration first. Interstage Turbo is intentionally excluded from the Isobaric Chamber economic comparison. The economic model normalizes the resulting SEC and feed/product ratios to the project capacity entered above.</p></section>`;
  $('#modeLabel').textContent=`Economic Analysis · Case ${activeCase}`;setPrimaryLabel('Run economic comparison');$('.solve-hint').textContent='Compare Single Stage Isobaric Chamber, Single Stage Turbo Charger and BiTurbo™ CAPEX, RO SEC, pretreatment SEC, annual energy cost, LCOW and lifecycle economics.';
}
function captureEconomic(){const o={...economicState};new FormData($('#calcForm')).forEach((v,k)=>o[k]=(v===''?'':(isNaN(v)?v:+v)));economicState=o;return o}
function resultCaseForEconomics(r){const f={'m3/h':1,'L/s':3.6,gpm:.227124707}[r.flow_unit]||1;return {feed_flow_m3h:Number(r.feed_flow)*f,product_flow_m3h:Number(r.product_flow)*f,recovery:Number(r.recovery),ro_sec:Number(r.ro_sec),pretreatment_sec:Number(r.pretreatment_sec),total_sec:Number(r.total_sec)}}
function money(v){if(v===null||v===undefined||!Number.isFinite(Number(v)))return '—';return '$'+Number(v).toLocaleString(undefined,{maximumFractionDigits:0})}
function economicResults(r){const order=['px','single','biturbo'].filter(k=>r.cases[k]);const rows=order.map(k=>{const c=r.cases[k];const bep=c.break_even_power_price_usd_kwh;return `<tr><td><strong>${escapeHtml(c.label)}</strong></td><td>${fmt(c.feed_capacity_factor_vs_px,2)}×</td><td>${fmt(c.ro_sec)}</td><td>${fmt(c.pretreatment_sec)}</td><td>${fmt(c.total_sec)}</td><td>${money(c.capex_usd)}</td><td>${money(c.pretreatment_capex_saving_vs_baseline_usd)}</td><td>${money(c.building_capex_saving_vs_baseline_usd)}</td><td>${money(c.annual_energy_cost_usd)}</td><td>${money(c.annualized_capex_usd_y)}</td><td>${money(c.equivalent_annual_cost_usd_y)}</td><td>$${fmt(c.lcow_usd_m3,3)}</td><td>${money(c.npv_usd)}</td><td>${bep==null?'—':'$'+fmt(bep,3)}</td></tr>`}).join('');
  const preferred=r.cases[r.preferred];
  const cards=order.filter(k=>k!=='px').map(k=>{const c=r.cases[k];const winner=c.annual_cost_advantage_winner||((c.annual_cost_advantage_vs_px_usd||0)>=0?c.label:'Isobaric Chamber');const advantage=c.annual_cost_advantage_usd??Math.abs(c.annual_cost_advantage_vs_px_usd||0);return `<div class="econ-saving-card"><h4>${escapeHtml(c.label)} vs Isobaric Chamber</h4><dl><dt>Upfront CAPEX saving</dt><dd>${money(c.capex_saving_vs_px_usd)}</dd><dt>Pretreatment CAPEX saving</dt><dd>${money(c.pretreatment_capex_saving_vs_baseline_usd)}</dd><dt>Building / footprint saving</dt><dd>${money(c.building_capex_saving_vs_baseline_usd)}</dd><dt>Pretreatment SEC</dt><dd>${fmt(c.pretreatment_sec)} kWh/m³</dd><dt>Annual cost advantage · ${escapeHtml(winner)}</dt><dd class="ok">${money(advantage)}/y</dd><dt>Break-even power price</dt><dd>${c.break_even_power_price_usd_kwh==null?'No positive break-even':('$'+fmt(c.break_even_power_price_usd_kwh,3)+'/kWh')}</dd></dl></div>`}).join('');
  return `<div class="kpi-strip five"><div><span>Preferred configuration</span><strong>${escapeHtml(r.preferred_label)}</strong></div><div><span>Lowest LCOW</span><strong>$${fmt(preferred.lcow_usd_m3,3)}/m³</strong></div><div><span>Annual production</span><strong>${fmt(r.annual_product_m3/1e6,2)} Mm³/y</strong></div><div><span>Baseline CAPEX</span><strong>${money(r.baseline_capex_usd)}</strong></div><div><span>Electricity</span><strong>$${fmt(r.electricity_price,3)}/kWh</strong></div></div>${economicVisualizations(r)}<section class="report-section"><h3>ECONOMIC COMPARISON</h3><div class="table-wrap"><table class="fedco-table econ-table"><tr><th>Technology</th><th>Feed capacity<br>vs PX</th><th>RO SEC<br>kWh/m³</th><th>Pret SEC<br>kWh/m³</th><th>Total SEC<br>kWh/m³</th><th>Installed CAPEX</th><th>Pretreatment<br>CAPEX saving</th><th>Footprint / building<br>saving</th><th>Annual energy</th><th>Annualized CAPEX</th><th>Equivalent annual cost</th><th>LCOW<br>USD/m³</th><th>Lifecycle NPV</th><th>Break-even<br>USD/kWh</th></tr>${rows}</table></div></section><section class="report-section"><h3>TURBO / BITURBO SAVINGS DETAIL</h3><div class="econ-card-grid">${cards}</div></section><p class="micro-note">${escapeHtml(r.source_note)}</p>`;
}
async function calcEconomic(){const data=captureEconomic();const cases={};Object.entries(caseResults).forEach(([k,r])=>{if(['px','single','biturbo'].includes(k))cases[k]=resultCaseForEconomics(r)});data.cases=cases;const j=await requestJson('/api/economics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)},'Economic calculation error');lastEconomicResult=j;$('#warnings').innerHTML='';$('#results').innerHTML=economicResults(j)}

async function pollComputeStatus(){
  try{
    const response=await totalroFetch('/api/compute/status',{cache:'no-store'});if(!response.ok)return;
    computeLiveStatus=await response.json();updateComputeStatus();renderComputePanel();
    const detail=$('#calculationDetail'),eta=$('#calculationEta'),bar=$('#calculationProgressBar');
    if(computeLiveStatus?.active){
      const phase=String(computeLiveStatus.phase||'Engineering calculation in progress');
      if(detail)detail.textContent=phase;
      const elapsed=Math.max(0,Number(computeLiveStatus.elapsed_seconds||0));
      const remaining=computeLiveStatus.eta_seconds==null?null:Math.max(0,Number(computeLiveStatus.eta_seconds));
      if(eta)eta.textContent=remaining==null?`Elapsed ${formatRunTime(elapsed)} · Estimated remaining: calculating…`:`Elapsed ${formatRunTime(elapsed)} · Estimated remaining ~${formatRunTime(remaining)}`;
      const progress=Number(computeLiveStatus.progress_fraction||0);
      if(bar&&progress>0){bar.classList.add('determinate');bar.style.width=`${Math.max(2,Math.min(100,progress*100))}%`;}
    }
  }catch(_){}
}
function startComputePolling(){if(computePollTimer)return;pollComputeStatus();computePollTimer=setInterval(pollComputeStatus,1500)}
function stopComputePolling(){if(computePollTimer){clearInterval(computePollTimer);computePollTimer=null}}

function formatRunTime(seconds){
  const n=Math.max(0,Number(seconds)||0);if(n<60)return `${Math.round(n)} s`;const m=Math.floor(n/60),sec=Math.round(n-m*60);if(m<60)return `${m}m ${String(sec).padStart(2,'0')}s`;const h=Math.floor(m/60),mm=m-h*60;return `${h}h ${mm}m`;
}
function showCalculationCancelledNotice(){const w=$('#warnings');if(w)w.innerHTML='<div class="calc-cancelled-note">Calculation stopped by user. The unfinished result was discarded; your input values were preserved.</div>';}
async function cancelActiveCalculation(){
  if(!document.body.classList.contains('calculating')||calculationCancelRequested)return;
  calculationCancelRequested=true;const b=$('#cancelCalculationBtn'),title=$('#calculationTitle'),detail=$('#calculationDetail'),eta=$('#calculationEta');
  if(b){b.disabled=true;b.textContent='Stopping…'}if(title)title.textContent='Stopping calculation…';if(detail)detail.textContent='Interrupting active solver workers and closing the current search safely.';if(eta)eta.textContent='Cancellation requested · unfinished results will not be applied.';
  try{await totalroFetch('/api/compute/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:computeLiveStatus?.run_id??null})});}catch(_){}
  try{activeCalculationController?.abort();}catch(_){}
}
function emitCalculationState(state,message=''){
  document.dispatchEvent(new CustomEvent('twds:ro-calculation-state',{detail:{state,mode,message}}));
}
function setCalculating(active){
  const overlay=$('#calculationOverlay');
  const btn=calculateButton();
  document.body.classList.toggle('calculating',active);
  if(overlay)overlay.hidden=!active;
  if(btn){
    btn.disabled=active;btn.setAttribute('aria-busy',active?'true':'false');btn.dataset.twdsBusy=active?'1':'0';
    if(active){
      btn.dataset.twdsCalculateState='calculating';
      if(!btn.dataset.twdsIdleLabel)btn.dataset.twdsIdleLabel=workspaceCalculateLabel(mode);
      const label=calculateButtonLabel();if(label)label.textContent=mode==='water'?'Calculating water chemistry…':mode==='multistage'?'Calculating Plant Design…':'Calculating…';
    }else{
      const idleLabel=btn.dataset.twdsIdleLabel||workspaceCalculateLabel(mode);
      btn.removeAttribute('data-twds-calculate-state');setPrimaryLabel(idleLabel);
    }
  }
  if(active){
    calculationCancelRequested=false;activeCalculationController=new AbortController();
    const detail=$('#calculationDetail'),eta=$('#calculationEta'),title=$('#calculationTitle'),bar=$('#calculationProgressBar'),cancel=$('#cancelCalculationBtn');
    const chemistryRun=mode==='water';
    if(title)title.textContent=chemistryRun?'Analyzing water chemistry…':'Calculating duty point…';
    if(detail)detail.textContent=chemistryRun?'Evaluating ion balance, speciation, osmotic pressure and scaling indices.':'Waiting for calculation status…';
    if(eta)eta.textContent=chemistryRun?'Results will appear when the chemistry analysis completes.':'Estimating run time…';
    if(bar){bar.classList.remove('determinate');bar.style.width='';}if(cancel){cancel.disabled=false;cancel.textContent='Stop calculation';}
    if(chemistryRun)stopComputePolling();else startComputePolling();
    emitCalculationState('calculating',title?.textContent||'Calculation started');
  }else{
    activeCalculationController=null;calculationCancelRequested=false;emitCalculationState('idle',workspaceCalculateLabel(mode));
    setTimeout(async()=>{await pollComputeStatus();if(!computePanelOpen)stopComputePolling();},550);
  }
}

async function calc(){
  if(mode==='water'){
    const runSequence=canonicalCalculationSequence;
    waterProfile=captureWater();caseSetupNotice='';
    const chem=await requestJson('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(profileChemPayload(waterProfile))},'Water chemistry calculation failed');
    if(runSequence!==canonicalCalculationSequence||calculationCancelRequested){const error=new Error('Calculation stopped by user.');error.kind='cancelled';error.cancelled=true;throw error;}
    lastChemistryResult=chem;const c=activeCaseData();if(c){c.chemistryResult=deepClone(chem);if(c.baseDesignSeed)c.baseDesignSeed.stale=true;c.caseResults={};c.advancedDesignResult=null;}syncActiveCaseStore();renderWaterChemistryResult(chem);renderCaseBar();updateWorkflowGates();return;
  }
  if(mode==='chemistry'){await loadChemistryResults();return;}
  if(mode==='envelope'){waterProfile=captureEnvelopeSettings();syncActiveCaseStore();await calculateHydraulicEnvelope();return;}
  if(mode==='scenario'){await calculateScenarioMatrix();return;}
  if(mode==='comparison'){syncActiveCaseStore();renderComparisonTab();$('#warnings').innerHTML='';$('#results').innerHTML=comparisonResults();return;}
  if(mode==='summary'){syncActiveCaseStore();renderSummaryTab();$('#warnings').innerHTML='';$('#results').innerHTML=summaryResults();return;}
  if(mode==='economic'){await calcEconomic();syncActiveCaseStore();return;}
  let captured=capture();const previousState=modeStates[mode]||{};const workflowMeta={};Object.entries(previousState).forEach(([k,v])=>{if(k.startsWith('_')||['generated_from_base_plant','solution_enabled','generalized_biturbo','plant_solution'].includes(k))workflowMeta[k]=v;});if(mode==='multistage'){delete workflowMeta._last_calculated_signature;delete workflowMeta._erd_populated_signature;captured.design_mode='manual';}let data={...waterProfile,...captured,...workflowMeta,...activeTurboLockFields(mode)};if(mode==='multistage'&&!tierAllows('vcmp_pump_selection'))data.pump_curve_basis='auto';modeStates[mode]={...captured,...workflowMeta};data.flow_unit=$('#flowUnit').value;data.pressure_unit=$('#pressureUnit').value;if(data.max_design_flux_lmh!==undefined&&data.max_design_flux_lmh!=='')data.max_design_flux_lmh=convert(data.max_design_flux_lmh,'flux',$('#fluxUnit').value,'LMH');
  if(mode==='px'){data.px_lp_inlet_pressure=data.suction_pressure;data.mpe_hp_dp=.66;data.mpe_lp_dp=.74;data.mpe_mixing=.02;data.mpe_motor_power=.8;}
  const j=await requestJson(`/api/calculate/${mode}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)},'Calculation error');

  if(mode==='multistage'){invalidateDerivedResultsFromBasePlant();caseResults.multistage=j;captured._last_calculated_signature=basePlantSignature(captured);modeStates.multistage={...captured};const c=activeCaseData();if(c){c.baseDesignSeed=makeBaseDesignSeed({...data,...captured},j);c.advancedDesignInput={};c.advancedDesignResult=null;}advancedDesignInput={};advancedDesignResult=null;}else{embeddedChemistryCache={};tailChemistryCache={};caseResults[mode]=j;}
  modeStates[mode]={...captured,...workflowMeta};caseResults[mode]=j;syncActiveCaseStore();syncSolveResult(j);show(j);renderCaseBar();updateWorkflowGates();
}
function convertedDefaults(){if(mode==='water')return waterProfile;if(mode==='advanced'||mode==='chemistry'||mode==='envelope'||mode==='scenario'||mode==='comparison'||mode==='summary')return {};if(mode==='economic')return economicState;const base=defaults[mode],d=defn(),v={...base};Object.entries(d).forEach(([k,f])=>{if(f.type==='flow')v[k]=convert(base[k],'flow','m3/h',$('#flowUnit').value);if(f.type==='pressure')v[k]=convert(base[k],'pressure','bar',$('#pressureUnit').value);if(f.type==='flux')v[k]=convert(base[k],'flux','LMH',$('#fluxUnit').value)});return v}
function changeMode(newMode){
  if(canonicalCalculationInFlight||document.body.classList.contains('calculating'))return;
  if(newMode==='chemistry')newMode=caseResults?.multistage?'multistage':'water';
  const entitlement=modeEntitlementAccess(newMode);if(!entitlement.ok){showCalcError(new Error(entitlement.reason),'subscription tier');return;}
  persistActiveCase();if(newMode==='multistage'&&!caseWaterIsValid()){showCalcError(new Error('Calculate valid Water Quality before Plant Design.'),'workflow');return;}if((newMode==='advanced'||newMode==='envelope')&&!casePlantIsValid()){showCalcError(new Error('Calculate a valid Plant Design first.'),'workflow');return;}if(ERD_MODES.includes(newMode)){const a=erdModeAccess(newMode);if(!a.ok){showCalcError(new Error(a.reason),'input');updateErdNavAccess();return;}ensureErdWorkspaceFromBase(newMode);} mode=newMode; lastResult=caseResults[mode]||null; updateWaterWorkspaceTabs(); currentUnits={flow:$('#flowUnit').value,pressure:$('#pressureUnit').value,flux:$('#fluxUnit')?.value||'LMH'};
  const vals=modeStates[mode]||convertedDefaults();
  const resultsHost=$('#results');if(resultsHost)resultsHost.innerHTML='<p class="muted">Loading configuration…</p>';
  try{renderFields(vals);}catch(e){if(resultsHost)resultsHost.innerHTML='<p class="muted">This configuration could not be rendered. No results from another technology are being shown.</p>';showCalcError(new Error(`Could not render ${newMode}: ${e?.message||e}`),'input');return;}$('#warnings').innerHTML='';
  if(mode==='water')renderCurrentWaterChemistry();
  else if(mode==='advanced'){$('#results').innerHTML=advancedResultHtml();}
    else if(mode==='envelope')$('#results').innerHTML=hydraulicEnvelopeStatusHtml();
  else if(mode==='scenario')$('#results').innerHTML=scenarioMatrixResults();
  else if(mode==='comparison')$('#results').innerHTML=comparisonResults();
  else if(mode==='summary')$('#results').innerHTML=summaryResults();
  else if(mode==='economic')$('#results').innerHTML=lastEconomicResult?economicResults(lastEconomicResult):'<p class="muted">Run the comparison after calculating the technology cases you want to evaluate.</p>';
  else if(caseResults[mode]){lastResult=caseResults[mode];show(lastResult)}else $('#results').innerHTML='<p class="muted">Enter required inputs and calculate.</p>';
  updateRequiredFieldStates();renderCaseBar();
}

function updateWaterWorkspaceTabs(){
  const strip=$('#waterSubtabs'); if(strip)strip.hidden=mode!=='water';
  document.querySelectorAll('.water-subtab').forEach(b=>b.classList.toggle('active',b.dataset.waterSubmode===mode));
  document.querySelectorAll('.tab').forEach(b=>{const bm=b.dataset.mode;b.classList.toggle('active',bm===mode);});updateWorkspaceChrome();
}
function captureProjectMeta(){
  const ids={project_name:'metaProjectName',client:'metaClient',user:'metaUser',project_location:'metaLocation',project_country_code:'metaProjectCountry',project_date:'metaDate',revision:'metaRevision'};
  Object.entries(ids).forEach(([k,id])=>{const el=$('#'+id);if(el)projectMeta[k]=String(el.value??'').trim()});const countryEl=$('#metaProjectCountry');if(countryEl)projectMeta.project_country=String(countryEl.selectedOptions?.[0]?.textContent||'').trim();
  if(!projectMeta.project_name)projectMeta.project_name='Total RO Design Project';if(!projectMeta.project_date)projectMeta.project_date=todayIso();updateWorkspaceChrome();return projectMeta;
}
function renderProjectMeta(){
  const map={metaProjectName:'project_name',metaClient:'client',metaUser:'user',metaLocation:'project_location',metaProjectCountry:'project_country_code',metaDate:'project_date',metaRevision:'revision'};
  Object.entries(map).forEach(([id,k])=>{const el=$('#'+id);if(el&&el.value!==String(projectMeta[k]??''))el.value=projectMeta[k]??''});updateWorkspaceChrome();
}
function toggleProjectMeta(force){const panel=$('#projectMetaPanel'),btn=$('#projectMetaToggle');if(!panel)return;const show=force===undefined?panel.hidden:!!force;panel.hidden=!show;if(btn)btn.setAttribute('aria-expanded',show?'true':'false');if(show)renderProjectMeta();}
function projectSnapshot(){
  captureProjectMeta();persistActiveCase();
  return {format:'Total RO Design Project',schema_version:7,app_version:'0.2',saved_at:new Date().toISOString(),project:deepClone(projectMeta),active_case:activeCase,active_mode:mode,units:deepClone(currentUnits),turbo_design_locks:deepClone(turboDesignLocks),scenario_matrix:deepClone(scenarioMatrixState),cases:deepClone(caseStore)};
}
function safeProjectName(){const d=projectMeta.project_date||todayIso(),base=(projectMeta.project_name||'Total_RO_Design_Project').replace(/[^a-z0-9_-]+/gi,'_').replace(/^_+|_+$/g,'').slice(0,60)||'Total_RO_Design_Project',rev=(projectMeta.revision||'').replace(/[^a-z0-9_-]+/gi,'_');return `${base}${rev?'_'+rev:''}_${d}.trodesign`;}
function downloadProjectFile(payload){const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=safeProjectName();document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},0)}
async function saveProject(){
  try{
    const payload=projectSnapshot();
    if(entitlementContext?.account?.id){
      const updating=Boolean(serverProjectRecord?.id);
      const data=await requestJson(updating?`/api/projects/${serverProjectRecord.id}`:'/api/projects',{method:updating?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({snapshot:payload})},'Project could not be saved');
      serverProjectRecord=data.project||serverProjectRecord;
      if(serverProjectRecord){projectMeta.revision=`Rev ${serverProjectRecord.revision??0}`;projectMeta.project_id=serverProjectRecord.visible_id||projectMeta.project_id||'';renderProjectMeta();}
      alert(`Project saved to your private Suite Project Library${serverProjectRecord?.visible_id?` · ${serverProjectRecord.visible_id}`:''}.`);
      return;
    }
    downloadProjectFile(payload);
  }catch(e){alert(`Could not save project: ${e.message||e}`)}
}
function validateImportedProject(p){
  if(!p||typeof p!=='object')throw new Error('Invalid project file.');
  if(!['Total RO Design Project','CalcOsPower Project'].includes(p.format))throw new Error('This is not a Total RO Design / legacy CalcOsPower project file.');
  if(!p.cases||typeof p.cases!=='object'||!Object.keys(p.cases).length)throw new Error('Project file contains no cases.');
  if(Object.keys(p.cases).length>MAX_CASES)throw new Error(`Project contains more than ${MAX_CASES} cases.`);
  for(const [id,c] of Object.entries(p.cases)){if(!c||!c.waterProfile)throw new Error(`Case ${id} has no water-quality definition.`)}
  return p;
}
function openImportedProject(p,serverRecord=null){
  validateImportedProject(p); persistActiveCase();serverProjectRecord=serverRecord||null;
  projectMeta={...projectMeta,...deepClone(p.project||{})};if(p.scenario_matrix)scenarioMatrixState={...scenarioMatrixState,...deepClone(p.scenario_matrix)};if(!projectMeta.project_date)projectMeta.project_date=todayIso();renderProjectMeta();
  const chemistryMigration=Number(p.schema_version||0)<4;
  caseStore=deepClone(p.cases);Object.values(caseStore).forEach(c=>{c.baseDesignSeed=c.baseDesignSeed||null;c.advancedDesignInput=c.advancedDesignInput||{};c.advancedDesignResult=c.advancedDesignResult||null;});
  let chemistryInvalidated=0;
  if(chemistryMigration){
    Object.values(caseStore).forEach(c=>{
      chemistryInvalidated+=Object.keys(c?.caseResults||{}).length;
      c.caseResults={};c.chemistryResult=null;
    });
  }
  const invalidated=invalidateMismatchedCaseResults(caseStore);
  if(p.turbo_design_locks)turboDesignLocks=deepClone(p.turbo_design_locks);
  if(chemistryMigration)Object.values(turboDesignLocks||{}).forEach(lock=>{if(lock)lock.stale=true});
  const requested=Number(p.active_case||1); activeCase=caseStore[requested]?requested:Number(Object.keys(caseStore).sort((a,b)=>Number(a)-Number(b))[0]);
  let wanted=['water','chemistry','advanced','envelope','scenario','multistage','single','px','interstage_px','interstage','biturbo','dweer','pelton','comparison','summary','economic'].includes(p.active_mode)?p.active_mode:'water';
  if(wanted==='chemistry')wanted=caseStore[requested]?.caseResults?.multistage?'multistage':'water';
  mode=wanted; if(p.units){currentUnits={flow:p.units.flow||'m3/h',pressure:p.units.pressure||'bar',flux:p.units.flux||'LMH'};$('#flowUnit').value=currentUnits.flow;$('#pressureUnit').value=currentUnits.pressure;if($('#fluxUnit'))$('#fluxUnit').value=currentUnits.flux;}
  enforceTierCaseAccess();loadCaseGlobals(activeCase);mode=modeEntitlementAccess(wanted).ok?wanted:'water';lastResult=caseResults[mode]||null;renderCaseBar();updateWaterWorkspaceTabs();
  const vals=modeStates[mode]||convertedDefaults();renderFields(vals);$('#warnings').innerHTML='';
  if(mode==='water')renderCurrentWaterChemistry();
  else if(mode==='advanced'){$('#results').innerHTML=advancedResultHtml();}
    else if(mode==='envelope')$('#results').innerHTML=hydraulicEnvelopeStatusHtml();
  else if(mode==='scenario')$('#results').innerHTML=scenarioMatrixResults();
  else if(mode==='comparison')$('#results').innerHTML=comparisonResults();
  else if(mode==='summary')$('#results').innerHTML=summaryResults();
  else if(mode==='economic')$('#results').innerHTML=lastEconomicResult?economicResults(lastEconomicResult):'<p class="muted">Run the comparison after calculating the technology cases you want to evaluate.</p>';
  else if(caseResults[mode]){lastResult=caseResults[mode];syncSolveResult(lastResult);show(lastResult)}else $('#results').innerHTML='<p class="muted">Project loaded. Recalculate this technology if inputs have changed.</p>';
  updateRequiredFieldStates();applyTierEntitlements();
  if(chemistryMigration)showCalcError(new Error(`This project was created before the v17.2 total-alkalinity/carbonate correction. ${chemistryInvalidated} stored technology result${chemistryInvalidated===1?' was':'s were'} invalidated. The legacy HCO₃⁻ number has been carried forward as Total Alkalinity expressed as HCO₃-equivalent; verify it against the laboratory alkalinity before recalculating, especially for high-TDS/high-recovery cases.`),'project chemistry migration');
  else if(invalidated>0)showCalcError(new Error(`${invalidated} stored calculation result${invalidated===1?' was':'s were'} invalidated because its recorded temperature/fouling/salt-passage basis did not match the case water-quality definition. Recalculate the affected technology tabs.`),'project import');
}
async function importProjectFile(file){
  try{const text=await file.text();const p=JSON.parse(text);openImportedProject(p,null);alert(`Project imported successfully · ${Object.keys(caseStore).length} case(s). Save it to create a new Suite project ID.`)}catch(e){alert(`Could not import project: ${e.message||e}`)}
}
function projectLibraryRowHtml(row){
  const updated=row.updated_at?new Date(row.updated_at).toLocaleString():'—';
  return `<article class="project-library-row" data-project-library-row data-search="${escapeHtml(String(row.visible_id||'')+' '+String(row.name||'')).toLowerCase()}"><div><strong>${escapeHtml(row.name||'Total RO Design Project')}</strong><span>${escapeHtml(row.visible_id||'')} · Rev ${Number(row.revision||0)} · Updated ${escapeHtml(updated)}</span></div><div class="project-library-actions"><button type="button" class="ghost-dialog-btn" data-project-open="${Number(row.id)}">Open</button><button type="button" class="ghost-dialog-btn" data-project-copy="${Number(row.id)}">Create copy</button></div></article>`;
}
function renderProjectLibrary(){
  const host=$('#projectLibraryBody');if(!host)return;
  if(!projectLibraryCache.length){host.innerHTML='<p class="muted">No server-side projects have been saved yet. Open a legacy file or create a new project and click Save.</p>';return;}
  host.innerHTML=projectLibraryCache.map(projectLibraryRowHtml).join('');
  filterProjectLibrary();
}
function filterProjectLibrary(){
  const q=String($('#projectLibrarySearch')?.value||'').trim().toLowerCase();
  document.querySelectorAll('[data-project-library-row]').forEach(row=>{row.hidden=Boolean(q)&&!String(row.dataset.search||'').includes(q)});
}
async function openProjectLibrary(){
  const d=$('#projectLibraryDialog');if(d){if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');}
  const host=$('#projectLibraryBody');if(host)host.innerHTML='<p class="muted">Loading saved projects…</p>';
  try{const data=await requestJson('/api/projects',{},'Project library could not be loaded');projectLibraryCache=Array.isArray(data.projects)?data.projects:[];renderProjectLibrary();}
  catch(e){if(host)host.innerHTML=`<div class="warning"><strong>Project library could not be loaded.</strong><div>${escapeHtml(e.message||String(e))}</div></div>`;}
}
function bootstrapBioHandoffProject(snapshot,serverRecord){
  /*
   * Bio -> RO handoff records may begin as interoperability envelopes
   * without a native Total RO Design case structure.
   *
   * Bootstrap those records from the currently initialized RO Case 1 so
   * the handoff automatically follows the current RO project schema and
   * defaults rather than duplicating RO defaults inside the server API.
   */
  const isBioHandoff=
    snapshot?.suite_handoff?.handoff_type==='bio_to_ro' ||
    snapshot?.bio_handoff?.sourceApplication==='Total Bio Design';

  const hasCases=
    snapshot?.cases &&
    typeof snapshot.cases==='object' &&
    Object.keys(snapshot.cases).length>0;

  if(!isBioHandoff||hasCases)return snapshot;

  const base=projectSnapshot();

  base.project={
    ...base.project,
    ...(snapshot.project||{}),
    project_id:
      serverRecord?.visible_id ||
      snapshot?.project?.project_id ||
      base.project?.project_id ||
      '',
    revision:`Rev ${serverRecord?.revision??0}`
  };

  base.active_case=1;
  base.active_mode='water';

  base.suite_handoff=deepClone(
    snapshot.suite_handoff||{}
  );

  base.bio_handoff=deepClone(
    snapshot.bio_handoff||{}
  );

  /*
   * Retain the upstream Bio payload as provenance in Case 1.
   * Engineering-field mapping is intentionally handled separately so
   * wastewater parameters are never silently mapped into incompatible
   * RO ionic-chemistry fields.
   */
  if(base.cases?.[1]){
    base.cases[1].sourceHandoff=deepClone(
      snapshot.bio_handoff||{}
    );

    base.cases[1].sourceApplication='Total Bio Design';

    base.cases[1].sourceProjectId=
      snapshot?.suite_handoff?.source_visible_id||'';
  }

  return base;
}


async function loadServerProject(id){
  const data=await requestJson(
    `/api/projects/${Number(id)}`,
    {},
    'Project could not be opened'
  );

  const snapshot=bootstrapBioHandoffProject(
    data.snapshot,
    data.project
  );

  openImportedProject(
    snapshot,
    data.project
  );

  const d=$('#projectLibraryDialog');
  if(d?.open)d.close();

  alert(
    `Opened ${data.project?.visible_id||'saved project'}.`
  );
}
async function createServerProjectRevision(id){
  const data=await requestJson(`/api/projects/${Number(id)}/copy`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'},'Project revision could not be created');
  await loadServerProject(data.project.id);
  alert(`Created ${data.project.visible_id}. You can rename the project in Project Information and click Save.`);
}
function computeStatusText(){
  const cpu=computeCapabilities?.cpu,live=computeLiveStatus;if(!cpu)return 'Compute · detecting…';
  if(live?.active)return `Compute · CPU ${live.active_workers||1}/${live.workers||1} active · ${live.completed_jobs||0}/${live.total_jobs||1} jobs`;
  return `Compute · ${cpu.default_workers||1} CPU worker${Number(cpu.default_workers||1)===1?'':'s'} available`;
}
function updateComputeStatus(){const el=$('#computeStatus');if(!el)return;el.textContent=computeStatusText();el.classList.toggle('compute-active',!!computeLiveStatus?.active);el.classList.remove('compute-gpu-ready','compute-warning');el.title='Click to open hosted CPU compute diagnostics';}
function fmtCompute(v,d=1){const n=Number(v);return Number.isFinite(n)?n.toFixed(d):'—'}
function renderComputePanel(){}
async function loadComputeCapabilities(){
  try{const r=await totalroFetch('/api/compute/capabilities');if(!r.ok)return;computeCapabilities=await r.json();updateComputeStatus();renderComputePanel();}
  catch(e){const el=$('#computeStatus');if(el){el.textContent='Compute · CPU';el.title='Hardware detection unavailable; CPU calculations remain enabled.';}}
}
async function pollComputeStatus(){
  try{
    const r=await totalroFetch('/api/compute/status',{cache:'no-store'});if(!r.ok)return;
    computeLiveStatus=await r.json(); updateComputeStatus(); renderComputePanel();
    const detail=$('#calculationDetail'),eta=$('#calculationEta'),bar=$('#calculationProgressBar'),title=$('#calculationTitle');
    if(detail&&computeLiveStatus?.active){
      const pct=computeLiveStatus.calcospower_cpu_percent==null?'':` · Total RO Design CPU ${fmtCompute(computeLiveStatus.calcospower_cpu_percent,1)}%`;
      const phase=String(computeLiveStatus.phase||'').trim();
      if(computeLiveStatus.cancel_requested){if(title)title.textContent='Stopping calculation…';detail.textContent=`Cancellation requested${pct}`;}
      else if(String(computeLiveStatus.backend||'').includes('opencl'))detail.textContent=`${phase||'Optional accelerator screening running'}${pct}`;
      else detail.textContent=`${phase?phase+' · ':''}${computeLiveStatus.active_workers||1}/${computeLiveStatus.workers||1} CPU workers active · ${computeLiveStatus.completed_jobs||0}/${computeLiveStatus.total_jobs||1} worker jobs complete${pct}`;
      const elapsed=Number(computeLiveStatus.duration_seconds||0),remaining=computeLiveStatus.eta_seconds;
      if(eta)eta.textContent=remaining==null?`Elapsed ${formatRunTime(elapsed)} · Estimated remaining: calculating…`:`Elapsed ${formatRunTime(elapsed)} · Estimated remaining ~${formatRunTime(remaining)} · Estimated total ~${formatRunTime(Number(computeLiveStatus.estimated_total_seconds||elapsed))}`;
      const f=Number(computeLiveStatus.progress_fraction||0);if(bar&&f>0){bar.classList.add('determinate');bar.style.width=`${Math.max(2,Math.min(100,f*100))}%`;}
    }
  }catch(e){}
}
function startComputePolling(){if(computePollTimer)return;pollComputeStatus();computePollTimer=setInterval(pollComputeStatus,450)}
function stopComputePolling(){if(computePollTimer){clearInterval(computePollTimer);computePollTimer=null}}
function toggleComputePanel(force){const panel=$('#computePanel');if(!panel)return;computePanelOpen=typeof force==='boolean'?force:!computePanelOpen;panel.hidden=!computePanelOpen;if(computePanelOpen){startComputePolling();loadComputeCapabilities();}else if(!document.body.classList.contains('calculating'))stopComputePolling()}
function enterCalculatorFromLanding(){
  const landing=$('#landingPage'),app=$('#calculatorApp');
  if(landing)landing.style.display='none';
  if(app)app.classList.remove('app-hidden');
  window.scrollTo({top:0,behavior:'instant'});
}
function flashLandingTarget(el){if(!el)return;el.classList.remove('landing-target-flash');void el.offsetWidth;el.classList.add('landing-target-flash');setTimeout(()=>el.classList.remove('landing-target-flash'),1700)}
function pulseAppControl(el){if(!el)return;el.scrollIntoView?.({behavior:'smooth',block:'center'});el.focus?.({preventScroll:true});el.classList.remove('landing-target-pulse');void el.offsetWidth;el.classList.add('landing-target-pulse');setTimeout(()=>el.classList.remove('landing-target-pulse'),1900)}
function openLandingDialog(id){const d=document.getElementById(id);if(!d)return;if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','')}
function closeLandingDialog(d){if(!d)return;if(typeof d.close==='function')d.close();else d.removeAttribute('open')}

// -----------------------------------------------------------------------------
// Total Water Design Suite v0.25 integration / Total RO Design Hotfix 14
// ----------------------------------------------------------------------------
function firstFinite(...values){for(const value of values){const n=Number(value);if(Number.isFinite(n))return n;}return null}
function resultTdsValue(r,kind='permeate'){
  const n=resultStageCount(r);
  if(kind==='feed')return firstFinite(r?.stage1_feed_tds_ppm,r?.feed_tds_ppm,r?.feed_tds,waterProfile?.analysis_tds,waterProfile?.feed_tds);
  if(kind==='concentrate')return firstFinite(r?.[`stage${n}_concentrate_tds_ppm`],r?.final_concentrate_tds_ppm,r?.concentrate_tds_ppm,compositionTds(r?.[`stage${n}_concentrate_composition_mg_l`]));
  return firstFinite(r?.composite_permeate_tds_ppm,r?.permeate_tds_ppm,compositionTds(r?.composite_permeate_composition_mg_l));
}
function resultAverageFluxValue(r){
  const direct=firstFinite(r?.average_flux_lmh,r?.average_design_flux_lmh,r?.system_average_flux_lmh);
  if(direct!==null)return fluxValue(direct);
  const area=firstFinite(r?.total_membrane_area_m2,r?.active_area_m2,r?.membrane_area_m2);
  const q=firstFinite(r?.product_flow,r?.permeate_flow);
  if(area&&q!==null){const qM3h=convert(q,'flow',r?.flow_unit||currentUnits.flow,'m3/h');return fluxValue(qM3h*1000/area)}
  return null;
}
function resultSecValue(r){return firstFinite(r?.total_plant_sec,r?.total_sec,r?.sec_total,r?.specific_energy,r?.sec,r?.ro_gross_sec,r?.gross_sec)}
function updateAllCaseOperatingSummary(){
  const host=$('#allCaseSummaryBody');if(!host)return;
  const ids=Object.keys(caseStore||{}).map(Number).sort((a,b)=>a-b);
  const rows=ids.map(id=>{
    const c=caseStore[id]||{},w=c.waterProfile||{},r=c.caseResults?.multistage||null,s=c.modeStates?.multistage||{};
    const state=r?(c.baseDesignSeed?.stale||s._inputs_changed_since_calculation?'stale':'current'):'not';
    const stateLabel=state==='current'?'✓ Current':state==='stale'?'! Inputs changed / stale':'— Not calculated';
    return `<tr class="case-summary-${state}"><td class="case-cell"><strong>Case ${id}</strong><small>${escapeHtml(w.envelope_label||'')}</small></td><td>${fmt(w.temperature_c,1)} °C</td><td>${fmt(w.fouling_factor,2)}</td><td>${fmt(w.salt_passage_factor??1,2)}</td><td>${fmt(w.analysis_tds??w.feed_tds,0)}</td><td>${r?fmt(firstFinite(r.membrane_pressure_1,r.solved_feed_pressure),2):'—'}</td><td>${r?fmt(firstFinite(r.recovery,0)*100,1)+'%':'—'}</td><td>${r?fmt(resultTdsValue(r,'permeate'),2):'—'}</td><td>${r?fmt(resultAverageFluxValue(r),2):'—'}</td><td>${r?fmt(resultSecValue(r),3):'—'}</td><td><span class="case-state ${state}">${stateLabel}</span></td></tr>`;
  }).join('');
  host.innerHTML=rows?`<div class="all-case-table-wrap"><table class="all-case-table"><thead><tr><th class="case-col">Case</th><th>Temp.<span>°C</span></th><th>Fouling<span>factor</span></th><th>Salt passage<span>factor</span></th><th>Feed TDS<span>mg/L</span></th><th>Feed pressure<span>${escapeHtml(currentUnits.pressure)}</span></th><th>Recovery<span>%</span></th><th>Permeate TDS<span>mg/L</span></th><th>Avg. flux<span>${escapeHtml(fluxUnit())}</span></th><th>SEC<span>kWh/m³</span></th><th class="state-col">Status</th></tr></thead><tbody>${rows}</tbody></table></div>`:'<p class="muted">No calculated cases yet.</p>';
}
function renderCaseBar(){
  const root=$('#caseTabs');if(!root)return;const allIds=Object.keys(caseStore).map(Number).sort((a,b)=>a-b),multi=tierAllows('multi_case'),ids=multi?allIds:allIds.slice(0,1),limit=caseLimitForTier();
  const chips=ids.map(id=>{const c=caseStore[id]||{},wp=c.waterProfile||{},label=escapeHtml(wp.envelope_label||`Case ${id}`),status=c.baseDesignSeed&&!c.baseDesignSeed.stale?'✓':(c.baseDesignSeed?.stale?'!':'—');return `<button type="button" class="case-chip case-tab ${id===activeCase?'active':''}" data-case="${id}" title="${label}"><strong>${id}</strong><span>${label}</span><em>${status}</em></button>`}).join('');
  const controls=multi?((allIds.length<limit?`<button type="button" class="case-chip case-tab add-case" data-add-case="1" title="Add case">+</button>`:'')+(allIds.length>1?`<button type="button" class="case-chip case-tab remove-case" data-remove-case="1" title="Delete selected case">−</button>`:'')):`<button type="button" class="case-chip tier-case-lock" disabled title="Silver unlocks up to 10 independent cases">1 case · Silver+</button>`;
  const preserved=!multi&&allIds.length>1?`<span class="tier-preserved-note">${allIds.length-1} higher-tier case${allIds.length===2?'':'s'} preserved</span>`:'';
  root.innerHTML=chips+controls+preserved;updateWorkspaceChrome();updateWorkflowGates();updateAllCaseOperatingSummary();
}
function embeddedChemistryComposition(r,stream){
  const streams=waterStreamsForResult({waterProfile},r);
  if(stream==='feed')return r?.stage1_feed_composition_mg_l||streams.feed;
  let m=String(stream||'').match(/^stage(\d+)_concentrate$/);
  if(m){const i=Number(m[1]);return r?.[`stage${i}_concentrate_composition_mg_l`]||streams.conc||streams.feed;}
  m=String(stream||'').match(/^stage(\d+)_permeate$/);
  if(m){const i=Number(m[1]);return r?.[`stage${i}_permeate_composition_mg_l`]||streams.perm||streams.feed;}
  if(stream==='permeate'||stream==='composite_permeate')return r?.composite_permeate_composition_mg_l||streams.perm||streams.feed;
  return streams.conc||streams.feed;
}
function resultChemistryBasis(r,stream){
  const n=resultStageCount(r);let comp,ph,alk;const key=String(stream||'');
  if(key==='feed'){comp=r?.stage1_feed_composition_mg_l;ph=r?.stage1_feed_ph;alk=r?.stage1_feed_alkalinity_mg_l_as_hco3;}
  else if(/^stage\d+_concentrate$/.test(key)){const i=Number(key.match(/\d+/)[0]);comp=r?.[`stage${i}_concentrate_composition_mg_l`];ph=r?.[`stage${i}_concentrate_ph`];alk=r?.[`stage${i}_concentrate_alkalinity_mg_l_as_hco3`];}
  else if(/^stage\d+_permeate$/.test(key)){const i=Number(key.match(/\d+/)[0]);comp=r?.[`stage${i}_permeate_composition_mg_l`];ph=r?.[`stage${i}_permeate_ph`];alk=r?.[`stage${i}_permeate_alkalinity_mg_l_as_hco3`];}
  else if(key==='permeate'||key==='composite_permeate'){comp=r?.composite_permeate_composition_mg_l||r?.[`stage${n}_permeate_composition_mg_l`];ph=r?.composite_permeate_ph??r?.[`stage${n}_permeate_ph`];alk=r?.composite_permeate_alkalinity_mg_l_as_hco3??r?.[`stage${n}_permeate_alkalinity_mg_l_as_hco3`];}
  else {comp=r?.[`stage${n}_concentrate_composition_mg_l`];ph=r?.[`stage${n}_concentrate_ph`];alk=r?.[`stage${n}_concentrate_alkalinity_mg_l_as_hco3`];}
  return {comp:comp||embeddedChemistryComposition(r,key),ph:Number(ph??waterProfile.feed_ph),alk:Number((alk??waterProfile.ion_bicarbonate)||0)};
}
function embeddedChemistrySection(r){
  if(!r?.membrane_coupling)return '';
  const n=resultStageCount(r);let selected=embeddedChemistryStreamByMode[mode]||'concentrate';
  const valid=['feed','concentrate','permeate'];for(let i=1;i<n;i++)valid.push(`stage${i}_concentrate`);for(let i=1;i<=n;i++)valid.push(`stage${i}_permeate`);if(!valid.includes(selected))selected='concentrate';embeddedChemistryStreamByMode[mode]=selected;
  let options=`<option value="feed" ${selected==='feed'?'selected':''}>Feed</option>`;
  for(let i=1;i<n;i++)options+=`<option value="stage${i}_concentrate" ${selected===`stage${i}_concentrate`?'selected':''}>Stage ${i} concentrate / Stage ${i+1} feed</option>`;
  options+=`<option value="concentrate" ${selected==='concentrate'?'selected':''}>Final concentrate</option>`;
  for(let i=1;i<=n;i++)options+=`<option value="stage${i}_permeate" ${selected===`stage${i}_permeate`?'selected':''}>Stage ${i} permeate</option>`;
  options+=`<option value="permeate" ${selected==='permeate'?'selected':''}>Composite permeate</option>`;
  return `<section class="report-section embedded-chemistry-section"><div class="chart-title-row"><h3>WATER CHEMISTRY</h3><span>Case-specific calculated stream</span></div><div class="embedded-chemistry-toolbar"><label>Stream <select id="embeddedChemStream">${options}</select></label></div><div id="embeddedChemistryBody"><p class="muted">Calculating ${escapeHtml(selected.replaceAll('_',' '))} chemistry…</p></div><p class="micro-note">Read-only result for the current calculated case. Edit the analytical basis in Water Quality, then recalculate the case when inputs change.</p></section>`;
}
function bindEmbeddedChemistry(r){
  const sel=$('#embeddedChemStream');if(sel)sel.addEventListener('change',()=>{embeddedChemistryStreamByMode[mode]=sel.value;loadEmbeddedChemistry(r)});
  loadEmbeddedChemistry(r);
}
function detailedElementsHtml(r){
  const rows=[];for(let stage=1;stage<=resultStageCount(r);stage++){
    const arr=Array.isArray(r?.[`stage${stage}_element_profile`])?r[`stage${stage}_element_profile`]:[];
    arr.forEach((e,index)=>{const model=e.membrane_model||e.model||r?.[`stage${stage}_membrane_model`]||'—';rows.push(`<tr><td>${stage}</td><td>${e.element??index+1}</td><td>${escapeHtml(model)}</td><td>${fmt(convert(e.feed_flow_m3h??e.feed_flow,'flow','m3/h',r.flow_unit||currentUnits.flow),2)}</td><td>${fmt(convert(e.permeate_flow_m3h??e.permeate_flow,'flow','m3/h',r.flow_unit||currentUnits.flow),2)}</td><td>${fmt(firstFinite(e.recovery,0)*100,2)}%</td><td>${fmt(convert(e.feed_pressure_bar??e.feed_pressure,'pressure','bar',r.pressure_unit||currentUnits.pressure),2)}</td><td>${fmt(convert(e.dp_bar??e.pressure_drop_bar,'pressure','bar',r.pressure_unit||currentUnits.pressure),3)}</td><td>${fmt(convert(e.ndp_bar??e.ndp,'pressure','bar',r.pressure_unit||currentUnits.pressure),2)}</td><td>${fmt(fluxValue(e.flux_lmh??e.flux),2)}</td><td>${fmt(e.polarization_factor_monovalent??e.polarization_factor,2)}</td><td>${fmt(e.polarization_factor_divalent??e.polarization_factor,2)}</td><td>${fmt(e.feed_tds_ppm??e.feed_tds,1)}</td><td>${fmt(e.permeate_tds_ppm??e.permeate_tds,2)}</td></tr>`);});
  }
  if(!rows.length)return '<section class="report-section"><h3>DETAILED ELEMENTS</h3><p class="muted">Element-level data are not available for this calculated case.</p></section>';
  return `<section class="report-section detailed-elements-section"><div class="chart-title-row"><h3>DETAILED ELEMENTS</h3><span>Representative pressure vessel · actual membrane recipe</span></div><div class="table-wrap"><table class="fedco-table detailed-element-table"><thead><tr><th>Stage</th><th>Element</th><th>Membrane</th><th>Feed flow<br><span>${escapeHtml(r.flow_unit||currentUnits.flow)}</span></th><th>Permeate<br><span>${escapeHtml(r.flow_unit||currentUnits.flow)}</span></th><th>Recovery</th><th>Feed P<br><span>${escapeHtml(r.pressure_unit||currentUnits.pressure)}</span></th><th>ΔP<br><span>${escapeHtml(r.pressure_unit||currentUnits.pressure)}</span></th><th>NDP<br><span>${escapeHtml(r.pressure_unit||currentUnits.pressure)}</span></th><th>Flux<br><span>${escapeHtml(fluxUnit())}</span></th><th>CP mono</th><th>CP div.</th><th>Feed TDS</th><th>Perm. TDS</th></tr></thead><tbody>${rows.join('')}</tbody></table></div></section>`;
}
function processResultTabsHtml(){
  const active=resultSubtabByMode[mode]||'performance';
  return `<div class="result-subtabs"><button type="button" data-result-subtab="performance" class="${active==='performance'?'active':''}">Performance</button><button type="button" data-result-subtab="chemistry" class="${active==='chemistry'?'active':''}">Water Chemistry</button><button type="button" data-result-subtab="tail" class="${active==='tail'?'active':''}">Tail Element Chemistry</button><button type="button" data-result-subtab="elements" class="${active==='elements'?'active':''}">Detailed Elements</button></div><div id="processResultSubtabBody"></div>`;
}
function turboAssessmentAllowed(r){
  if(!tierAllows('erd'))return false;
  if(!['gold','platinum'].includes(normalizeTier(effectiveTier)))return false;
  if(['single','interstage','biturbo'].includes(mode))return true;
  if(['px','interstage_px','dweer','pelton'].includes(mode))return Boolean(r?.multistage_turbo_available_hydraulic_kw&&r?.turbocharger_configured);
  return false;
}
function processPerformanceBody(r){
  const turbo=turboAssessmentAllowed(r)?multistageTurboAssessment(r):'';
  if(mode==='dweer'||mode==='pelton')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+stageReport(r)+mechanicalErdReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+membraneChecks(r);
  if(mode==='multistage')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+autoDesignJointReport(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);
  if(mode==='interstage'&&r?.generalized_interstage_turbo)return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+multistagePlantReport(r)+autoDesignJointReport(r)+stageReport(r)+turbo+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);
  if(mode==='biturbo'&&r?.generalized_biturbo)return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+multistageKpis(r)+acidDosingReport(r)+biturboFeasibilityReport(r)+performanceVisualizations(r)+stageReport(r)+turbo+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+tieredPumpCurveHtml(r)+tieredPumpReportHtml(r)+membraneChecks(r);
  if(mode==='px'||mode==='interstage_px')return solveStatus(r)+solverDiagnostics(r)+showMembraneHeader(r)+pxKpis(r)+acidDosingReport(r)+performanceVisualizations(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+(r.is_brackish_multistage_px||mode==='interstage_px'?multistagePxReport(r):pxReport(r))+tieredVcmpPxPumpSummary(r)+turbo+membraneChecks(r);
  return solveStatus(r)+turboDesignStatus(r)+fluxOptimizationPanel(r)+solverDiagnostics(r)+showMembraneHeader(r)+kpis(r)+acidDosingReport(r)+(mode==='biturbo'?biturboFeasibilityReport(r):'')+performanceVisualizations(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+turboRows(r)+dutyCards(r)+membraneChecks(r);
}
function renderProcessResultSubtab(r){
  const host=$('#processResultSubtabBody');if(!host)return;const tab=resultSubtabByMode[mode]||'performance';
  if(tab==='chemistry'){host.innerHTML=embeddedChemistrySection(r);bindEmbeddedChemistry(r);}
  else if(tab==='tail'){host.innerHTML=tailElementWaterChemistryHtml(r);loadTailChemistryRisks(r);}
  else if(tab==='elements'){host.innerHTML=detailedElementsHtml(r);}
  else{host.innerHTML=processPerformanceBody(r);bindFluxOptimizationActions();const envBtn=$('#viewHydraulicEnvelopeBtn');if(envBtn)envBtn.addEventListener('click',()=>changeMode('envelope'));}
  document.querySelectorAll('[data-result-subtab]').forEach(b=>b.classList.toggle('active',b.dataset.resultSubtab===tab));
}
function multistagePlantReport(r){
  const req=Number(r.required_capacity_m3d),hasReq=Number.isFinite(req)&&req>0,ok=r.n_minus_one_meets_required===true;
  const requirement=hasReq?`<span>Required: ${fmt(req,0)} m³/d · margin ${fmt(r.n_minus_one_capacity_margin_m3d,0)} m³/d</span><b class="${ok?'ok':'bad'}">${ok?'N−1 meets requirement':'N−1 below requirement'}</b>`:'<span>N−1 capacity shown for planning</span>';
  return `<section class="report-section compact-plant-summary"><div class="chart-title-row"><h3>PLANT / TRAIN CONFIGURATION</h3><span>${r.auto_sized?'Auto Design':'Manual array design'}</span></div><div class="plant-summary-three"><article><span>Per-train production</span><strong>${fmt(r.train_product_capacity_m3d,0)} m³/d</strong><small>${r.operating_trains} operating + ${r.standby_trains} standby · ${r.installed_trains} installed</small></article><article><span>Plant capacity</span><strong>${fmt(r.normal_operating_capacity_m3d,0)} m³/d normal</strong><small>${fmt(r.installed_capacity_m3d,0)} installed · ${fmt(r.n_minus_one_capacity_m3d,0)} N−1</small>${requirement}</article><article><span>Array inventory / train</span><strong>${fmt(r.total_pressure_vessels,0)} vessels · ${fmt(r.total_membrane_elements,0)} elements</strong><small>${fmt(r.total_membrane_area_m2,0)} m² active area</small></article></div><p class="micro-note">N−1 assumes one installed RO train is unavailable. Auto Design sizes whole pressure vessels and interstage energy inputs against the selected engineering constraints.</p></section>`;
}
function feedbackResultDialog(title,body,kind='info'){
  const d=$('#feedbackResultDialog'),t=$('#feedbackResultTitle'),b=$('#feedbackResultBody');if(!d||!b)return;
  if(t)t.textContent=title;b.innerHTML=`<div class="feedback-result-state ${kind}">${body}</div>`;
  if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');
}
async function reportCurrentIssue(){
  if(feedbackReporting||!lastReportableError)return;
  feedbackReporting=true;const btn=$('#reportIssueBtn');if(btn){btn.disabled=true;btn.textContent='Preparing report…'};
  try{
    persistActiveCase();const cap=await captureFeedbackScreenshots();const payload={error:lastReportableError.message,context:lastReportableError.context,active_mode:mode,active_case:activeCase,project:projectSnapshot(),screenshots:cap.screenshots,capture_error:cap.capture_error,chatgpt_prompt:buildChatGptDebugPrompt()};
    const j=await requestJson('/api/feedback/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},'Issue report could not be created');
    const capture=j.screenshots_saved?`${j.screenshots_saved} screenshot${j.screenshots_saved===1?'':'s'} included.`:`No screenshot was included${j.capture_warning?`: ${escapeHtml(j.capture_warning)}`:'.'}`;
    const sent=j.emailed;
    feedbackResultDialog(sent?'Issue submitted':'Issue saved for administrator retrieval',`<p><strong>${escapeHtml(j.ticket)}</strong></p><p>${escapeHtml(j.message||'The issue report was created.')}</p><p>${capture}</p>${sent?'':`<p class="feedback-action-note">Email delivery did not complete. The diagnostic bundle remains in the protected server outbox so an administrator can retrieve it.</p>`}`,sent?'success':'warning');
  }catch(e){feedbackResultDialog('Issue report could not be created',`<p>${escapeHtml(e.message||String(e))}</p><p>Please save the project and contact support@totalrodesign.com.</p>`,'error');}
  finally{feedbackReporting=false;if(btn){btn.disabled=false;btn.textContent='Report this issue'}}
}
function computeStatusText(){
  const cpu=computeCapabilities?.cpu,live=computeLiveStatus;if(!cpu)return 'Compute · detecting…';
  if(live?.active)return `Compute · CPU ${live.active_workers||1}/${live.workers||1} active · ${live.completed_jobs||0}/${live.total_jobs||1} jobs`;
  return `Compute · ${cpu.default_workers||1} CPU worker${Number(cpu.default_workers||1)===1?'':'s'} available`;
}
function updateComputeStatus(){const el=$('#computeStatus');if(!el)return;el.textContent=computeStatusText();el.classList.toggle('compute-active',!!computeLiveStatus?.active);el.classList.remove('compute-gpu-ready','compute-warning');el.title='Click to open hosted CPU compute diagnostics';}
function renderComputePanel(){
  const panel=$('#computePanel');if(!panel)return;const cpu=computeCapabilities?.cpu||{},live=computeLiveStatus||{},policy=computeCapabilities?.policy||{};
  const cpuPct=live.calcospower_cpu_percent==null?'warming up':`${fmtCompute(live.calcospower_cpu_percent,1)}% of total machine`,jobs=live.total_jobs?`${live.completed_jobs||0} / ${live.total_jobs}`:'—';
  panel.innerHTML=`<div class="compute-panel-head"><div><strong>COMPUTE DIAGNOSTICS</strong><span>Authenticated AWS deployment · CPU engineering mode</span></div><button type="button" id="computePanelClose" class="compute-panel-close" aria-label="Close compute diagnostics">×</button></div><div class="compute-diag-grid cpu-only"><article><h4>CPU CAPACITY</h4><dl><dt>Processor</dt><dd>${escapeHtml(cpu.processor||cpu.architecture||'CPU')}</dd><dt>EC2 logical vCPUs</dt><dd>${cpu.logical_processors??'—'}</dd><dt>Configured engineering workers</dt><dd>${cpu.default_workers??'—'}</dd><dt>Active workers</dt><dd><b>${live.active_workers||0} / ${live.workers||cpu.default_workers||1}</b></dd><dt>Total RO Design CPU utilization</dt><dd><b>${cpuPct}</b></dd><dt>Memory utilization</dt><dd>${live.memory_percent==null?'—':fmtCompute(live.memory_percent,1)+'%'}</dd></dl><p class="diag-message">${escapeHtml(policy.cpu_floor||'Independent engineering branches use the configured CPU workers without manufacturing dummy work.')}</p></article><article><h4>CURRENT / LAST CALCULATION</h4><dl><dt>Status</dt><dd><b>${live.active?'Running':'Idle'}</b></dd><dt>Calculation phase</dt><dd>${escapeHtml(live.phase||'—')}</dd><dt>Elapsed time</dt><dd>${fmtCompute(live.duration_seconds,2)} s</dd><dt>Estimated remaining</dt><dd>${live.eta_seconds==null?'—':fmtCompute(live.eta_seconds,1)+' s'}</dd><dt>Jobs completed</dt><dd>${jobs}</dd><dt>Queue / server state</dt><dd>${live.active?'Busy · one heavy job admitted':'Available'}</dd><dt>Last backend</dt><dd>${escapeHtml(live.backend||lastComputeRun?.backend||'CPU')}</dd></dl><p class="diag-message">CPU is the authoritative calculation backend. OpenCL is not probed or required in the hosted deployment.</p></article></div>`;
  $('#computePanelClose')?.addEventListener('click',()=>toggleComputePanel(false));
}


function reportReadiness(options={}){
  persistActiveCase();
  const c=activeCaseData(),result=c?.caseResults?.multistage||caseResults?.multistage,state=c?.modeStates?.multistage||modeStates?.multistage||{};
  const problems=[];
  if(document.body.classList.contains('calculating'))problems.push('A calculation is still running. Wait for it to finish.');
  if(!result)problems.push('Calculate Plant Design for the active case before generating the report.');
  const stale=Boolean(result)&&state._last_calculated_signature!==basePlantSignature(state);
  if(stale)problems.push('Plant Design inputs changed after the last calculation. Recalculate the active case.');
  const n=result?resultStageCount(result):Math.max(1,Math.min(4,Number(state.stage_count||1)));
  if(options.include_detailed_chemistry&&!lastChemistryResult)problems.push('Calculate the requested detailed water chemistry before including Appendix A.');
  const tail=result?.[`stage${n}_tail_element_chemistry`];
  if(options.include_tail_chemistry&&!tail)problems.push('Tail-element chemistry is not complete for this case. Recalculate with Full water chemistry before including Appendix B.');
  const envelope=c?.hydraulicEnvelope;
  if(options.include_hydraulic_envelope&&!envelope?.rows?.length)problems.push('The Hydraulic Envelope has not been calculated for this case.');
  return {ready:problems.length===0,problems,stale,result,state,caseData:c,stageCount:n,tail,envelope};
}
function currentReportOptions(){
  const form=$('#engineeringReportOptionsForm');if(!form)return {};
  return {include_detailed_chemistry:Boolean(form.querySelector('[name="include_detailed_chemistry"]')?.checked),include_tail_chemistry:Boolean(form.querySelector('[name="include_tail_chemistry"]')?.checked),include_hydraulic_envelope:Boolean(form.querySelector('[name="include_hydraulic_envelope"]')?.checked)};
}
function openEngineeringReportDialog(){
  persistActiveCase();const d=$('#engineeringReportDialog');if(!d)return;
  const c=activeCaseData(),env=c?.hydraulicEnvelope,full=tierAllows('full_engineering_report');
  const chem=d.querySelector('[name="include_detailed_chemistry"]'),tail=d.querySelector('[name="include_tail_chemistry"]'),hyd=d.querySelector('[name="include_hydraulic_envelope"]');
  if(chem){chem.disabled=!full;if(!full)chem.checked=false}if(tail){tail.disabled=!full;if(!full)tail.checked=false}if(hyd){hyd.disabled=!full||!env?.rows?.length;if(hyd.disabled)hyd.checked=false}
  $('#hydraulicEnvelopeReportOption')?.classList.toggle('disabled',Boolean(hyd?.disabled));
  const readiness=reportReadiness(currentReportOptions());
  const note=$('#reportReadinessNote');if(note){note.className=`report-readiness-note ${readiness.ready?'ready':'blocked'}`;note.textContent=readiness.ready?'The current solved case is ready. The report will be rendered from an immutable report snapshot.':readiness.problems[0]}
  if($('#reportOptionCase'))$('#reportOptionCase').textContent=`Case ${activeCase}`;
  if($('#reportOptionUnits'))$('#reportOptionUnits').textContent=`${currentUnits.flow} · ${currentUnits.pressure} · ${fluxUnit()}`;
  if($('#reportOptionState'))$('#reportOptionState').textContent=readiness.ready?'Ready':readiness.stale?'Stale':'Not ready';
  const gen=$('#generateEngineeringReportBtn');if(gen)gen.disabled=!readiness.ready;
  if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');
}
function reportWarningSnapshot(result){
  const out=[];for(const key of ['warnings','engineering_warnings','constraint_warnings']){const value=result?.[key];if(Array.isArray(value))value.forEach(x=>out.push(deepClone(x)));else if(value)out.push(deepClone(value))}
  const warningHost=$('#warnings');if(warningHost?.textContent?.trim())out.push({severity:'review',message:warningHost.textContent.replace(/\s+/g,' ').trim()});
  return out;
}
async function ensureReportScalingChemistry(result){
  if(!result)return null;
  const stream='concentrate',key=embeddedChemistryCacheKey('multistage',stream,result);
  if(embeddedChemistryCache[key])return deepClone(embeddedChemistryCache[key]);
  const basis=resultChemistryBasis(result,stream),comp=basis.comp||{};
  const payload={...profileChemPayload(waterProfile,comp,basis.ph,basis.alk),reported_tds:compositionTds(comp),source_ph:basis.ph};
  const resp=await totalroFetch('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const j=await resp.json();if(!resp.ok)throw new Error(j.error||'Final-concentrate scaling chemistry calculation failed');
  embeddedChemistryCache[key]=j;return deepClone(j);
}
function buildEngineeringReportSnapshot(options={},scalingChemistry=null){
  captureProjectMeta();persistActiveCase();const ready=reportReadiness(options);if(!ready.ready)throw new Error(ready.problems.join(' '));
  const result=deepClone(ready.result),state=deepClone(ready.state),c=ready.caseData;
  return {schema:'TotalRODesign.ReportSnapshot.v1',state:'Ready',stale:false,generated_at:new Date().toISOString(),app_name:'Total RO Design',app_version:'0.2',suite_name:'Total Water Design Suite',suite_version:'0.25',case_id:activeCase,case_name:c?.waterProfile?.envelope_label||`Case ${activeCase}`,stage_count:ready.stageCount,unit_system:deepClone(currentUnits),project:deepClone(projectMeta),water_profile:deepClone(c?.waterProfile||waterProfile),design_input:state,result,options:{report_type:'standard',...deepClone(options)},scaling_chemistry:scalingChemistry?deepClone(scalingChemistry):null,chemistry_detail:options.include_detailed_chemistry?deepClone(lastChemistryResult):null,tail_chemistry:options.include_tail_chemistry?deepClone(ready.tail):null,hydraulic_envelope:options.include_hydraulic_envelope?deepClone(ready.envelope):null,warning_messages:reportWarningSnapshot(result),report_integrity:{last_calculated_signature:state._last_calculated_signature,active_signature:basePlantSignature(state)}};
}
async function submitEngineeringReport(event){
  event?.preventDefault();const options=currentReportOptions(),ready=reportReadiness(options),note=$('#reportReadinessNote'),button=$('#generateEngineeringReportBtn');
  if(!ready.ready){if(note){note.className='report-readiness-note blocked';note.textContent=ready.problems.join(' ')}if(button)button.disabled=true;return}
  const popup=window.open('about:blank','_blank');if(popup)popup.document.write('<title>Preparing Total RO Design report…</title><p style="font:16px Segoe UI;padding:30px">Preparing the immutable engineering-report snapshot…</p>');
  try{if(button){button.disabled=true;button.textContent='Preparing report…'}const scalingChemistry=await ensureReportScalingChemistry(ready.result);const snapshot=buildEngineeringReportSnapshot(options,scalingChemistry);const response=await requestJson('/api/report/snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({snapshot})},'Engineering report could not be prepared');if(popup)popup.location=response.print_url;else window.location.assign(response.preview_url);const d=$('#engineeringReportDialog');if(d?.open)d.close();}
  catch(e){try{popup?.close()}catch(_){}if(note){note.className='report-readiness-note blocked';note.textContent=e.message||String(e)}showCalcError(e,'engineering report')}
  finally{if(button){button.disabled=false;button.textContent='Generate PDF'}}
}
function printResults(){openEngineeringReportDialog()}
function printCurrentTab(){openEngineeringReportDialog()}


async function init(){loadComputeCapabilities();try{const [ent,j,wj]=await Promise.all([requestJson('/api/entitlements',{},'Subscription entitlement load failed'),requestJson('/api/membranes',{},'Membrane database load failed'),requestJson('/api/seawater-presets',{},'Seawater preset load failed')]);membranes=j.membranes||[];seawaterPresets=wj.presets||[];if(!membranes.length)throw new Error('Membrane database is empty.');if(!seawaterPresets.length)throw new Error('Seawater preset database is empty.');waterProfile=blankWaterProfile();caseStore={1:{waterProfile:deepClone(waterProfile),modeStates:{},caseResults:{},economicState:deepClone(economicDefaults),lastEconomicResult:null,chemistryResult:null,baseDesignSeed:null,advancedDesignInput:{},advancedDesignResult:null}};activeCase=1;modeStates={};caseResults={};economicState={...economicDefaults};lastEconomicResult=null;lastChemistryResult=null;configureEntitlements(ent);enforceTierCaseAccess();renderCaseBar();updateWaterWorkspaceTabs();renderFields();applyTierEntitlements();$('#results').innerHTML=''}catch(e){showCalcError(e,'water chemistry')}}
$('.tabs').addEventListener('click',e=>{const button=e.target.closest('[data-mode]');if(button)changeMode(button.dataset.mode)});
$('#caseTabs')?.addEventListener('click',e=>{const caseBtn=e.target.closest('[data-case]'),add=e.target.closest('[data-add-case]'),remove=e.target.closest('[data-remove-case]');if(caseBtn)switchCase(Number(caseBtn.dataset.case));else if(add)addCase();else if(remove)removeActiveCase();});
$('#adminTierPreview')?.addEventListener('click',e=>{const b=e.target.closest('[data-tier-preview]');if(b)setAdminTierPreview(b.dataset.tierPreview);});
$('#waterSubtabs')?.addEventListener('click',e=>{const b=e.target.closest('[data-water-submode]');if(b)changeMode(b.dataset.waterSubmode)});
$('#projectMetaToggle')?.addEventListener('click',()=>toggleProjectMeta());
$('#projectMetaClose')?.addEventListener('click',()=>toggleProjectMeta(false));
['metaProjectName','metaClient','metaUser','metaLocation','metaDate','metaRevision'].forEach(id=>$('#'+id)?.addEventListener('input',captureProjectMeta));
$('#saveProjectBtn')?.addEventListener('click',saveProject);
$('#importProjectBtn')?.addEventListener('click',()=>{if(entitlementContext?.account?.id)openProjectLibrary();else $('#projectFileInput')?.click();});
$('#legacyProjectImportBtn')?.addEventListener('click',()=>$('#projectFileInput')?.click());
$('#projectLibrarySearch')?.addEventListener('input',filterProjectLibrary);
$('#projectLibraryBody')?.addEventListener('click',async e=>{const open=e.target.closest('[data-project-open]'),copy=e.target.closest('[data-project-copy]');try{if(open)await loadServerProject(open.dataset.projectOpen);else if(copy)await createServerProjectRevision(copy.dataset.projectCopy);}catch(err){alert(`Project library action failed: ${err.message||err}`)}});
$('#projectFileInput')?.addEventListener('change',async e=>{const f=e.target.files?.[0];if(f)await importProjectFile(f);e.target.value='';});
$('#flowUnit').addEventListener('change',e=>changeUnits('flow',e.target.value));$('#pressureUnit').addEventListener('change',e=>changeUnits('pressure',e.target.value));$('#fluxUnit')?.addEventListener('change',e=>changeUnits('flux',e.target.value));
$('#resetBtn').addEventListener('click',()=>{if(mode==='water'){const label=waterProfile.envelope_label;waterProfile=blankWaterProfile();waterProfile.envelope_label=label||'Base design';lastChemistryResult=null;lastResult=null;caseResults={};modeStates={};advancedDesignInput={};advancedDesignResult=null;const current=activeCaseData();if(current){current.waterProfile=deepClone(waterProfile);current.chemistryResult=null;current.caseResults={};current.modeStates={};current.baseDesignSeed=null;current.advancedDesignInput={};current.advancedDesignResult=null;}syncActiveCaseStore();renderWaterTab();renderCurrentWaterChemistry()}else if(mode==='envelope'){renderEnvelopeTab();$('#results').innerHTML=hydraulicEnvelopeStatusHtml()}else if(mode==='scenario'){scenarioMatrixState={normal_trains:10,required_capacity_m3d:100000,maintain_capacity_nminus1:true};renderScenarioMatrixTab();$('#results').innerHTML=scenarioMatrixResults()}else if(mode==='comparison'){renderComparisonTab();$('#results').innerHTML=comparisonResults()}else if(mode==='summary'){renderSummaryTab();$('#results').innerHTML=summaryResults()}else if(mode==='economic'){economicState={...economicDefaults};lastEconomicResult=null;syncActiveCaseStore();renderEconomicTab();$('#results').innerHTML='<p class="muted">Economic assumptions reset.</p>'}else{modeStates[mode]={...defaults[mode]};caseResults[mode]=undefined;syncActiveCaseStore();renderFields(convertedDefaults());$('#results').innerHTML='<p class="muted">Defaults restored. Enter required inputs and calculate.</p>';$('#warnings').innerHTML='';updateRequiredFieldStates();}});
$('#calcForm').addEventListener('submit',async event=>{
  event.preventDefault();
  if(canonicalCalculationInFlight)return;
  clearCalcError();updateRequiredFieldStates();
  if(!$('#calcForm').checkValidity()){const error=new Error('Please complete the highlighted mandatory fields before calculating.');showCalcError(error,'input');$('#calcForm').reportValidity();return;}
  if(mode==='water'&&!waterProfileHasAnalyticalBasis(captureWater())){showCalcError(new Error('Select a water preset or enter a valid analytical water composition before calculating water chemistry.'),'input');return;}
  if(mode==='comparison'||mode==='summary'){try{await calc()}catch(error){showCalcError(error,mode)}return;}
  canonicalCalculationInFlight=true;canonicalCalculationSequence+=1;setCalculating(true);
  try{await new Promise(requestAnimationFrame);await calc()}
  catch(error){if(error?.kind==='cancelled'||error?.cancelled){emitCalculationState('cancelled',error.message||'Calculation stopped');showCalculationCancelledNotice()}else{emitCalculationState('failed',error?.message||'Calculation failed');showCalcError(error,mode)}}
  finally{setCalculating(false);canonicalCalculationInFlight=false;}
});
$('#enterCalculatorBtn')?.addEventListener('click',enterCalculatorFromLanding);
$('#landingDisclaimerBtn')?.addEventListener('click',()=>{const t=$('#landingEngineeringBasis');t?.scrollIntoView({behavior:'smooth',block:'start'});flashLandingTarget(t)});
$('#landingReleaseNotesBtn')?.addEventListener('click',()=>openLandingDialog('landingReleaseNotesDialog'));
$('#landingFeedbackBtn')?.addEventListener('click',()=>{enterCalculatorFromLanding();setTimeout(startManualFeedback,80)});
$('#landingReportBtn')?.addEventListener('click',()=>{enterCalculatorFromLanding();setTimeout(()=>pulseAppControl(tierAllows('full_engineering_report')?$('#printResultsBtn'):$('#printTabBtn')),90)});
$('#landingHelpBtn')?.addEventListener('click',()=>openLandingDialog('landingHelpDialog'));
$('#landingHelpEnterBtn')?.addEventListener('click',()=>{closeLandingDialog($('#landingHelpDialog'));enterCalculatorFromLanding()});
document.querySelectorAll('[data-close-landing-dialog]').forEach(b=>b.addEventListener('click',()=>closeLandingDialog(b.closest('dialog'))));
document.querySelectorAll('.landing-dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d)closeLandingDialog(d)}));
$('#printTabBtn')?.addEventListener('click',printCurrentTab);
$('#feedbackBtn')?.addEventListener('click',startManualFeedback);
$('#printResultsBtn').addEventListener('click',printResults);
$('#computeStatus')?.addEventListener('click',()=>toggleComputePanel());
$('#computeQuickBtn')?.addEventListener('click',()=>toggleComputePanel());
$('#newProjectBtn')?.addEventListener('click',()=>{if(window.confirm('Start a new Total RO Design project? Unsaved changes will be lost.'))window.location.reload()});
$('#runAllBtn')?.addEventListener('click',()=>changeMode('scenario'));
$('#stopRunBtn')?.addEventListener('click',()=>{scenarioRunCancelled=true;const b=$('#stopRunBtn');if(b){b.disabled=true;b.title='Stop requested; the current solver batch will finish first.'}});
$('#cancelCalculationBtn')?.addEventListener('click',cancelActiveCalculation);
$('#compareQuickBtn')?.addEventListener('click',()=>changeMode('comparison'));
$('#addSolutionBtn')?.addEventListener('click',()=>{const order=['px','interstage_px','biturbo','single','interstage','dweer','pelton'];const next=order.find(k=>!processModeConfigured(k,modeStates?.[k]))||'px';changeMode(next)});
$('#conventionalSolutionBtn')?.addEventListener('click',()=>changeMode('multistage'));
$('#themeSelect')?.addEventListener('change',e=>applyTheme(e.target.value));
$('#engineeringReportOptionsForm')?.addEventListener('change',()=>{const ready=reportReadiness(currentReportOptions()),note=$('#reportReadinessNote'),button=$('#generateEngineeringReportBtn');if(note){note.className=`report-readiness-note ${ready.ready?'ready':'blocked'}`;note.textContent=ready.ready?'The current solved case is ready. The report will be rendered from an immutable report snapshot.':ready.problems[0]}if(button)button.disabled=!ready.ready;});
$('#engineeringReportOptionsForm')?.addEventListener('submit',submitEngineeringReport);
document.querySelectorAll('[data-close-suite-modal]').forEach(button=>button.addEventListener('click',()=>{const dialog=button.closest('dialog');if(dialog?.open)dialog.close();else dialog?.removeAttribute('open')}));
initTheme();bindContextualHelp();renderProjectMeta();toggleProjectMeta(false);
async function openDeepLinkedProject(){
  const params=new URLSearchParams(
    window.location.search
  );

  const raw=params.get(
    'project_revision_id'
  );

  if(!raw)return;

  const revisionId=Number(raw);

  if(
    !Number.isInteger(revisionId) ||
    revisionId<=0
  ){
    alert(
      'The requested Total RO Design project identifier is invalid.'
    );
    return;
  }

  try{
    await loadServerProject(
      revisionId
    );

    if(
      typeof enterCalculatorFromLanding==='function'
    ){
      enterCalculatorFromLanding();
    }

    /*
     * Remove the one-shot deep-link parameter after a successful load so
     * refreshing /ro does not reopen the project unexpectedly.
     */
    const clean=new URL(
      window.location.href
    );

    clean.searchParams.delete(
      'project_revision_id'
    );

    window.history.replaceState(
      {},
      document.title,
      clean.pathname+
      clean.search+
      clean.hash
    );

  }catch(err){
    alert(
      `The linked Total RO Design project could not be opened: ${
        err.message||err
      }`
    );
  }
}

init()
  .then(openDeepLinkedProject)
  .catch(err=>showCalcError(err,'startup'));
