(()=>{
  'use strict';

  const fmt=(x,d=2)=>Number.isFinite(Number(x))?Number(x).toLocaleString(undefined,{maximumFractionDigits:d,minimumFractionDigits:0}):'—';
  const pct=x=>`${fmt(Number(x)*100,1)}%`;
  const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  let initialized=false;
  let config={};

  function apiReady(){return Boolean(window.TotalBioMbrEquipment&&window.TotalBioDesignUI);}
  function getApi(){return window.TotalBioMbrEquipment;}
  function savedConfig(){return window.TotalBioDesignUI?.getMbrEquipmentConfig?.()||{};}
  function saveConfig(){window.TotalBioDesignUI?.setMbrEquipmentConfig?.(config);}

  function field(key,label,{type='number',step='any',min='',max='',unit='',note='',options=null,wide=false}={}){
    const value=config[key];
    let control;
    if(options){
      control=`<select data-mbr-key="${esc(key)}">${options.map(([v,t])=>`<option value="${esc(v)}"${String(value)===String(v)?' selected':''}>${esc(t)}</option>`).join('')}</select>`;
    }else{
      control=`<input data-mbr-key="${esc(key)}" type="${type}" step="${esc(step)}"${min!==''?` min="${esc(min)}"`:''}${max!==''?` max="${esc(max)}"`:''} value="${esc(value)}" />`;
    }
    return `<div class="mbr-eq-field${wide?' wide':''}"><label>${esc(label)}${unit?` · ${esc(unit)}`:''}</label>${control}${note?`<small>${esc(note)}</small>`:''}</div>`;
  }

  function activeUnit(){return window.TotalBioDesignUI?.getActiveUnit?.()||null;}

  function auditedMbrPageActive(){
    return [...document.querySelectorAll('#nav button.active,#nav .nav-item.active')]
      .some(button=>/Membrane Bioreactor/i.test(button.textContent||''));
  }

  function isMbrContext(){
    const unit=activeUnit();
    const activeMbr=unit&&['mbr','anmbr'].includes(String(unit.type||'').toLowerCase());
    return Boolean(activeMbr||auditedMbrPageActive());
  }

  function ensureJumpButton(main){
    const unit=activeUnit();
    const activeMbr=unit&&['mbr','anmbr'].includes(String(unit.type||'').toLowerCase());
    const existing=document.getElementById('mbrEquipmentUnitBtn');
    if(!activeMbr){existing?.remove();return;}
    const title=main.querySelector('.active-unit-context .section-title');
    if(!title)return;
    if(existing&&title.contains(existing))return;
    existing?.remove();
    const btn=document.createElement('button');
    btn.type='button';
    btn.id='mbrEquipmentUnitBtn';
    btn.className='action secondary mbr-equipment-launch';
    btn.textContent='Equipment & Mechanical Design ↓';
    btn.title='Jump to the augmented equipment and mechanical design for this MBR unit';
    btn.addEventListener('click',open);
    title.appendChild(btn);
  }

  function ensureMbrAugmentation(){
    document.getElementById('mbrEquipmentBtn')?.remove();
    document.getElementById('mbrEquipmentDialog')?.remove();
    const main=document.getElementById('main');
    const existing=document.getElementById('mbrEquipmentInline');
    if(!main||!isMbrContext()){
      existing?.remove();
      document.getElementById('mbrEquipmentUnitBtn')?.remove();
      return;
    }
    ensureJumpButton(main);
    if(existing&&main.contains(existing))return;
    existing?.remove();
    config=getApi().normalizeConfig({...getApi().defaults(),...savedConfig()});
    const section=document.createElement('section');
    section.id='mbrEquipmentInline';
    section.className='section-card mbr-equipment-inline';
    section.innerHTML=`
      <div class="section-title mbr-equipment-inline-title">
        <span>MBR Equipment & Mechanical Design</span>
        <span class="mbr-eq-badge">Augmented design layer</span>
      </div>
      <div class="mbr-equipment-inline-intro">
        <strong>Extends the audited MBR process model.</strong>
        <span>The original MBR biological and membrane-process inputs/results above remain unchanged. This section adds net-flux availability, membrane trains/racks, blowers, pumps, backwash, cleaning and pretreatment constraints using the solved project basis.</span>
      </div>
      <div class="mbr-eq-body" id="mbrEqBody"></div>`;
    main.appendChild(section);
    const host=section.querySelector('#mbrEqBody');
    renderInputs(host);
    renderResults(host.querySelector('#mbrEqResults'));
  }

  function readControls(host){
    host.querySelectorAll('[data-mbr-key]').forEach(el=>{
      const key=el.dataset.mbrKey;
      if(el.type==='checkbox')config[key]=el.checked;
      else if(el.tagName==='SELECT')config[key]=el.value;
      else config[key]=el.value===''?'':Number(el.value);
    });
    config=getApi().normalizeConfig(config);
    saveConfig();
  }

  function sizing(){
    let network=window.TotalBioDesignUI?.getLastNetwork?.();
    if(!network){
      try{network=window.TotalBioDesignUI?.recalculate?.();}catch(_){ }
    }
    return getApi().size({snapshot:window.TotalBioDesignUI?.getProjectSnapshot?.()||{},network:network||{},config});
  }

  function checkbox(key,label,note=''){
    return `<div class="mbr-eq-field wide"><label><input data-mbr-key="${esc(key)}" type="checkbox"${config[key]?' checked':''} /> ${esc(label)}</label>${note?`<small>${esc(note)}</small>`:''}</div>`;
  }

  function renderInputs(host){
    host.innerHTML=`
      <div class="mbr-eq-banner"><strong>Engineering basis</strong>The biological/process-network solver remains unchanged. This layer converts solved project flows and loads into planning equipment duties. Membrane supplier limits, final module selection, CIP compatibility and guaranteed flux must be replaced with current project/vendor data before design release.</div>
      <div id="mbrEqResults"></div>
      <details class="mbr-eq-input-details" open><summary>Equipment sizing inputs & vendor assumptions</summary>
      <section class="mbr-eq-section"><h3>Membrane train & hydraulic availability</h3><div class="mbr-eq-grid">
        ${field('membraneConfiguration','Membrane configuration',{options:[['HF','Hollow fibre (HF)'],['FS','Flat sheet (FS)']]})}
        ${field('grossFluxLMH','Gross operating flux',{unit:'LMH',min:1,note:'Historical planning default; not a vendor guarantee.'})}
        ${field('peakGrossFluxLMH','Peak gross flux',{unit:'LMH',min:1})}
        ${field('installedTrains','Installed membrane trains',{step:1,min:2,note:'Used for train-offline availability.'})}
        ${field('moduleAreaM2','Membrane area / module',{unit:'m²',min:1,note:'Generic planning value until a current product is selected.'})}
        ${field('modulesPerRack','Modules / rack',{step:1,min:1})}
        ${field('screenOpeningMm','Selected fine-screen opening',{unit:'mm',min:0.1})}
        ${field('redundancyMode','Redundancy',{options:[['N+1 train during peak/cleaning','N+1 train during peak / cleaning'],['No train redundancy','No train redundancy']]})}
        ${field('filtrationMinutes','Filtration period',{unit:'min',min:0.1})}
        ${field('relaxationMinutes','Relaxation period',{unit:'min',min:0})}
        ${checkbox('backwashEnabled','Use permeate backwash','HF systems commonly use backwash; FS is normally relaxation-based.')}
        ${field('backwashMinutes','Backwash duration',{unit:'min',min:0})}
        ${field('backwashFluxRatio','Backwash / operating flux ratio',{unit:'×',min:0})}
        ${field('simultaneousBackwashes','Simultaneous backwashes',{step:1,min:1})}
        ${field('backwashTankMarginPct','Backwash tank working-volume margin',{unit:'%',min:0,note:'TWDS planning allowance, not from the book.'})}
      </div></section>
      <section class="mbr-eq-section"><h3>Aeration & blower basis</h3><div class="mbr-eq-grid">
        ${field('mlssGL','MLSS',{unit:'g/L',min:0.1})}
        ${field('biomassYieldKgVssKgBod','Biomass yield used for O₂ planning',{unit:'kg VSS/kg BOD',min:0})}
        ${field('denitrifiedNkgD','Denitrified-N oxygen credit',{unit:'kg N/d',min:0,note:'Enter solved/project denitrification when available; default is zero (conservative).'})}
        ${field('alphaMode','α-factor method',{options:[['Gunder 2001 MLSS correlation','Literature MLSS correlation'],['Manual alpha','Manual α-factor']]})}
        ${field('alphaManual','Manual α-factor',{min:0.05,max:1})}
        ${field('cleanOtePerM','Clean-water OTE per metre',{unit:'fraction/m',min:0.001})}
        ${field('diffuserSubmergenceM','Diffuser submergence',{unit:'m',min:0.1})}
        ${field('beta','β-factor',{min:0.05,max:1.2})}
        ${field('theta','Temperature correction θ',{min:1,max:1.08})}
        ${field('membraneSadMNm3Hm2','Membrane SADm',{unit:'Nm³/(h·m²)',min:0,note:'Historical planning value; replace with current supplier requirement.'})}
        ${field('membraneAerationFraction','Average membrane aeration fraction',{unit:'0–1',min:0,max:1})}
        ${field('biologicalAirHeaderPressureKPaG','Biological blower discharge',{unit:'kPa(g)',min:1})}
        ${field('membraneAirHeaderPressureKPaG','Membrane blower discharge',{unit:'kPa(g)',min:1})}
        ${field('blowerEfficiency','Blower efficiency',{unit:'0–1',min:0.2,max:0.95})}
        ${field('ambientTemperatureC','Blower inlet temperature',{unit:'°C'})}
        ${field('atmosphericPressureKPa','Atmospheric pressure',{unit:'kPa abs',min:50})}
      </div></section>
      <section class="mbr-eq-section"><h3>Pumps</h3><div class="mbr-eq-grid">
        ${field('permeatePumpHeadM','Permeate pump TDH',{unit:'m',min:0})}
        ${field('backwashPumpHeadM','Backwash pump TDH',{unit:'m',min:0})}
        ${field('recyclePumpHeadM','Internal recycle pump TDH',{unit:'m',min:0})}
        ${field('pumpEfficiency','Pump efficiency',{unit:'0–1',min:0.2,max:0.95})}
        ${field('motorDesignMarginPct','Motor design margin',{unit:'%',min:0,note:'TWDS planning allowance; final motor selection belongs to equipment/vendor design.'})}
      </div></section>
      <section class="mbr-eq-section"><h3>Membrane maintenance & chemical-cleaning basis</h3><div class="mbr-eq-grid">
        ${field('maintenanceCleanIntervalDays','Maintenance clean interval',{unit:'d',min:0.1})}
        ${field('maintenanceCleanMinutes','Maintenance clean duration',{unit:'min',min:0})}
        ${field('maintenanceCleaningFluxLMH','Maintenance cleaning flux',{unit:'LMH',min:0.1})}
        ${field('maintenanceNaOClMgL','Maintenance NaOCl',{unit:'mg/L',min:0})}
        ${field('recoveryCleanIntervalDays','Recovery clean interval',{unit:'d',min:1})}
        ${field('recoveryCleanHours','Recovery clean duration',{unit:'h',min:0})}
        ${field('recoveryCleaningFluxLMH','Recovery cleaning flux',{unit:'LMH',min:0.1})}
        ${field('recoveryNaOClWtPct','Recovery NaOCl',{unit:'wt%',min:0})}
        ${field('recoveryCitricWtPct','Recovery citric acid',{unit:'wt%',min:0})}
      </div></section>
      </details>
      <div class="mbr-eq-actions"><button type="button" class="twds-button twds-button--quiet" id="mbrEqDefaults">Reset literature planning defaults</button><button type="button" class="twds-button twds-button--secondary" id="mbrEqTop">Back to MBR process model ↑</button></div>`;

    host.querySelectorAll('[data-mbr-key]').forEach(el=>el.addEventListener('change',()=>{readControls(host);renderResults(host.querySelector('#mbrEqResults'));}));
    host.querySelector('#mbrEqDefaults').onclick=()=>{config=getApi().defaults();saveConfig();renderInputs(host);renderResults(host.querySelector('#mbrEqResults'));};
    host.querySelector('#mbrEqTop').onclick=()=>document.querySelector('#main .page-head')?.scrollIntoView({behavior:'smooth',block:'start'});
  }

  function dl(rows){return `<dl>${rows.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join('')}</dl>`;}

  function renderResults(host){
    const r=sizing();
    const m=r.membrane,a=r.aeration,p=r.pumps,bw=r.backwash,cl=r.cleaning,s=r.pretreatment.screen;
    host.innerHTML=`
      <div class="mbr-eq-kpis">
        <div class="mbr-eq-kpi"><span>Installed membrane area</span><strong>${fmt(m.installedAreaM2,0)}</strong><small>m²</small></div>
        <div class="mbr-eq-kpi"><span>Normal net flux</span><strong>${fmt(m.normalNetFluxLMH,1)}</strong><small>LMH</small></div>
        <div class="mbr-eq-kpi"><span>Modules</span><strong>${fmt(m.totalModules,0)}</strong><small>${m.installedTrains} trains</small></div>
        <div class="mbr-eq-kpi"><span>Biological air</span><strong>${fmt(a.biologicalAirNm3h,0)}</strong><small>Nm³/h</small></div>
        <div class="mbr-eq-kpi"><span>Membrane air</span><strong>${fmt(a.membraneAirNm3h,0)}</strong><small>Nm³/h</small></div>
      </div>
      <div class="mbr-eq-results">
        <section class="mbr-eq-card"><h3>Membrane trains</h3>${dl([
          ['Average flow basis',`${fmt(r.basis.avgFlowM3d,0)} m³/d`],['Peak hydraulic basis',`${fmt(r.basis.peakFlowM3d,0)} m³/d`],['Chemical availability',pct(m.chemicalAvailability)],['Average area required',`${fmt(m.averageRequiredAreaM2,0)} m²`],['Peak area required',`${fmt(m.peakRequiredAreaM2,0)} m²`],['Installed trains',fmt(m.installedTrains,0)],['Racks / train',fmt(m.racksPerTrain,0)],['Modules / train',fmt(m.modulesPerTrain,0)],['Total racks',fmt(m.totalRacks,0)],['One-train-offline peak flux',`${fmt(m.oneTrainOfflinePeakFluxLMH,1)} LMH · ${m.n1Pass?'PASS':'REVIEW'}`]
        ])}</section>
        <section class="mbr-eq-card"><h3>Pumps & backwash</h3>${dl([
          ['Permeate pump duty',`${fmt(p.permeate.flowM3h,1)} m³/h @ ${fmt(p.permeate.headM,1)} m`],['Permeate motor design duty',`${fmt(p.permeate.motorDesignKw,1)} kW`],['Backwash pump duty',bw.enabled?`${fmt(p.backwash.flowM3h,1)} m³/h @ ${fmt(p.backwash.headM,1)} m`:'Not used'],['Backwash motor design duty',bw.enabled?`${fmt(p.backwash.motorDesignKw,1)} kW`:'—'],['Backwash event volume',bw.enabled?`${fmt(bw.eventVolumeM3,2)} m³`:'—'],['Backwash tank working volume',bw.enabled?`${fmt(bw.tankWorkingVolumeM3,2)} m³`:'—'],['Internal recycle',`${fmt(p.recycle.flowM3h,1)} m³/h · ${fmt(p.recycle.ratio,2)}× Q`],['Recycle motor design duty',`${fmt(p.recycle.motorDesignKw,1)} kW`]
        ])}</section>
        <section class="mbr-eq-card"><h3>Aeration & blowers</h3>${dl([
          ['Planning O₂ demand',`${fmt(a.oxygenDemand.oxygenKgD,0)} kg O₂/d`],['BOD removed',`${fmt(a.oxygenDemand.bodRemovedKgD,0)} kg/d`],['NH₄-N oxidized',`${fmt(a.oxygenDemand.nitrifiedNkgD,0)} kg N/d`],['α-factor',fmt(a.transfer.alpha,3)],['Calculated field OTE',pct(a.transfer.fieldOte)],['Biological blower flow',`${fmt(a.biologicalAirNm3h,0)} Nm³/h`],['Biological motor design duty',`${fmt(a.biologicalBlowerMotorDesignKw,1)} kW`],['Membrane scour flow',`${fmt(a.membraneAirNm3h,0)} Nm³/h`],['Membrane motor design duty',`${fmt(a.membraneBlowerMotorDesignKw,1)} kW`]
        ])}</section>
        <section class="mbr-eq-card"><h3>Cleaning & pretreatment</h3>${dl([
          ['Fine-screen planning range',`${fmt(s.recommendedMinMm,1)}–${fmt(s.recommendedMaxMm,1)} mm (${config.membraneConfiguration})`],['Selected screen opening',`${fmt(s.selectedMm,2)} mm · ${s.passes?'PASS':'REVIEW'}`],['Maintenance clean solution',`${fmt(cl.maintenanceSolutionM3,1)} m³/event`],['Maintenance NaOCl',`${fmt(cl.maintenanceNaOClKg,1)} kg/event`],['Recovery clean solution',`${fmt(cl.recoverySolutionM3,1)} m³/event`],['Recovery NaOCl',`${fmt(cl.recoveryNaOClKg,1)} kg/event`],['Recovery citric acid',`${fmt(cl.recoveryCitricKg,1)} kg/event`]
        ])}</section>
      </div>
      <section class="mbr-eq-section"><h3>Warnings & constraints</h3><div class="mbr-eq-guidance">
        ${r.warnings.map(x=>`<div class="mbr-eq-note warning"><strong>Warning</strong> · ${esc(x)}</div>`).join('')}
        ${r.reviews.map(x=>`<div class="mbr-eq-note review"><strong>Review</strong> · ${esc(x)}</div>`).join('')}
        ${!r.warnings.length?'<div class="mbr-eq-note info"><strong>Information</strong> · No blocking equipment-sizing warning was generated for the current planning basis.</div>':''}
      </div></section>
      <div class="mbr-eq-source"><strong>Reference basis:</strong> Simon Judd, <em>The MBR Book: Principles and Applications of Membrane Bioreactors in Water and Wastewater Treatment</em>, Elsevier, 2006 — especially Sections 2.2.5, 2.3.7–2.3.9, Chapter 3 design calculations, and Appendices A–D. Historical commercial-product values are not treated as current vendor guarantees.</div>`;
  }

  function open(){
    ensureMbrAugmentation();
    document.getElementById('mbrEquipmentInline')?.scrollIntoView({behavior:'smooth',block:'start'});
  }

  function init(){
    if(initialized||!apiReady())return false;
    initialized=true;ensureMbrAugmentation();
    new MutationObserver(ensureMbrAugmentation).observe(document.body,{childList:true,subtree:true});
    return true;
  }

  if(!init()){
    let attempts=0;const timer=setInterval(()=>{attempts++;if(init()||attempts>100)clearInterval(timer);},50);
  }
})();