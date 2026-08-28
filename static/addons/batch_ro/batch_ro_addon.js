/* Total RO Design Batch RO Add-on v0.1.0
 * Additive specialist workspace. Conventional RO and CCRO remain untouched.
 */
(() => {
  'use strict';
  const ADDON_VERSION='0.1.0';
  if(window.__TOTALRO_BATCH_RO_ADDON__) return;
  window.__TOTALRO_BATCH_RO_ADDON__={version:ADDON_VERSION};

  function register(){
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
    if(missing.length){console.error('Batch RO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}

    embeddedChemistryStreamByMode.batch_ro='concentrate';
    resultSubtabByMode.batch_ro='performance';
    FEATURE_REGISTRY.batch_ro={min:'entry',label:'Batch RO',maturity:'stable'};
    MODE_FEATURE.batch_ro='batch_ro';
    WORKSPACE_META.batch_ro=['DESIGN','Batch RO','Model a complete fully-batch RO cycle with variable pressure, explicit tank/external volume, reset duty, pressure recovery, salt passage, chemistry and SEC.'];

    const batchProcess={
      batch_configuration:{label:'Batch RO system configuration',type:'select',options:[['atmospheric_px','Atmospheric tank + isobaric PX'],['high_pressure_tank','Variable-volume high-pressure tank'],['dual_compartment','Dual-compartment / moving-divider continuous batch']],info:'Atmospheric + PX uses a standard low-pressure tank and explicit PX/booster losses. High-pressure tank removes PX transfer irreversibility. Dual-compartment mode alternates isolated volumes so refill/purge can overlap permeate production.'},
      batch_target_recovery:{label:'Target batch recovery',type:'recoveryPct',suffix:'%',min:1,max:97,info:'Permeate produced from the initially charged batch inventory. The solver stops early if the active permeate target can no longer be maintained inside the membrane/equipment pressure envelope.'},
      batch_average_product_flow:{label:'Target average product flow',type:'flow',info:'Average product over productive + reset time. The engine calculates the higher active permeate rate/flux required during the productive part of the batch.'},
      batch_operating_flux_lmh:{label:'Active operating flux',type:'flux',optional:true,min:1,max:80,info:'Used only when Target average product flow is blank. This is the flux while the batch is producing permeate; effective flux includes reset downtime.'},
      batch_permeate_per_cycle_m3:{label:'Permeate volume per cycle',type:'number',suffix:'m³',optional:true,min:0,info:'Optional explicit batch size. When blank, Total RO Design derives the minimum starting tank/inventory from target recovery, membrane-channel volume, external volume and end-of-cycle tank heel.'},
      batch_reset_time_s:{label:'Reset / purge / refill time',type:'number',suffix:'s',min:0,info:'Non-producing reset time for atmospheric- and high-pressure-tank batch systems. In dual-compartment mode this time is treated as an overlapping switch/purge operation and does not reduce product duty factor.'},
      batch_system_pressure_limit:{label:'System / equipment pressure rating',type:'pressure',optional:true,min:0,placeholder:'Blank = membrane rating',info:'Active pressure envelope is the lower of this value and the selected membrane pressure rating.'},
      batch_max_flux_lmh:{label:'Active flux review limit',type:'flux',min:1,max:100,info:'Engineering review limit for peak active membrane flux. This is a warning limit, not a substitute for the selected membrane manufacturer limits.'},
      batch_time_steps:{label:'Transient recovery increments',type:'integer',min:8,max:80,info:'Number of converged membrane states integrated across the productive batch. Higher values improve transient resolution but increase compute time.'},
    };

    const inventory={
      batch_piping_volume_pct_elements:{label:'Piping / heads / dead volume',type:'number',suffix:'% of membrane-channel volume',min:0,max:500,info:'Retained external liquid volume at the end of the productive batch, expressed relative to calculated membrane feed-channel liquid volume.'},
      batch_piping_volume_m3:{label:'External piping/dead volume override',type:'number',suffix:'m³',optional:true,min:0,info:'Optional absolute override. When entered it replaces the percent-of-element-volume input.'},
      batch_final_tank_volume_pct_elements:{label:'End-of-cycle tank heel',type:'number',suffix:'% of membrane-channel volume',min:0,max:500,info:'Liquid intentionally remaining in the batch tank when the productive cycle ends. Low values generally improve Batch RO energy performance.'},
      batch_final_tank_volume_m3:{label:'End-of-cycle tank heel override',type:'number',suffix:'m³',optional:true,min:0},
      batch_inlet_velocity_m_s:{label:'Membrane inlet bulk velocity',type:'number',suffix:'m/s',min:.01,max:1,info:'Used with membrane area, element length, feed-channel height and porosity to derive recirculation flow when a flow override is not entered.'},
      batch_recirculation_flow_per_vessel:{label:'Recirculation flow per vessel override',type:'flow',optional:true,min:0,info:'Optional hydraulic override. Blank derives flow from inlet velocity and the membrane feed-channel geometry.'},
      batch_channel_height_mm:{label:'Feed-channel height',type:'number',suffix:'mm',min:.1,max:2},
      batch_channel_porosity:{label:'Feed-channel porosity',type:'number',min:.2,max:.99},
      batch_element_length_m:{label:'Element length fallback',type:'number',suffix:'m',min:.1,max:2,info:'Used only when the selected membrane record does not carry element length.'},
      batch_loop_extra_dp:{label:'Additional recirculation loop ΔP',type:'pressure',min:0,info:'Piping, valves and external-loop loss in addition to the calculated membrane pressure-vessel ΔP.'},
    };

    const batchEnergy={
      pretreatment_discharge_pressure:{...energy.pretreatment_discharge_pressure},pretreatment_recovery:{...energy.pretreatment_recovery},pretreatment_pump_eff:{...energy.pretreatment_pump_eff},pretreatment_motor_eff:{...energy.pretreatment_motor_eff},pretreatment_vfd_eff:{...energy.pretreatment_vfd_eff},pretreatment_no_vfd:{...energy.pretreatment_no_vfd},
      pump_eff:{...energy.pump_eff,label:'Batch RO high-pressure pump efficiency'},motor_eff:{...energy.motor_eff,label:'Batch RO HPP motor efficiency'},vfd_eff:{...energy.vfd_eff,label:'Batch RO HPP VFD efficiency'},pump_no_vfd:{...energy.pump_no_vfd,label:'Batch RO HPP · no VFD'},
      batch_circulation_pump_eff:{label:'High-pressure circulation pump efficiency',type:'percent'},batch_circulation_motor_eff:{label:'Circulation motor efficiency',type:'percent'},batch_circulation_vfd_eff:{label:'Circulation VFD efficiency',type:'percent'},batch_circulation_no_vfd:{label:'Circulation pump · no VFD',type:'toggle'},
      batch_px_efficiency:{label:'Isobaric PX pressure-transfer efficiency',type:'percent',info:'Applied in Atmospheric tank + PX mode.'},batch_px_mixing:{label:'PX stream mixing',type:'percent',info:'Fractional concentration blend between the high- and low-pressure streams used in the instantaneous membrane-feed state.'},batch_px_leakage:{label:'PX leakage',type:'percent'},
      batch_px_hp_dp:{label:'PX high-pressure side ΔP',type:'pressure'},batch_px_lp_dp:{label:'PX low-pressure side ΔP',type:'pressure'},
      batch_booster_pump_eff:{label:'PX booster pump efficiency',type:'percent'},batch_booster_motor_eff:{label:'PX booster motor efficiency',type:'percent'},batch_booster_vfd_eff:{label:'PX booster VFD efficiency',type:'percent'},batch_booster_no_vfd:{label:'PX booster · no VFD',type:'toggle'},
      batch_refill_dp:{label:'Refill / purge pump ΔP',type:'pressure'},batch_refill_pump_eff:{label:'Refill pump efficiency',type:'percent'},batch_refill_motor_eff:{label:'Refill motor efficiency',type:'percent'},
      batch_reference_ro_sec:{label:'Conventional RO reference SEC',type:'number',suffix:'kWh/m³',optional:true,min:0,info:'Optional reference RO SEC used only to report a Batch RO energy-saving percentage.'},
    };

    const batchChemistry={
      batch_stop_on_saturation:{label:'Thermodynamic saturation stop',type:'toggle',toggleText:'Stop the batch at the saturation review limit',info:'Optional conservative envelope control. Bulk thermodynamic saturation does not represent antiscalant kinetics.'},
      batch_saturation_limit_pct:{label:'Saturation review limit',type:'number',suffix:'%',min:1,max:100000,info:'Concentration saturation percentage from the shared Total RO chemistry engine.'},
    };

    defaults.batch_ro={
      solve_basis:'batch_ro',membrane_coupling:'on',membrane_1:defaultMembrane,vessels_1:'',elements_per_vessel_1:8,permeate_pressure_1:0,
      batch_configuration:'atmospheric_px',batch_target_recovery:50,batch_average_product_flow:'',batch_operating_flux_lmh:'',batch_permeate_per_cycle_m3:'',batch_reset_time_s:10,batch_system_pressure_limit:'',batch_max_flux_lmh:55,batch_time_steps:28,
      batch_piping_volume_pct_elements:12,batch_piping_volume_m3:'',batch_final_tank_volume_pct_elements:0,batch_final_tank_volume_m3:'',batch_inlet_velocity_m_s:.18,batch_recirculation_flow_per_vessel:'',batch_channel_height_mm:.71,batch_channel_porosity:.90,batch_element_length_m:1.016,batch_loop_extra_dp:.3,
      pretreatment_discharge_pressure:6,pretreatment_recovery:.85,pretreatment_pump_eff:.82,pretreatment_motor_eff:.95,pretreatment_vfd_eff:.97,pretreatment_no_vfd:false,pump_eff:.85,motor_eff:.97,vfd_eff:.97,pump_no_vfd:false,
      batch_circulation_pump_eff:.82,batch_circulation_motor_eff:.96,batch_circulation_vfd_eff:.97,batch_circulation_no_vfd:false,batch_px_efficiency:.96,batch_px_mixing:.06,batch_px_leakage:0,batch_px_hp_dp:.6,batch_px_lp_dp:.6,batch_booster_pump_eff:.82,batch_booster_motor_eff:.96,batch_booster_vfd_eff:.97,batch_booster_no_vfd:false,batch_refill_dp:1.5,batch_refill_pump_eff:.80,batch_refill_motor_eff:.94,batch_reference_ro_sec:'',
      batch_stop_on_saturation:false,batch_saturation_limit_pct:100,fouling_factor:1,salt_passage_factor:1,generated_from_base_plant:false
    };

    const hostSections=sections;
    sections=function(values=null){
      if(mode==='batch_ro'){
        const mem=['RO membrane condition',{fouling_factor:{...operating.fouling_factor},salt_passage_factor:{...operating.salt_passage_factor}}];
        return [['Batch cycle & productivity',batchProcess],['Batch liquid inventory & recirculation',inventory],mem,stageMembraneSection(1,false,values),['Pumps, PX & pretreatment',batchEnergy],['Batch chemistry envelope',batchChemistry]];
      }
      return hostSections(values);
    };

    function batchModeAccess(){
      if(!processModeConfigured('multistage',modeStates.multistage||{}))return {ok:false,reason:'Complete the Plant Design inputs first.'};
      if(!basePlantIsCurrent())return {ok:false,reason:'Calculate the current Plant Design before opening Batch RO.'};
      return {ok:true};
    }
    window.TotalROBatchRO={version:ADDON_VERSION,batchModeAccess};

    function ensureBatchWorkspaceFromBase(){
      const base=modeStates.multistage||{},result=caseResults.multistage;if(!basePlantIsCurrent()||!result)return;
      const sig=base._last_calculated_signature;if(modeStates.batch_ro?.generated_from_base_plant&&modeStates.batch_ro?._base_plant_signature===sig)return;
      const n=Math.max(1,Math.min(4,Number(base.stage_count||1))),epv=Math.max(1,Math.min(8,Number(base.elements_per_vessel_1||8)));
      let totalElements=0;for(let i=1;i<=n;i++)totalElements+=Math.max(0,Number(base[`vessels_${i}`]||0))*Math.max(0,Number(base[`elements_per_vessel_${i}`]||0));
      const vessels=Math.max(1,Math.ceil(totalElements/epv)),q=Number(result.product_flow||base.target_product_flow||0),rr=100*Number(result.recovery||0);
      modeStates.batch_ro={...defaults.batch_ro,membrane_1:base.membrane_1||defaultMembrane,vessels_1:vessels,elements_per_vessel_1:epv,membrane_design_mode_1:base.membrane_design_mode_1,membrane_recipe_1:base.membrane_recipe_1,permeate_pressure_1:base.permeate_pressure_1??0,batch_average_product_flow:q>0?q:'',batch_target_recovery:rr>1&&rr<97?rr:defaults.batch_ro.batch_target_recovery,batch_reference_ro_sec:Number(result.ro_sec||0)>0?Number(result.ro_sec):'',suction_pressure:base.suction_pressure??2,pretreatment_discharge_pressure:base.pretreatment_discharge_pressure??6,pretreatment_recovery:base.pretreatment_recovery??.85,pretreatment_pump_eff:base.pretreatment_pump_eff??.82,pretreatment_motor_eff:base.pretreatment_motor_eff??.95,pretreatment_vfd_eff:base.pretreatment_vfd_eff??.97,pretreatment_no_vfd:base.pretreatment_no_vfd??false,pump_eff:base.pump_eff??.85,motor_eff:base.motor_eff??.97,vfd_eff:base.vfd_eff??.97,pump_no_vfd:base.pump_no_vfd??false,fouling_factor:base.fouling_factor??1,salt_passage_factor:base.salt_passage_factor??1,generated_from_base_plant:true,_base_plant_signature:sig,_base_design_seed:deepClone(caseBaseSeed()),_inherited_from:`Plant Design · Case ${activeCase}`};
      syncActiveCaseStore();
    }

    function updateBatchNavAccess(){
      document.querySelectorAll('[data-mode="batch_ro"]').forEach(btn=>{const a=batchModeAccess();btn.disabled=!a.ok;btn.classList.toggle('erd-locked',!a.ok);btn.title=a.ok?'Fully-batch RO system design':a.reason;});
    }

    function injectNavigation(){
      if(document.querySelector('[data-batch-ro-addon-nav]'))return;
      const plant=document.querySelector('[data-mode="multistage"]');if(!plant)return;
      const anchor=document.querySelector('[data-mode="ccro"]')||plant;
      const button=document.createElement('button');button.className=plant.className;button.dataset.mode='batch_ro';button.dataset.batchRoAddonNav='1';button.disabled=true;button.title='Calculate Plant Design before opening Batch RO';
      button.innerHTML='<span class="nav-icon"><img src="/static/addons/batch_ro/batch_ro.svg" alt=""></span><span>Batch RO Design</span><b class="nav-detail">Fully batch RO · variable-pressure cycle</b>';
      anchor.insertAdjacentElement('afterend',button);
    }

    const hostProcessConfigured=processModeConfigured;
    processModeConfigured=function(tech,s){
      if(tech==='batch_ro')return !!s&&Number(s.batch_target_recovery)>0&&Number(s.vessels_1)>0&&Number(s.elements_per_vessel_1)>0&&(Number(s.batch_average_product_flow)>0||Number(s.batch_operating_flux_lmh)>0);
      return hostProcessConfigured(tech,s);
    };

    const hostPersist=persistActiveCase;
    persistActiveCase=function(){
      if(mode==='batch_ro'&&document.querySelector('#calcForm [name]')){
        const captured=capture(),previous=modeStates.batch_ro||{},workflowMeta={};
        Object.entries(previous).forEach(([k,v])=>{if(k.startsWith('_')||['generated_from_base_plant','batch_reference_ro_sec'].includes(k))workflowMeta[k]=v;});
        modeStates.batch_ro={...captured,...workflowMeta};syncActiveCaseStore();return;
      }
      return hostPersist();
    };

    const hostInvalidate=invalidateDerivedResultsFromBasePlant;
    invalidateDerivedResultsFromBasePlant=function(){hostInvalidate();if(modeStates.batch_ro?.generated_from_base_plant)caseResults.batch_ro=undefined;syncActiveCaseStore();};
    const hostApplyTier=applyTierEntitlements;applyTierEntitlements=function(){hostApplyTier();updateBatchNavAccess();};
    const hostWorkflow=updateWorkflowGates;updateWorkflowGates=function(){hostWorkflow();updateBatchNavAccess();};
    const hostChrome=updateWorkspaceChrome;updateWorkspaceChrome=function(){hostChrome();updateBatchNavAccess();};
    const hostRenderFields=renderFields;renderFields=function(values=defaults[mode]){hostRenderFields(values);if(mode==='batch_ro'){const ml=$('#modeLabel'),sh=$('.solve-hint');if(ml)ml.textContent=`Batch RO · Case ${activeCase}`;setPrimaryLabel('Calculate Batch RO cycle');if(sh)sh.textContent='Fully-batch transient inventory · pressure and chemistry are re-solved through the productive cycle.';}};
    const hostChangeMode=changeMode;changeMode=function(newMode){if(newMode==='batch_ro'){const a=batchModeAccess();if(!a.ok){showCalcError(new Error(a.reason),'input');updateBatchNavAccess();return;}ensureBatchWorkspaceFromBase();}return hostChangeMode(newMode);};

    const hostWarnings=showWarnings;
    showWarnings=function(r){
      hostWarnings(r);if(mode!=='batch_ro'||!Array.isArray(r?.batch_ro_warnings)||!r.batch_ro_warnings.length)return;
      const h=$('#warnings');if(!h)return;const extra=r.batch_ro_warnings.map(w=>`<div class="warning dynamic-note"><div class="warning-head"><strong>Batch RO engineering review</strong></div><div class="warning-text">${escapeHtml(w)}</div></div>`).join('');h.insertAdjacentHTML('afterbegin',extra);
    };
    const hostShow=show;show=function(r){hostShow(r);updateBatchNavAccess();};

    if(!comparisonOrder.some(([k])=>k==='batch_ro'))comparisonOrder.splice(1,0,['batch_ro','Batch RO']);

    const hostWaterStreams=waterStreamsForResult;
    waterStreamsForResult=function(c,r){
      if(!r?.batch_ro)return hostWaterStreams(c,r);
      const sourceFeed=Object.fromEntries(summarySpecies.map(([k])=>[k,Number(c.waterProfile?.['ion_'+k]||0)]));
      return {feed:sourceFeed,conc:r.batch_ro_final_bulk_composition_mg_l||null,perm:r.batch_ro_composite_permeate_composition_mg_l||null};
    };
    const hostChemBasis=resultChemistryBasis;
    resultChemistryBasis=function(r,stream){
      if(!r?.batch_ro)return hostChemBasis(r,stream);const key=String(stream||'');
      if(key==='feed')return {comp:waterStreamsForResult({waterProfile},r).feed,ph:Number(waterProfile.feed_ph),alk:Number(waterProfile.ion_bicarbonate||0)};
      if(key==='concentrate')return {comp:r.batch_ro_final_bulk_composition_mg_l,ph:Number(r.batch_ro_final_bulk_ph??waterProfile.feed_ph),alk:null};
      if(key==='permeate')return {comp:r.batch_ro_composite_permeate_composition_mg_l,ph:Number(r.batch_ro_composite_permeate_ph??7),alk:null};
      return hostChemBasis(r,stream);
    };

    function profileRows(r){
      const p=Array.isArray(r?.batch_ro_cycle_profile)?r.batch_ro_cycle_profile:[];
      return p.map(x=>{const sat=Number(x.highest_mineral_saturation_pct),satText=Number.isFinite(sat)?`${fmt(sat,1)}%${x.limiting_mineral?` · ${escapeHtml(x.limiting_mineral)}`:''}`:'—';return `<tr><td>${fmt(x.step,0)}</td><td>${fmt(x.time_min,2)}</td><td>${fmt(100*x.recovery,2)}%</td><td>${fmt(x.tank_volume_m3,3)}</td><td>${fmt(x.feed_tds_mg_l,0)}</td><td>${fmt(x.feed_osmotic_bar,2)}</td><td>${fmt(x.feed_pressure_bar,2)}</td><td>${fmt(x.ndp_bar,2)}</td><td>${fmt(x.flux_lmh,2)}</td><td>${fmt(100*x.per_pass_recovery,2)}%</td><td>${fmt(x.permeate_tds_mg_l,1)}</td><td>${fmt(x.polarization_factor,2)}</td><td class="${Number.isFinite(sat)&&sat>=100?'scaling-attention':''}">${satText}</td><td>${fmt(x.hpp_kw,1)}</td><td>${fmt(x.recirculation_kw,1)}</td><td>${fmt(x.booster_kw,1)}</td></tr>`}).join('');
    }

    function batchPerformanceReport(r){
      const rows=profileRows(r),sat=Number(r.batch_ro_highest_mineral_saturation_pct),hasSat=Number.isFinite(sat),saving=Number(r.batch_ro_energy_saving_vs_reference_pct),hasSaving=Number.isFinite(saving);
      const onset=Number(r.batch_ro_first_scaling_onset_recovery),hasOnset=r.batch_ro_first_scaling_onset_recovery!==null&&r.batch_ro_first_scaling_onset_recovery!==undefined&&Number.isFinite(onset);
      const onsetText=hasOnset?`${fmt(100*onset,2)}% recovery · ${escapeHtml(r.batch_ro_first_scaling_onset_mineral||'limiting mineral')}`:'No configured saturation onset';
      return `<div class="kpi-strip five"><div><span>Achieved recovery</span><strong>${fmt(r.batch_ro_achieved_recovery_pct,2)}%</strong></div><div><span>Total SEC</span><strong>${fmt(r.total_sec,3)} kWh/m³</strong></div><div><span>Peak pressure</span><strong>${fmt(r.batch_ro_peak_pressure_bar,2)} bar</strong></div><div><span>Active / effective flux</span><strong>${fmt(r.batch_ro_active_flux_lmh,1)} / ${fmt(r.batch_ro_effective_flux_lmh,1)} LMH</strong></div><div><span>Composite permeate TDS</span><strong>${fmt(r.batch_ro_composite_permeate_tds_mg_l,1)} mg/L</strong></div></div>
      <section class="report-section"><div class="chart-title-row"><h3>BATCH SYSTEM & LIMITING CONDITION</h3><span>${escapeHtml(r.batch_configuration_label||'Batch RO')}</span></div><div class="plant-summary-three"><article><span>Recovery limiter</span><strong>${escapeHtml(r.batch_ro_recovery_limiter||'Engineering review')}</strong><small>${escapeHtml(r.batch_ro_recovery_limiter_detail||'')}</small></article><article><span>Pressure envelope</span><strong>${fmt(r.batch_ro_pressure_utilization_pct,1)}% utilized</strong><small>${fmt(r.batch_ro_peak_pressure_bar,2)} of ${fmt(r.batch_ro_pressure_limit_bar,2)} bar · minimum NDP ${fmt(r.batch_ro_minimum_ndp_bar,2)} bar</small></article><article><span>Mineral saturation screen</span><strong>${hasSat?`${fmt(sat,1)}% · ${escapeHtml(r.batch_ro_limiting_mineral||'limiting mineral')}`:'Full-ion chemistry required'}</strong><small>${onsetText}</small></article></div></section>
      <section class="report-section"><div class="chart-title-row"><h3>BATCH INVENTORY & DUTY CYCLE</h3><span>Productive + reset cycle</span></div><div class="plant-summary-three"><article><span>Starting inventory / tank</span><strong>${fmt(r.batch_ro_initial_inventory_m3,3)} / ${fmt(r.batch_ro_initial_tank_volume_m3,3)} m³</strong><small>Membrane channels ${fmt(r.batch_ro_membrane_channel_volume_m3,3)} m³ · piping/dead ${fmt(r.batch_ro_piping_external_volume_m3,3)} m³</small></article><article><span>Permeate / final brine per cycle</span><strong>${fmt(r.batch_ro_permeate_volume_per_cycle_m3,3)} / ${fmt(r.batch_ro_final_brine_inventory_m3,3)} m³</strong><small>End tank heel ${fmt(r.batch_ro_final_tank_volume_m3,3)} m³ · external ${fmt(r.batch_ro_external_volume_pct_elements,1)}% of channel volume</small></article><article><span>Productive / reset / total time</span><strong>${fmt(r.batch_ro_productive_time_s,1)} / ${fmt(r.batch_ro_effective_reset_downtime_s,1)} / ${fmt(r.batch_ro_cycle_time_s,1)} s</strong><small>Duty factor ${fmt(100*r.batch_ro_duty_factor,1)}% · average product ${fmt(r.batch_ro_average_product_flow_m3h,2)} m³/h</small></article></div></section>
      <section class="report-section"><div class="chart-title-row"><h3>TRANSIENT BATCH PROFILE</h3><span>Converged membrane states over recovery</span></div><div class="table-wrap"><table class="fedco-table"><thead><tr><th>Step</th><th>Time<br><span>min</span></th><th>Recovery</th><th>Tank<br><span>m³</span></th><th>Feed TDS<br><span>mg/L</span></th><th>Feed π<br><span>bar</span></th><th>Feed P<br><span>bar</span></th><th>NDP<br><span>bar</span></th><th>Flux<br><span>LMH</span></th><th>Pass RR</th><th>Perm. TDS<br><span>mg/L</span></th><th>CP</th><th>Max mineral saturation</th><th>HPP<br><span>kW</span></th><th>Recirc<br><span>kW</span></th><th>PX boost<br><span>kW</span></th></tr></thead><tbody>${rows}</tbody></table></div></section>
      <section class="report-section"><h3>BATCH RO ENERGY</h3><div class="plant-summary-three"><article><span>RO / pretreatment / total SEC</span><strong>${fmt(r.ro_sec,3)} / ${fmt(r.pretreatment_sec,3)} / ${fmt(r.total_sec,3)} kWh/m³</strong><small>${hasSaving?`${fmt(saving,1)}% RO-energy change vs entered conventional reference`: 'Enter conventional RO reference SEC for a direct saving comparison'}</small></article><article><span>HPP / recirculation cycle energy</span><strong>${fmt(r.batch_ro_hpp_energy_kwh_cycle,3)} / ${fmt(r.batch_ro_circulation_energy_kwh_cycle,3)} kWh</strong><small>PX booster ${fmt(r.batch_ro_px_booster_energy_kwh_cycle,3)} kWh · refill ${fmt(r.batch_ro_refill_energy_kwh_cycle,3)} kWh</small></article><article><span>Cycle salt balance residual</span><strong>${fmt(r.batch_ro_salt_balance_residual_pct,4)}%</strong><small>${escapeHtml(r.batch_ro_model_basis||'')}</small></article></div><p class="micro-note">${escapeHtml(r.batch_ro_model_limitations||'')}</p></section>`;
    }

    const hostPerformance=processPerformanceBody;
    processPerformanceBody=function(r){if(mode==='batch_ro')return solveStatus(r)+showMembraneHeader(r)+batchPerformanceReport(r)+stageReport(r)+fluxProfileChart(r)+polarizationProfileChart(r)+osmoticProfileChart(r)+membraneChecks(r);return hostPerformance(r);};

    const hostOpenProject=openImportedProject;
    openImportedProject=function(p,serverRecord=null){if(p?.active_mode!=='batch_ro')return hostOpenProject(p,serverRecord);const clone=deepClone(p);clone.active_mode='multistage';hostOpenProject(clone,serverRecord);if(basePlantIsCurrent())changeMode('batch_ro');};

    injectNavigation();applyTierEntitlements();updateBatchNavAccess();
    console.info(`Total RO Design Batch RO add-on v${ADDON_VERSION} activated.`);
  }

  try{register()}catch(err){console.error('Batch RO add-on activation failed:',err);}
})();
