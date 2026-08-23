(async function(){
  const model = await fetch('model.json').then(r=>r.json());
  const engine = new WorkbookEngine(model);
  const main = document.getElementById('main');
  const nav = document.getElementById('nav');
  const calcDot = document.getElementById('calcDot');
  const calcState = document.getElementById('calcState');
  let current='MarketIntake';
  let projectName='Untitled Biological Design';
  const M3D_TO_GPD=264.1720523581484;
  const APP_VERSION='0.2.3';
  const SUITE_HOSTED=window.location.pathname.startsWith('/apps/bio/');
  let suiteCsrfToken='';
  let suiteAccount=null;
  let serverProjectRecord=null;
  let projectLibraryCache=[];

  // --------------------------------------------------------
  // TOTAL BIO DESIGN TIER PREVIEW / FEATURE ENTITLEMENTS
  // --------------------------------------------------------

  const BIO_TIER_ORDER=Object.freeze({
    entry:0,
    silver:1,
    gold:2,
    platinum:3
  });

  let bioEffectiveTier='platinum';

  function normalizeBioTier(value,fallback='entry'){
    const tier=String(value||'').trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(BIO_TIER_ORDER,tier)
      ? tier
      : fallback;
  }

  function bioTierTitle(tier){
    const t=normalizeBioTier(tier,'entry');
    return t.charAt(0).toUpperCase()+t.slice(1);
  }

  function bioTierAllows(minimum){
    return BIO_TIER_ORDER[bioEffectiveTier] >=
           BIO_TIER_ORDER[normalizeBioTier(minimum,'entry')];
  }

  function bioModuleMeta(id){
    try{
      for(const [group,items] of modules){
        for(const item of items){
          if(String(item[0])===String(id)){
            return {
              group:String(group||''),
              id:String(item[0]||''),
              badge:String(item[1]||''),
              name:String(item[2]||'')
            };
          }
        }
      }
    }catch(_){}
    return {
      group:'',
      id:String(id||''),
      badge:'',
      name:String(id||'')
    };
  }

  function bioModuleMinimumTier(group,id,name){
    const g=String(group||'').toLowerCase();
    const key=String(id||'').toLowerCase();
    const label=String(name||'').toLowerCase();

    // Entry-level project workflow.
    if(
      ['marketintake','dashboard','massbalance','compactreport'].includes(key) ||
      g.includes('project inputs') ||
      label.includes('client / rfq') ||
      label.includes('design dashboard') ||
      label.includes('process mass balance') ||
      label.includes('compact design report') ||
      label.includes('reference') ||
      label.includes('readme')
    ){
      return 'entry';
    }

    // Detailed biological-process engineering.
    if(
      g.includes('engineering design') ||
      g.includes('suspended growth') ||
      label.includes('fractionation') ||
      label.includes('kinetics') ||
      label.includes('stoichiometry') ||
      label.includes('activated sludge') ||
      label.includes('nitrification') ||
      label.includes('denitrification') ||
      label.includes('bnr') ||
      label.includes('ebpr') ||
      label.includes('phosphorus')
    ){
      return 'silver';
    }

    // Advanced process-train / residuals / alternative reactor design.
    if(
      g.includes('alternative') ||
      g.includes('attached') ||
      g.includes('residual') ||
      g.includes('sludge') ||
      g.includes('dewatering') ||
      label.includes('membrane bioreactor') ||
      label.includes('mbbr') ||
      label.includes('ifas') ||
      label.includes('dewatering') ||
      label.includes('residual')
    ){
      return 'gold';
    }

    // Optimization / scenario capability.
    if(
      g.includes('optimization') ||
      g.includes('scenario') ||
      label.includes('optimization') ||
      label.includes('scenario')
    ){
      return 'platinum';
    }

    // Unknown specialist modules default to Gold rather than accidentally
    // exposing an advanced module in Entry/Silver.
    return 'gold';
  }

  function bioModuleAccess(id){
    const meta=bioModuleMeta(id);

    // Internal detail pages inherit their parent advanced capability.
    let minimum=bioModuleMinimumTier(
      meta.group,
      meta.id,
      meta.name
    );

    if(
      ['unitoperationdetail','residualsnetwork','sludgeunitdetail']
        .includes(String(id||'').toLowerCase())
    ){
      minimum='gold';
    }

    return {
      ...meta,
      minimum,
      allowed:bioTierAllows(minimum)
    };
  }

  function applyBioTierToolbar(){
    const revision=document.getElementById('revisionBtn');
    if(revision){
      revision.hidden=!(
        SUITE_HOSTED &&
        serverProjectRecord?.id &&
        bioTierAllows('silver')
      );
      revision.title=bioTierAllows('silver')
        ? 'Create a new project revision'
        : 'Silver tier or higher';
    }

    const send=document.getElementById('sendToROBtn');
    if(send){
      send.hidden=!SUITE_HOSTED;
      send.disabled=!bioTierAllows('silver');
      send.title=bioTierAllows('silver')
        ? 'Create a linked Total RO Design project'
        : 'Silver tier or higher';
    }
  }

  function renderAdminBioTierPreview(){
    const host=document.getElementById('adminTierPreview');
    if(!host)return;

    const isAdmin=Boolean(suiteAccount?.is_admin);

    host.hidden=!(
      SUITE_HOSTED &&
      isAdmin
    );

    if(!isAdmin)return;

    const status=document.getElementById('adminTierPreviewStatus');
    if(status){
      status.textContent=`Viewing as ${bioTierTitle(bioEffectiveTier)}`;
    }

    host.querySelectorAll('[data-bio-tier-preview]').forEach(button=>{
      const tier=normalizeBioTier(
        button.dataset.bioTierPreview,
        'entry'
      );

      button.classList.toggle(
        'active',
        tier===bioEffectiveTier
      );

      button.setAttribute(
        'aria-pressed',
        tier===bioEffectiveTier?'true':'false'
      );
    });
  }

  function applyBioTierPreview(tier,{persist=true}={}){
    bioEffectiveTier=normalizeBioTier(tier,'platinum');

    if(
      persist &&
      SUITE_HOSTED &&
      suiteAccount?.is_admin
    ){
      sessionStorage.setItem(
        'totalbiodesign-admin-tier-preview',
        bioEffectiveTier
      );
    }

    const access=bioModuleAccess(current);

    if(!access.allowed){
      current='MarketIntake';
      activeUnitId=null;
      activeSludgeUnit=null;
    }

    document.documentElement.dataset.bioTier=bioEffectiveTier;
    document.body.dataset.bioTier=bioEffectiveTier;

    renderAdminBioTierPreview();
    renderNav();
    applyBioTierToolbar();
    render();
  }

  function configureBioTierPreview(){
    if(!SUITE_HOSTED)return;

    if(suiteAccount?.is_admin){
      const remembered=sessionStorage.getItem(
        'totalbiodesign-admin-tier-preview'
      );

      bioEffectiveTier=normalizeBioTier(
        remembered,
        'platinum'
      );
    }else{
      // Bio remains admin-preview/in-development at present.
      // Customer entitlement resolution can replace this when Bio
      // is opened to normal accounts.
      bioEffectiveTier='platinum';
    }

    document.documentElement.dataset.bioTier=bioEffectiveTier;
    document.body.dataset.bioTier=bioEffectiveTier;

    renderAdminBioTierPreview();
    applyBioTierToolbar();
  }

  const TOTAL_RO_DESIGN_TYPES=new Set(['nanofiltration','reverse_osmosis']);
  const marketDefaults=()=>({
    unitSystem:'US',
    client:'', location:'', consultant:'', permittingState:'',
    avgFlowM3d:Number(engine.get('DesignBasis','C6'))||0,
    peakHourlyEqM3d:Number(engine.get('DesignBasis','C11'))||0,
    designFlowM3d:Number(engine.get('DesignBasis','C6'))||0,
    calculationFlowBasis:'Average daily flow',
    wasteType:'100% domestic waste', kitchenWaste:'No', foodPrescreenGrease:'Yes',
    influentBOD:Number(engine.get('DesignBasis','C27'))||0,
    influentCOD:Number(engine.get('DesignBasis','C25'))||0,
    influentTSS:Number(engine.get('DesignBasis','C28'))||0,
    influentAmmonia:Number(engine.get('DesignBasis','C31'))||0,
    influentTKN:Number(engine.get('DesignBasis','C30'))||0,
    influentFOG:'', pH:Number(engine.get('DesignBasis','C19'))||7,
    tempC:Number(engine.get('DesignBasis','C16'))||20,
    effluentBOD:Number(engine.get('DesignBasis','C61'))||0,
    effluentCOD:'', effluentTSS:Number(engine.get('DesignBasis','C62'))||0,
    effluentAmmonia:Number(engine.get('DesignBasis','C63'))||0,
    effluentTN:Number(engine.get('DesignBasis','C64'))||0,
    effluentTP:Number(engine.get('DesignBasis','C65'))||0,
    effluentFOG:'',
    operatingPattern:'24/7 continuous', hoursPerDay:24, daysPerWeek:7,
    redundancy:'One package plant (1 × 100%)',
    voltage:'460V-3Ph-60Hz', screeningRequired:'Yes', manualBarRack:'Yes',
    dischargeType:'Direct discharge permit', installation:'Above grade', cathodicProtection:'No',
    tertiarySandFilters:'No', grating:'Yes', handrails:'Yes', insulated:'No',
    disinfection:'UV', uvRedundancy:'Duty + 100% redundant UV bank',
    disinfectionLimit:'200 FC/100 mL — 30-day geometric mean',
    sludgeHolding:'Yes', material:'Painted A-36 carbon steel'
  });
  let market=marketDefaults();
  const planningDefaults=Object.freeze({...market});
  let bypassedMandatory={};

  const mandatoryFieldSpecs=[
    {key:'avgFlowM3d',label:'Average daily flow',section:'Project & Flow Basis',kind:'flow'},
    {key:'peakHourlyEqM3d',label:'Peak hourly flow',section:'Project & Flow Basis',kind:'flow'},
    {key:'designFlowM3d',label:'Design flow',section:'Project & Flow Basis',kind:'flow'},
    {key:'wasteType',label:'Type of waste',section:'Wastewater Type & Influent',kind:'text'},
    {key:'influentBOD',label:'Influent BOD₅',section:'Wastewater Type & Influent',kind:'number'},
    {key:'influentCOD',label:'Influent COD',section:'Wastewater Type & Influent',kind:'number'},
    {key:'influentTSS',label:'Influent TSS',section:'Wastewater Type & Influent',kind:'number'},
    {key:'influentAmmonia',label:'Influent ammonia-N',section:'Wastewater Type & Influent',kind:'number'},
    {key:'influentTKN',label:'Influent TKN',section:'Wastewater Type & Influent',kind:'number'},
    {key:'pH',label:'Wastewater pH',section:'Wastewater Type & Influent',kind:'number'},
    {key:'tempC',label:'Wastewater design temperature',section:'Wastewater Type & Influent',kind:'number'},
    {key:'effluentBOD',label:'Required effluent BOD₅',section:'Required Effluent',kind:'number',target:true},
    {key:'effluentTSS',label:'Required effluent TSS',section:'Required Effluent',kind:'number',target:true},
    {key:'effluentAmmonia',label:'Required effluent ammonia-N',section:'Required Effluent',kind:'number',target:true},
    {key:'effluentTN',label:'Required effluent total nitrogen',section:'Required Effluent',kind:'number',target:true},
    {key:'effluentTP',label:'Required effluent total phosphorus',section:'Required Effluent',kind:'number',target:true},
    {key:'dischargeType',label:'Discharge basis',section:'Required Effluent',kind:'text'}
  ];
  const mandatoryFieldMap=new Map(mandatoryFieldSpecs.map(x=>[x.key,x]));
  const effluentTargetKeys=new Set(mandatoryFieldSpecs.filter(x=>x.target).map(x=>x.key));
  function valueMissingForSpec(spec,value){
    if(value===null||value===undefined)return true;
    if(typeof value==='string'&&value.trim()==='')return true;
    if(spec.kind==='flow')return !Number.isFinite(Number(value))||Number(value)<=0;
    if(spec.kind==='number')return !Number.isFinite(Number(value));
    return false;
  }
  function mandatoryFallback(spec){
    if(spec.key==='designFlowM3d'){
      const q=Number(market.avgFlowM3d);
      if(Number.isFinite(q)&&q>0)return q;
    }
    if(spec.key==='peakHourlyEqM3d'){
      const q=Number(market.designFlowM3d)||Number(market.avgFlowM3d);
      if(Number.isFinite(q)&&q>0){
        const baseQ=Number(planningDefaults.designFlowM3d)||Number(planningDefaults.avgFlowM3d)||1;
        const basePeak=Number(planningDefaults.peakHourlyEqM3d)||baseQ*2.2;
        return q*(basePeak/baseQ);
      }
    }
    return planningDefaults[spec.key];
  }
  function effectiveMarketValue(key){
    const spec=mandatoryFieldMap.get(key),actual=market[key];
    if(!spec||!valueMissingForSpec(spec,actual))return actual;
    return bypassedMandatory[key]?bypassedMandatory[key].value:actual;
  }
  function mandatoryInputStatus(){
    const missing=[],bypassed=[],provided=[];
    for(const spec of mandatoryFieldSpecs){
      if(!valueMissingForSpec(spec,market[spec.key]))provided.push(spec);
      else if(bypassedMandatory[spec.key])bypassed.push(spec);
      else missing.push(spec);
    }
    return {missing,bypassed,provided,total:mandatoryFieldSpecs.length,pct:Math.round((provided.length+bypassed.length)/mandatoryFieldSpecs.length*100)};
  }
  function clearResolvedBypass(key){
    const spec=mandatoryFieldMap.get(key);
    if(spec&&!valueMissingForSpec(spec,market[key]))delete bypassedMandatory[key];
  }

  const unitCatalog=Array.isArray(window.TotalBioUnitCatalog)?window.TotalBioUnitCatalog:[];
  const processNetwork=window.TotalBioProcessNetwork;
  const complianceAdvisor=window.TotalBioComplianceAdvisor;
  if(!unitCatalog.length) throw new Error('Unit-operation catalog failed to load.');
  if(!processNetwork) throw new Error('Sequential process-network solver failed to load.');
  if(!complianceAdvisor) throw new Error('Effluent compliance advisor failed to load.');
  let unitSeq=0,sludgeUnitSeq=0,recycleSeq=0,sludgeLineSeq=0;
  function newId(prefix,seq){return `${prefix}${Date.now().toString(36)}${seq.toString(36)}`;}
  function unitDef(type){return unitCatalog.find(u=>u.type===type)||{type,name:'Legacy / Custom Unit Operation',tag:'User-defined duty',tab:'UnitOperationDetail',badge:'+',group:'Other',keywords:''};}
  function unitSearchText(u){
    const aliases=[];
    if(u.group==='Phosphorus Removal') aliases.push('phosphorus phosphate phosphorous phophate p removal nutrient removal');
    if(u.type==='daf') aliases.push('daf flotation pretreatment fats oils grease fog algae solids');
    if(u.type==='daf_secondary') aliases.push('daf flotation secondary biomass separation algae solids');
    if(u.type==='sludge_equalization') aliases.push('sludge blending buffer common dewatering equalisation equalization');
    return `${u.name} ${u.tag} ${u.group} ${u.keywords||''} ${aliases.join(' ')}`.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'');
  }
  function makeUnit(type){const d=unitDef(type);return {id:newId('u',++unitSeq),type,stage:1,name:d.name,tag:d.tag,tab:d.tab,config:processNetwork.defaultConfig(type)};}
  function makeSludgeUnit(type){const d=unitDef(type);return {id:newId('su',++sludgeUnitSeq),type,name:d.name,tag:d.tag,config:processNetwork.sludgeDefaultConfig(type)};}
  function defaultTrain(){return ['ebpr','denit','cas','secondary'].map(makeUnit);}
  let treatmentTrain=defaultTrain();
    function defaultRecycles(){
    const internalSource=treatmentTrain.find(u=>['cas','extended_aeration','mbr','mbbr_ifas','mbbr_nit','baf','mabr'].includes(u.type));
    const internalTarget=treatmentTrain.find(u=>['denit','pre_anoxic','ebpr','bio_p_ao','a2o','vip_bnr'].includes(u.type))||treatmentTrain[0];
    const solidsSource=[...treatmentTrain].reverse().find(u=>['secondary','lamella_secondary','daf_secondary','mbr','anmbr'].includes(u.type));
    const solidsTarget=treatmentTrain.find(u=>['ebpr','bio_p_ao','a2o','vip_bnr','denit','pre_anoxic','cas','extended_aeration'].includes(u.type))||treatmentTrain[0];
    const defaults=[];
    if(internalSource&&internalTarget&&internalSource.id!==internalTarget.id){
      defaults.push({
        id:newId('r',++recycleSeq),
        name:'Internal mixed-liquor recycle',
        sourceUnitId:internalSource.id,
        targetUnitId:internalTarget.id,
        sourcePort:'liquid',
        basis:'ratio',
        value:3,
        enabled:true
      });
    }
    if(solidsSource&&solidsTarget&&solidsSource.id!==solidsTarget.id){
      defaults.push({
        id:newId('r',++recycleSeq),
        name:'Return activated sludge (RAS)',
        sourceUnitId:solidsSource.id,
        targetUnitId:solidsTarget.id,
        sourcePort:'sludge',
        basis:'source_fraction',
        value:90,
        enabled:true
      });
    }
    return defaults;
  }

    function defaultSludgeLines(){
    // Residual routing is intentionally explicit. The software identifies all
    // available sludge-producing water units, but the user decides which
    // source feeds each common or parallel residuals line and at what split.
    return [{
      id:newId('sl',++sludgeLineSeq),
      name:'Common Sludge Line',
      sources:[],
      returnEnabled:true,
      returnFraction:1,
      returnTargetUnitId:treatmentTrain[0]?.id||'',
      units:['sludge_equalization','sludge_thickening','centrifuge'].map(makeSludgeUnit)
    }];
  }

  let recycles=defaultRecycles();
  let sludgeStrategy='common';
  let sludgeLines=defaultSludgeLines();
  let activeUnitId=null;
  let activeSludgeUnit=null;
  let lastNetworkResult=null;
  function hydrateWaterUnit(raw){
    const unit=raw&&typeof raw==='object'?raw:{};const d=unitDef(unit.type);
    unit.id=unit.id||newId('u',++unitSeq);unit.name=unit.name||d.name;unit.tag=unit.tag||d.tag;unit.tab=d.tab;unit.stage=Number(unit.stage)||1;
    unit.config={...processNetwork.defaultConfig(unit.type),...(unit.config||{})};return unit;
  }
  function hydrateSludgeUnit(raw){
    const unit=raw&&typeof raw==='object'?raw:{};const d=unitDef(unit.type);
    unit.id=unit.id||newId('su',++sludgeUnitSeq);unit.name=unit.name||d.name;unit.tag=unit.tag||d.tag;
    unit.config={...processNetwork.sludgeDefaultConfig(unit.type),...(unit.config||{})};return unit;
  }
  function normalizeTrainStages(){const counts={};treatmentTrain.forEach(u=>{counts[u.type]=(counts[u.type]||0)+1;u.stage=counts[u.type];});}
  function sanitizeNetwork(){
    // Hydrate in place so UI event handlers keep valid references even when a
    // live recalculation runs between opening a dialog and applying changes.
    treatmentTrain=(treatmentTrain||[]).filter(u=>!TOTAL_RO_DESIGN_TYPES.has(u?.type)).map(hydrateWaterUnit);
    normalizeTrainStages();
    const ids=new Set(treatmentTrain.map(u=>u.id));
    recycles=(recycles||[])
      .filter(r=>r&&ids.has(r.sourceUnitId)&&ids.has(r.targetUnitId)&&r.sourceUnitId!==r.targetUnitId)
      .map(r=>{
        r.id=r.id||newId('r',++recycleSeq);r.enabled=r.enabled!==false;
        r.sourcePort=['liquid','sludge','residual'].includes(r.sourcePort)?r.sourcePort:'liquid';
        let basisValue=r.basis;let value=Math.max(0,Number(r.value)||0);
        if(basisValue==='sourceFraction'){basisValue='source_fraction';if(value>0&&value<=1)value*=100;}
        r.basis=['fixed','source_fraction'].includes(basisValue)?basisValue:'ratio';r.value=value;
        return r;
      });
    sludgeLines=(sludgeLines||[]).map(raw=>{
      const line=raw&&typeof raw==='object'?raw:{};
      line.id=line.id||newId('sl',++sludgeLineSeq);line.name=line.name||'Sludge Line';
      line.sources=(line.sources||[]).filter(x=>x&&ids.has(x.unitId)).map(x=>{x.fraction=Math.max(0,Math.min(1,Number(x.fraction)||0));return x;});
      line.returnEnabled=line.returnEnabled!==false;
      line.returnFraction=Math.max(0,Math.min(1,Number.isFinite(Number(line.returnFraction))?Number(line.returnFraction):1));
      line.returnTargetUnitId=ids.has(line.returnTargetUnitId)?line.returnTargetUnitId:(treatmentTrain[0]?.id||'');
      line.units=(line.units||[]).map(hydrateSludgeUnit);
      return line;
    });
    if(!sludgeLines.length)sludgeLines=defaultSludgeLines();
  }

  function syncTrainToWorkbook(){
    const hasFlag=flag=>treatmentTrain.some(u=>(unitDef(u.type).flags||[]).includes(flag));
    engine.set('TrainConfig','C21',hasFlag('ebpr')?1:0);
    engine.set('TrainConfig','C22',hasFlag('denit')?1:0);
    engine.set('TrainConfig','C23',hasFlag('cas')?1:0);
    engine.set('TrainConfig','C24',hasFlag('mbr')?1:0);
    engine.set('TrainConfig','C25',hasFlag('mbbr')?1:0);
    engine.set('TrainConfig','C26',hasFlag('uasb')?1:0);
    engine.set('TrainConfig','C27',hasFlag('anammox')?1:0);
    engine.set('TrainConfig','C28',hasFlag('secondary')?1:0);
    engine.set('TrainConfig','C29',hasFlag('chemP')?1:0);
  }
  function influentStream(){
    return processNetwork.makeStream(Number(v('DesignBasis','C6'))||0,{cod:Number(v('DesignBasis','C25'))||0,bod:Number(v('DesignBasis','C27'))||0,tss:Number(v('DesignBasis','C28'))||0,vss:Number(v('DesignBasis','C29'))||0,tkn:Number(v('DesignBasis','C30'))||0,nh4:Number(v('DesignBasis','C31'))||0,nox:Number(v('DesignBasis','C32'))||0,tp:Number(v('DesignBasis','C33'))||0,po4:Number(v('DesignBasis','C34'))||0,fog:Number(market.influentFOG)||0,alk:Number(v('DesignBasis','C35'))||0},{temperatureC:Number(v('DesignBasis','C16'))||20,pH:Number(v('DesignBasis','C19'))||7,label:'Plant influent'});
  }
  function calculateNetwork(){sanitizeNetwork();syncTrainToWorkbook();lastNetworkResult=processNetwork.solveIntegratedNetwork({influent:influentStream(),units:treatmentTrain,recycles,sludgeLines},{maxIterations:400,maxOuterIterations:35,tolerance:1e-5,outerTolerance:1e-4,relaxation:0.8});return lastNetworkResult;}
  function saveNetwork(){sanitizeNetwork();syncTrainToWorkbook();persistAutosave();lastNetworkResult=null;}
  function removeWaterUnit(id){treatmentTrain=treatmentTrain.filter(u=>u.id!==id);recycles=recycles.filter(r=>r.sourceUnitId!==id&&r.targetUnitId!==id);for(const line of sludgeLines){line.sources=(line.sources||[]).filter(s=>s.unitId!==id);if(line.returnTargetUnitId===id)line.returnTargetUnitId=treatmentTrain[0]?.id||'';}saveNetwork();}


  const modules=[
    ['Project Inputs',[['MarketIntake','IN','Client / RFQ Inputs'],['Dashboard','DB','Design Dashboard'],['MassBalance','MB','Process Mass Balance'],['CompactReport','RP','Compact Design Report']]],
    ['Engineering Design',[['DesignBasis','DB','Detailed Design Basis'],['Fractionation','FR','COD / N / P Fractionation'],['Kinetics','KN','Kinetics & Stoichiometry']]],
    ['Suspended Growth',[['CAS','AS','Activated Sludge (CAS)'],['Nitrification','NI','Nitrification'],['Denitrification','DN','Denitrification'],['BNR_WRC','WR','BNR WRC Cross-Check'],['EBPR','EP','EBPR / P Removal']]],
    ['Alternative Bioreactors',[['MBR','MB','Membrane Bioreactor'],['MBBR_IFAS','IF','MBBR / IFAS'],['UASB_EGSB','AN','UASB / EGSB'],['Anammox','AM','Anammox PN/A']]],
    ['Utilities & Handover',[['Aeration','O₂','Aeration'],['ResidualsNetwork','RN','Residuals Network'],['Sludge','SL','Workbook Sludge Basis'],['TrainConfig','TR','Train Configuration'],['Summary','Σ','Design Summary'],['References','RF','References'],['README','?','Guide & Scope']]]
  ];

  const optionMap={
    'Denitrification!C6':['MLE (pre-anoxic)','4-stage Bardenpho','Post-anoxic only','Step-feed'],
    'Denitrification!C66':['Methanol','Ethanol','Acetic acid','Glycerol','Proprietary blend'],
    'EBPR!C48':['Ferric chloride 40 %','Ferric sulphate 42 %','Ferrous sulphate hepta.','Alum 48 %','PACl 10 % Al₂O₃'],
    'MBR!C23':['Hollow fibre, submerged','Flat sheet, submerged','Multi-tube sidestream'],
    'MBBR_IFAS!C15':['AnoxKaldnes K1','AnoxKaldnes K3','AnoxKaldnes K5','BiofilmChip M','AnoxKaldnes Z-400','Generic saddle/wheel'],
    'UASB_EGSB!C13':['UASB','EGSB','IC (internal circulation)','Anaerobic contact'],
    'Anammox!C6':['Sidestream (dewatering liquor)','Mainstream','Industrial high-strength'],
    'Anammox!C34':['Granular, single-stage (DEMON-type SBR)','Granular, single-stage (continuous UASB-type)','MBBR / IFAS, single-stage','Two-stage (SHARON + anammox)','Mainstream, MBBR or granular'],
    'Aeration!C6':['CAS','MBR','MBBR'],
    'Aeration!C67':['A — Mid-depth pressure only','B — ASCE / M&E arithmetic (off-gas corrected)','C — Log-mean driving force'],
    'Sludge!C6':['Yes','No'],
    'Sludge!C17':['Gravity belt thickener','Rotary drum','Dissolved air flotation','Gravity thickener'],
    'Sludge!C27':['Yes','No'],
    'Sludge!C43':['Centrifuge','Belt filter press','Screw press','Filter press']
  };

  function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function addrRow(a){const m=String(a).match(/\d+/);return m?Number(m[0]):0;}
  function c(sheet,addr){return model.sheets[sheet]?.cells?.[addr]||{};}
  function v(sheet,addr){return engine.get(sheet,addr);}
  function label(sheet,row){return c(sheet,`A${row}`).value??'';}
  function symbol(sheet,row){return c(sheet,`B${row}`).value??'';}
  function unit(sheet,row){return c(sheet,`D${row}`).value??'';}
  function basis(sheet,row){return c(sheet,`E${row}`).value??'';}
  function formatValue(x,u=''){
    if(x===null||x===undefined||x==='') return '—';
    if(typeof x==='string') return x;
    if(typeof x!=='number'||!Number.isFinite(x)) return 'Calculation error';
    const a=Math.abs(x);
    let d= a>=1000?0 : a>=100?1 : a>=10?2 : a>=1?3 : a>=0.01?4 : 6;
    if(u.includes('%') && Number.isInteger(x)) d=1;
    return x.toLocaleString(undefined,{minimumFractionDigits:0,maximumFractionDigits:d});
  }
  function toast(msg){const t=document.getElementById('toast');t.className='toast-show';t.textContent=msg;setTimeout(()=>{t.className='';t.textContent='';},2200);}
  function mandatoryFallbackDisplay(spec,value){
    if(spec.kind==='flow'){
      const shown=market.unitSystem==='US'?Number(value)*M3D_TO_GPD:Number(value);
      return `${formatValue(shown,marketUnit('flow'))} ${marketUnit('flow')}`;
    }
    if(spec.key==='tempC'){
      const shown=market.unitSystem==='US'?Number(value)*9/5+32:Number(value);
      return `${formatValue(shown,marketUnit('temp'))} ${marketUnit('temp')}`;
    }
    if(spec.key==='pH')return formatValue(Number(value),'');
    if(spec.kind==='number')return `${formatValue(Number(value),'mg/L')} mg/L`;
    return String(value??'Planning default');
  }
  function applyMandatoryBypass(specs){
    const at=new Date().toISOString();
    for(const spec of specs){
      const value=mandatoryFallback(spec);
      bypassedMandatory[spec.key]={value,at,target:!!spec.target,label:spec.label};
    }
    syncMarketToEngine();lastNetworkResult=null;persistAutosave();
  }
  function showMandatoryDialog(specs,onContinue,destination='the requested calculation'){
    const issues=(specs||[]).filter(Boolean);
    if(!issues.length){onContinue?.();return;}
    let modal=document.getElementById('mandatoryInputModal');
    if(!modal){modal=document.createElement('div');modal.id='mandatoryInputModal';modal.className='mandatory-modal hidden';document.body.appendChild(modal);}
    const rows=issues.map(spec=>{
      const fallback=mandatoryFallback(spec),note=spec.target
        ?`Compliance will remain unassessed. ${mandatoryFallbackDisplay(spec,fallback)} will be used only as a planning value in workbook sizing.`
        :`${mandatoryFallbackDisplay(spec,fallback)} will be used as an explicit planning assumption.`;
      return `<div class="mandatory-review-row"><div><b>${esc(spec.label)}</b><span>${esc(spec.section)}</span></div><p>${esc(note)}</p></div>`;
    }).join('');
    modal.innerHTML=`<div class="mandatory-dialog" role="dialog" aria-modal="true" aria-labelledby="mandatoryTitle"><div class="mandatory-dialog-head"><div><span class="eyebrow">INPUT REVIEW</span><h2 id="mandatoryTitle">Mandatory project information is missing</h2><p>${issues.length} required field${issues.length===1?' is':'s are'} blank. Complete the information or explicitly bypass it before opening ${esc(destination)}.</p></div><button type="button" id="mandatoryClose" aria-label="Close">×</button></div><div class="mandatory-dialog-body"><div class="mandatory-explainer"><b>Bypass behavior</b><span>The software records each bypass. Planning defaults keep the calculation running, while a missing effluent limit is shown as unassessed rather than falsely reported as compliant.</span></div><div class="mandatory-review-list">${rows}</div></div><div class="mandatory-dialog-actions"><button type="button" class="action secondary" id="mandatoryCancel">Cancel</button><button type="button" class="action secondary" id="mandatoryInputs">Return to Inputs</button><button type="button" class="action primary-action" id="mandatoryBypass">Bypass missing values & continue</button></div></div>`;
    modal.classList.remove('hidden');document.body.classList.add('mandatory-modal-open');
    const close=()=>{modal.classList.add('hidden');document.body.classList.remove('mandatory-modal-open');document.removeEventListener('keydown',onKey);};
    const onKey=e=>{if(e.key==='Escape')close();};document.addEventListener('keydown',onKey);
    modal.querySelector('#mandatoryClose').onclick=close;modal.querySelector('#mandatoryCancel').onclick=close;
    modal.querySelector('#mandatoryInputs').onclick=()=>{close();current='MarketIntake';activeUnitId=null;activeSludgeUnit=null;renderNav();renderMarketIntake();};
    modal.querySelector('#mandatoryBypass').onclick=()=>{applyMandatoryBypass(issues);close();onContinue?.();toast(`${issues.length} missing value${issues.length===1?'':'s'} bypassed with recorded planning assumptions`);};
    modal.onclick=e=>{if(e.target===modal)close();};
    setTimeout(()=>modal.querySelector('#mandatoryBypass')?.focus(),0);
  }
  const mandatoryValidationPages=new Set(['Dashboard','MassBalance','CompactReport','Summary','ResidualsNetwork','UnitOperationDetail','SludgeUnitDetail']);
  function navigateTo(id,afterRender=null){
    const access=bioModuleAccess(id);

    if(!access.allowed){
      alert(
        `${access.name||'This Total Bio Design feature'} requires the `+
        `${bioTierTitle(access.minimum)} tier or higher.\n\n`+
        `Administrator preview is currently set to `+
        `${bioTierTitle(bioEffectiveTier)}.`
      );
      return;
    }

    const go=()=>{
      current=id;
      activeUnitId=null;
      activeSludgeUnit=null;
      renderNav();
      render();
      applyBioTierToolbar();

      if(typeof afterRender==='function'){
        setTimeout(afterRender,80);
      }
    };

    const status=mandatoryInputStatus();

    if(
      mandatoryValidationPages.has(id) &&
      status.missing.length
    ){
      showMandatoryDialog(
        status.missing,
        go,
        id==='CompactReport'
          ? 'the compact report'
          : 'the design results'
      );
    }else{
      go();
    }
  }
  function updateCalcState(){
    ['C28','C38','C56','C57'].forEach(a=>engine.get('Summary',a));
    const inputs=mandatoryInputStatus();
    const net=lastNetworkResult;
    if(inputs.missing.length){calcDot.className='status-dot warn';calcState.textContent=`${inputs.missing.length} mandatory input${inputs.missing.length===1?'':'s'} missing`;}
    else if(engine.errors.length){calcDot.className='status-dot bad';calcState.textContent=`${engine.errors.length} calculation issue${engine.errors.length===1?'':'s'}`;}
    else if(!net){calcDot.className='status-dot warn';calcState.textContent='Recalculate';}
    else if(!net.converged||!net.water.converged){calcDot.className='status-dot warn';calcState.textContent='Process network needs review';}
    else if(inputs.bypassed.length){calcDot.className='status-dot warn';calcState.textContent=`${inputs.bypassed.length} bypassed planning assumption${inputs.bypassed.length===1?'':'s'}`;}
    else{calcDot.className='status-dot ok';calcState.textContent='Converged';}
  }

  function renderNav(){
    nav.innerHTML='';

    for(const [group,items] of modules){
      const g=document.createElement('div');
      g.className='nav-group';
      g.textContent=group;
      nav.appendChild(g);

      for(const [id,badge,name] of items){
        const access=bioModuleAccess(id);

        const b=document.createElement('button');

        b.className=
          'nav-item'+
          (current===id?' active':'')+
          (!access.allowed?' tier-locked':'');

        b.innerHTML=
          `<span class="nav-badge">${esc(badge)}</span>`+
          `<span>${esc(name)}</span>`+
          (!access.allowed
            ? `<span class="tier-lock">${bioTierTitle(access.minimum)}</span>`
            : '');

        b.title=!access.allowed
          ? `${name} requires the ${bioTierTitle(access.minimum)} tier or higher.`
          : '';

        b.onclick=()=>navigateTo(id);

        nav.appendChild(b);
      }
    }
  }
  function makeSelect(sheet,addr,val,opts){
    const sel=document.createElement('select');sel.className='input-control';
    const all=opts.includes(String(val))?opts:[String(val),...opts];
    all.forEach(o=>{const op=document.createElement('option');op.value=o;op.textContent=o;if(String(val)===o)op.selected=true;sel.appendChild(op);});
    sel.onchange=()=>commitInput(sheet,addr,sel.value);return sel;
  }
  function makeInput(sheet,addr,val){
    const key=`${sheet}!${addr}`;
    if(optionMap[key]) return makeSelect(sheet,addr,val,optionMap[key]);
    if(sheet==='TrainConfig' && addrRow(addr)>=21 && addrRow(addr)<=29){
      const lab=document.createElement('label');lab.className='toggle';const ch=document.createElement('input');ch.type='checkbox';ch.checked=Number(val)!==0;
      const sp=document.createElement('span');lab.append(ch,sp);ch.onchange=()=>commitInput(sheet,addr,ch.checked?1:0);return lab;
    }
    const inp=document.createElement('input');inp.className='input-control';
    if(typeof val==='number'){inp.type='number';inp.step='any';inp.value=Number.isFinite(val)?String(val):'';inp.onchange=()=>commitInput(sheet,addr,Number(inp.value));}
    else{inp.type='text';inp.value=String(val??'');inp.onchange=()=>commitInput(sheet,addr,inp.value);}
    return inp;
  }
  function commitInput(sheet,addr,val){
    engine.set(sheet,addr,val);
    if(sheet==='DesignBasis'){
      const keyByAddr={C16:'tempC',C19:'pH',C25:'influentCOD',C27:'influentBOD',C28:'influentTSS',C30:'influentTKN',C31:'influentAmmonia',C61:'effluentBOD',C62:'effluentTSS',C63:'effluentAmmonia',C64:'effluentTN',C65:'effluentTP'};
      if(addr==='C6'){
        const flowKey=market.calculationFlowBasis==='Design flow'?'designFlowM3d':'avgFlowM3d';market[flowKey]=val;clearResolvedBypass(flowKey);
      }else if(addr==='C8'){
        market.peakHourlyEqM3d=(Number(engine.get('DesignBasis','C6'))||0)*(Number(val)||0);clearResolvedBypass('peakHourlyEqM3d');
      }else if(keyByAddr[addr]){
        market[keyByAddr[addr]]=val;clearResolvedBypass(keyByAddr[addr]);
      }
    }
    lastNetworkResult=null;persistAutosave();
    updateCalcState();render();
  }
  function rowHtml(sheet,row){
    const cc=c(sheet,`C${row}`), role=cc.role||'';
    if(!(role==='input'||cc.formula||role==='key'||role==='linked')) return null;
    const tr=document.createElement('tr');
    const name=label(sheet,row)||`Row ${row}`;
    tr.innerHTML=`<td class="pname"><div class="param-label">${esc(name)}</div>${role==='input'?'<div class="subnote">Editable design input</div>':''}</td><td class="symbol">${esc(symbol(sheet,row)||'—')}</td><td class="valuecell"></td><td class="unit">${esc(unit(sheet,row)||'')}</td><td class="basis">${esc(basis(sheet,row)||'')}</td>`;
    const cell=tr.children[2];
    if(role==='input'){const wrap=document.createElement('div');wrap.className='input-wrap';wrap.appendChild(makeInput(sheet,`C${row}`,engine.getInputValue(sheet,`C${row}`)));cell.appendChild(wrap);}
    else{const r=document.createElement('div');r.className='result'+(role==='key'?' key':role==='linked'?' linked':'');r.textContent=formatValue(v(sheet,`C${row}`),unit(sheet,row));cell.appendChild(r);}
    return tr;
  }
  function sectionCandidates(sheet){
    const rows={}; const cells=model.sheets[sheet].cells;
    for(const a of Object.keys(cells)){const r=addrRow(a);if(!rows[r])rows[r]=[];rows[r].push(a);}
    return Object.keys(rows).map(Number).sort((a,b)=>a-b);
  }
  function isSection(sheet,row){
    const a=label(sheet,row), b=c(sheet,`B${row}`).value, cc=c(sheet,`C${row}`).value, d=c(sheet,`D${row}`).value;
    return typeof a==='string' && a.trim() && !b && (cc===null||cc===undefined||cc==='') && !d && (/^\d/.test(a.trim()) || /^[A-Z][A-Z0-9 &/()–—-]{5,}$/.test(a.trim()));
  }
  function renderSheet(sheet){
    engine.errors=[];
    const title=c(sheet,'A1').value||sheet; const sub=c(sheet,'A2').value||'';
    main.innerHTML=`<div class="page-head"><div class="page-title"><h1>${esc(title)}</h1><p>${esc(sub)}</p><div class="sheet-stats"><span class="chip input-chip">Yellow = input</span><span class="chip key-chip">Blue = key result</span><span class="chip">Live-linked calculation</span></div></div><div class="head-tag">SI units · Steady state</div></div>`;
    const selected=treatmentTrain.find(u=>u.id===activeUnitId);const selectedDef=selected?unitDef(selected.type):null;
    if(selected&&selectedDef?.tab===sheet)main.insertAdjacentHTML('beforeend',activeUnitPanelHtml(selected,calculateNetwork(),true));
    if(sheet==='README'||sheet==='References'){renderTextPage(sheet);if(selected&&selectedDef?.tab===sheet)bindActiveUnitPanel(selected);updateCalcState();return;}
    const rows=sectionCandidates(sheet); let currentCard=null,currentTable=null,any=false;
    for(const row of rows){
      if(row<=2)continue;
      if(isSection(sheet,row)){
        currentCard=document.createElement('section');currentCard.className='section-card';currentCard.innerHTML=`<div class="section-title">${esc(label(sheet,row))}</div>`;
        currentTable=document.createElement('table');currentTable.className='param-table';currentCard.appendChild(currentTable);main.appendChild(currentCard);continue;
      }
      const tr=rowHtml(sheet,row); if(!tr)continue;
      any=true;
      if(!currentTable){currentCard=document.createElement('section');currentCard.className='section-card';currentCard.innerHTML='<div class="section-title">Design Parameters</div>';currentTable=document.createElement('table');currentTable.className='param-table';currentCard.appendChild(currentTable);main.appendChild(currentCard);}
      currentTable.appendChild(tr);
    }
    if(!any)main.insertAdjacentHTML('beforeend','<div class="empty">No editable or calculated rows on this page.</div>');
    if(selected&&selectedDef?.tab===sheet)bindActiveUnitPanel(selected);
    updateCalcState();
  }

  function renderTextPage(sheet){
    const box=document.createElement('div');box.className='text-page';
    const rows=sectionCandidates(sheet);
    for(const r of rows){if(r<=2)continue;const a=c(sheet,`A${r}`).value,b=c(sheet,`B${r}`).value,cc=c(sheet,`C${r}`).value,d=c(sheet,`D${r}`).value,e=c(sheet,`E${r}`).value;
      if(a===null||a===undefined||a==='')continue;
      if(isSection(sheet,r)) box.insertAdjacentHTML('beforeend',`<h3>${esc(a)}</h3>`);
      else if(sheet==='References') box.insertAdjacentHTML('beforeend',`<div class="ref-row"><b>${esc(a)}</b>${b?` — ${esc(b)}`:''}${cc?` — ${esc(cc)}`:''}${d?` — ${esc(d)}`:''}${e?`<div class="subnote">${esc(e)}</div>`:''}</div>`);
      else box.insertAdjacentHTML('beforeend',`<p><b>${esc(a)}</b>${b?` — ${esc(b)}`:''}</p>`);
    }
    main.appendChild(box);
  }
  function marketUnit(kind){
    if(kind==='flow') return market.unitSystem==='US'?'gal/d':'m³/d';
    if(kind==='temp') return market.unitSystem==='US'?'°F':'°C';
    return kind||'';
  }
  function marketDisplayValue(key,kind){
    const x=market[key];
    if(x===''||x===null||x===undefined)return '';
    if(kind==='flow'){const n=market.unitSystem==='US'?Number(x)*M3D_TO_GPD:Number(x);return market.unitSystem==='US'?Math.round(n):Math.round(n*100)/100;}
    if(kind==='temp'){const n=market.unitSystem==='US'?Number(x)*9/5+32:Number(x);return Math.round(n*10)/10;}
    return x;
  }
  function toCanonicalMarket(kind,x){
    if(x===null||x===undefined||String(x).trim()==='')return '';
    const n=Number(x); if(!Number.isFinite(n))return '';
    if(kind==='flow')return market.unitSystem==='US'?n/M3D_TO_GPD:n;
    if(kind==='temp')return market.unitSystem==='US'?(n-32)*5/9:n;
    return n;
  }
  function persistAutosave(){
    if(SUITE_HOSTED)return;
    try{
      localStorage.setItem(
        'tbd-autosave',
        JSON.stringify({
          version:APP_VERSION,
          name:projectName,
          inputs:engine.exportInputs(),
          market,
          bypassedMandatory,
          treatmentTrain,
          recycles,
          sludgeStrategy,
          sludgeLines
        })
      );
    }catch(_){
      /* autosave unavailable; project can still be saved explicitly */
    }
  }
  function setEngineIfNumber(sheet,addr,x){if(x===''||x===null||x===undefined)return;const n=Number(x);if(Number.isFinite(n))engine.set(sheet,addr,n);}
  function syncMarketToEngine(){
    const avg=effectiveMarketValue('avgFlowM3d'),design=effectiveMarketValue('designFlowM3d');
    const basis=(market.calculationFlowBasis==='Average daily flow'||!Number(design))?Number(avg):Number(design);
    if(Number.isFinite(basis)&&basis>0){
      engine.set('DesignBasis','C6',basis);
      const peak=Number(effectiveMarketValue('peakHourlyEqM3d'));
      if(Number.isFinite(peak)&&peak>0)engine.set('DesignBasis','C8',peak/basis);
    }
    setEngineIfNumber('DesignBasis','C25',effectiveMarketValue('influentCOD'));
    setEngineIfNumber('DesignBasis','C27',effectiveMarketValue('influentBOD'));
    setEngineIfNumber('DesignBasis','C28',effectiveMarketValue('influentTSS'));
    setEngineIfNumber('DesignBasis','C30',effectiveMarketValue('influentTKN'));
    setEngineIfNumber('DesignBasis','C31',effectiveMarketValue('influentAmmonia'));
    setEngineIfNumber('DesignBasis','C19',effectiveMarketValue('pH'));
    setEngineIfNumber('DesignBasis','C16',effectiveMarketValue('tempC'));
    setEngineIfNumber('DesignBasis','C61',effectiveMarketValue('effluentBOD'));
    setEngineIfNumber('DesignBasis','C62',effectiveMarketValue('effluentTSS'));
    setEngineIfNumber('DesignBasis','C63',effectiveMarketValue('effluentAmmonia'));
    setEngineIfNumber('DesignBasis','C64',effectiveMarketValue('effluentTN'));
    setEngineIfNumber('DesignBasis','C65',effectiveMarketValue('effluentTP'));
  }
  function marketField(key,labelText,{kind='',unit='',options=null,note='',linked=false,type='number',wide=false}={}){
    const val=marketDisplayValue(key,kind),spec=mandatoryFieldMap.get(key),isRequired=!!spec,isMissing=isRequired&&valueMissingForSpec(spec,market[key]),isBypassed=isMissing&&!!bypassedMandatory[key];
    let control='';
    if(options){
      const placeholder=isRequired&&String(val??'').trim()===''?'<option value="" selected>— Select required value —</option>':'';
      control=`<select class="market-control" data-key="${esc(key)}" data-kind="${esc(kind)}" ${isRequired?'aria-required="true"':''}>${placeholder}${options.map(o=>`<option value="${esc(o)}"${String(val)===String(o)?' selected':''}>${esc(o)}</option>`).join('')}</select>`;
    }else{
      control=`<input class="market-control" data-key="${esc(key)}" data-kind="${esc(kind)}" type="${esc(type)}" ${type==='number'?'step="any"':''} ${isRequired?'aria-required="true"':''} value="${esc(val)}" />`;
    }
    const u=unit||marketUnit(kind),requiredBadge=isRequired?'<span class="required-badge">Required</span>':'',bypassBadge=isBypassed?'<span class="bypass-badge">Bypassed</span>':'';
    const bypassNote=isBypassed?`<div class="market-bypass-note">Planning assumption active: ${esc(mandatoryFallbackDisplay(spec,bypassedMandatory[key].value))}${spec.target?' for sizing only; compliance is unassessed.':'.'}</div>`:'';
    return `<div class="market-field${wide?' wide':''}${isMissing?' mandatory-missing':''}${isBypassed?' mandatory-bypassed':''}"><div class="market-label"><span>${esc(labelText)}</span><span class="market-badges">${requiredBadge}${bypassBadge}${linked?'<span class="link-badge">Calculation-linked</span>':'<span class="project-badge">Project data</span>'}</span></div><div class="market-input-line">${control}${u?`<span class="market-unit">${esc(u)}</span>`:''}</div>${note?`<div class="market-note">${esc(note)}</div>`:''}${bypassNote}</div>`;
  }
  function marketText(key,labelText,note=''){return marketField(key,labelText,{type:'text',note,wide:true});}
  function bindMarketControls(){
    main.querySelectorAll('.market-control[data-key]').forEach(el=>{el.onchange=()=>{
      const key=el.dataset.key,kind=el.dataset.kind||'';
      market[key]=el.type==='number'?toCanonicalMarket(kind,el.value):el.value;
      delete bypassedMandatory[key];clearResolvedBypass(key);
      syncMarketToEngine();lastNetworkResult=null;persistAutosave();updateCalcState();renderMarketIntake();
    };});
    const pn=main.querySelector('#marketProjectName'); if(pn)pn.onchange=()=>{if(pn.value.trim()){projectName=pn.value.trim();document.getElementById('projectName').textContent=projectName;persistAutosave();renderMarketIntake();}};
    main.querySelectorAll('[data-units]').forEach(b=>b.onclick=()=>{market.unitSystem=b.dataset.units;persistAutosave();renderMarketIntake();});
    const adv=main.querySelector('#openDetailedBasis');if(adv)adv.onclick=()=>navigateTo('DesignBasis');
    const dash=main.querySelector('#goDashboard');if(dash)dash.onclick=()=>navigateTo('Dashboard');
    const review=main.querySelector('#reviewMandatory');if(review)review.onclick=()=>{const st=mandatoryInputStatus();showMandatoryDialog(st.missing,()=>renderMarketIntake(),'the calculation basis');};
    const clear=main.querySelector('#clearBypasses');if(clear)clear.onclick=()=>{bypassedMandatory={};lastNetworkResult=null;persistAutosave();renderMarketIntake();toast('Bypassed assumptions cleared');};
  }
  function intakeCompleteness(){return mandatoryInputStatus();}
  function mandatoryStatusBanner(status){
    if(status.missing.length)return `<div class="mandatory-status missing"><div><b>${status.missing.length} mandatory field${status.missing.length===1?' is':'s are'} missing</b><span>The design results and compact report will pause for review. You may provide the values or explicitly bypass them with recorded planning assumptions.</span></div><button class="action secondary" id="reviewMandatory">Review / bypass</button></div>`;
    if(status.bypassed.length)return `<div class="mandatory-status bypassed"><div><b>${status.bypassed.length} bypassed planning assumption${status.bypassed.length===1?'':'s'} active</b><span>Calculations can proceed. Missing effluent limits remain unassessed and the compact report identifies every bypass.</span></div><button class="action secondary" id="clearBypasses">Clear bypasses</button></div>`;
    return `<div class="mandatory-status complete"><div><b>Mandatory project basis complete</b><span>All required flow, influent, effluent-target and discharge-basis fields have been supplied.</span></div></div>`;
  }
  function renderMarketIntake(){
    engine.errors=[];
    const inputStatus=intakeCompleteness(),pct=inputStatus.pct;
    const flowUnit=marketUnit('flow'),tempUnit=marketUnit('temp');
    main.innerHTML=`<div class="page-head intake-head"><div class="page-title"><div class="eyebrow">CLIENT / RFQ DATA ENTRY</div><h1>Project Design Inputs</h1><p>Enter information the way it is normally received from a consultant, end user or package-plant RFQ. Total Bio Design converts these market inputs into the detailed biological design basis used by the calculation engine.</p></div><div class="unit-switch"><button data-units="US" class="${market.unitSystem==='US'?'active':''}">US Customary</button><button data-units="SI" class="${market.unitSystem==='SI'?'active':''}">SI</button></div></div>
    <div class="intake-summary"><div><b>${pct}%</b><span>Mandatory basis usable</span><small>${inputStatus.provided.length} supplied · ${inputStatus.bypassed.length} bypassed · ${inputStatus.missing.length} missing</small></div><div class="summary-line"><span>Calculation flow</span><strong>${esc(formatValue(v('DesignBasis','C6'), 'm³/d'))} m³/d</strong></div><div class="summary-line"><span>Peak-hour factor</span><strong>${esc(formatValue(v('DesignBasis','C8'),'–'))}</strong></div><div class="summary-line"><span>Design temperature</span><strong>${esc(formatValue(v('DesignBasis','C16'),'°C'))} °C</strong></div></div>
    ${mandatoryStatusBanner(inputStatus)}
    <section class="intake-card"><div class="intake-card-head"><span class="step">1</span><div><h3>Project & Flow Basis</h3><p>Start with the information typically shown on the project questionnaire or RFQ.</p></div></div><div class="market-grid">
      <div class="market-field wide"><div class="market-label"><span>Project / RFQ name</span><span class="project-badge">Project data</span></div><div class="market-input-line"><input id="marketProjectName" class="market-control project-name-control" type="text" value="${esc(projectName)}" /></div></div>
      ${marketText('client','Client / End User')}${marketText('location','Project location')}
      ${marketField('avgFlowM3d','Average daily flow',{kind:'flow',linked:true,note:'Market-supplied average daily flow.'})}
      ${marketField('peakHourlyEqM3d','Peak hourly flow',{kind:'flow',linked:true,note:'Enter as an equivalent daily rate, matching common package-plant questionnaires.'})}
      ${marketField('designFlowM3d','Design flow',{kind:'flow',linked:true,note:'Default calculation basis when a specific design flow is provided.'})}
      ${marketField('calculationFlowBasis','Flow used by biological model',{options:['Design flow','Average daily flow'],linked:true,note:'Choose which market flow drives reactor sizing.'})}
      ${marketField('operatingPattern','Wastewater arrival pattern',{options:['24/7 continuous','Limited hours per day','Weekends only','Limited days per week'],note:'Stored as project basis; equalization sizing can use this in a later hydraulic module.'})}
      ${marketField('hoursPerDay','Hours per day',{unit:'h/d',note:'Used when flow is not received continuously.'})}
      ${marketField('daysPerWeek','Days per week',{unit:'d/week',note:'Used for intermittent operations.'})}
    </div></section>
    <section class="intake-card"><div class="intake-card-head"><span class="step">2</span><div><h3>Wastewater Type & Influent Characterization</h3><p>Use the same analytes and terminology normally provided by the market.</p></div></div><div class="market-grid">
      ${marketField('wasteType','Type of waste',{options:['100% domestic waste','Blend of industrial and domestic waste','100% industrial process waste'],note:'Project basis for selecting appropriate assumptions and warnings.'})}
      ${marketField('kitchenWaste','Kitchen / foodservice wastewater',{options:['No','Yes'],note:'Flags grease and food solids considerations.'})}
      ${marketField('foodPrescreenGrease','Food waste pre-screened / grease removed',{options:['Yes','No','Not applicable']})}
      ${marketField('influentBOD','BOD₅',{unit:'mg/L',linked:true})}
      ${marketField('influentCOD','COD',{unit:'mg/L',linked:true})}
      ${marketField('influentTSS','TSS',{unit:'mg/L',linked:true})}
      ${marketField('influentAmmonia','Ammonia-N',{unit:'mg/L',linked:true})}
      ${marketField('influentTKN','TKN',{unit:'mg/L',linked:true})}
      ${marketField('influentFOG','FOG',{unit:'mg/L',note:'Captured from RFQ; not yet used in the biological reactor equations.'})}
      ${marketField('pH','pH',{unit:'',linked:true})}
      ${marketField('tempC','Wastewater design temperature',{kind:'temp',linked:true,note:`Displayed as ${tempUnit}; converted internally to °C and used as the minimum biological design temperature. Maximum aeration-case temperature remains an engineering input.`})}
    </div></section>
    <section class="intake-card"><div class="intake-card-head"><span class="step">3</span><div><h3>Required Effluent</h3><p>Enter permit, reuse or pretreatment targets before selecting the biological configuration.</p></div></div><div class="market-grid">
      ${marketField('effluentBOD','BOD₅',{unit:'mg/L',linked:true})}
      ${marketField('effluentCOD','COD',{unit:'mg/L',note:'Captured as project requirement; current workbook does not expose a COD consent input.'})}
      ${marketField('effluentTSS','TSS',{unit:'mg/L',linked:true})}
      ${marketField('effluentAmmonia','Ammonia-N',{unit:'mg/L',linked:true})}
      ${marketField('effluentTN','Total Nitrogen',{unit:'mg/L',linked:true})}
      ${marketField('effluentTP','Total Phosphorus',{unit:'mg/L',linked:true})}
      ${marketField('effluentFOG','FOG',{unit:'mg/L',note:'Stored with the project for proposal/design documentation.'})}
      ${marketField('dischargeType','Discharge basis',{options:['Direct discharge permit','Pretreatment / discharge to POTW','Water reuse','Other'],note:'Defines the commercial treatment objective.'})}
    </div></section>
    <section class="intake-card"><div class="intake-card-head"><span class="step">4</span><div><h3>Package Plant & Site Requirements</h3><p>Commercial and mechanical requirements stay with the project so the software can evolve from reactor sizing into a complete package-plant design suite.</p></div></div><div class="market-grid">
      ${marketField('redundancy','Plant redundancy',{options:['One package plant (1 × 100%)','Two parallel plants (2 × 100%)','Two parallel plants (2 × 50%)','Other'],note:'Stored as project configuration; reactor calculations currently report total required process capacity.'})}
      ${marketField('voltage','Plant voltage',{options:['230V-3Ph-60Hz','460V-3Ph-60Hz','208V-3Ph-60Hz','Other']})}
      ${marketField('screeningRequired','Influent screening required',{options:['Yes','No']})}
      ${marketField('manualBarRack','Manual bar rack acceptable',{options:['Yes','No','Not applicable']})}
      ${marketField('installation','Package plant installation',{options:['Above grade','Partially below grade','Below grade']})}
      ${marketField('cathodicProtection','Cathodic protection required',{options:['No','Yes','Not applicable']})}
      ${marketField('tertiarySandFilters','Tertiary sand filters required',{options:['No','Yes']})}
      ${marketField('grating','Grating required',{options:['Yes','No']})}
      ${marketField('handrails','Handrails required',{options:['Yes','No']})}
      ${marketField('insulated','Insulation required',{options:['No','Yes']})}
      ${marketField('disinfection','Disinfection',{options:['UV','Tablet chlorination + dechlorination','UV + redundant UV bank','UV + redundant tablet chlorination/dechlorination','Other']})}
      ${marketField('disinfectionLimit','Disinfection limit',{options:['200 FC/100 mL — 30-day geometric mean','200 FC/100 mL mean + 400 FC/100 mL daily max','14 FC/100 mL — 30-day geometric mean for reuse','Other']})}
      ${marketField('sludgeHolding','Sludge holding / digester compartment',{options:['Yes','No']})}
      ${marketField('material','Tank / package material',{options:['Painted A-36 carbon steel','Stainless steel','Other']})}
      ${marketText('consultant','Design / permitting consultant')}${marketText('permittingState','Permitting state / jurisdiction')}
    </div></section>
    <div class="intake-actions"><div><strong>Engineering layer</strong><span>Detailed peaking factors, fractionation, kinetics and process-specific assumptions remain available to the engineer without burdening the client-input screen.</span></div><button class="action secondary" id="openDetailedBasis">Detailed Design Basis</button><button class="action primary-action" id="goDashboard">Continue to Dashboard →</button></div>`;
    bindMarketControls();updateCalcState();
  }
  function kpi(labelText,sheet,addr,unitText,cls){return `<div class="kpi ${cls}"><div class="label">${esc(labelText)}</div><div class="value">${esc(formatValue(v(sheet,addr),unitText))}<span class="unit">${esc(unitText)}</span></div></div>`;}
  function streamConc(s,key){return key==='tn'?processNetwork.totalNConcentration(s):processNetwork.concentration(s,key);}
  function unitNameById(id){const u=treatmentTrain.find(x=>x.id===id);return u?(u.name||unitDef(u.type).name):'Unknown unit';}
  function unitOptions(selected){return treatmentTrain.map((u,i)=>`<option value="${esc(u.id)}"${u.id===selected?' selected':''}>${i+1}. ${esc(u.name||unitDef(u.type).name)}</option>`).join('');}
  function performanceFieldHtml(meta,cfg,prefix='unit-config'){
    return `<label class="performance-field"><span>${esc(meta.label)}</span><div class="performance-input"><input class="input-control" type="number" step="${esc(meta.step??'any')}" min="${esc(meta.min??'')}" max="${esc(meta.max??'')}" value="${esc(cfg[meta.key]??0)}" data-${prefix}="${esc(meta.key)}"><em>${esc(meta.unit||'')}</em></div></label>`;
  }
  function streamTableRows(inlet,outlet){
    return [['COD','cod'],['BOD₅','bod'],['TSS','tss'],['Ammonia-N','nh4'],['Total nitrogen','tn'],['Total phosphorus','tp'],['FOG','fog']].map(([name,key])=>`<tr><td>${esc(name)}</td><td>${esc(formatValue(streamConc(inlet,key),'mg/L'))}</td><td>${esc(formatValue(streamConc(outlet,key),'mg/L'))}</td><td>${esc(formatValue(streamConc(inlet,key)-streamConc(outlet,key),'mg/L'))}</td></tr>`).join('');
  }
  function activeUnitPanelHtml(u,network,embedded=false){
    const d=unitDef(u.type),state=network.water.byId[u.id],profile=processNetwork.profileForType(u.type),cfg=processNetwork.effectiveConfig(u),fields=processNetwork.profileFields(u.type);
    if(!state)return '';
    const controls=fields.length?fields.map(f=>performanceFieldHtml(f,cfg)).join(''):'<div class="unit-pass-note">No default constituent transformation is assigned. This unit passes the stream through until performance assumptions are entered in a future dedicated model.</div>';
    return `<section class="section-card active-unit-context"><div class="section-title"><span>Selected Train Unit · Position ${treatmentTrain.findIndex(x=>x.id===u.id)+1}</span><button class="action secondary" id="backToTrain">← Treatment Train</button></div><div class="active-unit-head"><div><span class="unit-group">${esc(d.group)}</span><h3>${esc(u.name||d.name)}</h3><p>${esc(profile.description)}</p></div><div class="stream-flow-readout"><span>Hydraulic flow</span><b>${esc(formatValue(state.inlet.flow,'m³/d'))} → ${esc(formatValue(state.forward.flow,'m³/d'))} m³/d</b></div></div><div class="unit-identity-grid"><label><span>Display name</span><input id="unitDisplayName" class="input-control" value="${esc(u.name||d.name)}"></label><label><span>Process tag / duty</span><input id="unitDisplayTag" class="input-control" value="${esc(u.tag||d.tag)}"></label></div><div class="unit-balance-grid"><div><h4>Sequential Stream Balance</h4><table class="eff-table stream-table"><thead><tr><th>Determinand</th><th>Inlet</th><th>Outlet</th><th>Change</th></tr></thead><tbody>${streamTableRows(state.inlet,state.forward)}</tbody></table></div><div><h4>Unit Performance Assumptions</h4><div class="performance-grid">${controls}</div><div class="performance-actions"><button class="action secondary" id="resetUnitDefaults">Restore planning defaults</button><span>Editable assumptions are applied to this individual unit only. Downstream units receive this calculated outlet.</span></div></div></div><div class="unit-balance-footer"><span>Generated residuals</span><b>${esc(formatValue(state.sludgeAvailable?.mass?.tss??state.sludge?.drySolids??0,'kg/d'))} kg DS/d</b><span>Calculation mode</span><b>Ordered, constituent-by-constituent</b></div></section>`;
  }
  function bindActiveUnitPanel(u){
    const d=unitDef(u.type);const name=main.querySelector('#unitDisplayName'),tag=main.querySelector('#unitDisplayTag');
    if(name)name.onchange=e=>{u.name=e.target.value.trim()||d.name;saveNetwork();render();toast('Unit name updated');};
    if(tag)tag.onchange=e=>{u.tag=e.target.value.trim()||d.tag;saveNetwork();render();toast('Unit duty updated');};
    main.querySelectorAll('[data-unit-config]').forEach(inp=>inp.onchange=()=>{u.config={...processNetwork.defaultConfig(u.type),...(u.config||{}),[inp.dataset.unitConfig]:Number(inp.value)};saveNetwork();render();});
    const reset=main.querySelector('#resetUnitDefaults');if(reset)reset.onclick=()=>{u.config=processNetwork.defaultConfig(u.type);saveNetwork();render();toast('Planning defaults restored');};
    const back=main.querySelector('#backToTrain');if(back)back.onclick=()=>{activeUnitId=null;current='Dashboard';renderNav();renderDashboard();};
  }
  const effluentDeterminandDefs=[
    {name:'Total COD',key:'cod',targetKey:'effluentCOD'},
    {name:'BOD₅',key:'bod',targetKey:'effluentBOD'},
    {name:'TSS',key:'tss',targetKey:'effluentTSS'},
    {name:'Ammonia-N',key:'nh4',targetKey:'effluentAmmonia'},
    {name:'Total nitrogen',key:'tn',targetKey:'effluentTN'},
    {name:'Total phosphorus',key:'tp',targetKey:'effluentTP'},
    {name:'FOG',key:'fog',targetKey:'effluentFOG'}
  ];
  function actualMarketNumber(key){
    const x=market[key];if(x===null||x===undefined||(typeof x==='string'&&x.trim()===''))return null;
    const n=Number(x);return Number.isFinite(n)?n:null;
  }
  function effluentAssessment(network){
    const stream=network.water.finalEffluent;
    return effluentDeterminandDefs.map(def=>{
      const predicted=streamConc(stream,def.key),target=actualMarketNumber(def.targetKey),hasTarget=target!==null&&target>=0,pass=hasTarget?predicted<=target:null;
      return {...def,predicted,target,hasTarget,pass,ratio:hasTarget&&target>0?predicted/target:null,bypassed:!!bypassedMandatory[def.targetKey]};
    });
  }
  function targetNumber(x){
    if(x===''||x===null||x===undefined)return null;
    const n=Number(x);return Number.isFinite(n)&&n>=0?n:null;
  }
  function effluentTargets(){
    const configured=key=>{
      const spec=mandatoryFieldMap.get(key);
      if(spec&&valueMissingForSpec(spec,market[key]))return null;
      return targetNumber(market[key]);
    };
    return {
      cod:targetNumber(market.effluentCOD),
      bod:configured('effluentBOD'),
      tss:configured('effluentTSS'),
      nh4:configured('effluentAmmonia'),
      tn:configured('effluentTN'),
      tp:configured('effluentTP'),
      fog:targetNumber(market.effluentFOG)
    };
  }
  function effluentAssessments(network){return complianceAdvisor.assess(network.water.finalEffluent,effluentTargets(),processNetwork);}
  function complianceRecommendations(network){
    const assessments=effluentAssessments(network),types=treatmentTrain.map(u=>u.type);
    return assessments.filter(x=>x.hasTarget&&!x.pass).map(assessment=>({assessment,options:complianceAdvisor.suggestionsFor(assessment,types,{assessments})})).filter(x=>x.options.length);
  }
  function effluentRows(network){
    return effluentAssessments(network).map(row=>`<tr><td>${esc(row.name)}</td><td>${esc(formatValue(row.predicted,'mg/L'))}</td><td>${row.hasTarget?esc(formatValue(row.target,'mg/L')):'—'}</td><td><span class="status ${row.hasTarget?(row.pass?'pass':'fail'):'na'}">${esc(row.status)}</span></td></tr>`).join('');
  }
  function complianceGuidanceHtml(network,reportMode=false){
    const recs=complianceRecommendations(network);
    if(!recs.length){
      const assessed=effluentAssessments(network).filter(x=>x.hasTarget);
      if(!assessed.length)return reportMode?'<p class="report-note">No discharge targets are available for compliance assessment.</p>':'<div class="compliance-clear neutral"><b>No discharge targets are available</b><span>Enter the required effluent limits to activate compliance guidance.</span></div>';
      return reportMode?'<p class="report-note pass-note">All assessed final-effluent targets are met by the configured treatment train.</p>':'<div class="compliance-clear"><b>All assessed targets pass</b><span>No additional treatment method is suggested from the current steady-state result.</span></div>';
    }
    const rows=recs.map(({assessment,options})=>{
      const primary=options[0],alternatives=options.slice(1).map(x=>x.name).join('; ');
      if(reportMode)return `<tr><td>${esc(assessment.name)}</td><td>${esc(formatValue(assessment.predicted,'mg/L'))} / ${esc(formatValue(assessment.target,'mg/L'))} mg/L</td><td><b>${esc(primary.name)}</b><br><span>${esc(primary.summary)}</span>${alternatives?`<br><small>Other options: ${esc(alternatives)}</small>`:''}</td></tr>`;
      return `<tr><td><b>${esc(assessment.name)}</b><span>${esc(formatValue(assessment.predicted,'mg/L'))} vs ${esc(formatValue(assessment.target,'mg/L'))} mg/L</span></td><td><b>${esc(primary.name)}</b><span>${esc(primary.summary)}</span>${alternatives?`<small>Alternatives: ${esc(alternatives)}</small>`:''}</td><td><button class="action secondary remedy-add" data-remedy-type="${esc(primary.type)}" data-remedy-parameter="${esc(assessment.name)}">+ Add method</button></td></tr>`;
    }).join('');
    if(reportMode)return `<table class="report-table recommendation-table"><thead><tr><th>Failed parameter</th><th>Predicted / target</th><th>Suggested treatment response</th></tr></thead><tbody>${rows}</tbody></table>`;
    return `<div class="compliance-guidance"><div class="subpanel-head"><div><h4>Suggested treatment additions</h4><span>Planning guidance is generated only for parameters that fail their configured final-effluent target. Verify process assumptions, loading, chemistry, hydraulics and vendor requirements before adopting a recommendation.</span></div></div><div class="guidance-table-wrap"><table class="guidance-table"><tbody>${rows}</tbody></table></div></div>`;
  }
  function addRecommendedTreatment(type,parameter){
    const index=complianceAdvisor.recommendedInsertionIndex(type,treatmentTrain),unit=makeUnit(type);
    treatmentTrain.splice(index,0,unit);
    if(type==='pre_anoxic'){
      const source=treatmentTrain.slice(index+1).find(u=>['cas','extended_aeration','mbr','mbbr_nit','mbbr_ifas','baf','mabr','oxidation_ditch'].includes(u.type));
      if(source&&!recycles.some(r=>r.enabled!==false&&r.targetUnitId===unit.id&&r.sourcePort==='liquid'))recycles.push({id:newId('r',++recycleSeq),name:'Internal mixed-liquor recycle',sourceUnitId:source.id,targetUnitId:unit.id,sourcePort:'liquid',basis:'ratio',value:3,enabled:true});
    }
    saveNetwork();renderDashboard();toast(`${unit.name} added for ${parameter}`);
  }
  function bindComplianceGuidance(){main.querySelectorAll('[data-remedy-type]').forEach(b=>b.onclick=()=>addRecommendedTreatment(b.dataset.remedyType,b.dataset.remedyParameter||'failed target'));}
    function recycleCardsHtml(network){
    if(!recycles.length)return '<div class="recycle-empty">No recirculation is configured. Add an internal mixed-liquor recycle, return activated sludge, membrane concentrate return, filter backwash return, or another looped process connection.</div>';
    return recycles.map((r,i)=>{
      const actual=network.water.recycles.find(x=>x.recycleId===r.id);
      const si=treatmentTrain.findIndex(u=>u.id===r.sourceUnitId);
      const ti=treatmentTrain.findIndex(u=>u.id===r.targetUnitId);
      const loop=si>ti?'Back recycle':si<ti?'Forward transfer / bypass':'Invalid same-unit connection';
      const port=processNetwork.recyclePortLabel?processNetwork.recyclePortLabel(r.sourcePort):(r.sourcePort==='sludge'?'Separated sludge / underflow':r.sourcePort==='residual'?'Concentrate / liquid residual':'Liquid outlet');
      const basisLabel=r.basis==='fixed'?'Flow':r.basis==='source_fraction'?'Percent of source flow':'Recycle ratio';
      const basisUnit=r.basis==='fixed'?'m³/d':r.basis==='source_fraction'?'%':'× plant Q';
      return `<div class="recycle-card${r.enabled===false?' disabled':''}" data-recycle-id="${esc(r.id)}">
        <div class="recycle-card-top">
          <input class="recycle-name" data-recycle-name value="${esc(r.name||`Recirculation ${i+1}`)}">
          <label class="mini-toggle" title="Enable or disable this connection"><input type="checkbox" data-recycle-enabled ${r.enabled!==false?'checked':''}><span></span></label>
          <button class="recycle-delete" data-recycle-delete title="Delete recirculation">×</button>
        </div>
        <div class="recycle-fields">
          <label><span>Source unit</span><select data-recycle-source>${unitOptions(r.sourceUnitId)}</select></label>
          <label><span>Source stream</span><select data-recycle-port>
            <option value="liquid"${r.sourcePort==='liquid'?' selected':''}>Liquid outlet</option>
            <option value="sludge"${r.sourcePort==='sludge'?' selected':''}>Separated sludge / underflow</option>
            <option value="residual"${r.sourcePort==='residual'?' selected':''}>Concentrate / liquid residual</option>
          </select></label>
          <div class="recycle-arrow">↩</div>
          <label><span>Target unit inlet</span><select data-recycle-target>${unitOptions(r.targetUnitId)}</select></label>
          <label><span>Flow basis</span><select data-recycle-basis>
            <option value="ratio"${r.basis==='ratio'?' selected':''}>Ratio × plant flow</option>
            <option value="fixed"${r.basis==='fixed'?' selected':''}>Fixed flow</option>
            <option value="source_fraction"${r.basis==='source_fraction'?' selected':''}>Percent of source flow</option>
          </select></label>
          <label><span>${esc(basisLabel)}</span><div class="inline-unit-input"><input type="number" step="any" min="0" ${r.basis==='source_fraction'?'max="100"':''} data-recycle-value value="${esc(r.value)}"><em>${esc(basisUnit)}</em></div></label>
        </div>
        <div class="recycle-summary">
          <span>${esc(loop)} · ${esc(port)}</span>
          <b>${r.enabled===false?'Disabled':`${esc(formatValue(actual?.flow||0,'m³/d'))} m³/d`}</b>
          <span>${esc(unitNameById(r.sourceUnitId))} → ${esc(unitNameById(r.targetUnitId))}</span>
        </div>
      </div>`;
    }).join('');
  }


  function sludgeSourceChips(line){
    if(!(line.sources||[]).length)return '<span class="source-chip missing">No sludge sources assigned</span>';
    return line.sources.map(s=>`<span class="source-chip">${esc(unitNameById(s.unitId))}<b>${Math.round((Number(s.fraction)||0)*100)}%</b></span>`).join('');
  }
    function sludgeLineHtml(line,network,index){
    const result=network.sludge.lines.find(x=>x.line.id===line.id);
    const add=idx=>`<button class="train-add sludge-add" data-sludge-line-id="${esc(line.id)}" data-sludge-add-index="${idx}" title="Add a residuals unit here">+</button>`;
    const nodes=(line.units||[]).length?(line.units||[]).map((u,i)=>{
      const d=unitDef(u.type),r=result?.units?.[i],ds=r?.outlet?.flow>0?r.outlet.mass.tss/(r.outlet.flow*1000)*100:0;
      const parallel=Math.max(1,Math.round(Number(r?.metrics?.parallelUnits)||1));
      const perUnit=parallel>1?` · ${parallel} parallel · ${esc(formatValue(r?.metrics?.feedDrySolidsPerUnitKgD||0,'kg/d'))} kg DS/d each`:'';
      return `${add(i)}<div class="train-node sludge-node draggable" draggable="true" data-sludge-line-id="${esc(line.id)}" data-sludge-unit-id="${esc(u.id)}" tabindex="0">
        <button class="train-remove" data-sludge-remove title="Remove residuals unit">×</button>
        <span class="tiny">${esc(u.tag||d.tag)}</span><strong>${esc(u.name||d.name)}</strong>
        <span class="train-flow">${esc(formatValue(r?.outlet?.mass?.tss||0,'kg/d'))} kg DS/d · ${esc(formatValue(ds,'%'))}% DS${perUnit}</span>
      </div>`;
    }).join('<span class="arrow">→</span>')+add(line.units.length):`${add(0)}<div class="empty small">Add equalization, thickening, digestion or dewatering.</div>`;
    const targetOptions=unitOptions(line.returnTargetUnitId);
    const returnPct=Math.round((Number.isFinite(Number(line.returnFraction))?Number(line.returnFraction):1)*1000)/10;
    const returnFlow=result?.returnStream?.flow||0;
    const unreturnedFlow=result?.unreturnedReturnStream?.flow||0;
    return `<div class="sludge-line" data-sludge-line-id="${esc(line.id)}">
      <div class="sludge-line-head">
        <div class="sludge-line-title"><span>Residuals Line ${index+1}</span><input data-sludge-line-name value="${esc(line.name||`Sludge Line ${index+1}`)}"></div>
        <div class="sludge-line-actions"><button class="action secondary" data-assign-sources>Assign sludge sources</button>${sludgeLines.length>1?'<button class="action danger-action" data-delete-sludge-line>Delete line</button>':''}</div>
      </div>
      <div class="sludge-source-row"><span class="source-label">Sources</span><div class="source-chips">${sludgeSourceChips(line)}</div></div>
      <div class="sludge-train train" data-sludge-builder>${nodes}</div>
      <div class="sludge-return-row">
        <label class="mini-toggle" title="Return centrate / filtrate to the water line"><input type="checkbox" data-return-enabled ${line.returnEnabled!==false?'checked':''}><span></span></label>
        <label><span>Return centrate / filtrate to water-unit inlet</span><select data-return-target ${line.returnEnabled===false?'disabled':''}>${targetOptions}</select></label>
        <label><span>Fraction returned</span><div class="inline-unit-input"><input type="number" min="0" max="100" step="1" data-return-fraction value="${esc(returnPct)}" ${line.returnEnabled===false?'disabled':''}><em>%</em></div></label>
        <div class="route-summary">
          <span>Feed</span><b>${esc(formatValue(result?.input?.mass?.tss||0,'kg/d'))} kg DS/d</b>
          <span>Equalization</span><b>${esc(formatValue(result?.equalizationVolumeM3||0,'m³'))} m³</b>
          <span>Wet cake</span><b>${esc(formatValue(result?.wetCakeTD||0,'t/d'))} t/d</b>
          <span>Returned</span><b>${esc(formatValue(returnFlow,'m³/d'))} m³/d</b>
          <span>Other liquid disposal</span><b>${esc(formatValue(unreturnedFlow,'m³/d'))} m³/d</b>
        </div>
      </div>
    </div>`;
  }

    function sludgeNetworkPanelHtml(network,standalone=false){
    const sum=network.sludge.summary;
    const lanes=sludgeLines.map((line,i)=>sludgeLineHtml(line,network,i)).join('');
    const generated=network.water.sludgeSources.reduce((a,s)=>a+(s.mass?.tss||0),0);
    return `<div class="panel residual-network-panel${standalone?' standalone':''}">
      <div class="panel-head">
        <div><h3>Residuals & Dewatering Network</h3><span class="panel-sub">Manually assign sludge from each water-line operation. Combine all sources in one equalized line or divide them among independent parallel dewatering systems.</span></div>
        <div class="residual-toolbar">
          <select id="sludgeStrategy" aria-label="Sludge handling strategy">
            <option value="common"${sludgeStrategy==='common'?' selected':''}>One common sludge line</option>
            <option value="parallel"${sludgeStrategy==='parallel'?' selected':''}>Multiple parallel sludge lines</option>
          </select>
          <button class="action secondary" id="addSludgeLine"${sludgeStrategy==='common'?' disabled':''}>+ Parallel line</button>
        </div>
      </div>
      <div class="panel-body">
        <div class="residual-summary">
          <div><span>Waste sludge available</span><b>${esc(formatValue(generated,'kg/d'))} kg DS/d</b></div>
          <div><span>Unassigned sludge</span><b class="${sum.unassignedDrySolidsKgD>0.001?'warning-text':''}">${esc(formatValue(sum.unassignedDrySolidsKgD,'kg/d'))} kg DS/d</b></div>
          <div><span>Total wet cake</span><b>${esc(formatValue(sum.wetCakeTD,'t/d'))} t/d</b></div>
          <div><span>Dewatering polymer</span><b>${esc(formatValue(sum.polymerKgD,'kg/d'))} kg/d</b></div>
          <div><span>Returned sidestream</span><b>${esc(formatValue(sum.returnedLiquidM3D||0,'m³/d'))} m³/d</b></div>
          <div><span>Unreturned liquid</span><b>${esc(formatValue(sum.unreturnedLiquidM3D||0,'m³/d'))} m³/d</b></div>
        </div>
        <div class="sludge-lines">${lanes}</div>
      </div>
    </div>`;
  }

  function networkWarningsHtml(network){
    const list=[...network.warnings];if(network.sludge.summary.unassignedDrySolidsKgD>0.001)list.unshift(`${formatValue(network.sludge.summary.unassignedDrySolidsKgD,'kg/d')} kg DS/d is not assigned to a residuals line.`);
    if(!list.length)return '';
    return `<div class="network-warning"><b>Process-network review</b><div>${list.slice(0,8).map(x=>`<span>${esc(x)}</span>`).join('')}</div></div>`;
  }
    function renderDashboard(){
    engine.errors=[];
    const network=calculateNetwork();
    const finalQ=network.water.finalEffluent.flow;
    const convergence=network.converged&&network.water.converged;
    const inputStatus=mandatoryInputStatus();
    const bypassBanner=inputStatus.bypassed.length?`<div class="dashboard-bypass-banner"><div><b>${inputStatus.bypassed.length} mandatory value${inputStatus.bypassed.length===1?' is':'s are'} being bypassed</b><span>Planning defaults are active. Missing effluent limits remain unassessed and are identified in the compact report.</span></div><button class="action secondary" id="reviewBypassedInputs">Review inputs</button></div>`:'';
    main.innerHTML=`<div class="page-head"><div class="page-title"><h1>Biological Treatment Design Dashboard</h1><p>Order-sensitive water-quality mass balance, configurable recirculation loops, and source-routed residuals handling solved together at steady state.</p></div><div class="page-head-actions"><button class="action secondary" id="openCompactReport">Compact Report</button><button class="action secondary" id="openMassBalance">Full Mass Balance</button><button class="action secondary" id="exportTotalRO">Send to Total RO Design</button><div class="head-tag ${convergence?'':'warning-tag'}">${convergence?'Network converged':'Review convergence'} · v${APP_VERSION}</div></div></div>${bypassBanner}`;
    main.insertAdjacentHTML('beforeend',`<div class="kpi-grid">${kpi('Total Reactor Volume','Summary','C28','m³','bio')}${kpi('Final Treated Flow','Summary','C6','m³/d','water')}${kpi('Process Power','Summary','C38','kW','energy')}${kpi('Specific Energy','Summary','C40','kWh/m³','footprint')}</div>`);
    const waterKpi=main.querySelector('.kpi.water .value');
    if(waterKpi)waterKpi.innerHTML=`${esc(formatValue(finalQ,'m³/d'))}<span class="unit">m³/d</span>`;
    normalizeTrainStages();
    const addBubble=idx=>`<button class="train-add" data-add-index="${idx}" title="Add a unit operation here" aria-label="Add unit operation">+</button>`;
    const train=treatmentTrain.length?treatmentTrain.map((u,i)=>{
      const d=unitDef(u.type),duplicate=treatmentTrain.filter(x=>x.type===u.type).length>1,stage=duplicate?` · Stage ${u.stage}`:'',state=network.water.byId[u.id],displayName=u.name||d.name,displayTag=u.tag||d.tag;
      return `${addBubble(i)}<div class="train-node active draggable" draggable="true" data-unit-id="${esc(u.id)}" tabindex="0" title="Open ${esc(displayName)} design module">
        <button class="train-remove" data-remove-id="${esc(u.id)}" title="Remove unit">×</button>
        <span class="tiny">${esc(displayTag)}${esc(stage)}</span><strong>${esc(displayName)}</strong>
        <span class="train-flow">Q ${esc(formatValue(state?.inlet?.flow||0,'m³/d'))} → ${esc(formatValue(state?.forward?.flow||0,'m³/d'))} m³/d</span>
        <span class="train-quality">BOD ${esc(formatValue(streamConc(state?.forward,'bod'),'mg/L'))} · TSS ${esc(formatValue(streamConc(state?.forward,'tss'),'mg/L'))} · NH₄ ${esc(formatValue(streamConc(state?.forward,'nh4'),'mg/L'))} · TN ${esc(formatValue(streamConc(state?.forward,'tn'),'mg/L'))} · TP ${esc(formatValue(streamConc(state?.forward,'tp'),'mg/L'))}</span>
      </div>`;
    }).join('<span class="arrow">→</span>')+addBubble(treatmentTrain.length):`${addBubble(0)}<div class="empty">Add the first unit operation to build the treatment train.</div>`;
    const pmax=Math.max(1,Number(v('Summary','C38')),Number(v('Summary','C37')));
    const totalSludge=network.water.sludgeSources.reduce((a,s)=>a+(s.mass?.tss||0),0);
    const chem=[
      ['Alkali',Number(v('Summary','C44')),'kg/d'],['External carbon',Number(v('Summary','C45')),'kg/d'],['Coagulant',Number(v('Summary','C46')),'kg/d'],
      ['Dewatering polymer',network.sludge.summary.polymerKgD,'kg/d'],['Waste sludge',totalSludge,'kg DS/d'],['Wet cake',network.sludge.summary.wetCakeTD,'t/d']
    ].map(([n,x,u])=>`<div class="mini"><label>${esc(n)}</label><b>${esc(formatValue(x,u))} <span class="unit">${esc(u)}</span></b></div>`).join('');
    main.insertAdjacentHTML('beforeend',`<div class="dashboard-grid">
      <div class="panel train-builder-panel"><div class="panel-head"><div><h3>Configured Water Treatment Train</h3><span class="panel-sub">Each unit receives the calculated outlet from the unit immediately upstream, plus any recycles or sludge-line returns directed to that inlet.</span></div><span class="chip">${network.totalWaterIterations||network.water.iterations} total water iterations · ${network.outerIterations||0} coupled iterations</span></div><div class="panel-body"><div class="train train-builder" id="trainBuilder">${train}</div><div class="train-hint"><b>Sequential basis:</b> unit order is part of the calculation. Adding, removing, duplicating or reordering a unit recalculates every downstream concentration and sludge source.</div><div class="recycle-section"><div class="subpanel-head"><div><h4>Recirculation Connections</h4><span>Return liquid, separated sludge/underflow, or membrane residuals to any selected upstream inlet using plant-flow ratio, fixed flow, or percent of source flow.</span></div><button class="action secondary" id="addRecycle">+ Add recirculation</button></div><div class="recycle-list">${recycleCardsHtml(network)}</div></div></div></div>
      <div class="panel effluent-panel"><div class="panel-head"><h3>Predicted Final Effluent</h3><span class="chip">Calculated network outlet</span></div><div class="panel-body"><table class="eff-table"><thead><tr><th>Determinand</th><th>Predicted</th><th>Target</th><th>Status</th></tr></thead><tbody>${effluentRows(network)}</tbody></table><div class="final-flow-note">Final water-line flow: <b>${esc(formatValue(finalQ,'m³/d'))} m³/d</b>. Predicted concentrations are recalculated from the final stream mass and flow every time the network changes.</div>${complianceGuidanceHtml(network)}</div></div>
      <div class="panel"><div class="panel-head"><h3>Aeration & Energy</h3><span class="chip">Workbook sizing basis</span></div><div class="panel-body"><div class="metric-row"><span>Net AOR</span><div class="bar"><span style="width:88%"></span></div><b>${esc(formatValue(v('Summary','C34'),'kg O₂/d'))}</b></div><div class="metric-row"><span>Blower shaft power</span><div class="bar"><span style="width:${Math.min(100,Number(v('Summary','C37'))/pmax*100)}%"></span></div><b>${esc(formatValue(v('Summary','C37'),'kW'))}</b></div><div class="metric-row"><span>Total process power</span><div class="bar"><span style="width:${Math.min(100,Number(v('Summary','C38'))/pmax*100)}%"></span></div><b>${esc(formatValue(v('Summary','C38'),'kW'))}</b></div><div class="note-card">Validated reactor, oxygen and power sizing remains workbook-linked. The new network layer provides the order-sensitive water-quality and residuals routing calculation.</div></div></div>
      <div class="panel"><div class="panel-head"><h3>Chemicals & Residuals</h3><span class="chip">Integrated totals</span></div><div class="panel-body"><div class="chem-grid">${chem}</div></div></div>
      ${sludgeNetworkPanelHtml(network)}
    </div>${networkWarningsHtml(network)}<div id="networkModal" class="train-picker hidden"></div>`);
    const mb=main.querySelector('#openMassBalance');if(mb)mb.onclick=()=>navigateTo('MassBalance');
    const report=main.querySelector('#openCompactReport');if(report)report.onclick=()=>navigateTo('CompactReport');
    const roExport=main.querySelector('#exportTotalRO');if(roExport)roExport.onclick=exportToTotalRODesign;
    const review=main.querySelector('#reviewBypassedInputs');if(review)review.onclick=()=>navigateTo('MarketIntake');
    bindTrainBuilder();bindRecycleControls();bindSludgeNetwork();bindComplianceGuidance();updateCalcState();
  }

  function renderTrainPicker(index,anchor,scope='water',lineId=null){
    const picker=main.querySelector('#networkModal');if(!picker)return;
    const available=unitCatalog.filter(u=>scope==='sludge'?u.group==='Residuals':u.group!=='Residuals');const groups=[...new Set(available.map(u=>u.group))];
    const cards=groups.map(g=>`<section class="picker-group" data-picker-group="${esc(g)}"><span>${esc(g)} <em>${available.filter(u=>u.group===g).length}</em></span><div>${available.filter(u=>u.group===g).map(u=>`<button class="picker-unit" data-unit-type="${esc(u.type)}" data-search="${esc(unitSearchText(u))}"><i>${esc(u.badge)}</i><b>${esc(u.name)}</b><small>${esc(u.tag)}</small></button>`).join('')}</div></section>`).join('');
    const groupChips=['All',...groups].map((g,i)=>{const total=g==='All'?available.length:available.filter(u=>u.group===g).length;return `<button class="picker-category${i===0?' active':''}" data-picker-category="${esc(g)}">${esc(g)} <em>${total}</em></button>`;}).join('');
    const title=scope==='sludge'?'Add residuals / dewatering operation':'Add water-line unit operation';
    picker.innerHTML=`<div class="picker-shell" role="dialog" aria-modal="true" aria-labelledby="pickerTitle"><div class="picker-head"><div><b id="pickerTitle">${title}</b><small>${available.length} options · duplicates and series stages allowed</small></div><button id="pickerClose" type="button" aria-label="Close selector">×</button></div><div class="picker-tools"><input id="pickerSearch" type="search" placeholder="Search DAF, phosphate, MBBR, equalization, centrifuge…" autocomplete="off"><span id="pickerVisibleCount">${available.length} operations shown · insert at position ${index+1}</span></div><div class="picker-categories">${groupChips}</div><div class="picker-scroll">${cards}<div id="pickerEmpty" class="picker-empty" hidden><b>No matching unit operations</b><span>Try a broader search or select another category.</span></div></div><div class="picker-footer"><span>${scope==='water'?'Click a process tile to insert it at position '+(index+1)+'. RO and NF are designed in Total RO Design.':'Click a residuals tile to insert it at position '+(index+1)+'.'}</span><button id="pickerCancel" type="button" class="action secondary">Cancel</button></div></div>`;
    picker.classList.remove('hidden');document.body.classList.add('unit-picker-open');
    const close=()=>{picker.classList.add('hidden');document.body.classList.remove('unit-picker-open');document.removeEventListener('keydown',onKey);if(anchor?.focus)anchor.focus();};const onKey=e=>{if(e.key==='Escape')close();};document.addEventListener('keydown',onKey);
    picker.querySelector('#pickerClose').onclick=close;picker.querySelector('#pickerCancel').onclick=close;picker.onclick=e=>{if(e.target===picker)close();};
    const search=picker.querySelector('#pickerSearch'),count=picker.querySelector('#pickerVisibleCount');let activeGroup='All';
    const applyFilter=()=>{const terms=search.value.trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').split(/\s+/).filter(Boolean);let visible=0;picker.querySelectorAll('.picker-unit').forEach(b=>{const group=b.closest('.picker-group').dataset.pickerGroup,text=b.dataset.search,show=(activeGroup==='All'||group===activeGroup)&&terms.every(t=>text.includes(t));b.hidden=!show;if(show)visible++;});picker.querySelectorAll('.picker-group').forEach(g=>{g.hidden=[...g.querySelectorAll('.picker-unit')].every(b=>b.hidden);});picker.querySelector('#pickerEmpty').hidden=visible!==0;count.textContent=`${visible} operation${visible===1?'':'s'} shown · insert at position ${index+1}`;};
    picker.querySelectorAll('[data-picker-category]').forEach(b=>b.onclick=()=>{activeGroup=b.dataset.pickerCategory;picker.querySelectorAll('.picker-category').forEach(x=>x.classList.toggle('active',x===b));applyFilter();picker.querySelector('.picker-scroll').scrollTop=0;});search.oninput=applyFilter;setTimeout(()=>search.focus(),0);
    picker.querySelectorAll('[data-unit-type]').forEach(b=>b.onclick=()=>{if(scope==='sludge'){const line=sludgeLines.find(x=>x.id===lineId);if(line)line.units.splice(index,0,makeSludgeUnit(b.dataset.unitType));}else treatmentTrain.splice(index,0,makeUnit(b.dataset.unitType));saveNetwork();close();scope==='sludge'?render():renderDashboard();toast('Unit operation added');});
  }
  function renderSludgeSourcePicker(lineId,anchor){
    const picker=main.querySelector('#networkModal'),line=sludgeLines.find(x=>x.id===lineId);if(!picker||!line)return;const network=calculateNetwork();const existing=new Map((line.sources||[]).map(x=>[x.unitId,x.fraction]));const candidates=treatmentTrain.filter(u=>processNetwork.canProduceSludge(u.type));
    const cards=candidates.map(u=>{const source=network.water.sludgeSources.find(s=>s.sourceUnitId===u.id);const checked=existing.has(u.id);return `<label class="source-option"><input type="checkbox" data-source-check="${esc(u.id)}" ${checked?'checked':''}><div><b>${esc(u.name||unitDef(u.type).name)}</b><span>${esc(unitDef(u.type).group)} · currently ${esc(formatValue(source?.mass?.tss||0,'kg/d'))} kg DS/d</span></div><div class="source-allocation"><input type="number" min="0" max="100" step="1" data-source-fraction="${esc(u.id)}" value="${Math.round((existing.get(u.id)??1)*100)}"><em>%</em></div></label>`;}).join('');
    picker.innerHTML=`<div class="picker-shell source-shell" role="dialog" aria-modal="true"><div class="picker-head"><div><b>Assign sludge sources</b><small>Select exactly where this dewatering line receives sludge. Sources may be divided between parallel lines using allocation percentages.</small></div><button id="pickerClose">×</button></div><div class="picker-scroll source-scroll">${cards||'<div class="picker-empty"><b>No sludge-producing water units are available</b><span>Add a clarifier, DAF, MBR, membrane separator or another solids-separation unit first.</span></div>'}</div><div class="picker-footer"><span>Across all lines, allocations above 100% are automatically normalized by the solver.</span><div><button id="pickerCancel" class="action secondary">Cancel</button><button id="sourceApply" class="action primary-action">Apply sources</button></div></div></div>`;
    picker.classList.remove('hidden');document.body.classList.add('unit-picker-open');const close=()=>{picker.classList.add('hidden');document.body.classList.remove('unit-picker-open');document.removeEventListener('keydown',onKey);anchor?.focus?.();};const onKey=e=>{if(e.key==='Escape')close();};document.addEventListener('keydown',onKey);picker.querySelector('#pickerClose').onclick=close;picker.querySelector('#pickerCancel').onclick=close;picker.onclick=e=>{if(e.target===picker)close();};
    const apply=picker.querySelector('#sourceApply');if(apply)apply.onclick=()=>{line.sources=[];picker.querySelectorAll('[data-source-check]').forEach(ch=>{if(ch.checked){const id=ch.dataset.sourceCheck,frac=Number(picker.querySelector(`[data-source-fraction="${CSS.escape(id)}"]`)?.value)/100;line.sources.push({unitId:id,fraction:Math.max(0,Math.min(1,frac||0))});}});saveNetwork();close();render();toast('Sludge sources updated');};
  }
    function bindRecycleControls(){
    const add=main.querySelector('#addRecycle');
    if(add)add.onclick=()=>{
      if(treatmentTrain.length<2){toast('Add at least two water-line units first');return;}
      recycles.push({
        id:newId('r',++recycleSeq),
        name:`Recirculation ${recycles.length+1}`,
        sourceUnitId:treatmentTrain[treatmentTrain.length-1].id,
        targetUnitId:treatmentTrain[0].id,
        sourcePort:'liquid',
        basis:'ratio',
        value:1,
        enabled:true
      });
      saveNetwork();renderDashboard();
    };
    main.querySelectorAll('.recycle-card').forEach(card=>{
      const r=recycles.find(x=>x.id===card.dataset.recycleId);if(!r)return;
      const rerender=()=>{saveNetwork();renderDashboard();};
      card.querySelector('[data-recycle-name]').onchange=e=>{r.name=e.target.value.trim()||'Recirculation';rerender();};
      card.querySelector('[data-recycle-enabled]').onchange=e=>{r.enabled=e.target.checked;rerender();};
      card.querySelector('[data-recycle-source]').onchange=e=>{
        r.sourceUnitId=e.target.value;
        if(r.sourceUnitId===r.targetUnitId)r.targetUnitId=treatmentTrain.find(u=>u.id!==r.sourceUnitId)?.id||'';
        rerender();
      };
      card.querySelector('[data-recycle-port]').onchange=e=>{
        r.sourcePort=['sludge','residual'].includes(e.target.value)?e.target.value:'liquid';
        if(r.sourcePort==='sludge'){r.basis='source_fraction';r.value=90;}
        else if(r.sourcePort==='residual'){r.basis='source_fraction';r.value=100;}
        else if(r.basis==='source_fraction'){r.basis='ratio';r.value=1;}
        rerender();
      };
      card.querySelector('[data-recycle-target]').onchange=e=>{
        r.targetUnitId=e.target.value;
        if(r.sourceUnitId===r.targetUnitId)r.sourceUnitId=[...treatmentTrain].reverse().find(u=>u.id!==r.targetUnitId)?.id||'';
        rerender();
      };
      card.querySelector('[data-recycle-basis]').onchange=e=>{
        r.basis=e.target.value;
        if(r.basis==='source_fraction')r.value=Math.max(0,Math.min(100,Number(r.value)||100));
        rerender();
      };
      card.querySelector('[data-recycle-value]').onchange=e=>{
        let value=Math.max(0,Number(e.target.value)||0);
        if(r.basis==='source_fraction')value=Math.min(100,value);
        r.value=value;rerender();
      };
      card.querySelector('[data-recycle-delete]').onclick=()=>{recycles=recycles.filter(x=>x.id!==r.id);saveNetwork();renderDashboard();};
    });
  }

    function bindSludgeNetwork(){
    const strategy=main.querySelector('#sludgeStrategy');
    if(strategy)strategy.onchange=e=>{
      const next=e.target.value;
      if(next==='common'&&sludgeLines.length>1){
        if(!confirm('Combine the source assignments into the first sludge line and remove the other parallel lines?')){strategy.value='parallel';return;}
        const first=sludgeLines[0],merged={};
        for(const line of sludgeLines)for(const src of line.sources||[])merged[src.unitId]=Math.min(1,(merged[src.unitId]||0)+(Number(src.fraction)||0));
        first.sources=Object.entries(merged).map(([unitId,fraction])=>({unitId,fraction}));
        first.name='Common Sludge Line';
        if(!(first.units||[]).some(u=>u.type==='sludge_equalization'))first.units.unshift(makeSludgeUnit('sludge_equalization'));
        sludgeLines=[first];
      }
      sludgeStrategy=next;saveNetwork();render();
    };
    const addLine=main.querySelector('#addSludgeLine');
    if(addLine)addLine.onclick=()=>{
      sludgeStrategy='parallel';
      sludgeLines.push({
        id:newId('sl',++sludgeLineSeq),
        name:`Parallel Sludge Line ${sludgeLines.length+1}`,
        sources:[],returnEnabled:true,returnFraction:1,
        returnTargetUnitId:treatmentTrain[0]?.id||'',
        units:['sludge_equalization','centrifuge'].map(makeSludgeUnit)
      });
      saveNetwork();render();
    };
    main.querySelectorAll('.sludge-line').forEach(el=>{
      const line=sludgeLines.find(x=>x.id===el.dataset.sludgeLineId);if(!line)return;
      const name=el.querySelector('[data-sludge-line-name]');
      if(name)name.onchange=e=>{line.name=e.target.value.trim()||'Sludge Line';saveNetwork();};
      const assign=el.querySelector('[data-assign-sources]');if(assign)assign.onclick=()=>renderSludgeSourcePicker(line.id,assign);
      const del=el.querySelector('[data-delete-sludge-line]');
      if(del)del.onclick=()=>{sludgeLines=sludgeLines.filter(x=>x.id!==line.id);if(sludgeLines.length<=1)sludgeStrategy='common';saveNetwork();render();};
      const re=el.querySelector('[data-return-enabled]');
      if(re)re.onchange=e=>{line.returnEnabled=e.target.checked;saveNetwork();render();};
      const rt=el.querySelector('[data-return-target]');
      if(rt)rt.onchange=e=>{line.returnTargetUnitId=e.target.value;saveNetwork();render();};
      const rf=el.querySelector('[data-return-fraction]');
      if(rf)rf.onchange=e=>{line.returnFraction=Math.max(0,Math.min(1,(Number(e.target.value)||0)/100));saveNetwork();render();};
      el.querySelectorAll('[data-sludge-add-index]').forEach(b=>b.onclick=e=>{e.stopPropagation();renderTrainPicker(Number(b.dataset.sludgeAddIndex),b,'sludge',line.id);});
      el.querySelectorAll('.sludge-node').forEach(n=>{
        n.onclick=e=>{if(e.target.closest('[data-sludge-remove]'))return;activeSludgeUnit={lineId:line.id,unitId:n.dataset.sludgeUnitId};activeUnitId=null;current='SludgeUnitDetail';renderNav();render();};
        n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();n.click();}};
        const remove=n.querySelector('[data-sludge-remove]');
        if(remove)remove.onclick=e=>{e.stopPropagation();line.units=line.units.filter(u=>u.id!==n.dataset.sludgeUnitId);saveNetwork();render();};
        n.ondragstart=e=>{e.dataTransfer.setData('text/plain',n.dataset.sludgeUnitId);n.classList.add('dragging');};
        n.ondragend=()=>n.classList.remove('dragging');
        n.ondragover=e=>{e.preventDefault();n.classList.add('drag-over');};
        n.ondragleave=()=>n.classList.remove('drag-over');
        n.ondrop=e=>{e.preventDefault();n.classList.remove('drag-over');const id=e.dataTransfer.getData('text/plain'),from=line.units.findIndex(u=>u.id===id),to=line.units.findIndex(u=>u.id===n.dataset.sludgeUnitId);if(from<0||to<0||from===to)return;const [moved]=line.units.splice(from,1);line.units.splice(to,0,moved);saveNetwork();render();};
      });
    });
  }

  function openUnit(u){const d=unitDef(u.type);activeUnitId=u.id;activeSludgeUnit=null;if(d.tab==='UnitOperationDetail'||d.tab==='MarketIntake'){current='UnitOperationDetail';renderNav();render();return;}current=d.tab;renderNav();render();}
  function renderUnitOperationDetail(){
    const u=treatmentTrain.find(x=>x.id===activeUnitId)||treatmentTrain[0];if(!u){current='Dashboard';renderNav();renderDashboard();return;}const d=unitDef(u.type),network=calculateNetwork();main.innerHTML=`<div class="page-head"><div class="page-title"><h1>${esc(u.name||d.name)}</h1><p>${esc(d.group)} · ${esc(u.tag||d.tag)} · Individual sequential unit model</p></div></div>${activeUnitPanelHtml(u,network,false)}`;bindActiveUnitPanel(u);updateCalcState();
  }
    function renderResidualsNetwork(){
    const network=calculateNetwork();
    main.innerHTML=`<div class="page-head"><div class="page-title"><h1>Residuals & Dewatering Network</h1><p>Assign sludge from individual water-line operations to a common equalized treatment line or to multiple independent dewatering systems. Return all or part of each centrate/filtrate stream to a selected water-unit inlet.</p></div><div class="page-head-actions"><button class="action secondary" id="residualsDashboard">← Dashboard</button><button class="action secondary" id="residualsMassBalance">Full Mass Balance</button><div class="head-tag">Source-routed residuals</div></div></div>${sludgeNetworkPanelHtml(network,true)}${networkWarningsHtml(network)}<div id="networkModal" class="train-picker hidden"></div>`;
    main.querySelector('#residualsDashboard').onclick=()=>{current='Dashboard';renderNav();render();};
    main.querySelector('#residualsMassBalance').onclick=()=>{current='MassBalance';renderNav();render();};
    bindSludgeNetwork();updateCalcState();
  }

  function sludgeStreamRows(inlet,outlet,ret){return [['Flow','flow','m³/d'],['Dry solids','tss','kg/d'],['Volatile solids','vss','kg/d'],['COD load','cod','kg/d'],['Ammonia-N load','nh4','kg/d'],['Total-P load','tp','kg/d']].map(([name,key,u])=>{const a=key==='flow'?inlet.flow:inlet.mass[key],b=key==='flow'?outlet.flow:outlet.mass[key],c=key==='flow'?ret.flow:ret.mass[key];return `<tr><td>${name}</td><td>${esc(formatValue(a,u))}</td><td>${esc(formatValue(b,u))}</td><td>${esc(formatValue(c,u))}</td></tr>`;}).join('');}
    function renderSludgeUnitDetail(){
    const line=sludgeLines.find(x=>x.id===activeSludgeUnit?.lineId);
    const u=line?.units.find(x=>x.id===activeSludgeUnit?.unitId);
    if(!line||!u){current='ResidualsNetwork';renderNav();renderResidualsNetwork();return;}
    const network=calculateNetwork();
    const lr=network.sludge.lines.find(x=>x.line.id===line.id);
    const idx=line.units.findIndex(x=>x.id===u.id),state=lr?.units?.[idx],d=unitDef(u.type);
    const profile=processNetwork.sludgeProfileForType(u.type),cfg={...processNetwork.sludgeDefaultConfig(u.type),...(u.config||{})};
    const fields=processNetwork.sludgeProfileFields(u.type);
    const controls=fields.length?fields.map(f=>performanceFieldHtml(f,cfg,'sludge-config')).join(''):'<div class="unit-pass-note">This residuals operation transfers the sludge without changing its properties.</div>';
    const parallel=Math.max(1,Math.round(Number(state?.metrics?.parallelUnits)||1));
    main.innerHTML=`<div class="page-head"><div class="page-title"><h1>${esc(u.name||d.name)}</h1><p>${esc(line.name)} · Residuals-train position ${idx+1}</p></div><button class="action secondary" id="backResiduals">← Residuals Network</button></div>
      <section class="section-card active-unit-context">
        <div class="section-title">Residuals Unit Configuration</div>
        <div class="active-unit-head"><div><span class="unit-group">${esc(d.group)}</span><h3>${esc(profile.name)}</h3><p>${esc(profile.description)}</p></div><div class="stream-flow-readout"><span>Outlet dry solids</span><b>${esc(formatValue(state?.outlet?.mass?.tss||0,'kg/d'))} kg/d</b></div></div>
        <div class="unit-identity-grid"><label><span>Display name</span><input id="sludgeDisplayName" class="input-control" value="${esc(u.name||d.name)}"></label><label><span>Process tag / duty</span><input id="sludgeDisplayTag" class="input-control" value="${esc(u.tag||d.tag)}"></label></div>
        <div class="unit-balance-grid"><div><h4>Residuals Balance</h4><table class="eff-table stream-table"><thead><tr><th>Parameter</th><th>Inlet</th><th>Outlet</th><th>Separated liquid</th></tr></thead><tbody>${sludgeStreamRows(state?.inlet||processNetwork.makeStream(0),state?.outlet||processNetwork.makeStream(0),state?.returnStream||processNetwork.makeStream(0))}</tbody></table></div><div><h4>Performance & Equipment Assumptions</h4><div class="performance-grid">${controls}</div><div class="performance-actions"><button class="action secondary" id="resetSludgeDefaults">Restore planning defaults</button><span>Parallel equipment divides the hydraulic and solids duty; total line mass balance is unchanged.</span></div></div></div>
        <div class="unit-balance-footer residual-unit-footer"><span>Equalization / storage volume</span><b>${esc(formatValue(state?.metrics?.equalizationVolumeM3||0,'m³'))} m³</b><span>Polymer</span><b>${esc(formatValue(state?.metrics?.polymerKgD||0,'kg/d'))} kg/d</b><span>Parallel equipment</span><b>${parallel}</b><span>Feed per equipment</span><b>${esc(formatValue(state?.metrics?.feedFlowPerUnitM3d||0,'m³/d'))} m³/d · ${esc(formatValue(state?.metrics?.feedDrySolidsPerUnitKgD||0,'kg/d'))} kg DS/d</b><span>Wet cake per equipment</span><b>${esc(formatValue(state?.metrics?.wetCakePerUnitTD||0,'t/d'))} t/d</b></div>
      </section>`;
    main.querySelector('#backResiduals').onclick=()=>{current='ResidualsNetwork';activeSludgeUnit=null;renderNav();renderResidualsNetwork();};
    main.querySelector('#sludgeDisplayName').onchange=e=>{u.name=e.target.value.trim()||d.name;saveNetwork();render();};
    main.querySelector('#sludgeDisplayTag').onchange=e=>{u.tag=e.target.value.trim()||d.tag;saveNetwork();render();};
    main.querySelectorAll('[data-sludge-config]').forEach(inp=>inp.onchange=()=>{
      let val=Number(inp.value);
      if(inp.dataset.sludgeConfig==='parallelUnits')val=Math.max(1,Math.round(val||1));
      u.config={...processNetwork.sludgeDefaultConfig(u.type),...(u.config||{}),[inp.dataset.sludgeConfig]:val};saveNetwork();render();
    });
    main.querySelector('#resetSludgeDefaults').onclick=()=>{u.config=processNetwork.sludgeDefaultConfig(u.type);saveNetwork();render();};
    updateCalcState();
  }

  function bindTrainBuilder(){
    const builder=main.querySelector('#trainBuilder');if(!builder)return;builder.querySelectorAll('.train-add').forEach(b=>b.onclick=e=>{e.stopPropagation();renderTrainPicker(Number(b.dataset.addIndex),b,'water');});builder.querySelectorAll('.train-remove').forEach(b=>b.onclick=e=>{e.stopPropagation();removeWaterUnit(b.dataset.removeId);renderDashboard();toast('Unit operation removed');});builder.querySelectorAll('.train-node[data-unit-id]').forEach(n=>{n.onclick=e=>{if(e.target.closest('.train-remove'))return;const u=treatmentTrain.find(x=>x.id===n.dataset.unitId);if(u)openUnit(u);};n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();const u=treatmentTrain.find(x=>x.id===n.dataset.unitId);if(u)openUnit(u);}};n.ondragstart=e=>{e.dataTransfer.setData('text/plain',n.dataset.unitId);n.classList.add('dragging');};n.ondragend=()=>n.classList.remove('dragging');n.ondragover=e=>{e.preventDefault();n.classList.add('drag-over');};n.ondragleave=()=>n.classList.remove('drag-over');n.ondrop=e=>{e.preventDefault();n.classList.remove('drag-over');const id=e.dataTransfer.getData('text/plain'),from=treatmentTrain.findIndex(u=>u.id===id),to=treatmentTrain.findIndex(u=>u.id===n.dataset.unitId);if(from<0||to<0||from===to)return;const [moved]=treatmentTrain.splice(from,1);treatmentTrain.splice(to,0,moved);saveNetwork();renderDashboard();toast('Treatment train reordered');};});
  }
  function renderMassBalance(){
    engine.errors=[];
    const network=calculateNetwork();
    const inlet=influentStream(),outlet=network.water.finalEffluent;
    const recycleTotal=network.water.recycles.reduce((a,s)=>a+(s.flow||0),0);
    const waterRows=network.water.units.map((state,i)=>{
      const u=state.unit,d=unitDef(u.type),residual=state.sludgeAvailable?.mass?.tss||0;
      return `<tr>
        <td>${i+1}</td><td><b>${esc(u.name||d.name)}</b><small>${esc(d.group)} · ${esc(u.tag||d.tag)}</small></td>
        <td>${esc(formatValue(state.inlet.flow,'m³/d'))}</td><td>${esc(formatValue(state.forward.flow,'m³/d'))}</td>
        <td>${esc(formatValue(streamConc(state.inlet,'bod'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'bod'),'mg/L'))}</td>
        <td>${esc(formatValue(streamConc(state.forward,'tss'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'nh4'),'mg/L'))}</td>
        <td>${esc(formatValue(streamConc(state.forward,'tn'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'tp'),'mg/L'))}</td>
        <td>${esc(formatValue(residual,'kg/d'))}</td>
      </tr>`;
    }).join('');
    const recycleRows=recycles.length?recycles.map(r=>{
      const actual=network.water.recycles.find(x=>x.recycleId===r.id);
      const port=processNetwork.recyclePortLabel?processNetwork.recyclePortLabel(r.sourcePort):r.sourcePort;
      return `<tr><td>${esc(r.name||'Recirculation')}</td><td>${esc(unitNameById(r.sourceUnitId))}</td><td>${esc(port)}</td><td>${esc(unitNameById(r.targetUnitId))}</td><td>${r.enabled===false?'Disabled':`${esc(formatValue(actual?.flow||0,'m³/d'))} m³/d`}</td><td>${esc(formatValue(streamConc(actual,'tss'),'mg/L'))}</td><td>${esc(formatValue(streamConc(actual,'tn'),'mg/L'))}</td><td>${esc(formatValue(streamConc(actual,'tp'),'mg/L'))}</td></tr>`;
    }).join(''):'<tr><td colspan="8" class="empty-cell">No recirculation connections are configured.</td></tr>';
    const sludgeRows=network.sludge.lines.map((lr,i)=>{
      const line=lr.line,sources=(line.sources||[]).map(s=>`${unitNameById(s.unitId)} (${Math.round((Number(s.fraction)||0)*100)}%)`).join(', ')||'None assigned';
      const ds=lr.output.flow>0?lr.output.mass.tss/(lr.output.flow*1000)*100:0;
      const equipment=(line.units||[]).map(u=>{const cfg={...processNetwork.sludgeDefaultConfig(u.type),...(u.config||{})};const n=Math.max(1,Math.round(Number(cfg.parallelUnits)||1));return `${u.name||unitDef(u.type).name}${n>1?` (${n} parallel)`:''}`;}).join(' → ')||'No operations';
      return `<tr><td>${i+1}</td><td><b>${esc(line.name)}</b><small>${esc(sources)}</small></td><td>${esc(equipment)}</td><td>${esc(formatValue(lr.input.mass.tss,'kg/d'))}</td><td>${esc(formatValue(lr.input.flow,'m³/d'))}</td><td>${esc(formatValue(lr.cakeDrySolidsKgD,'kg/d'))}</td><td>${esc(formatValue(ds,'%'))}</td><td>${esc(formatValue(lr.wetCakeTD,'t/d'))}</td><td>${esc(formatValue(lr.returnStream?.flow||0,'m³/d'))}</td><td>${esc(unitNameById(line.returnTargetUnitId))}</td></tr>`;
    }).join('');
    main.innerHTML=`<div class="page-head"><div class="page-title"><h1>Process Mass Balance</h1><p>Trace every water-line outlet, recirculation connection, sludge source, dewatering line, and returned sidestream. Unit order and source routing are part of the calculation.</p></div><div class="page-head-actions"><button class="action secondary" id="backDashboard">← Dashboard</button><button class="action secondary" id="openResiduals">Residuals Network</button><div class="head-tag ${network.converged&&network.water.converged?'':'warning-tag'}">${network.converged&&network.water.converged?'Converged':'Review network'}</div></div></div>
      <div class="balance-summary">
        <div><span>Plant influent</span><b>${esc(formatValue(inlet.flow,'m³/d'))} m³/d</b></div>
        <div><span>Final effluent</span><b>${esc(formatValue(outlet.flow,'m³/d'))} m³/d</b></div>
        <div><span>Total recirculation</span><b>${esc(formatValue(recycleTotal,'m³/d'))} m³/d</b></div>
        <div><span>Waste sludge routed</span><b>${esc(formatValue(network.sludge.summary.cakeDrySolidsKgD,'kg/d'))} kg DS/d</b></div>
        <div><span>Returned sidestream</span><b>${esc(formatValue(network.sludge.summary.returnedLiquidM3D||0,'m³/d'))} m³/d</b></div>
        <div><span>Solver iterations</span><b>${network.totalWaterIterations||network.water.iterations} water / ${network.outerIterations||0} coupled</b></div>
      </div>
      <section class="section-card balance-section"><div class="section-title">Ordered Water-Line Balance</div><div class="balance-table-wrap"><table class="eff-table balance-table"><thead><tr><th>#</th><th>Unit operation</th><th>Inlet Q<br>m³/d</th><th>Forward Q<br>m³/d</th><th>Inlet BOD<br>mg/L</th><th>Outlet BOD<br>mg/L</th><th>Outlet TSS<br>mg/L</th><th>Outlet NH₄-N<br>mg/L</th><th>Outlet TN<br>mg/L</th><th>Outlet TP<br>mg/L</th><th>Waste sludge<br>kg DS/d</th></tr></thead><tbody>${waterRows||'<tr><td colspan="11" class="empty-cell">No water-line units are configured.</td></tr>'}</tbody></table></div></section>
      <section class="section-card balance-section"><div class="section-title">Recirculation Connections</div><div class="balance-table-wrap"><table class="eff-table balance-table"><thead><tr><th>Connection</th><th>Source</th><th>Source stream</th><th>Target inlet</th><th>Actual flow</th><th>TSS mg/L</th><th>TN mg/L</th><th>TP mg/L</th></tr></thead><tbody>${recycleRows}</tbody></table></div></section>
      <section class="section-card balance-section"><div class="section-title">Sludge Treatment & Dewatering</div><div class="balance-table-wrap"><table class="eff-table balance-table"><thead><tr><th>#</th><th>Line / sources</th><th>Residuals operations</th><th>Feed kg DS/d</th><th>Feed m³/d</th><th>Cake kg DS/d</th><th>Cake %DS</th><th>Wet cake t/d</th><th>Returned m³/d</th><th>Return target</th></tr></thead><tbody>${sludgeRows||'<tr><td colspan="10" class="empty-cell">No sludge lines are configured.</td></tr>'}</tbody></table></div></section>
      <section class="section-card final-stream-card"><div class="section-title">Final Water-Line Stream</div><div class="final-stream-grid">${[['Flow',outlet.flow,'m³/d'],['COD',streamConc(outlet,'cod'),'mg/L'],['BOD₅',streamConc(outlet,'bod'),'mg/L'],['TSS',streamConc(outlet,'tss'),'mg/L'],['Ammonia-N',streamConc(outlet,'nh4'),'mg/L'],['Total nitrogen',streamConc(outlet,'tn'),'mg/L'],['Total phosphorus',streamConc(outlet,'tp'),'mg/L'],['Alkalinity',streamConc(outlet,'alk'),'mg/L as CaCO₃']].map(([n,x,u])=>`<div><span>${esc(n)}</span><b>${esc(formatValue(x,u))}</b><em>${esc(u)}</em></div>`).join('')}</div></section>
      ${networkWarningsHtml(network)}`;
    main.querySelector('#backDashboard').onclick=()=>navigateTo('Dashboard');
    main.querySelector('#openResiduals').onclick=()=>navigateTo('ResidualsNetwork');
    updateCalcState();
  }
  function reportFlow(q){
    const n=Number(q)||0;
    return `${formatValue(n,'m³/d')} m³/d (${formatValue(n*M3D_TO_GPD,'gpd')} gpd)`;
  }
  function reportTemperature(celsius){
    const n=Number(celsius);
    if(!Number.isFinite(n))return '—';
    return `${formatValue(n,'°C')} °C (${formatValue(n*9/5+32,'°F')} °F)`;
  }
  function reportKeyGrid(items){
    return `<div class="report-kv-grid">${items.map(([label,value])=>`<div class="report-kv"><span>${esc(label)}</span><b>${value}</b></div>`).join('')}</div>`;
  }
  function reportStreamQuality(stream){
    return `BOD₅ ${formatValue(streamConc(stream,'bod'),'mg/L')}; TSS ${formatValue(streamConc(stream,'tss'),'mg/L')}; NH₄-N ${formatValue(streamConc(stream,'nh4'),'mg/L')}; TN ${formatValue(streamConc(stream,'tn'),'mg/L')}; TP ${formatValue(streamConc(stream,'tp'),'mg/L')} mg/L`;
  }
  function reportAssumptionRows(network,status){
    const rows=[];
    for(const spec of status.bypassed){
      const entry=bypassedMandatory[spec.key],effect=spec.target?'The target is excluded from the PASS/FAIL assessment; the fallback is used only for workbook planning calculations.':'The fallback is used as an explicit planning assumption.';
      rows.push(`<tr><td>Bypassed mandatory input</td><td><b>${esc(spec.label)}</b>: ${esc(mandatoryFallbackDisplay(spec,entry?.value))}. ${esc(effect)}</td></tr>`);
    }
    for(const warning of network.warnings||[])rows.push(`<tr><td>Network review</td><td>${esc(warning)}</td></tr>`);
    const unassigned=Number(network.sludge?.summary?.unassignedDrySolidsKgD)||0;
    if(unassigned>1e-6)rows.push(`<tr><td>Residuals routing</td><td>${esc(formatValue(unassigned,'kg/d'))} kg DS/d remains unassigned to a sludge-treatment line.</td></tr>`);
    if(!rows.length)rows.push('<tr><td>Design review</td><td>No bypassed mandatory values or active process-network warnings.</td></tr>');
    return rows.join('');
  }
  function renderCompactReport(){
    engine.errors=[];
    const network=calculateNetwork(),inlet=influentStream(),outlet=network.water.finalEffluent;
    const assessments=effluentAssessments(network),assessed=assessments.filter(x=>x.hasTarget),failures=assessed.filter(x=>!x.pass);
    const inputStatus=mandatoryInputStatus(),targetBypass=inputStatus.bypassed.some(x=>x.target);
    const converged=!!(network.converged&&network.water.converged);
    let reportStatus='PASS',reportStatusClass='pass',reportStatusText='All entered discharge targets are met.';
    if(!converged){reportStatus='REVIEW';reportStatusClass='review';reportStatusText='The process network requires convergence review.';}
    else if(failures.length){reportStatus='FAIL';reportStatusClass='fail';reportStatusText=`${failures.length} assessed parameter${failures.length===1?' does':'s do'} not meet the entered discharge target.`;}
    else if(targetBypass||!assessed.length){reportStatus='UNASSESSED';reportStatusClass='unassessed';reportStatusText='One or more required effluent limits are missing or bypassed.';}
    else if(inputStatus.bypassed.length){reportStatus='PASS WITH ASSUMPTIONS';reportStatusClass='assumption';reportStatusText='Targets pass, but planning assumptions are recorded for missing project inputs.';}

    const trainText=treatmentTrain.length?treatmentTrain.map((u,i)=>`${i+1}. ${u.name||unitDef(u.type).name}`).join(' → '):'No water-treatment units configured';
    const avg=Number(effectiveMarketValue('avgFlowM3d'))||0,design=Number(effectiveMarketValue('designFlowM3d'))||0,peak=Number(effectiveMarketValue('peakHourlyEqM3d'))||0;
    const basisGrid=reportKeyGrid([
      ['Calculation flow',esc(reportFlow(Number(v('DesignBasis','C6'))||0))],
      ['Flow basis',esc(market.calculationFlowBasis||'—')],
      ['Average daily flow',esc(reportFlow(avg))],
      ['Design flow',esc(reportFlow(design))],
      ['Peak-hour equivalent flow',esc(reportFlow(peak))],
      ['Design temperature',esc(reportTemperature(effectiveMarketValue('tempC')))],
      ['Wastewater type',esc(effectiveMarketValue('wasteType')||'—')],
      ['Influent pH',esc(formatValue(Number(effectiveMarketValue('pH')),''))],
      ['Discharge basis',esc(effectiveMarketValue('dischargeType')||'—')],
      ['Operating pattern',esc(market.operatingPattern||'—')],
      ['Plant redundancy',esc(market.redundancy||'—')],
      ['Installation',esc(market.installation||'—')]
    ]);

    const waterRows=network.water.units.map((state,i)=>{
      const unit=state.unit,d=unitDef(unit.type),sludge=state.sludgeAvailable?.mass?.tss??state.sludge?.mass?.tss??0;
      return `<tr><td>${i+1}</td><td><b>${esc(unit.name||d.name)}</b><br><small>${esc(unit.tag||d.tag)}</small></td><td>${esc(formatValue(state.inlet.flow,'m³/d'))} → ${esc(formatValue(state.forward.flow,'m³/d'))}</td><td>${esc(formatValue(streamConc(state.forward,'bod'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'tss'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'nh4'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'tn'),'mg/L'))}</td><td>${esc(formatValue(streamConc(state.forward,'tp'),'mg/L'))}</td><td>${esc(formatValue(sludge,'kg/d'))}</td></tr>`;
    }).join('');

    const effluentRowsReport=assessments.map(row=>{
      const influent=streamConc(inlet,row.key),target=row.hasTarget?`${formatValue(row.target,'mg/L')} mg/L`:'—';
      return `<tr><td>${esc(row.name)}</td><td>${esc(formatValue(influent,'mg/L'))}</td><td><b>${esc(formatValue(row.predicted,'mg/L'))}</b></td><td>${esc(target)}</td><td><span class="report-result ${row.hasTarget?(row.pass?'pass':'fail'):'unassessed'}">${esc(row.status==='NO TARGET'?'UNASSESSED':row.status)}</span></td></tr>`;
    }).join('');

    const keyGrid=reportKeyGrid([
      ['Design SRT',`${esc(formatValue(v('Summary','C18'),'d'))} d`],
      ['MLSS',`${esc(formatValue(v('Summary','C20'),'mg/L'))} mg/L`],
      ['Total reactor volume',`${esc(formatValue(v('Summary','C28'),'m³'))} m³`],
      ['Overall HRT',`${esc(formatValue(v('Summary','C29'),'h'))} h`],
      ['Net oxygen demand',`${esc(formatValue(v('Summary','C34'),'kg O₂/d'))} kg O₂/d`],
      ['Blower shaft power',`${esc(formatValue(v('Summary','C37'),'kW'))} kW`],
      ['Total process power',`${esc(formatValue(v('Summary','C38'),'kW'))} kW`],
      ['Specific energy',`${esc(formatValue(v('Summary','C40'),'kWh/m³'))} kWh/m³`],
      ['Alkali demand',`${esc(formatValue(v('Summary','C44'),'kg/d'))} kg/d`],
      ['External carbon',`${esc(formatValue(v('Summary','C45'),'kg/d'))} kg/d`],
      ['Coagulant',`${esc(formatValue(v('Summary','C46'),'kg/d'))} kg/d`],
      ['Dewatering polymer',`${esc(formatValue(network.sludge.summary.polymerKgD,'kg/d'))} kg/d`],
      ['Dewatered dry solids',`${esc(formatValue(network.sludge.summary.cakeDrySolidsKgD,'kg/d'))} kg DS/d`],
      ['Wet cake production',`${esc(formatValue(network.sludge.summary.wetCakeTD,'t/d'))} t/d`]
    ]);

    const recycleRows=network.water.recycles.map(stream=>{
      const cfg=recycles.find(r=>r.id===stream.recycleId)||{};
      return `<tr><td>${esc(cfg.name||'Recirculation')}</td><td>${esc(unitNameById(stream.sourceUnitId))}<br><small>${esc(processNetwork.recyclePortLabel(stream.sourcePort))}</small></td><td>${esc(unitNameById(stream.targetUnitId))}</td><td>${esc(formatValue(stream.flow,'m³/d'))}</td><td>${esc(formatValue(streamConc(stream,'tss'),'mg/L'))}</td><td>${esc(formatValue(streamConc(stream,'tn'),'mg/L'))}</td><td>${esc(formatValue(streamConc(stream,'tp'),'mg/L'))}</td></tr>`;
    }).join('');

    const sludgeRows=network.sludge.lines.map(lr=>{
      const line=lr.line;
      const sources=(line.sources||[]).map(src=>`${unitNameById(src.unitId)} (${Math.round((Number(src.fraction)||0)*100)}%)`).join('; ')||'No sources assigned';
      const operations=(line.units||[]).map(u=>{const cfg={...processNetwork.sludgeDefaultConfig(u.type),...(u.config||{})},n=Math.max(1,Math.round(Number(cfg.parallelUnits)||1));return `${u.name||unitDef(u.type).name}${n>1?` (${n} parallel)`:''}`;}).join(' → ')||'No residuals operations';
      const returnTarget=line.returnEnabled===false?'Not returned':`${unitNameById(line.returnTargetUnitId)} (${Math.round((Number(line.returnFraction)||0)*100)}%)`;
      return `<tr><td><b>${esc(line.name)}</b><br><small>${esc(sources)}</small></td><td>${esc(operations)}</td><td>${esc(formatValue(lr.input.mass.tss,'kg/d'))}</td><td>${esc(formatValue(lr.cakeDrySolidsKgD,'kg/d'))}</td><td>${esc(formatValue(lr.wetCakeTD,'t/d'))}</td><td>${esc(formatValue(lr.returnStream?.flow||0,'m³/d'))}</td><td>${esc(returnTarget)}</td></tr>`;
    }).join('');

    const generated=new Date().toLocaleString();
    main.innerHTML=`<div class="page-head report-screen-head"><div class="page-title"><h1>Compact Design Report</h1><p>Dense landscape text-and-table summary, optimized for one to two printed pages in normal design cases.</p></div><div class="page-head-actions"><button class="action secondary" id="reportDashboard">← Dashboard</button><button class="action secondary" id="reportMassBalance">Full Mass Balance</button><button class="action primary-action" id="printCompactReport">Print / Save PDF</button></div></div>
      <article class="compact-report">
        <header class="report-header"><div><span class="report-suite">TOTAL WATER DESIGN SUITE</span><h1>Total Bio Design</h1><h2>Compact Biological Treatment Design Report</h2></div><div class="report-status ${reportStatusClass}"><span>DESIGN STATUS</span><b>${esc(reportStatus)}</b><small>${esc(reportStatusText)}</small></div></header>
        <div class="report-meta-grid">
          <div class="report-meta-item"><span>Project</span><b>${esc(projectName)}</b></div>
          <div class="report-meta-item"><span>Client</span><b>${esc(market.client||'Not provided')}</b></div>
          <div class="report-meta-item"><span>Location</span><b>${esc(market.location||'Not provided')}</b></div>
          <div class="report-meta-item"><span>Generated</span><b>${esc(generated)}</b></div>
          <div class="report-meta-item"><span>Software</span><b>Total Bio Design v${esc(APP_VERSION)}</b></div>
          <div class="report-meta-item"><span>Calculation</span><b>${converged?'Steady-state network converged':'Network requires review'}</b></div>
        </div>

        <div class="report-grid report-grid-top">
          <section class="report-section"><h3>1. Design Basis</h3>${basisGrid}</section>
          <section class="report-section"><h3>2. Influent, Predicted Effluent and Discharge Targets</h3><div class="report-table-wrap"><table class="report-table compliance-report-table"><thead><tr><th>Determinand</th><th>Influent<br>mg/L</th><th>Predicted<br>mg/L</th><th>Target</th><th>Status</th></tr></thead><tbody>${effluentRowsReport}</tbody></table></div></section>
        </div>
        <section class="report-section report-train-section"><h3>3. Configured Treatment Train</h3><p class="report-train-text">${esc(trainText)}</p><div class="report-table-wrap"><table class="report-table train-report-table"><thead><tr><th>#</th><th>Unit operation / duty</th><th>Flow in → out<br>m³/d</th><th>BOD₅<br>mg/L</th><th>TSS<br>mg/L</th><th>NH₄-N<br>mg/L</th><th>TN<br>mg/L</th><th>TP<br>mg/L</th><th>Waste sludge<br>kg DS/d</th></tr></thead><tbody>${waterRows||'<tr><td colspan="9">No treatment units configured.</td></tr>'}</tbody></table></div></section>
        <section class="report-section report-key-section"><h3>4. Key Design, Utility and Residuals Parameters</h3>${keyGrid}</section>
        <section class="report-section report-sludge-section"><h3>5. Sludge Treatment and Dewatering</h3><p class="report-note">Strategy: <b>${sludgeStrategy==='parallel'?'Multiple parallel residuals lines':'Common sludge-treatment line'}</b>. Sludge sources are manually assigned to each line.</p><div class="report-table-wrap"><table class="report-table sludge-report-table"><thead><tr><th>Line / assigned sources</th><th>Residuals operations</th><th>Feed<br>kg DS/d</th><th>Cake<br>kg DS/d</th><th>Wet cake<br>t/d</th><th>Return<br>m³/d</th><th>Return target</th></tr></thead><tbody>${sludgeRows||'<tr><td colspan="7">No sludge-treatment lines configured.</td></tr>'}</tbody></table></div></section>
        <div class="report-grid report-grid-lower">
          ${network.water.recycles.length?`<section class="report-section"><h3>6. Recirculation Connections</h3><div class="report-table-wrap"><table class="report-table recycle-report-table"><thead><tr><th>Connection</th><th>Source</th><th>Target inlet</th><th>Flow<br>m³/d</th><th>TSS<br>mg/L</th><th>TN<br>mg/L</th><th>TP<br>mg/L</th></tr></thead><tbody>${recycleRows}</tbody></table></div></section>`:''}
          <section class="report-section ${network.water.recycles.length?'':'report-grid-span'}"><h3>${network.water.recycles.length?'7':'6'}. Design Review and Suggested Treatment Response</h3>${complianceGuidanceHtml(network,true)}</section>
        </div>
        <section class="report-section report-assumptions-section"><h3>${network.water.recycles.length?'8':'7'}. Assumptions, Bypasses and Warnings</h3><table class="report-table"><thead><tr><th>Item</th><th>Recorded basis / action required</th></tr></thead><tbody>${reportAssumptionRows(network,inputStatus)}</tbody></table></section>
        <footer class="report-footer"><p><b>Calculation scope.</b> Steady-state planning and proposal model. Sequential unit-operation profiles and user-entered assumptions must be checked against treatability data, pilot results, vendor guarantees and applicable permit requirements. The report intentionally uses text and tables only.</p><p>Generated by Total Bio Design v${esc(APP_VERSION)} · ${esc(reportStreamQuality(outlet))}</p></footer>
      </article>`;
    main.querySelector('#reportDashboard').onclick=()=>navigateTo('Dashboard');
    main.querySelector('#reportMassBalance').onclick=()=>navigateTo('MassBalance');
    main.querySelector('#printCompactReport').onclick=()=>window.print();
    updateCalcState();
  }
  function render(){
    if(current==='MarketIntake')renderMarketIntake();
    else if(current==='Dashboard')renderDashboard();
    else if(current==='MassBalance')renderMassBalance();
    else if(current==='CompactReport')renderCompactReport();
    else if(current==='UnitOperationDetail')renderUnitOperationDetail();
    else if(current==='ResidualsNetwork')renderResidualsNetwork();
    else if(current==='SludgeUnitDetail')renderSludgeUnitDetail();
    else renderSheet(current);
  }
  async function initSuiteSession(){
    if(!SUITE_HOSTED)return;
    const r=await fetch('/api/suite/session',{
      credentials:'same-origin',
      headers:{'Accept':'application/json'}
    });
    const data=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(data.error||'Suite session could not be loaded.');
    suiteCsrfToken=String(data.csrf_token||'');
    suiteAccount=data.account||null;
    configureBioTierPreview();
  }

  async function suiteRequest(url,options={}){
    const opts={...options};
    opts.credentials='same-origin';
    opts.headers={...(opts.headers||{})};

    const method=String(opts.method||'GET').toUpperCase();
    if(
      suiteCsrfToken &&
      !['GET','HEAD','OPTIONS','TRACE'].includes(method)
    ){
      opts.headers['X-CSRFToken']=suiteCsrfToken;
    }

    const response=await fetch(url,opts);
    const data=await response.json().catch(()=>({}));

    if(!response.ok){
      const err=new Error(data.error||`Request failed (${response.status})`);
      err.status=response.status;
      err.payload=data;
      throw err;
    }

    return data;
  }

  function projectSnapshot(){
    return {
      format:'Total Bio Design Project',
      schema_version:1,
      app_version:APP_VERSION,
      saved_at:new Date().toISOString(),
      project:{
        project_name:projectName,
        project_id:serverProjectRecord?.visible_id||'',
        revision:serverProjectRecord
          ? `Rev ${serverProjectRecord.revision??0}`
          : 'Rev 0',
        client:market.client||'',
        location:market.location||''
      },
      inputs:engine.exportInputs(),
      market,
      bypassedMandatory,
      treatmentTrain,
      recycles,
      sludgeStrategy,
      sludgeLines
    };
  }

  function updateHostedProjectIdentity(){
    const host=document.getElementById('projectName');
    if(!host)return;

    if(serverProjectRecord?.visible_id){
      host.textContent=`${serverProjectRecord.visible_id} · ${projectName}`;
      host.title=`${serverProjectRecord.visible_id} — ${projectName}`;
    }else{
      host.textContent=projectName;
      host.title=projectName;
    }

    const rev=document.getElementById('revisionBtn');
    if(rev)rev.hidden=!(SUITE_HOSTED&&serverProjectRecord?.id&&bioTierAllows('silver'));
  }

  async function saveHostedProject(){
    const snapshot=projectSnapshot();
    let data;

    if(serverProjectRecord?.id){
      data=await suiteRequest(
        `/api/projects/${Number(serverProjectRecord.id)}`,
        {
          method:'PUT',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({snapshot})
        }
      );
    }else{
      data=await suiteRequest(
        '/api/projects',
        {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            product_id:'bio',
            snapshot
          })
        }
      );
    }

    serverProjectRecord=data.project||serverProjectRecord;
    updateHostedProjectIdentity();

    toast(
      serverProjectRecord?.visible_id
        ? `Project saved · ${serverProjectRecord.visible_id}`
        : 'Project saved'
    );
  }

  async function loadHostedProject(id){
    const data=await suiteRequest(`/api/projects/${Number(id)}`);
    const record=data.project||null;

    if(!record||record.product_id!=='bio'){
      throw new Error('The selected record is not a Total Bio Design project.');
    }

    serverProjectRecord=record;
    loadPayload(data.snapshot);
    updateHostedProjectIdentity();
    closeProjectLibrary();
    toast(`Project opened · ${record.visible_id}`);
  }

  async function createHostedRevision(){
    if(!serverProjectRecord?.id){
      await saveHostedProject();
      return;
    }

    const data=await suiteRequest(
      `/api/projects/${Number(serverProjectRecord.id)}/copy`,
      {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({snapshot:projectSnapshot()})
      }
    );

    serverProjectRecord=data.project||null;
    updateHostedProjectIdentity();
    toast(`New revision created · ${serverProjectRecord?.visible_id||''}`);
  }

  function closeProjectLibrary(){
    document.getElementById('suiteProjectLibrary')?.remove();
  }

  function renderProjectLibrary(){
    closeProjectLibrary();

    const rows=projectLibraryCache.length
      ? projectLibraryCache.map(p=>`
        <button class="suite-project-row" type="button" data-project-id="${p.id}">
          <span class="suite-project-id">${esc(p.visible_id||'')}</span>
          <span class="suite-project-name">${esc(p.name||'Untitled Bio Project')}</span>
          <span class="suite-project-revision">Rev ${esc(p.revision??0)}</span>
          <span class="suite-project-date">${esc((p.updated_at||'').replace('T',' ').slice(0,16))}</span>
        </button>
      `).join('')
      : `<div class="suite-project-empty">
           No Total Bio Design projects are stored in your Suite Project Library yet.
         </div>`;

    const host=document.createElement('div');
    host.id='suiteProjectLibrary';
    host.className='suite-project-library-overlay';

    host.innerHTML=`
      <div class="suite-project-library-dialog" role="dialog" aria-modal="true">
        <div class="suite-project-library-head">
          <div>
            <span>TOTAL WATER DESIGN SUITE</span>
            <h2>Bio Project Library</h2>
          </div>
          <button type="button" id="closeSuiteProjects" aria-label="Close">×</button>
        </div>

        <div class="suite-project-library-body">
          ${rows}
        </div>

        <div class="suite-project-library-actions">
          <button type="button" class="action secondary" id="legacyBioImport">
            Import legacy .tbd file
          </button>
          <button type="button" class="action secondary" id="closeSuiteProjectsBottom">
            Close
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(host);

    host.querySelector('#closeSuiteProjects').onclick=closeProjectLibrary;
    host.querySelector('#closeSuiteProjectsBottom').onclick=closeProjectLibrary;

    host.onclick=e=>{
      if(e.target===host)closeProjectLibrary();
    };

    host.querySelectorAll('[data-project-id]').forEach(btn=>{
      btn.onclick=async()=>{
        try{
          await loadHostedProject(btn.dataset.projectId);
        }catch(err){
          alert(`Project could not be opened: ${err.message||err}`);
        }
      };
    });

    host.querySelector('#legacyBioImport').onclick=()=>{
      closeProjectLibrary();
      document.getElementById('fileOpen').click();
    };
  }

  async function openHostedProjectLibrary(){
    const data=await suiteRequest('/api/projects');
    projectLibraryCache=(Array.isArray(data.projects)?data.projects:[])
      .filter(p=>p.product_id==='bio');
    renderProjectLibrary();
  }

  async function exportToTotalRODesign(){
    const network=calculateNetwork();
    const s=network?.water?.finalEffluent;

    if(!s||!(Number(s.flow)>0)){
      alert('A solved final biological effluent stream is required before creating a Total RO Design handoff.');
      return;
    }

    const mgL=k=>Number(streamConc(s,k).toFixed(6));

    const handoff={
      format:'TotalWaterDesign Interop',
      schemaVersion:'1.0',
      sourceApplication:'Total Bio Design',
      sourceVersion:APP_VERSION,
      targetApplication:'Total RO Design',
      project:{
        name:projectName,
        client:market.client||'',
        location:market.location||'',
        exportedAt:new Date().toISOString()
      },
      stream:{
        name:'Biological treatment final effluent',
        flow_m3_d:Number(s.flow.toFixed(6)),
        temperature_C:Number(
          (s.temperatureC||Number(market.tempC)||20).toFixed(3)
        ),
        pH:Number(
          (s.pH||Number(market.pH)||7).toFixed(3)
        ),
        quality_mg_L:{
          COD:mgL('cod'),
          BOD5:mgL('bod'),
          TSS:mgL('tss'),
          VSS:mgL('vss'),
          TKN:mgL('tkn'),
          NH4_N:mgL('nh4'),
          NOx_N:mgL('nox'),
          TN:Number(processNetwork.totalNConcentration(s).toFixed(6)),
          TP:mgL('tp'),
          PO4_P:mgL('po4'),
          FOG:mgL('fog'),
          Alkalinity_as_CaCO3:mgL('alk')
        }
      },
      membraneDesignBoundary:{
        RO_and_NF_calculations_performed:false,
        note:'RO and NF are intentionally outside Total Bio Design scope. Complete membrane feed-water chemistry, ionic analysis, salinity/TDS, silica, boron, scaling species and membrane design in Total RO Design.',
        missingForROProjection:[
          'complete ionic composition',
          'TDS/conductivity',
          'silica',
          'boron',
          'scaling species/speciation',
          'feed pressure and membrane design basis'
        ]
      }
    };

    /*
     * Hosted Suite mode:
     * Create a linked Total RO Design project in the Suite database.
     *
     * The Suite backend assigns the next independent TROD-N-0 identifier.
     * It does NOT reuse the TBIO public project number.
     */
    if(SUITE_HOSTED){
      try{
        // A handoff must originate from a persisted Bio revision.
        if(!serverProjectRecord?.id){
          await saveHostedProject();
        }else{
          // Save the latest Bio inputs before transferring the stream.
          await saveHostedProject();
        }

        if(!serverProjectRecord?.id){
          throw new Error(
            'The Bio project could not be saved before the handoff.'
          );
        }

        const sourceVisibleId=serverProjectRecord.visible_id||'Bio project';

        const data=await suiteRequest(
          `/api/projects/${Number(serverProjectRecord.id)}/handoff/ro`,
          {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
              name:projectName,
              handoff
            })
          }
        );

        const target=data?.project;

        if(!target?.id||!target?.visible_id){
          throw new Error(
            'The Suite created the handoff but did not return a valid Total RO Design project identifier.'
          );
        }

        toast(
          `${sourceVisibleId} → ${target.visible_id} · opening Total RO Design`
        );

        // Deep-link by the immutable database revision ID. The TROD public
        // number remains application-specific and independent from TBIO.
        window.location.assign(
          `/ro?project_revision_id=${encodeURIComponent(String(target.id))}`
        );

        return target;

      }catch(err){
        alert(
          `Total RO Design handoff could not be created: ${err.message||err}`
        );
        return;
      }
    }

    /*
     * Standalone desktop mode:
     * Preserve the existing JSON interoperability export.
     */
    const blob=new Blob(
      [JSON.stringify(handoff,null,2)],
      {type:'application/json'}
    );

    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download=(
      projectName.replace(/[^a-z0-9_-]+/gi,'_')||
      'TotalBioDesign'
    )+'_to_TotalRODesign.json';

    a.click();

    setTimeout(
      ()=>URL.revokeObjectURL(a.href),
      1000
    );

    toast('Total RO Design handoff file created');
  }
  async function saveProject(){
    const payload=projectSnapshot();

    if(SUITE_HOSTED){
      try{
        await saveHostedProject();
      }catch(err){
        alert(`Project could not be saved: ${err.message||err}`);
      }
      return;
    }

    const legacyPayload={
      ...payload,
      version:APP_VERSION,
      name:projectName,
      savedAt:new Date().toISOString()
    };

    const blob=new Blob(
      [JSON.stringify(legacyPayload,null,2)],
      {type:'application/json'}
    );

    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download=(projectName.replace(/[^a-z0-9_-]+/gi,'_')||'TotalBioDesign_Project')+'.tbd';
    a.click();

    setTimeout(()=>URL.revokeObjectURL(a.href),1000);
    toast('Project file created');
  }
  function loadPayload(p){
    if(!p||!p.inputs)throw new Error('This is not a Total Bio Design project file.');
    projectName=(p.project&&p.project.project_name)||p.name||'Imported Biological Design';engine.importInputs(p.inputs);market={...marketDefaults(),...(p.market||{})};bypassedMandatory=p.bypassedMandatory&&typeof p.bypassedMandatory==='object'?{...p.bypassedMandatory}:{};treatmentTrain=Array.isArray(p.treatmentTrain)&&p.treatmentTrain.length?p.treatmentTrain.map(hydrateWaterUnit):defaultTrain();recycles=Array.isArray(p.recycles)?p.recycles.map(r=>({...r})):defaultRecycles();sludgeStrategy=p.sludgeStrategy==='parallel'?'parallel':'common';sludgeLines=Array.isArray(p.sludgeLines)&&p.sludgeLines.length?p.sludgeLines.map(line=>({...line,sources:(line.sources||[]).map(x=>({...x})),units:(line.units||[]).map(hydrateSludgeUnit)})):defaultSludgeLines();sanitizeNetwork();syncMarketToEngine();syncTrainToWorkbook();lastNetworkResult=null;document.getElementById('projectName').textContent=projectName;persistAutosave();render();toast(p.version===APP_VERSION?'Project loaded':`Project migrated to the v${APP_VERSION} report and input-review format`);
  }
  window.TotalBioDesignUI=Object.freeze({
    recalculate(){engine.errors=[];lastNetworkResult=calculateNetwork();updateCalcState();render();return lastNetworkResult;},
    getLastNetwork(){return lastNetworkResult;},
    getProjectSnapshot(){return projectSnapshot();}
  });
  document.querySelector('.project-pill').style.cursor='pointer';
  document.querySelector('.project-pill').title='Click to rename project';
  document.querySelector('.project-pill').onclick=()=>{const n=prompt('Project name',projectName);if(n&&n.trim()){projectName=n.trim();document.getElementById('projectName').textContent=projectName;persistAutosave();}};
  document.getElementById('saveBtn').onclick=saveProject;

  document.getElementById('adminTierPreview')?.addEventListener(
    'click',
    e=>{
      const button=e.target.closest('[data-bio-tier-preview]');
      if(!button||!suiteAccount?.is_admin)return;

      applyBioTierPreview(
        button.dataset.bioTierPreview
      );
    }
  );

  const openBtn=document.getElementById('openBtn');
  if(SUITE_HOSTED){
    openBtn.textContent='Project Library';
    openBtn.onclick=async()=>{
      try{
        await openHostedProjectLibrary();
      }catch(err){
        alert(`Project Library could not be loaded: ${err.message||err}`);
      }
    };
  }else{
    openBtn.onclick=()=>document.getElementById('fileOpen').click();
  }
  document.getElementById('fileOpen').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{loadPayload(JSON.parse(await f.text()));}catch(err){alert(err.message);}e.target.value='';};
  document.getElementById('newBtn').onclick=()=>{if(confirm('Start a new design and restore workbook defaults?')){engine.reset();market=marketDefaults();bypassedMandatory={};treatmentTrain=defaultTrain();recycles=defaultRecycles();sludgeStrategy='common';sludgeLines=defaultSludgeLines();lastNetworkResult=null;syncMarketToEngine();syncTrainToWorkbook();projectName='Untitled Biological Design';serverProjectRecord=null;updateHostedProjectIdentity();try{if(!SUITE_HOSTED)localStorage.removeItem('tbd-autosave');}catch(_){ }current='MarketIntake';renderNav();render();toast('New project created');}};
  const revisionBtn=document.getElementById('revisionBtn');
  if(revisionBtn){
    revisionBtn.onclick=async()=>{
      if(!SUITE_HOSTED)return;
      try{
        await createHostedRevision();
      }catch(err){
        alert(`Project revision could not be created: ${err.message||err}`);
      }
    };
  }

  const sendToROBtn=document.getElementById('sendToROBtn');
  if(sendToROBtn){
    sendToROBtn.hidden=!SUITE_HOSTED;sendToROBtn.disabled=!bioTierAllows('silver');
    sendToROBtn.onclick=async()=>{
      if(!SUITE_HOSTED)return;
      if(!bioTierAllows('silver')){
        alert('Send to Total RO Design requires the Silver tier or higher.');
        return;
      }
      await exportToTotalRODesign();
    };
  }

  document.getElementById('printBtn').onclick=()=>navigateTo('CompactReport',()=>window.print());
  const exitBtn=document.getElementById('exitBtn');
  const suiteHosted=window.location.pathname.startsWith('/apps/bio/');
  if(suiteHosted){
    exitBtn.textContent='Return to Suite';
    exitBtn.onclick=()=>{window.location.href='/suite';};
  }else{
    exitBtn.onclick=async()=>{
      if(confirm('Close Total Bio Design?')){
        try{await fetch('/shutdown',{method:'POST'});}catch(_){}
        window.close();
        document.body.innerHTML='<div style="font-family:Segoe UI;padding:40px"><h2>Total Bio Design closed.</h2><p>You may close this browser tab.</p></div>';
      }
    };
  }
  document.getElementById('helpBtn').onclick=()=>document.getElementById('modal').classList.remove('hidden');
  document.getElementById('modalClose').onclick=()=>document.getElementById('modal').classList.add('hidden');
  document.getElementById('modal').onclick=e=>{if(e.target.id==='modal')e.currentTarget.classList.add('hidden');};

  try{const saved=SUITE_HOSTED?null:JSON.parse(localStorage.getItem('tbd-autosave')||'null');if(saved?.inputs){projectName=saved.name||projectName;engine.importInputs(saved.inputs);market={...marketDefaults(),...(saved.market||{})};bypassedMandatory=saved.bypassedMandatory&&typeof saved.bypassedMandatory==='object'?{...saved.bypassedMandatory}:{};treatmentTrain=Array.isArray(saved.treatmentTrain)&&saved.treatmentTrain.length?saved.treatmentTrain.map(hydrateWaterUnit):defaultTrain();recycles=Array.isArray(saved.recycles)?saved.recycles.map(r=>({...r})):defaultRecycles();sludgeStrategy=saved.sludgeStrategy==='parallel'?'parallel':'common';sludgeLines=Array.isArray(saved.sludgeLines)&&saved.sludgeLines.length?saved.sludgeLines.map(line=>({...line,sources:(line.sources||[]).map(x=>({...x})),units:(line.units||[]).map(hydrateSludgeUnit)})):defaultSludgeLines();sanitizeNetwork();syncMarketToEngine();syncTrainToWorkbook();lastNetworkResult=null;document.getElementById('projectName').textContent=projectName;}}catch(_){ }
  if(SUITE_HOSTED){
    try{
      await initSuiteSession();
    }catch(err){
      console.error(err);
      alert('Your Total Water Design Suite session could not be initialized. Return to the Suite and sign in again.');
    }
  }

  updateHostedProjectIdentity();
  renderNav();
  render();
})();
