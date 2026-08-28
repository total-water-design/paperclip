/* Total RO Design CCRO Add-on v1.1.0
 * Runtime integration shim.  The host static/app.js remains untouched.
 */
(() => {
  'use strict';
  const ADDON_VERSION='1.1.0';
  if (window.__TOTALRO_CCRO_ADDON__) return;
  window.__TOTALRO_CCRO_ADDON__={version:ADDON_VERSION};

  function register(){
    // Latest Total RO Design exposes these host hooks as top-level lexical
    // bindings (const/let). Probe them directly rather than through nested
    // eval(), which can falsely report valid cross-script lexical bindings as
    // missing. A future incompatible host still fails visibly before CCRO
    // mutates any host state.
    const missing=[];
    if(typeof FEATURE_REGISTRY==='undefined')missing.push('FEATURE_REGISTRY');
    if(typeof MODE_FEATURE==='undefined')missing.push('MODE_FEATURE');
    if(typeof WORKSPACE_META==='undefined')missing.push('WORKSPACE_META');
    if(typeof defaults==='undefined')missing.push('defaults');
    if(typeof sections==='undefined')missing.push('sections');
    if(typeof processModeConfigured==='undefined')missing.push('processModeConfigured');
    if(typeof renderFields==='undefined')missing.push('renderFields');
    if(typeof changeMode==='undefined')missing.push('changeMode');
    if(typeof processPerformanceBody==='undefined')missing.push('processPerformanceBody');
    if(missing.length){console.error('CCRO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}

    embeddedChemistryStreamByMode.ccro='concentrate';
    resultSubtabByMode.ccro='performance';
    FEATURE_REGISTRY.ccro={min:'entry',label:'Closed Circuit RO (CCRO)',maturity:'stable'};
    MODE_FEATURE.ccro='ccro';
    WORKSPACE_META.ccro=['DESIGN','Closed Circuit RO (CCRO)','Simulate a cyclic single-stage closed-circuit RO sequence with dynamic pressure, concentrate recycle, plug-flow flush, chemistry constraints and batch-integrated SEC.'];

    const ccroProcess={
      ccro_target_average_recovery:{label:'Target sequence-average recovery',type:'recoveryPct',suffix:'%',min:1,max:99.9,info:'Average recovery across the complete CCRO sequence, including the plug-flow flush. No universal CCRO recovery ceiling is imposed; the calculated envelope is constrained by membrane/equipment pressure, osmotic pressure, chemistry, flux, polarization and hydraulics.'},
      ccro_closed_circuit_permeate_flow:{label:'Closed-circuit permeate / net feed flow',type:'flow',info:'During closed-circuit operation, fresh feed replaces permeate leaving the loop. This is both the target membrane permeate flow and the net fresh-feed flow during CC mode.'},
      ccro_concentrate_recycle_per_vessel:{label:'Concentrate recycle per pressure vessel',type:'flow',info:'High-pressure concentrate recirculated through each pressure vessel during closed-circuit operation. Enter the intended hydraulic duty and verify final crossflow/pressure-drop limits for the selected membranes and vessels.'},
      ccro_pf_feed_ratio:{label:'Plug-flow feed ratio / CC net feed',type:'number',suffix:'×',min:0.01,info:'PF feed flow divided by the closed-circuit net feed/permeate flow.'},
      ccro_pf_recovery:{label:'Plug-flow recovery',type:'recoveryPct',suffix:'%',min:1,max:95,info:'Membrane recovery during the plug-flow flush. The model determines PF duration so one entered closed-circuit system volume is displaced.'},
      ccro_system_volume_m3:{label:'Closed-circuit system volume',type:'number',suffix:'m³',optional:true,min:0,placeholder:'Blank = normalized 1 m³ basis',info:'Pressurized CCRO loop liquid volume. If blank, recovery/cycle count/SEC use a normalized 1 m³ basis; absolute duration and batch volume are not equipment-sizing values.'},
      ccro_loop_extra_dp:{label:'Additional loop piping / valve ΔP',type:'pressure',optional:true,min:0,info:'High-pressure closed-loop loss beyond membrane pressure-vessel pressure drop.'},
      ccro_system_pressure_limit:{label:'System / equipment pressure rating',type:'pressure',optional:true,min:0,placeholder:'Blank = membrane rating',info:'Optional pressure-vessel/piping/valve/pump envelope. When entered, Total RO Design uses the lower of this rating and the selected membrane rating. This allows standard SWRO and UHPRO systems to use their actual equipment class without an artificial CCRO-specific pressure cap.'},
      suction_pressure:{label:'CCRO HPP inlet pressure',type:'pressure',info:'Pressure at the high-pressure pump suction. During CC operation the HPP pressurizes fresh make-up flow while the high-pressure circulation pump carries recycle.'}
    };
    const ccroEnergy={
      pretreatment_discharge_pressure:{...energy.pretreatment_discharge_pressure},pretreatment_recovery:{...energy.pretreatment_recovery},pretreatment_pump_eff:{...energy.pretreatment_pump_eff},pretreatment_motor_eff:{...energy.pretreatment_motor_eff},pretreatment_vfd_eff:{...energy.pretreatment_vfd_eff},pretreatment_no_vfd:{...energy.pretreatment_no_vfd},
      pump_eff:{...energy.pump_eff,label:'CCRO high-pressure pump efficiency'},motor_eff:{...energy.motor_eff,label:'CCRO HPP motor efficiency'},vfd_eff:{...energy.vfd_eff,label:'CCRO HPP VFD efficiency'},pump_no_vfd:{...energy.pump_no_vfd,label:'CCRO HPP · no VFD'},
      ccro_circulation_pump_eff:{label:'High-pressure circulation pump efficiency',type:'percent',info:'Hydraulic efficiency of the recycle pump that overcomes membrane-vessel and loop pressure losses.'},
      ccro_circulation_motor_eff:{label:'Circulation-pump motor efficiency',type:'percent'},
      ccro_circulation_vfd_eff:{label:'Circulation-pump VFD efficiency',type:'percent'},
      ccro_circulation_no_vfd:{label:'Circulation pump · no VFD',type:'toggle'}
    };
    defaults.ccro={solve_basis:'ccro',membrane_coupling:'on',membrane_1:defaultMembrane,vessels_1:'',elements_per_vessel_1:7,permeate_pressure_1:0,ccro_target_average_recovery:90,ccro_closed_circuit_permeate_flow:'',ccro_concentrate_recycle_per_vessel:4.54,ccro_pf_feed_ratio:1.20,ccro_pf_recovery:20,ccro_system_volume_m3:'',ccro_loop_extra_dp:.4,ccro_system_pressure_limit:'',suction_pressure:2,pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,ccro_circulation_pump_eff:.82,ccro_circulation_motor_eff:.96,ccro_circulation_vfd_eff:.97,ccro_circulation_no_vfd:false,generated_from_base_plant:false};

    const hostSections=sections;
    sections=function(values=null){
      if(mode==='ccro'){
        const mem=['RO / membrane model',{fouling_factor:{...operating.fouling_factor},salt_passage_factor:{...operating.salt_passage_factor}}];
        return [['CCRO sequence & flow',ccroProcess],mem,stageMembraneSection(1,false,values),['HPP, circulation pump & pretreatment',ccroEnergy]];
      }
      return hostSections(values);
    };

    function ccroModeAccess(){
      if(!processModeConfigured('multistage',modeStates.multistage||{}))return {ok:false,reason:'Complete the Plant Design inputs first.'};
      if(!basePlantIsCurrent())return {ok:false,reason:'Calculate the current Plant Design before opening CCRO.'};
      return {ok:true};
    }
    window.TotalROCCRO={version:ADDON_VERSION,ccroModeAccess};

    function ensureCcroWorkspaceFromBase(){
      const base=modeStates.multistage||{},result=caseResults.multistage;if(!basePlantIsCurrent()||!result)return;
      const sig=base._last_calculated_signature;if(modeStates.ccro?.generated_from_base_plant&&modeStates.ccro?._base_plant_signature===sig)return;
      const n=Math.max(1,Math.min(4,Number(base.stage_count||1))),epv=Math.max(1,Math.min(8,Number(base.elements_per_vessel_1||7)));
      let totalElements=0;for(let i=1;i<=n;i++)totalElements+=Math.max(0,Number(base[`vessels_${i}`]||0))*Math.max(0,Number(base[`elements_per_vessel_${i}`]||0));
      const vessels=Math.max(1,Math.ceil(totalElements/epv)),q=Number(result.product_flow||base.target_product_flow||0);
      modeStates.ccro={...defaults.ccro,membrane_1:base.membrane_1||defaultMembrane,vessels_1:vessels,elements_per_vessel_1:epv,membrane_design_mode_1:base.membrane_design_mode_1,membrane_recipe_1:base.membrane_recipe_1,ccro_closed_circuit_permeate_flow:q>0?q:'',suction_pressure:base.suction_pressure??defaults.ccro.suction_pressure,pretreatment_discharge_pressure:base.pretreatment_discharge_pressure??defaults.ccro.pretreatment_discharge_pressure,pretreatment_recovery:base.pretreatment_recovery??defaults.ccro.pretreatment_recovery,pretreatment_pump_eff:base.pretreatment_pump_eff??defaults.ccro.pretreatment_pump_eff,pretreatment_motor_eff:base.pretreatment_motor_eff??defaults.ccro.pretreatment_motor_eff,pretreatment_vfd_eff:base.pretreatment_vfd_eff??defaults.ccro.pretreatment_vfd_eff,pretreatment_no_vfd:base.pretreatment_no_vfd??defaults.ccro.pretreatment_no_vfd,pump_eff:base.pump_eff??defaults.ccro.pump_eff,motor_eff:base.motor_eff??defaults.ccro.motor_eff,vfd_eff:base.vfd_eff??defaults.ccro.vfd_eff,pump_no_vfd:base.pump_no_vfd??defaults.ccro.pump_no_vfd,generated_from_base_plant:true,_base_plant_signature:sig,_base_design_seed:deepClone(caseBaseSeed()),_inherited_from:`Plant Design · Case ${activeCase}`};
      syncActiveCaseStore();
    }
    function updateCcroNavAccess(){
      document.querySelectorAll('[data-mode="ccro"]').forEach(btn=>{const a=ccroModeAccess();btn.disabled=!a.ok;btn.classList.toggle('erd-locked',!a.ok);btn.title=a.ok?'Cyclic Closed Circuit RO sequence design':a.reason;});
    }

    function injectNavigation(){
      if(document.querySelector('[data-ccro-addon-nav]'))return;
      const plant=document.querySelector('[data-mode="multistage"]');if(!plant)return;
      const button=document.createElement('button');
      button.className=plant.className;
      button.dataset.mode='ccro';
      button.dataset.ccroAddonNav='1';
      button.disabled=true;
      button.title='Calculate Plant Design before opening CCRO';
      button.innerHTML=`<span class="nav-icon"><img src="/static/addons/ccro/ccro.svg" alt=""></span><span>CCRO Design</span><b class="nav-detail">Closed Circuit RO · cyclic high-recovery design</b>`;
      plant.insertAdjacentElement('afterend',button);
    }

    const hostProcessConfigured=processModeConfigured;
    processModeConfigured=function(tech,s){
      if(tech==='ccro')return !!s&&Number(s.ccro_closed_circuit_permeate_flow)>0&&Number(s.vessels_1)>0&&Number(s.elements_per_vessel_1)>0&&Number.isFinite(Number(s.suction_pressure))&&Number.isFinite(Number(s.pretreatment_discharge_pressure));
      return hostProcessConfigured(tech,s);
    };

    const hostPersist=persistActiveCase;
    persistActiveCase=function(){
      if(mode==='ccro'&&document.querySelector('#calcForm [name]')){
        const captured=capture(),previous=modeStates.ccro||{},workflowMeta={};
        Object.entries(previous).forEach(([k,v])=>{if(k.startsWith('_')||['generated_from_base_plant','solution_enabled','generalized_biturbo','plant_solution'].includes(k))workflowMeta[k]=v;});
        modeStates.ccro={...captured,...workflowMeta};syncActiveCaseStore();return;
      }
      return hostPersist();
    };

    const hostInvalidate=invalidateDerivedResultsFromBasePlant;
    invalidateDerivedResultsFromBasePlant=function(){hostInvalidate();if(modeStates.ccro?.generated_from_base_plant)caseResults.ccro=undefined;syncActiveCaseStore();};

    const hostApplyTier=applyTierEntitlements;
    applyTierEntitlements=function(){hostApplyTier();updateCcroNavAccess();};
    const hostWorkflow=updateWorkflowGates;
    updateWorkflowGates=function(){hostWorkflow();updateCcroNavAccess();};
    const hostChrome=updateWorkspaceChrome;
    updateWorkspaceChrome=function(){hostChrome();updateCcroNavAccess();};

    const hostRenderFields=renderFields;
    renderFields=function(values=defaults[mode]){hostRenderFields(values);if(mode==='ccro'){const ml=$('#modeLabel'),sh=$('.solve-hint');if(ml)ml.textContent=`Closed Circuit RO · Case ${activeCase}`;setPrimaryLabel('Calculate CCRO sequence');if(sh)sh.textContent='Cyclic PF + closed-circuit projection · pressure and chemistry are re-solved through the sequence.';}};

    const hostChangeMode=changeMode;
    changeMode=function(newMode){
      if(newMode==='ccro'){
        const a=ccroModeAccess();if(!a.ok){showCalcError(new Error(a.reason),'input');updateCcroNavAccess();return;}
        ensureCcroWorkspaceFromBase();
      }
      return hostChangeMode(newMode);
    };


    const hostWarnings=showWarnings;
    showWarnings=function(r){
      hostWarnings(r);if(mode!=='ccro'||!Array.isArray(r?.ccro_warnings)||!r.ccro_warnings.length)return;
      const h=$('#warnings');if(!h)return;const extra=r.ccro_warnings.map(w=>`<div class="warning dynamic-note"><div class="warning-head"><strong>CCRO engineering review</strong></div><div class="warning-text">${escapeHtml(w)}</div></div>`).join('');h.insertAdjacentHTML('afterbegin',extra);
    };

    const hostShow=show;
    show=function(r){hostShow(r);updateCcroNavAccess();};

    if(!comparisonOrder.some(([k])=>k==='ccro'))comparisonOrder.splice(1,0,['ccro','Closed Circuit RO (CCRO)']);

    const hostWaterStreams=waterStreamsForResult;
    waterStreamsForResult=function(c,r){
      if(!r?.ccro)return hostWaterStreams(c,r);
      const sourceFeed=Object.fromEntries(summarySpecies.map(([k])=>[k,Number(c.waterProfile?.['ion_'+k]||0)]));
      const perm=r.composite_permeate_composition_mg_l||r.stage1_permeate_composition_mg_l||null;
      return {feed:sourceFeed,conc:r.ccro_final_loop_composition_mg_l||r.stage1_concentrate_composition_mg_l||null,perm};
    };

    const hostChemBasis=resultChemistryBasis;
    resultChemistryBasis=function(r,stream){
      if(!r?.ccro)return hostChemBasis(r,stream);const key=String(stream||'');
      if(key==='feed')return {comp:waterStreamsForResult({waterProfile},r).feed,ph:Number(waterProfile.feed_ph),alk:Number(waterProfile.ion_bicarbonate||0)};
      if(key==='concentrate')return {comp:r.ccro_final_loop_composition_mg_l||r.stage1_concentrate_composition_mg_l,ph:Number(r.ccro_final_loop_ph??r.stage1_concentrate_ph??waterProfile.feed_ph),alk:Number(r.ccro_final_loop_alkalinity_mg_l_as_hco3??r.stage1_concentrate_alkalinity_mg_l_as_hco3??waterProfile.ion_bicarbonate??0)};
      return hostChemBasis(r,stream);
    };

    function ccroPerformanceReport(r){
      const profile=Array.isArray(r?.ccro_cycle_profile)?r.ccro_cycle_profile:[];
      const rows=profile.map(x=>{const sat=Number(x.highest_mineral_saturation_pct),satText=Number.isFinite(sat)?`${fmt(sat,1)}%${x.limiting_mineral?` · ${escapeHtml(x.limiting_mineral)}`:''}`:'—';return `<tr><td>${fmt(x.cycle,0)}${Number(x.cycle_fraction)<.999?` · ${fmt(100*x.cycle_fraction,1)}%`:''}</td><td>${fmt(x.duration_min,2)}</td><td>${fmt(x.feed_tds_mg_l,0)}</td><td>${fmt(x.feed_osmotic_bar,2)}</td><td>${fmt(x.feed_pressure_bar,2)}</td><td>${fmt(x.minimum_element_ndp_bar,2)}</td><td>${fmt(x.permeate_tds_mg_l,1)}</td><td>${fmt(100*x.sequence_equivalent_recovery,2)}%</td><td>${fmt(x.flux_lmh,2)}</td><td>${fmt(x.polarization_factor,2)}</td><td class="${Number.isFinite(sat)&&sat>=100?'scaling-attention':''}">${satText}</td><td>${fmt(x.hpp_kw,1)}</td><td>${fmt(x.recirculation_kw,1)}</td></tr>`}).join('');
      const warns=(r?.ccro_warnings||[]).map(w=>`<li>${escapeHtml(w)}</li>`).join(''),sat=Number(r?.ccro_highest_mineral_saturation_pct),hasSat=Number.isFinite(sat),onset=Number(r?.ccro_first_scaling_onset_recovery),hasOnset=r?.ccro_first_scaling_onset_recovery!==null&&r?.ccro_first_scaling_onset_recovery!==undefined&&Number.isFinite(onset);
      const scalingSummary=hasSat?`${fmt(sat,1)}% · ${escapeHtml(r.ccro_limiting_mineral||'limiting mineral')}`:'Full-ion chemistry required';
      const onsetText=hasOnset?`First ≥100% saturation at ${fmt(100*onset,2)}% sequence recovery${r.ccro_first_scaling_onset_mineral?` · ${escapeHtml(r.ccro_first_scaling_onset_mineral)}`:''}`:'No thermodynamic saturation onset calculated within target sequence';
      const activeLimit=Number(r.ccro_system_pressure_limit_bar||r.ccro_membrane_pressure_limit_bar||0);
      return `<div class="kpi-strip five"><div><span>Average recovery</span><strong>${fmt(100*Number(r.recovery||0),2)}%</strong></div><div><span>Total SEC</span><strong>${fmt(r.total_sec,3)} kWh/m³</strong></div><div><span>CC pressure rise</span><strong>${fmt(r.ccro_first_cycle_pressure_bar,2)} → ${fmt(r.ccro_final_cycle_pressure_bar,2)} bar</strong></div><div><span>Active pressure envelope</span><strong>${fmt(r.ccro_pressure_utilization_pct,1)}% of ${fmt(activeLimit,1)} bar</strong></div><div><span>Composite permeate TDS</span><strong>${fmt(r.ccro_composite_permeate_tds_mg_l,1)} mg/L</strong></div></div>
      <section class="report-section"><div class="chart-title-row"><h3>RECOVERY LIMITING CONDITION</h3><span>Calculated engineering envelope</span></div><div class="plant-summary-three"><article><span>Current limiting basis</span><strong>${escapeHtml(r.ccro_recovery_limiter||'Engineering review')}</strong><small>${escapeHtml(r.ccro_recovery_limiter_detail||'')}</small></article><article><span>Pressure / osmotic margin</span><strong>${fmt(r.ccro_pressure_margin_bar,2)} bar remaining</strong><small>Final feed osmotic ${fmt(r.ccro_final_feed_osmotic_bar,2)} bar · minimum element NDP ${fmt(r.ccro_minimum_element_ndp_bar,2)} bar</small></article><article><span>Mineral saturation screen</span><strong>${scalingSummary}</strong><small>${onsetText}</small></article></div><p class="micro-note">The active pressure envelope is the lower of the selected membrane rating and any entered system/equipment pressure rating. Mineral saturation is a thermodynamic bulk-concentrate screen, not an antiscalant performance guarantee.</p></section>
      <section class="report-section"><div class="chart-title-row"><h3>CCRO SEQUENCE</h3><span>Cyclic single-stage projection · PF + closed circuit</span></div><div class="plant-summary-three"><article><span>Complete sequence</span><strong>${fmt(r.ccro_complete_sequence_duration_min,2)} min</strong><small>${fmt(r.ccro_pf_sequence_duration_min,2)} min PF + ${fmt(r.ccro_cc_sequence_duration_min,2)} min CC</small></article><article><span>System / batch volume</span><strong>${fmt(r.ccro_system_volume_m3,3)} m³ loop</strong><small>${fmt(r.ccro_permeate_volume_per_batch_m3,3)} m³ permeate · ${fmt(r.ccro_brine_flush_volume_m3,3)} m³ brine displacement</small></article><article><span>Final loop concentration</span><strong>${fmt(r.ccro_final_loop_feed_tds_mg_l,0)} mg/L</strong><small>Final membrane concentrate ${fmt(r.ccro_final_membrane_concentrate_tds_mg_l,0)} mg/L</small></article></div><div class="table-wrap"><table class="fedco-table"><thead><tr><th>CC cycle</th><th>Duration<br><span>min</span></th><th>Loop feed TDS<br><span>mg/L</span></th><th>Feed π<br><span>bar</span></th><th>Feed P<br><span>bar</span></th><th>Min NDP<br><span>bar</span></th><th>Perm. TDS<br><span>mg/L</span></th><th>Sequence recovery</th><th>Flux<br><span>LMH</span></th><th>CP</th><th>Max mineral saturation</th><th>HPP<br><span>kW</span></th><th>Recirc<br><span>kW</span></th></tr></thead><tbody>${rows}</tbody></table></div></section><section class="report-section"><h3>CCRO ENERGY & PUMP DUTIES</h3><div class="plant-summary-three"><article><span>RO sequence SEC</span><strong>${fmt(r.ro_sec,3)} kWh/m³</strong><small>HPP + high-pressure recirculation</small></article><article><span>Peak HPP / recirculation</span><strong>${fmt(r.ccro_hpp_peak_kw,1)} / ${fmt(r.ccro_recirculation_peak_kw,1)} kW</strong><small>PF HPP ${fmt(r.ccro_pf_hpp_kw,1)} kW</small></article><article><span>Pretreatment SEC</span><strong>${fmt(r.pretreatment_sec,3)} kWh/m³</strong><small>Total ${fmt(r.total_sec,3)} kWh/m³</small></article></div>${warns?`<div class="dynamic-note"><strong>CCRO engineering review</strong><ul>${warns}</ul></div>`:''}</section>`;
    }


    const CCRO_SIGNATURE_KEYS=[
      'membrane_1','membrane_design_mode_1','membrane_recipe_1','vessels_1','elements_per_vessel_1','permeate_pressure_1',
      'ccro_target_average_recovery','ccro_closed_circuit_permeate_flow','ccro_concentrate_recycle_per_vessel','ccro_pf_feed_ratio','ccro_pf_recovery',
      'ccro_system_volume_m3','ccro_loop_extra_dp','ccro_system_pressure_limit','suction_pressure','pump_eff','motor_eff','vfd_eff','pump_no_vfd',
      'ccro_circulation_pump_eff','ccro_circulation_motor_eff','ccro_circulation_vfd_eff','ccro_circulation_no_vfd',
      'pretreatment_discharge_pressure','pretreatment_recovery','pretreatment_pump_eff','pretreatment_motor_eff','pretreatment_vfd_eff','pretreatment_no_vfd',
      'fouling_factor','salt_passage_factor'
    ];
    function ccroCalculationSignature(state={}){
      const o={};CCRO_SIGNATURE_KEYS.forEach(k=>o[k]=state?.[k]??null);
      o.flow_unit=currentUnits.flow;o.pressure_unit=currentUnits.pressure;o.flux_unit=currentUnits.flux;
      o.source_water_type=waterProfile.source_water_type||null;o.water_tds=Number(waterProfile.analysis_tds||waterProfile.feed_tds||0);o.water_ph=Number(waterProfile.feed_ph||0);o.water_temp=Number(waterProfile.temperature_c||0);o.water_fouling_factor=Number(waterProfile.fouling_factor??state.fouling_factor??0);o.water_salt_passage_factor=Number(waterProfile.salt_passage_factor??state.salt_passage_factor??0);
      if(typeof summarySpecies!=='undefined')for(const [key] of summarySpecies)o[`water_${key}`]=Number(waterProfile?.[`ion_${key}`]||0);
      return JSON.stringify(o);
    }
    function calculationSignatureForMode(reportMode,state={}){return reportMode==='ccro'?ccroCalculationSignature(state):basePlantSignature(state);}

    function ccroGraphProfiles(result){
      const profiles=Array.isArray(result?.ccro_cycle_graph_profiles)?result.ccro_cycle_graph_profiles.filter(x=>Array.isArray(x?.element_profile)&&x.element_profile.length):[];
      if(profiles.length)return {profiles,legacy:false};
      const finalElements=Array.isArray(result?.stage1_element_profile)?result.stage1_element_profile:[];
      if(!finalElements.length)return {profiles:[],legacy:true};
      const cycles=Array.isArray(result?.ccro_cycle_profile)?result.ccro_cycle_profile:[],last=cycles[cycles.length-1]||{};
      return {profiles:[{cycle:Number(last.cycle||Math.ceil(Number(result?.ccro_cc_cycles||1))),cycle_fraction:Number(last.cycle_fraction??result?.ccro_final_cycle_fraction??1),sequence_equivalent_recovery:Number(last.sequence_equivalent_recovery??result?.recovery??0),feed_pressure_bar:Number(last.feed_pressure_bar??result?.ccro_final_cycle_pressure_bar??0),reject_pressure_bar:Number(result?.reject_pressure_1??0),element_profile:deepClone(finalElements)}],legacy:true};
    }
    function ccroSelectedGraphProfile(result,c=activeCaseData()){
      const info=ccroGraphProfiles(result),profiles=info.profiles;if(!profiles.length)return {...info,selected:null};
      const requested=Number(c?.ccroSelectedGraphCycle),selected=profiles.find(p=>Number(p.cycle)===requested)||profiles[profiles.length-1];
      if(c&&Number(c.ccroSelectedGraphCycle)!==Number(selected.cycle)){c.ccroSelectedGraphCycle=Number(selected.cycle);syncActiveCaseStore();}
      return {...info,selected};
    }
    function ccroCycleLabel(profile,profiles=[]){const final=profiles.length&&profile===profiles[profiles.length-1],fraction=Number(profile?.cycle_fraction??1);return `Cycle ${Number(profile?.cycle||1)}${final?' · Final':''}${fraction<.999?` · ${fmt(100*fraction,1)}% cycle`:''}`;}
    function ccroProfileAsResult(result,profile){return {...result,stage_count:1,stage1_element_profile:deepClone(profile?.element_profile||[])};}
    function relabelCcroChart(html,label){return String(html||'').replaceAll('STAGE 1',label.toUpperCase()).replaceAll('Stage 1',label).replaceAll('Stage 1, element',`${label}, element`);}
    function ccroHydraulicProfileChart(profile,result){
      const pts=Array.isArray(profile?.element_profile)?profile.element_profile:[];if(!pts.length)return '';
      const factor=result?.pressure_unit==='psi'?14.5037738:1,series=pts.map((e,i)=>({x:i+1,p:Number(e.feed_pressure_bar)*factor,pi:Number(e.membrane_surface_osmotic_bar)*factor,ndp:Number(e.ndp_bar)*factor}));
      const values=series.flatMap(x=>[x.p,x.pi,x.ndp]).filter(Number.isFinite);if(!values.length)return '';
      const W=820,H=270,L=56,R=22,T=24,B=44,min=Math.min(0,...values),max=Math.max(...values),span=Math.max(max-min,1),x=i=>L+i*(W-L-R)/Math.max(1,series.length-1),y=v=>T+(max-v)*(H-T-B)/span;
      const path=k=>series.filter(v=>Number.isFinite(v[k])).map((v,i)=>`${i?'L':'M'} ${x(i).toFixed(1)} ${y(v[k]).toFixed(1)}`).join(' '),ticks=series.map((_,i)=>`<text x="${x(i)}" y="${H-B+19}" text-anchor="middle" class="flux-axis-text">${i+1}</text>`).join('');
      return `<section class="report-section flux-chart-section"><div class="chart-title-row"><h3>HYDRAULIC / OSMOTIC PROFILE</h3><span>Feed pressure · membrane-surface π · NDP</span></div><div class="cp-legend"><span>Feed pressure</span><span>Surface osmotic pressure</span><span>NDP</span></div><div class="flux-chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="CCRO selected-cycle hydraulic, osmotic and NDP profile"><line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="flux-axis"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="flux-axis"/><path d="${path('p')}" class="flux-line"/><path d="${path('pi')}" class="cp-line cp-line-mono"/><path d="${path('ndp')}" class="cp-line cp-line-di"/>${ticks}<text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" class="flux-axis-title">Membrane position</text><text x="15" y="${(T+H-B)/2}" transform="rotate(-90 15 ${(T+H-B)/2})" text-anchor="middle" class="flux-axis-title">Pressure (${escapeHtml(result?.pressure_unit||'bar')})</text></svg></div></section>`;
    }
    function ccroCycleElementTable(profile){const rows=(profile?.element_profile||[]).map((e,i)=>`<tr><td>${i+1}</td><td>${escapeHtml(e.membrane_model||e.membrane_id||'—')}</td><td>${fmt(e.flux_lmh,2)}</td><td>${fmt(e.polarization_factor_monovalent??e.polarization_factor,2)}</td><td>${fmt(e.polarization_factor_divalent??e.polarization_factor,2)}</td><td>${fmt(e.feed_pressure_bar,2)}</td><td>${fmt(e.reject_pressure_bar,2)}</td><td>${fmt(e.membrane_surface_osmotic_bar,2)}</td><td>${fmt(e.ndp_bar,2)}</td><td>${fmt(e.feed_tds_ppm,0)}</td><td>${fmt(e.reject_tds_ppm,0)}</td><td>${fmt(e.permeate_tds_ppm,1)}</td></tr>`).join('');return `<div class="table-wrap"><table class="fedco-table"><thead><tr><th>Element</th><th>Membrane</th><th>Flux<br>LMH</th><th>CP mono</th><th>CP div.</th><th>Feed P<br>bar</th><th>Reject P<br>bar</th><th>Surface π<br>bar</th><th>NDP<br>bar</th><th>Feed TDS</th><th>Reject TDS</th><th>Perm. TDS</th></tr></thead><tbody>${rows}</tbody></table></div>`;}
    function ccroCycleGraphSection(result){
      const c=activeCaseData(),info=ccroSelectedGraphProfile(result,c),p=info.selected;if(!p)return `<section id="ccroCycleGraphSection" class="report-section"><h3>CCRO CYCLE GRAPHS</h3><p class="dynamic-note">No cycle-specific element graph profile is available for this result.</p></section>`;
      const label=ccroCycleLabel(p,info.profiles),options=info.profiles.map(x=>`<option value="${Number(x.cycle)}" ${Number(x.cycle)===Number(p.cycle)?'selected':''}>Cycle ${Number(x.cycle)}${x===info.profiles[info.profiles.length-1]?' · Final':''} · ${fmt(100*Number(x.sequence_equivalent_recovery||0),1)}% sequence recovery</option>`).join(''),temp=ccroProfileAsResult(result,p);
      const charts=relabelCcroChart(fluxProfileChart(temp),label)+relabelCcroChart(polarizationProfileChart(temp),label)+ccroHydraulicProfileChart(p,result),compat=info.legacy?'<p class="dynamic-note"><strong>Compatibility note:</strong> This legacy CCRO result predates per-cycle graph storage; only its final-cycle element profile is available.</p>':'';
      return `<section id="ccroCycleGraphSection" class="report-section ccro-cycle-graphs"><div class="chart-title-row"><h3>CCRO ELEMENT-POSITION GRAPHS</h3><span>${escapeHtml(label)}</span></div><label class="field"><span>Displayed CCRO cycle</span><select id="ccroCycleGraphSelect">${options}</select></label><p class="micro-note">Sequence-equivalent recovery ${fmt(100*Number(p.sequence_equivalent_recovery||0),2)}% · cycle fraction ${fmt(100*Number(p.cycle_fraction??1),1)}%. Changing this selector redraws stored cycle data only; it does not recalculate.</p>${compat}${ccroCycleElementTable(p)}${charts}</section>`;
    }
    function bindCcroCycleSelector(result){const select=document.getElementById('ccroCycleGraphSelect');if(!select)return;select.addEventListener('change',()=>{const c=activeCaseData();if(c){c.ccroSelectedGraphCycle=Number(select.value);syncActiveCaseStore();}const old=document.getElementById('ccroCycleGraphSection');if(old){old.outerHTML=ccroCycleGraphSection(result);bindCcroCycleSelector(result);}});}

    function activeReportContext(){
      persistActiveCase();const c=activeCaseData();let reportMode=(mode==='ccro'||mode==='multistage')?mode:(c?.lastReportableMode||'multistage');
      if(mode==='ccro')reportMode='ccro';
      const result=c?.caseResults?.[reportMode]||caseResults?.[reportMode]||null,state=c?.modeStates?.[reportMode]||modeStates?.[reportMode]||{};
      const selected=reportMode==='ccro'?ccroSelectedGraphProfile(result,c):{selected:null,profiles:[],legacy:false};
      const n=reportMode==='ccro'?1:(result?resultStageCount(result):Math.max(1,Math.min(4,Number(state.stage_count||1))));
      return {caseData:c,mode:reportMode,result,state,calculationSignature:calculationSignatureForMode(reportMode,state),stageCount:n,tail:result?.[`stage${n}_tail_element_chemistry`]||null,envelope:c?.hydraulicEnvelope||null,selectedCcroCycle:selected.selected,selectedGraphProfile:selected.selected,cycleProfiles:selected.profiles,legacyCycleProfile:selected.legacy};
    }
    window.TotalROCCRO.activeReportContext=activeReportContext;
    window.TotalROCCRO.calculationSignatureForMode=calculationSignatureForMode;

    const hostCalc=calc;
    calc=async function(){const calculatingMode=mode,out=await hostCalc();const c=activeCaseData();if(calculatingMode==='ccro'&&caseResults?.ccro){const state=modeStates.ccro||{};state._last_calculated_signature=calculationSignatureForMode('ccro',state);modeStates.ccro=state;if(c){c.lastReportableMode='ccro';c.ccroSelectedGraphCycle=ccroGraphProfiles(caseResults.ccro).profiles.at(-1)?.cycle??null;}syncActiveCaseStore();}else if(calculatingMode==='multistage'&&caseResults?.multistage){if(c)c.lastReportableMode='multistage';syncActiveCaseStore();}return out;};

    const hostReportReadiness=reportReadiness;
    reportReadiness=function(options={}){
      const ctx=activeReportContext();if(ctx.mode!=='ccro')return hostReportReadiness(options);
      const problems=[];if(document.body.classList.contains('calculating'))problems.push('A calculation is still running. Wait for it to finish.');
      if(!ctx.result)problems.push('Calculate the active CCRO design before generating its report.');
      const stale=Boolean(ctx.result)&&ctx.state._last_calculated_signature!==ctx.calculationSignature;if(stale)problems.push('CCRO design inputs changed after the last calculation. Recalculate the active CCRO case.');
      if(options.include_detailed_chemistry&&!lastChemistryResult)problems.push('Calculate the requested detailed water chemistry before including Appendix A.');
      if(options.include_tail_chemistry&&!ctx.tail)problems.push('Tail-element chemistry is not complete for this CCRO case. Recalculate with Full water chemistry before including Appendix B.');
      if(options.include_hydraulic_envelope&&!ctx.envelope?.rows?.length)problems.push('The Hydraulic Envelope has not been calculated for this case.');
      return {ready:problems.length===0,problems,stale,result:ctx.result,state:ctx.state,caseData:ctx.caseData,stageCount:ctx.stageCount,tail:ctx.tail,envelope:ctx.envelope,reportMode:'ccro',context:ctx};
    };

    const hostEnsureReportScalingChemistry=ensureReportScalingChemistry;
    ensureReportScalingChemistry=async function(contextOrResult){
      const ctx=contextOrResult?.mode?contextOrResult:activeReportContext();if(ctx.mode!=='ccro')return hostEnsureReportScalingChemistry(contextOrResult?.result||contextOrResult);
      const result=ctx.result;if(!result)return null;const stream='concentrate',identity=ctx.state?._last_calculated_signature||`${result.ccro_final_cycle_pressure_bar||''}:${result.ccro_final_loop_feed_tds_mg_l||''}`,key=`report:${activeCase}:ccro:${identity}:${stream}`;
      if(embeddedChemistryCache[key])return deepClone(embeddedChemistryCache[key]);
      const comp=result.ccro_final_loop_composition_mg_l||result.stage1_concentrate_composition_mg_l;if(!comp)return null;
      const ph=Number(result.ccro_final_loop_ph??result.stage1_concentrate_ph??waterProfile.feed_ph),alk=Number(result.ccro_final_loop_alkalinity_mg_l_as_hco3??result.stage1_concentrate_alkalinity_mg_l_as_hco3??waterProfile.ion_bicarbonate??0),payload={...profileChemPayload(waterProfile,comp,ph,alk),reported_tds:compositionTds(comp),source_ph:ph};
      const resp=await totalroFetch('/api/chemistry/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const j=await resp.json();if(!resp.ok)throw new Error(j.error||'Final-loop scaling chemistry calculation failed');embeddedChemistryCache[key]=j;return deepClone(j);
    };

    const hostBuildEngineeringReportSnapshot=buildEngineeringReportSnapshot;
    buildEngineeringReportSnapshot=function(options={},scalingChemistry=null){
      const ctx=activeReportContext();if(ctx.mode!=='ccro')return hostBuildEngineeringReportSnapshot(options,scalingChemistry);
      const ready=reportReadiness(options);if(!ready.ready)throw new Error(ready.problems.join(' '));const result=deepClone(ctx.result),state=deepClone(ctx.state),selected=deepClone(ctx.selectedGraphProfile),c=ctx.caseData;
      return {schema:'TotalRODesign.ReportSnapshot.v1',state:'Ready',stale:false,generated_at:new Date().toISOString(),app_name:'Total RO Design',app_version:'0.2',suite_name:'Total Water Design Suite',suite_version:'0.25',case_id:activeCase,case_name:c?.waterProfile?.envelope_label||`Case ${activeCase}`,active_mode:'ccro',calculation_mode:'ccro',stage_count:1,unit_system:deepClone(currentUnits),project:deepClone(projectMeta),water_profile:deepClone(c?.waterProfile||waterProfile),design_input:state,result,options:{report_type:'standard',...deepClone(options)},report_selection:{ccro_cycle:Number(selected?.cycle||0)},selected_graph_profile:selected,scaling_chemistry:scalingChemistry?deepClone(scalingChemistry):null,chemistry_detail:options.include_detailed_chemistry?deepClone(lastChemistryResult):null,tail_chemistry:options.include_tail_chemistry?deepClone(ctx.tail):null,hydraulic_envelope:options.include_hydraulic_envelope?deepClone(ctx.envelope):null,warning_messages:deepClone(result.ccro_warnings||[]),report_integrity:{last_calculated_signature:state._last_calculated_signature,active_signature:ctx.calculationSignature}};
    };

    const hostSubmitEngineeringReport=submitEngineeringReport;
    submitEngineeringReport=async function(event){
      const ctx=activeReportContext();if(ctx.mode!=='ccro')return hostSubmitEngineeringReport(event);
      event?.preventDefault();const options=currentReportOptions(),ready=reportReadiness(options),note=$('#reportReadinessNote'),button=$('#generateEngineeringReportBtn');if(!ready.ready){if(note){note.className='report-readiness-note blocked';note.textContent=ready.problems.join(' ')}if(button)button.disabled=true;return;}
      const popup=window.open('about:blank','_blank');if(popup)popup.document.write('<title>Preparing CCRO report…</title><p style="font:16px Segoe UI;padding:30px">Preparing the immutable CCRO engineering-report snapshot…</p>');
      try{if(button){button.disabled=true;button.textContent='Preparing report…'}const scaling=await ensureReportScalingChemistry(ctx);const snapshot=buildEngineeringReportSnapshot(options,scaling);const response=await requestJson('/api/report/snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({snapshot})},'CCRO engineering report could not be prepared');if(popup&&!popup.closed)popup.location=response.print_url;else window.location.assign(response.preview_url);const d=$('#engineeringReportDialog');if(d?.open)d.close();}
      catch(e){try{popup?.close()}catch(_){}if(note){note.className='report-readiness-note blocked';note.textContent=e.message||String(e)}showCalcError(e,'CCRO engineering report');}
      finally{if(button){button.disabled=false;button.textContent='Generate PDF';}}
    };

    const hostBindProcessResultTabs=bindProcessResultTabs;
    bindProcessResultTabs=function(r){hostBindProcessResultTabs(r);if(mode==='ccro')bindCcroCycleSelector(r);};

    const hostPerformance=processPerformanceBody;
    processPerformanceBody=function(r){if(mode==='ccro')return solveStatus(r)+showMembraneHeader(r)+ccroPerformanceReport(r)+ccroCycleGraphSection(r)+membraneChecks(r);return hostPerformance(r);};

    const hostOpenProject=openImportedProject;
    openImportedProject=function(p,serverRecord=null){
      if(p?.active_mode!=='ccro')return hostOpenProject(p,serverRecord);
      const clone=deepClone(p);clone.active_mode='multistage';hostOpenProject(clone,serverRecord);if(basePlantIsCurrent())changeMode('ccro');
    };

    injectNavigation();applyTierEntitlements();updateCcroNavAccess();
    console.info(`Total RO Design CCRO add-on v${ADDON_VERSION} activated.`);
  }

  try{register()}catch(err){console.error('CCRO add-on activation failed:',err);}
})();
