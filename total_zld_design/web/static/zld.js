(() => {
  const $ = id => document.getElementById(id);
  const $$ = selector => Array.from(document.querySelectorAll(selector));
  const THEME_KEY = 'totalrodesign-theme';
  const TIER_KEY = 'totalzld-preview-tier';
  const apiBase = '/zld/api';
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const headers = {'Content-Type':'application/json'};
  if (csrf && !csrf.includes('{{')) headers['X-CSRFToken'] = csrf;

  let defaults = null;
  let commercial = null;
  let last = null;
  let activeProject = null;
  let activePage = 'project-basis';
  let previewTier = 'platinum';

  const TIER_ORDER = {entry:0,silver:1,gold:2,platinum:3};
  const TIER_LABELS = {entry:'Entry',silver:'Silver',gold:'Gold',platinum:'Platinum'};
  const pageMeta = {
    'project-basis':['DESIGN BASIS','Project Basis','Define the facility, feed basis and overall recovery objective.'],
    'feed-chemistry':['WATER CHEMISTRY','Feed Chemistry','Define the ionic feed basis and review high-salinity model coverage.'],
    'process-train':['PROCESS CONFIGURATION','Process Train','Review the connected ZLD unit-operation sequence.'],
    'fo-design':['MEMBRANE CONCENTRATION','Forward Osmosis','Configure and calculate the active FO transport regression model.'],
    'thermal':['THERMAL CONCENTRATION','Thermal Concentration','Configure the brine concentrator and VFFE screening calculations.'],
    'crystallization':['THERMAL FINISHING','Crystallization','Configure the current forced-circulation crystallizer screening model.'],
    'energy':['UTILITIES','Energy & Utilities','Review electrical and thermal duties from the calculated case.'],
    'equipment':['PRELIMINARY SIZING','Equipment Sizing','Review workbook-derived screening sizing metrics.'],
    'results':['ENGINEERING RESULTS','Calculated Results','Review mass balance, warnings, metrics and profiles.'],
    'scenarios':['ADVANCED WORKFLOW','Scenarios & Comparison','Gold-tier comparison architecture; currently planned.'],
    'optimization':['OPTIMIZATION','Process-Train Optimization','Platinum-tier optimization architecture; currently planned.'],
    'report':['DOCUMENTATION','Engineering Report','Commercial report architecture; currently planned.']
  };

  const fmt=(v,n=2)=>(v===null||v===undefined||Number.isNaN(Number(v)))?'—':Number(v).toLocaleString(undefined,{maximumFractionDigits:n});
  function toast(message){ const el=$('toast'); if(!el)return; el.textContent=message; el.classList.remove('hidden'); setTimeout(()=>el.classList.add('hidden'),4200); }
  async function getJSON(url){ const r=await fetch(url,{credentials:'same-origin'}); const j=await r.json(); if(!r.ok)throw new Error(j.error||r.statusText); return j; }
  async function requestJSON(method,url,body){ const r=await fetch(url,{method,headers,credentials:'same-origin',body:JSON.stringify(body)}); const j=await r.json(); if(!r.ok)throw new Error(j.error||r.statusText); return j; }
  const postJSON=(url,body)=>requestJSON('POST',url,body);
  const putJSON=(url,body)=>requestJSON('PUT',url,body);
  const setVal=(id,v)=>{ if($(id))$(id).value=v; };
  const getNum=id=>Number($(id)?.value||0);

  function applyTheme(value){
    const theme=value==='light'?'light':'dark';
    document.documentElement.dataset.theme=theme;
    try{localStorage.setItem(THEME_KEY,theme);}catch(_){ }
    if($('themeSelect'))$('themeSelect').value=theme;
    if(last?.mode==='fo_regression')drawFlux(last.modules.stages);
  }
  function initTheme(){
    let saved='dark';
    try{saved=localStorage.getItem(THEME_KEY)||localStorage.getItem('calcospower-theme')||'dark';}catch(_){ }
    applyTheme(saved==='light'?'light':'dark');
  }

  function featureDef(id){ return commercial?.features?.[id]||{label:id,minimum_tier:'entry',maturity:'planned'}; }
  function tierAllows(id){ return (TIER_ORDER[previewTier]??0)>=(TIER_ORDER[featureDef(id).minimum_tier]??0); }
  function pageFeature(page){ return document.querySelector(`.nav-item[data-page="${page}"]`)?.dataset.feature||'project_basis'; }
  function pageAllowed(page){ return tierAllows(pageFeature(page)); }
  function renderTierCards(){
    if(!$('tierCards'))return;
    const d={entry:'Core screening, FO transport, thermal train, projects and results.',silver:'Crystallization, utilities and preliminary equipment sizing.',gold:'Advanced chemistry and scenario comparison as validated.',platinum:'Optimization and system-integration workflows as validated.'};
    $('tierCards').innerHTML=Object.keys(TIER_ORDER).map(t=>`<article class="tier-card ${previewTier===t?'selected':''}"><span>${TIER_LABELS[t]}</span><p>${d[t]}</p></article>`).join('');
  }
  function applyTier(value){
    previewTier=TIER_ORDER[value]!==undefined?value:'platinum';
    try{localStorage.setItem(TIER_KEY,previewTier);}catch(_){ }
    if($('tierSelect'))$('tierSelect').value=previewTier;
    if($('tierLabel'))$('tierLabel').textContent=TIER_LABELS[previewTier];
    $$('.nav-item').forEach(btn=>{
      const def=featureDef(btn.dataset.feature),allowed=tierAllows(btn.dataset.feature),badge=btn.querySelector('b');
      btn.classList.toggle('tier-locked',!allowed);
      if(badge)badge.textContent=!allowed?`${def.minimum_tier.toUpperCase()}+`:def.maturity==='planned'?'PLANNED':def.minimum_tier!=='entry'?def.minimum_tier.toUpperCase():'';
    });
    $$('[data-lock-for]').forEach(el=>{
      const id=el.dataset.lockFor,def=featureDef(id),allowed=tierAllows(id),page=el.closest('.workspace-page');
      page?.classList.toggle('feature-locked',!allowed);
      el.innerHTML=allowed?'':`<div class="lock-card"><span>LOCKED FOR ${TIER_LABELS[previewTier].toUpperCase()}</span><strong>${def.label||id}</strong><p>Requires the ${TIER_LABELS[def.minimum_tier]||def.minimum_tier} tier or higher.</p></div>`;
    });
    renderTierCards();
    if(!pageAllowed(activePage))showPage('project-basis');
  }
  function showPage(page){
    if(!pageAllowed(page)){ const def=featureDef(pageFeature(page)); toast(`${def.label||'This workspace'} requires ${TIER_LABELS[def.minimum_tier]} tier or higher.`); return; }
    activePage=page;
    $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
    $$('.workspace-page').forEach(p=>p.classList.toggle('active',p.dataset.pagePanel===page));
    const meta=pageMeta[page]||pageMeta['project-basis'];
    $('pageEyebrow').textContent=meta[0]; $('pageTitle').textContent=meta[1]; $('pageSubtitle').textContent=meta[2];
    window.scrollTo({top:0,behavior:'instant'});
  }

  function loadThermal(d){
    ['feed_flow_m3_h','feed_temperature_c','feed_tds_mg_l','feed_ph','bc_concentrate_tds_mg_l','vffe_concentrate_tds_mg_l','nacl_saturation_mg_l'].forEach(k=>setVal(k,d[k]));
    setVal('target_recovery_pct',d.target_overall_recovery*100);
    const cg=$('chemistryGrid'); if(cg){cg.innerHTML='';Object.entries(d.species_mg_l).forEach(([k,v])=>{const label=document.createElement('label');label.innerHTML=`${k}<span>mg/L</span><input id="chem_${k}" type="number" step="any" value="${v}">`;cg.appendChild(label);});}
    setVal('bc_dt',d.bc.compressor_approach_dt_c);setVal('bc_eff',d.bc.compressor_isentropic_efficiency);setVal('bc_latent',d.bc.latent_heat_kj_kg);setVal('bc_recirculation',d.bc.seed_to_feed_recirculation_ratio);
    setVal('effects',d.vffe.effects);setVal('tube_od',d.vffe.tube_od_m);setVal('tubes_per_effect',d.vffe.tubes_per_effect);setVal('steam_temp',d.vffe.live_steam_temperature_c);setVal('fcc_tau',d.fcc.residence_time_h);setVal('fcc_evap',d.fcc.evaporation_fraction);
  }
  function loadFO(d){ setVal('fo_A',d.water_permeability_lmh_bar);setVal('fo_B',d.salt_permeability_lmh);setVal('fo_S',d.structural_parameter_um);setVal('fo_area',d.membrane_area_m2);setVal('fo_feed',d.feed_flow_m3_h);setVal('fo_draw_flow',d.draw_flow_m3_h);setVal('fo_draw_m',d.draw_inlet_molality);setVal('fo_velocity',d.feed_crossflow_velocity_m_s); }
  function thermalPayload(){
    const species={};Object.keys(defaults.thermal.species_mg_l).forEach(k=>species[k]=getNum('chem_'+k));
    return {feed_flow_m3_h:getNum('feed_flow_m3_h'),feed_temperature_c:getNum('feed_temperature_c'),feed_tds_mg_l:getNum('feed_tds_mg_l'),feed_ph:getNum('feed_ph'),species_mg_l:species,bc_concentrate_tds_mg_l:getNum('bc_concentrate_tds_mg_l'),vffe_concentrate_tds_mg_l:getNum('vffe_concentrate_tds_mg_l'),nacl_saturation_mg_l:getNum('nacl_saturation_mg_l'),target_overall_recovery:getNum('target_recovery_pct')/100,bc:{compressor_approach_dt_c:getNum('bc_dt'),compressor_isentropic_efficiency:getNum('bc_eff'),latent_heat_kj_kg:getNum('bc_latent'),seed_to_feed_recirculation_ratio:getNum('bc_recirculation')},vffe:{effects:getNum('effects'),tube_od_m:getNum('tube_od'),tubes_per_effect:getNum('tubes_per_effect'),live_steam_temperature_c:getNum('steam_temp')},fcc:{residence_time_h:getNum('fcc_tau'),evaporation_fraction:getNum('fcc_evap')}};
  }
  function foPayload(){return {water_permeability_lmh_bar:getNum('fo_A'),salt_permeability_lmh:getNum('fo_B'),structural_parameter_um:getNum('fo_S'),membrane_area_m2:getNum('fo_area'),feed_flow_m3_h:getNum('fo_feed'),draw_flow_m3_h:getNum('fo_draw_flow'),draw_inlet_molality:getNum('fo_draw_m'),feed_crossflow_velocity_m_s:getNum('fo_velocity')};}

  const kpi=(label,value,unit)=>`<div class="kpi"><div class="label">${label}</div><div class="value">${value}<span class="unit">${unit||''}</span></div></div>`;
  const rows=(obj,keys)=>keys.map(([k,l,u,n=2])=>`<div class="detail-row"><span>${l}</span><strong>${fmt(obj[k],n)} ${u||''}</strong></div>`).join('');
  const card=(title,inner)=>`<div class="detail-card"><h3>${title}</h3>${inner}</div>`;
  function render(result){
    last=result;$('emptyState').classList.add('hidden');$('results').classList.remove('hidden');$('modelStatus').textContent=result.model_status;$('jsonOutput').textContent=JSON.stringify(result,null,2);
    const s=result.summary;
    if(result.mode==='thermal_legacy'){
      $('modeLabel').textContent='Thermal ZLD';
      $('kpis').innerHTML=[kpi('Overall recovery',fmt(s.overall_recovery*100,2),'%'),kpi('Recovered water',fmt(s.total_recovered_water_m3_h,2),'m³/h'),kpi('Electrical power',fmt(s.total_electrical_power_kw,0),'kW'),kpi('Live steam',fmt(s.total_live_steam_t_h,2),'t/h'),kpi('Dry salt',fmt(s.dry_salt_t_h,2),'t/h'),kpi('Screening CAPEX','$'+fmt(s.screening_capex_usd/1e6,2),'MM')].join('');
      $('foChartPanel').classList.add('hidden');
      const b=result.modules.brine_concentrator,v=result.modules.vffe,f=result.modules.fcc,e=result.modules.economics_screening;
      $('detailCards').innerHTML=card('Brine concentrator',rows(b,[['distillate_m3_h','Distillate','m³/h'],['concentrate_m3_h','Concentrate','m³/h'],['total_power_kw','BC power','kW',0]]))+card('VFFE',rows(v,[['distillate_m3_h','Distillate','m³/h'],['film_reynolds','Film Re','',0],['live_steam_t_h','Live steam','t/h']]))+card('FCC',rows(f,[['relative_supersaturation','Supersaturation','',4],['dominant_crystal_size_mm','Crystal size','mm',3],['mother_liquor_m3_h','Mother liquor','m³/h']]))+card('Economics screen',rows(e,[['total_usd','Total screening','$',0]]));
      renderEnergy(result);renderEquipment(result);
    }else{
      $('modeLabel').textContent='FO Validation';
      $('kpis').innerHTML=[kpi('FO recovery',fmt(s.feed_water_recovery*100,2),'%'),kpi('Recovered water',fmt(s.total_water_recovered_m3_h,2),'m³/h'),kpi('Average flux',fmt(s.average_water_flux_lmh,2),'LMH'),kpi('Bulk CF',fmt(s.final_bulk_concentration_factor,3),''),kpi('Wall CF',fmt(s.maximum_wall_concentration_factor,3),''),kpi('Reverse draw salt',fmt(s.total_draw_solute_lost_kg_h,2),'kg/h')].join('');
      $('foChartPanel').classList.remove('hidden');drawFlux(result.modules.stages);
      const t=result.modules.transport_coefficients,h=result.modules.handoff;
      $('detailCards').innerHTML=card('Transport coefficients',rows(t,[['reynolds','Re','',1],['schmidt','Sc','',1],['sherwood','Sh','',2],['mass_transfer_coefficient_lmh','k','LMH',2]]))+card('Bulk handoff',rows(h.bulk_outlet,[['flow_m3_h','Final bulk flow','m³/h'],['bulk_concentration_factor','Bulk CF','',4],['osmotic_pressure_bar','Osmotic pressure','bar',2]]))+card('Wall diagnostic',rows(h.wall_diagnostic,[['maximum_wall_concentration_factor','Maximum wall CF','',4],['wall_equivalent_recovery','Equivalent recovery','',4]]));
      renderEquipment(result);
    }
    $('streamRows').innerHTML=result.streams.map(st=>`<tr><td>${st.name}</td><td>${fmt(st.flow_m3_h,3)}</td><td>${fmt(st.tds_mg_l,0)}</td><td>${fmt(st.solids_t_h,3)}</td><td>${st.phase}</td></tr>`).join('');
    $('warningCount').textContent=result.warnings.length+' items';$('warnings').innerHTML=result.warnings.map(w=>`<div class="warning ${w.severity}"><span class="w-code">${w.code}</span><div class="w-title">${w.title}</div><div class="w-detail">${w.detail}</div></div>`).join('');
  }
  function renderEnergy(r){
    if(!$('energySummary'))return;
    if(!r||r.mode!=='thermal_legacy'){$('energySummary').innerHTML='<p>Thermal energy/utilities populate after a thermal calculation.</p>';return;}
    const s=r.summary,b=r.modules.brine_concentrator,v=r.modules.vffe;
    $('energySummary').innerHTML=[['Total electrical power',fmt(s.total_electrical_power_kw,0)+' kW'],['BC power',fmt(b.total_power_kw,0)+' kW'],['Live steam',fmt(s.total_live_steam_t_h,2)+' t/h'],['VFFE live steam',fmt(v.live_steam_t_h,2)+' t/h'],['Recovered water',fmt(s.total_recovered_water_m3_h,2)+' m³/h'],['Model status','Screening / regression']].map(x=>`<article><span>${x[0]}</span><strong>${x[1]}</strong></article>`).join('');
  }
  function renderEquipment(r){
    if(!$('equipmentSummary'))return;
    if(!r){$('equipmentSummary').innerHTML='<p>Run a calculation to populate sizing metrics.</p>';return;}
    if(r.mode==='thermal_legacy'){
      const b=r.modules.brine_concentrator,v=r.modules.vffe,f=r.modules.fcc;
      $('equipmentSummary').innerHTML=card('Brine concentrator',rows(b,[['concentrate_m3_h','Concentrate','m³/h'],['total_power_kw','Power','kW',0]]))+card('VFFE',rows(v,[['film_reynolds','Film Re','',0],['film_htc_w_m2_k','Film HTC','W/m²·K',0]]))+card('Crystallizer',rows(f,[['dominant_crystal_size_mm','Crystal size','mm',3],['mother_liquor_m3_h','Mother liquor','m³/h']]));
    }else{
      const t=r.modules.transport_coefficients,h=r.modules.handoff;
      $('equipmentSummary').innerHTML=card('FO transport',rows(t,[['reynolds','Re','',1],['mass_transfer_coefficient_lmh','Mass transfer k','LMH',2]]))+card('FO outlet',rows(h.bulk_outlet,[['flow_m3_h','Bulk flow','m³/h'],['bulk_concentration_factor','Bulk CF','',4]]));
    }
  }
  function drawFlux(stages){
    const c=$('foChart');if(!c||!stages?.length)return;const ctx=c.getContext('2d'),w=c.width,h=c.height,p=42,css=getComputedStyle(document.documentElement),grid=css.getPropertyValue('--chart-grid').trim()||'#31517a',text=css.getPropertyValue('--chart-text').trim()||'#8ea8cb',line=css.getPropertyValue('--chart-line').trim()||'#ff9f0a',label=css.getPropertyValue('--chart-label').trim()||'#ffbd45';ctx.clearRect(0,0,w,h);ctx.strokeStyle=grid;ctx.fillStyle=text;ctx.font='12px Segoe UI';for(let i=0;i<=5;i++){const y=p+(h-2*p)*i/5;ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(w-p,y);ctx.stroke();}const vals=stages.map(x=>x.water_flux_lmh),max=Math.max(...vals)*1.12;ctx.strokeStyle=line;ctx.lineWidth=4;ctx.beginPath();vals.forEach((v,i)=>{const x=p+(w-2*p)*i/(vals.length-1),y=h-p-v/max*(h-2*p);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);ctx.fillStyle=label;ctx.fillText(v.toFixed(2),x-15,y-10);});ctx.stroke();ctx.fillStyle=text;stages.forEach((_,i)=>ctx.fillText(String(i+1),p+(w-2*p)*i/(stages.length-1)-3,h-12));
  }

  async function run(mode){
    try{const inputs=mode==='thermal'?thermalPayload():foPayload(),j=await postJSON(apiBase+'/calculate',{mode:mode==='thermal'?'thermal_legacy':'fo_regression',inputs});render(j.result);showPage('results');toast('Calculation complete — spreadsheet-free engine.');}catch(e){toast('Calculation error: '+e.message);}
  }
  function externalCalculation(){return window.ZLDTrain?.getActiveCalculation?.()||null;}
  function currentInputs(){const external=!last?externalCalculation():null;if(external)return external.inputs||null;return !last?null:last.mode==='thermal_legacy'?thermalPayload():foPayload();}
  async function makeProjectSnapshot(){
    const external=!last?externalCalculation():null;
    const calculation=last||external;
    if(!calculation)throw new Error('Run a calculation before saving.');
    const projectName=$('projectName')?.value?.trim()||activeProject?.name||'Total ZLD Design Project';
    const project={project_name:projectName,case_name:$('caseName')?.value||'Base Case'};
    if(window.ZLDTrain?.getState)project.process_train=window.ZLDTrain.getState();
    const activeUnit=window.ZLDTrain?.getActiveUnit?.();
    if(activeUnit?.instance_id)project.active_unit_instance_id=activeUnit.instance_id;
    const j=await postJSON(apiBase+'/project/snapshot',{mode:calculation.mode,inputs:currentInputs(),project});return j.snapshot;
  }
  function setActiveProject(project){activeProject=project||null;$('projectLabel').textContent=activeProject?.visible_id||'Unsaved';$('projectNameMini').textContent=$('projectName')?.value||activeProject?.name||'Total ZLD Design Project';$('createRevision').disabled=!activeProject;}
  async function save(){try{const snapshot=await makeProjectSnapshot();let j;if(activeProject){j=await putJSON('/api/projects/'+activeProject.id,{snapshot});toast('Project saved — '+j.project.visible_id);}else{j=await postJSON('/api/projects',{product_id:'zld',snapshot});toast('Project created — '+j.project.visible_id);}setActiveProject(j.project);}catch(e){toast('Save error: '+e.message);}}
  async function createRevision(){if(!activeProject){toast('Save the project before creating a revision.');return;}try{const snapshot=await makeProjectSnapshot(),j=await postJSON('/api/projects/'+activeProject.id+'/copy',{snapshot,name:$('projectName')?.value||activeProject.name});setActiveProject(j.project);toast('Revision created — '+j.project.visible_id);}catch(e){toast('Revision error: '+e.message);}}
  function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));}
  async function loadProject(id){
    try{const j=await getJSON('/api/projects/'+id),snapshot=j.snapshot||{},key=String(snapshot.active_case||1),data=(snapshot.cases||{})[key]||{},mode=snapshot.active_mode||'thermal_legacy';setVal('projectName',snapshot.project?.project_name||j.project.name||'Total ZLD Design Project');setVal('caseName',snapshot.project?.case_name||'Base Case');if(window.ZLDTrain?.setState){if(Array.isArray(snapshot.project?.process_train))window.ZLDTrain.setState(snapshot.project.process_train);else window.ZLDTrain.reset?.();if(snapshot.project?.active_unit_instance_id)window.ZLDTrain.selectUnit?.(snapshot.project.active_unit_instance_id,{open:false});}if(mode==='fo_regression')loadFO(data.inputs||defaults.fo);else if(mode==='thermal_legacy')loadThermal(data.inputs||defaults.thermal);else if(mode==='falling_film_evaporator')window.ZLDTrain?.loadCalculation?.(data.results||null,data.inputs||null,snapshot.project?.active_unit_instance_id||null);if(data.results&&mode!=='falling_film_evaporator')render(data.results);else if(mode==='falling_film_evaporator'){last=null;$('results').classList.add('hidden');$('emptyState').classList.remove('hidden');}else{last=null;$('results').classList.add('hidden');$('emptyState').classList.remove('hidden');}setActiveProject(j.project);$('projectLibraryDialog').close();showPage(data.results?(mode==='falling_film_evaporator'?'thermal':'results'):'project-basis');toast('Opened '+j.project.visible_id);}catch(e){toast('Open project error: '+e.message);}
  }
  async function openProjectLibrary(){
    try{const j=await getJSON('/api/projects'),projects=(j.projects||[]).filter(p=>p.product_id==='zld'),rowsEl=$('projectLibraryRows');if(!projects.length)rowsEl.innerHTML='<div class="project-library-empty">No Total ZLD Design projects have been saved yet.</div>';else{rowsEl.innerHTML=projects.map(p=>`<button class="project-library-item" data-project-id="${Number(p.id)}"><span><strong>${escapeHtml(p.visible_id)}</strong><small>${escapeHtml(p.name)}</small></span><span>Rev ${Number(p.revision)}<small>${escapeHtml(p.updated_at||'')}</small></span></button>`).join('');rowsEl.querySelectorAll('.project-library-item').forEach(b=>b.onclick=()=>loadProject(Number(b.dataset.projectId)));}$('projectLibraryDialog').showModal();}catch(e){toast('Project Library error: '+e.message);}
  }
  function newProject(){last=null;window.ZLDTrain?.reset?.();setActiveProject(null);setVal('projectName','Total ZLD Design Project');setVal('caseName','Base Case');$('results').classList.add('hidden');$('emptyState').classList.remove('hidden');loadThermal(defaults.thermal);loadFO(defaults.fo);renderEnergy(null);renderEquipment(null);$('modeLabel').textContent='Not calculated';showPage('project-basis');toast('New unsaved Total ZLD Design project.');}

  function bindEvents(){
    $$('.nav-item').forEach(b=>b.onclick=()=>showPage(b.dataset.page));
    $$('[data-open-page]').forEach(el=>el.onclick=()=>showPage(el.dataset.openPage));
    $('themeSelect').onchange=e=>applyTheme(e.target.value);$('tierSelect').onchange=e=>applyTier(e.target.value);
    $('runFO').onclick=()=>run('fo');$('runThermal').onclick=()=>run('thermal');$('runCrystallization').onclick=()=>run('thermal');
    $('saveProject').onclick=save;$('newProject').onclick=newProject;$('createRevision').onclick=createRevision;$('projectLibrary').onclick=openProjectLibrary;$('closeProjectLibrary').onclick=()=>$('projectLibraryDialog').close();
    $('projectName').addEventListener('input',()=>{$('projectNameMini').textContent=$('projectName').value||'Total ZLD Design Project';});
    $('toggleJson').onclick=()=>{$('jsonOutput').classList.toggle('hidden');$('toggleJson').textContent=$('jsonOutput').classList.contains('hidden')?'Engineering JSON':'Hide JSON';};
  }

  initTheme();try{previewTier=localStorage.getItem(TIER_KEY)||'platinum';}catch(_){previewTier='platinum';}bindEvents();
  getJSON(apiBase+'/defaults').then(d=>{defaults=d;commercial=d.commercial||null;loadThermal(d.thermal);loadFO(d.fo);applyTier(previewTier);renderEnergy(null);renderEquipment(null);}).catch(e=>toast('Could not load defaults: '+e.message));
})();