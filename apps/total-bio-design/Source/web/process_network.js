(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports){module.exports=api;}
  else{root.TotalBioProcessNetwork=api;}
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const KEYS=['cod','bod','tss','vss','tkn','nh4','nox','tp','po4','fog','alk'];
  const EPS=1e-9;
  const pct=x=>Math.max(0,Math.min(1,(Number(x)||0)/100));
  const num=(x,d=0)=>Number.isFinite(Number(x))?Number(x):d;
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  const zeroMass=()=>Object.fromEntries(KEYS.map(k=>[k,0]));
  const copyMass=m=>Object.fromEntries(KEYS.map(k=>[k,Math.max(0,num(m?.[k]))]));
  const copyStream=s=>({flow:Math.max(0,num(s?.flow)),mass:copyMass(s?.mass),temperatureC:num(s?.temperatureC,20),pH:num(s?.pH,7),label:s?.label||''});
  const concentration=(s,k)=>s&&s.flow>EPS?num(s.mass?.[k])*1000/s.flow:0;
  const totalN=s=>num(s?.mass?.tkn)+num(s?.mass?.nox);
  const totalNConcentration=s=>s&&s.flow>EPS?totalN(s)*1000/s.flow:0;

  function makeStream(flow,concentrations={},meta={}){
    const q=Math.max(0,num(flow));
    const mass=zeroMass();
    for(const k of KEYS) mass[k]=Math.max(0,num(concentrations[k]))*q/1000;
    const s={flow:q,mass,temperatureC:num(meta.temperatureC,20),pH:num(meta.pH,7),label:meta.label||''};
    normalizeStream(s);
    return s;
  }
  function normalizeStream(s){
    s.flow=Math.max(0,num(s.flow));
    s.mass=copyMass(s.mass);
    s.mass.bod=Math.min(s.mass.bod,s.mass.cod);
    s.mass.vss=Math.min(s.mass.vss,s.mass.tss);
    s.mass.nh4=Math.min(s.mass.nh4,s.mass.tkn);
    s.mass.po4=Math.min(s.mass.po4,s.mass.tp);
    return s;
  }
  function mixStreams(streams,label=''){
    const valid=(streams||[]).filter(s=>s&&num(s.flow)>=0);
    const out={flow:0,mass:zeroMass(),temperatureC:20,pH:7,label};
    let tempLoad=0,pHLoad=0;
    for(const s0 of valid){
      const s=copyStream(s0);out.flow+=s.flow;
      for(const k of KEYS)out.mass[k]+=s.mass[k];
      tempLoad+=s.temperatureC*s.flow;pHLoad+=s.pH*s.flow;
    }
    if(out.flow>EPS){out.temperatureC=tempLoad/out.flow;out.pH=pHLoad/out.flow;}
    return normalizeStream(out);
  }
  function splitByFlow(s,flow,label=''){
    const src=copyStream(s);const q=clamp(num(flow),0,src.flow);
    const f=src.flow>EPS?q/src.flow:0;
    return normalizeStream({flow:q,mass:Object.fromEntries(KEYS.map(k=>[k,src.mass[k]*f])),temperatureC:src.temperatureC,pH:src.pH,label});
  }
  function subtractStream(a,b,label=''){
    const out=copyStream(a);const sub=copyStream(b);
    out.flow=Math.max(0,out.flow-sub.flow);
    for(const k of KEYS)out.mass[k]=Math.max(0,out.mass[k]-sub.mass[k]);
    out.label=label;return normalizeStream(out);
  }
  function scaleStream(s,f,label=''){
    const x=copyStream(s);const m=Math.max(0,num(f));x.flow*=m;for(const k of KEYS)x.mass[k]*=m;x.label=label||x.label;return normalizeStream(x);
  }
  function streamDifference(a,b){
    if(!a||!b)return Infinity;
    let d=Math.abs(num(a.flow)-num(b.flow))/Math.max(1,num(a.flow),num(b.flow));
    for(const k of KEYS)d=Math.max(d,Math.abs(concentration(a,k)-concentration(b,k))/Math.max(1,concentration(a,k),concentration(b,k)));
    return d;
  }

  const FIELD_META={
    bodRemoval:{label:'BOD₅ removal',unit:'%',min:0,max:100,step:0.1},
    codRemoval:{label:'Total COD removal',unit:'%',min:0,max:100,step:0.1},
    tssRemoval:{label:'TSS capture / removal',unit:'%',min:0,max:100,step:0.1},
    fogRemoval:{label:'FOG removal',unit:'%',min:0,max:100,step:0.1},
    orgNRemoval:{label:'Organic-N removal',unit:'%',min:0,max:100,step:0.1},
    nh4ToNox:{label:'NH₄-N converted to NOx',unit:'%',min:0,max:100,step:0.1},
    nh4Removal:{label:'Direct NH₄-N removal',unit:'%',min:0,max:100,step:0.1},
    noxRemoval:{label:'NOx-N denitrified / removed',unit:'%',min:0,max:100,step:0.1},
    tpRemoval:{label:'Total-P removal',unit:'%',min:0,max:100,step:0.1},
    po4Removal:{label:'Orthophosphate conversion / removal',unit:'%',min:0,max:100,step:0.1},
    biomassYield:{label:'Biological solids yield',unit:'kg TSS/kg BOD removed',min:0,max:1.5,step:0.01},
    chemicalSludgeFactor:{label:'Chemical sludge factor',unit:'kg TSS/kg P removed',min:0,max:20,step:0.1},
    sludgeDS:{label:'Separated sludge concentration',unit:'% DS',min:0.1,max:50,step:0.1},
    waterRecovery:{label:'Treated-water recovery',unit:'%',min:1,max:100,step:0.1},
    carbonDemand:{label:'COD demand for denitrification',unit:'kg COD/kg NOx-N',min:0,max:10,step:0.01},
    alkalinityPerN:{label:'Alkalinity consumed by nitrification',unit:'kg as CaCO₃/kg NH₄-N',min:0,max:15,step:0.01},
    alkalinityRecoveryPerN:{label:'Alkalinity recovered by denitrification',unit:'kg as CaCO₃/kg NOx-N',min:0,max:10,step:0.01}
  };

  function profile(name,description,defaults,fields,extra={}){return {name,description,defaults:{waterRecovery:100,...defaults},fields,canProduceSludge:!!extra.canProduceSludge,separatesSolids:!!extra.separatesSolids,pMode:extra.pMode||'remove',category:extra.category||'water'};}
  const PROFILES={
    pass:profile('Pass-through / hydraulic','No constituent removal is assumed. The unit remains in the ordered hydraulic train.',{},[]),
    coarseScreen:profile('Coarse screening','Planning capture for gross solids and debris.',{bodRemoval:2,codRemoval:2,tssRemoval:5,fogRemoval:5,sludgeDS:20},['bodRemoval','codRemoval','tssRemoval','fogRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    fineScreen:profile('Fine screening','Planning capture for fine screenings and fibrous solids.',{bodRemoval:5,codRemoval:4,tssRemoval:15,fogRemoval:10,sludgeDS:18},['bodRemoval','codRemoval','tssRemoval','fogRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    drumScreen:profile('Rotary screening','Fine-solids separation with a concentrated screenings stream.',{bodRemoval:12,codRemoval:10,tssRemoval:30,fogRemoval:20,sludgeDS:15},['bodRemoval','codRemoval','tssRemoval','fogRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    grit:profile('Grit separation','Predominantly inorganic suspended-solids capture.',{tssRemoval:5,sludgeDS:60},['tssRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    oil:profile('Oil / grease separation','Free and dispersed oil removal with limited soluble COD removal.',{bodRemoval:8,codRemoval:10,tssRemoval:25,fogRemoval:85,sludgeDS:8},['bodRemoval','codRemoval','tssRemoval','fogRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    primary:profile('Primary clarification','Settling of primary solids and associated particulate organics.',{bodRemoval:30,codRemoval:30,tssRemoval:60,fogRemoval:35,orgNRemoval:10,tpRemoval:12,sludgeDS:3},['bodRemoval','codRemoval','tssRemoval','fogRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    daf:profile('Dissolved air flotation','Coagulated or naturally floatable solids, FOG and particulate nutrient removal.',{bodRemoval:35,codRemoval:30,tssRemoval:85,fogRemoval:90,orgNRemoval:20,tpRemoval:50,sludgeDS:4},['bodRemoval','codRemoval','tssRemoval','fogRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    coag:profile('Coagulation / precipitation','Soluble phosphorus is converted to separable particulate solids. Add a clarification or filtration unit downstream unless the selected process includes separation.',{bodRemoval:10,codRemoval:10,po4Removal:80,chemicalSludgeFactor:4.5},['bodRemoval','codRemoval','po4Removal','chemicalSludgeFactor'],{pMode:'convert'}),
    chemPIntegrated:profile('Chemical phosphorus removal with separation','Chemical precipitation and solids separation are represented in one block.',{bodRemoval:15,codRemoval:12,tssRemoval:70,tpRemoval:85,po4Removal:92,chemicalSludgeFactor:4.5,sludgeDS:3.5},['bodRemoval','codRemoval','tssRemoval','tpRemoval','po4Removal','chemicalSludgeFactor','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    aerobic:profile('Aerobic biological treatment','Carbon oxidation and nitrification. Generated biomass remains in the water stream until a downstream separator captures it.',{bodRemoval:94,codRemoval:75,nh4ToNox:95,biomassYield:0.45,alkalinityPerN:7.14},['bodRemoval','codRemoval','nh4ToNox','biomassYield','alkalinityPerN']),
    extendedAeration:profile('Extended aeration','Long-SRT carbon removal and nitrification; biomass requires downstream separation.',{bodRemoval:96,codRemoval:80,nh4ToNox:98,biomassYield:0.4,alkalinityPerN:7.14},['bodRemoval','codRemoval','nh4ToNox','biomassYield','alkalinityPerN']),
    integratedBio:profile('Integrated biological treatment and solids separation','Biological conversion and solids separation are combined in one unit operation.',{bodRemoval:96,codRemoval:82,tssRemoval:98,orgNRemoval:90,nh4ToNox:97,tpRemoval:90,biomassYield:0.42,sludgeDS:1,alkalinityPerN:7.14},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','nh4ToNox','tpRemoval','biomassYield','sludgeDS','alkalinityPerN'],{separatesSolids:true,canProduceSludge:true}),
    mbr:profile('Membrane bioreactor','Biological treatment with membrane solids separation.',{bodRemoval:98,codRemoval:88,tssRemoval:99.8,orgNRemoval:99.5,nh4ToNox:98,tpRemoval:99.5,biomassYield:0.42,sludgeDS:1.2,alkalinityPerN:7.14},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','nh4ToNox','tpRemoval','biomassYield','sludgeDS','alkalinityPerN'],{separatesSolids:true,canProduceSludge:true}),
    anaerobic:profile('High-rate anaerobic treatment','Anaerobic COD conversion with low biological solids yield and internal solids retention.',{bodRemoval:75,codRemoval:80,tssRemoval:50,fogRemoval:35,biomassYield:0.10,sludgeDS:5},['bodRemoval','codRemoval','tssRemoval','fogRemoval','biomassYield','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    anaerobicFilm:profile('Anaerobic fixed-film treatment','Anaerobic carbon removal; generated solids remain in the water stream unless separately captured.',{bodRemoval:70,codRemoval:70,biomassYield:0.10},['bodRemoval','codRemoval','biomassYield']),
    mbbrBod:profile('MBBR carbon-removal stage','Attached-growth carbon removal. Sloughed biomass remains in the water stream for downstream separation.',{bodRemoval:80,codRemoval:60,biomassYield:0.35},['bodRemoval','codRemoval','biomassYield']),
    mbbrNit:profile('MBBR nitrification stage','Attached-growth ammonia oxidation with limited carbon removal.',{bodRemoval:20,codRemoval:15,nh4ToNox:90,biomassYield:0.12,alkalinityPerN:7.14},['bodRemoval','codRemoval','nh4ToNox','biomassYield','alkalinityPerN']),
    denit:profile('Anoxic denitrification','Nitrate reduction using influent or supplemental COD.',{bodRemoval:10,codRemoval:12,noxRemoval:80,carbonDemand:2.86,biomassYield:0.20,alkalinityRecoveryPerN:3.57},['noxRemoval','carbonDemand','biomassYield','alkalinityRecoveryPerN']),
    anammox:profile('Partial nitritation / anammox','Direct autotrophic nitrogen removal represented as a configurable ammonia-removal fraction.',{nh4Removal:85,biomassYield:0.06},['nh4Removal','biomassYield']),
    ammoniaRemoval:profile('Direct ammonia removal','Physical or chemical removal of ammonia-N.',{nh4Removal:85},['nh4Removal']),
    ebpr:profile('Enhanced biological phosphorus removal','Orthophosphate is transferred to particulate biomass; total P is removed only when solids are separated downstream.',{po4Removal:70,biomassYield:0.08},['po4Removal','biomassYield'],{pMode:'convert'}),
    separator:profile('Secondary solids separation','Capture of biological solids and their associated particulate BOD, COD, N and P.',{bodRemoval:35,codRemoval:25,tssRemoval:99.5,orgNRemoval:99.0,tpRemoval:99.0,po4Removal:0,sludgeDS:0.8},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    highRateSeparator:profile('High-rate solids separation','Compact clarification or flotation with high solids capture.',{bodRemoval:40,codRemoval:30,tssRemoval:98.5,orgNRemoval:98,tpRemoval:98,po4Removal:0,sludgeDS:3.5},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    tertiaryFilter:profile('Tertiary filtration','Polishing of residual suspended solids and associated organics and phosphorus.',{bodRemoval:20,codRemoval:12,tssRemoval:75,orgNRemoval:10,tpRemoval:25,sludgeDS:1.5},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    membrane:profile('Low-pressure membrane separation','Near-complete suspended-solids removal with partial particulate organics and nutrient removal.',{bodRemoval:45,codRemoval:25,tssRemoval:99.5,orgNRemoval:35,tpRemoval:40,sludgeDS:2},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true}),
    adsorption:profile('Adsorption / polishing','Planning removal of residual dissolved organics.',{bodRemoval:25,codRemoval:30},['bodRemoval','codRemoval']),
    oxidation:profile('Oxidation / advanced oxidation','Planning oxidation of residual biodegradable and refractory organics.',{bodRemoval:35,codRemoval:20},['bodRemoval','codRemoval']),
    wetland:profile('Constructed wetland','Combined biological, settling and plant uptake performance.',{bodRemoval:80,codRemoval:60,tssRemoval:80,orgNRemoval:35,nh4Removal:55,noxRemoval:35,tpRemoval:40,sludgeDS:5},['bodRemoval','codRemoval','tssRemoval','orgNRemoval','nh4Removal','noxRemoval','tpRemoval','sludgeDS'],{separatesSolids:true,canProduceSludge:true})
  };

  const TYPE_PROFILE={};
  const map=(types,p)=>types.forEach(t=>TYPE_PROFILE[t]=p);
  map(['screening'],'coarseScreen');
  map(['fine_screen','step_screen'],'fineScreen');
  map(['rotary_drum_screen','microscreen'],'drumScreen');
  map(['grit','hydrocyclone'],'grit');
  map(['api_separator','cpi_separator','grease_interceptor','oil_water','igf'],'oil');
  map(['primary','lamella_primary'],'primary');
  map(['daf'],'daf');
  map(['coag_floc','electrocoagulation','p_preprecip','p_coprecip','ferric_p','ferric_sulfate_p','ferrous_p','alum_p','pacl_p','lime_p','electrocoag_p'],'coag');
  map(['chem_p','p_postprecip','tertiary_p_filter','ballasted_p','struvite','hap_recovery','vivianite','p_adsorption','reactive_media_p'],'chemPIntegrated');
  map(['cas','oxidation_ditch','aerated_lagoon'],'aerobic');
  map(['extended_aeration'],'extendedAeration');
  map(['sbr','aerobic_granular'],'integratedBio');
  map(['mbr','anmbr'],'mbr');
  map(['uasb','egsb','ic_reactor','anaerobic_contact'],'anaerobic');
  map(['anaerobic_filter','anaerobic_lagoon'],'anaerobicFilm');
  map(['mbbr_bod','trickling_filter','rbc','submerged_fixed_film'],'mbbrBod');
  map(['mbbr_nit','baf','mabr','partial_nitritation'],'mbbrNit');
  map(['mbbr_ifas'],'aerobic');
  map(['denit','pre_anoxic','post_anoxic','mbbr_denit'],'denit');
  map(['step_feed_bnr','bardenpho','a2o','vip_bnr'],'integratedBio');
  map(['anammox','deammonification'],'anammox');
  map(['ammonia_stripping','zeolite_nh4','breakpoint_chlorination'],'ammoniaRemoval');
  map(['ebpr','bio_p_ao','vfa_fermentation'],'ebpr');
  map(['secondary','lamella_secondary'],'separator');
  map(['daf_secondary'],'highRateSeparator');
  map(['tertiary','dual_media_filter','cloth_filter','disc_filter','cartridge_filter'],'tertiaryFilter');
  map(['microfiltration','uf','ceramic_membrane'],'membrane');
  map(['gac','pac_contact','ion_exchange'],'adsorption');
  map(['ozone','aop_uv_h2o2','fenton'],'oxidation');
  map(['constructed_wetland'],'wetland');

  function profileForType(type){return PROFILES[TYPE_PROFILE[type]||'pass'];}
  function defaultConfig(type){return {...profileForType(type).defaults};}
  function effectiveConfig(unit){return {...defaultConfig(unit?.type),...(unit?.config||{})};}
  function profileFields(type){return profileForType(type).fields.map(k=>({key:k,...FIELD_META[k]}));}
  function canProduceSludge(type){return profileForType(type).canProduceSludge;}

  function applyWaterUnit(input,unit){
    const inlet=copyStream(input);
    const out=copyStream(inlet);
    const profile=profileForType(unit.type);
    const cfg=effectiveConfig(unit);
    const removed=zeroMass();
    const warnings=[];
    const take=(key,fraction)=>{
      const amount=Math.max(0,out.mass[key]*clamp(fraction,0,1));
      out.mass[key]-=amount;
      removed[key]+=amount;
      return amount;
    };

    // Generic solids/organic capture or destruction. All calculations are load based (kg/d).
    const tssRemoved=take('tss',pct(cfg.tssRemoval));
    const vssRemoved=Math.min(take('vss',pct(cfg.tssRemoval)),tssRemoved);
    const bodRemoved=take('bod',pct(cfg.bodRemoval));
    const codRemoved=take('cod',pct(cfg.codRemoval));
    const fogRemoved=take('fog',pct(cfg.fogRemoval));

    // Organic nitrogen is represented as TKN minus ammonia. Solids separators remove this pool.
    const organicN=Math.max(0,out.mass.tkn-out.mass.nh4);
    const orgNRemoved=Math.min(organicN,organicN*pct(cfg.orgNRemoval));
    out.mass.tkn=Math.max(out.mass.nh4,out.mass.tkn-orgNRemoved);
    removed.tkn+=orgNRemoved;

    // Nitrification transfers N from TKN/NH4 to NOx and consumes alkalinity.
    const nh4Converted=Math.min(out.mass.nh4,out.mass.nh4*pct(cfg.nh4ToNox));
    out.mass.nh4-=nh4Converted;
    out.mass.tkn=Math.max(0,out.mass.tkn-nh4Converted);
    out.mass.nox+=nh4Converted;
    const alkNitr=Math.min(out.mass.alk,nh4Converted*Math.max(0,num(cfg.alkalinityPerN,7.14)));
    out.mass.alk-=alkNitr;

    // Physical/chemical ammonia removal leaves the liquid network as a separate residual/product.
    const nh4Removed=Math.min(out.mass.nh4,out.mass.nh4*pct(cfg.nh4Removal));
    out.mass.nh4-=nh4Removed;
    out.mass.tkn=Math.max(0,out.mass.tkn-nh4Removed);
    removed.nh4+=nh4Removed;
    removed.tkn+=nh4Removed;

    // Denitrification destroys NOx-N to nitrogen gas, consumes biodegradable COD, and recovers alkalinity.
    const noxRemoved=Math.min(out.mass.nox,out.mass.nox*pct(cfg.noxRemoval));
    let denitCodUsed=0;
    if(noxRemoved>0){
      out.mass.nox-=noxRemoved;
      removed.nox+=noxRemoved;
      const codNeed=noxRemoved*Math.max(0,num(cfg.carbonDemand,2.86));
      denitCodUsed=Math.min(out.mass.cod,codNeed);
      out.mass.cod-=denitCodUsed;
      removed.cod+=denitCodUsed;
      const bodUsed=Math.min(out.mass.bod,denitCodUsed);
      out.mass.bod-=bodUsed;
      removed.bod+=bodUsed;
      out.mass.alk+=noxRemoved*Math.max(0,num(cfg.alkalinityRecoveryPerN,3.57));
    }

    // Phosphorus is tracked as total P and orthophosphate. The difference is particulate/organic P.
    const tpBefore=out.mass.tp;
    const po4Before=out.mass.po4;
    let particulatePRemoved=0;
    let po4Removed=0;
    let po4Converted=0;
    if(profile.pMode==='convert'){
      po4Converted=po4Before*pct(cfg.po4Removal);
      out.mass.po4=Math.max(0,po4Before-po4Converted);
      // Total P remains in the liquid train as particulate P until a downstream separator captures it.
    }else{
      const particulateP=Math.max(0,tpBefore-po4Before);
      particulatePRemoved=Math.min(particulateP,particulateP*pct(cfg.tpRemoval));
      po4Removed=Math.min(po4Before,po4Before*pct(cfg.po4Removal));
      out.mass.tp=Math.max(0,tpBefore-particulatePRemoved-po4Removed);
      out.mass.po4=Math.min(out.mass.tp,Math.max(0,po4Before-po4Removed));
      removed.tp+=particulatePRemoved+po4Removed;
      removed.po4+=po4Removed;
    }

    // Planning-level biomass generation. In a non-separating bioreactor it remains in the water stream.
    const bioSolids=Math.max(0,(bodRemoved+Math.min(bodRemoved,codRemoved)*0.15)*Math.max(0,num(cfg.biomassYield)));
    const bioCOD=Math.min(codRemoved,1.42*bioSolids);
    const bioBOD=Math.min(bodRemoved,0.2*bioCOD);
    const bioN=profile.separatesSolids?Math.min(out.mass.tkn,bioSolids*0.08):0;
    const bioP=profile.separatesSolids?Math.min(out.mass.tp,bioSolids*0.02):0;
    if(profile.separatesSolids){
      out.mass.tkn=Math.max(0,out.mass.tkn-bioN);
      out.mass.nh4=Math.min(out.mass.nh4,out.mass.tkn);
      out.mass.tp=Math.max(0,out.mass.tp-bioP);
      out.mass.po4=Math.min(out.mass.po4,out.mass.tp);
      removed.tkn+=bioN;
      removed.tp+=bioP;
    }

    const pRemovedForSludge=particulatePRemoved+po4Removed;
    const chemSolids=Math.max(0,pRemovedForSludge*Math.max(0,num(cfg.chemicalSludgeFactor)));
    const convertedPSolids=Math.max(0,po4Converted*Math.max(0,num(cfg.chemicalSludgeFactor)));

    const sludge={
      flow:0,mass:zeroMass(),temperatureC:out.temperatureC,pH:out.pH,
      label:`${unit.name||unit.type} residuals`,sourceUnitId:unit.id,sourceType:unit.type,
      drySolids:0,dsPct:0,kind:'sludge'
    };
    if(profile.separatesSolids){
      sludge.mass.tss=tssRemoved+bioSolids+chemSolids+convertedPSolids+fogRemoved;
      sludge.mass.vss=Math.min(sludge.mass.tss,vssRemoved+bioSolids*0.8+fogRemoved*0.5);
      // codRemoved/bodRemoved already represent the total load transferred
      // out of the forward water stream. Biomass COD/BOD is a portion of that
      // removed load, not an additional load. Adding it again would create
      // constituent mass in integrated biological/separation units.
      sludge.mass.cod=Math.min(inlet.mass.cod,codRemoved);
      sludge.mass.bod=Math.min(sludge.mass.cod,bodRemoved);
      sludge.mass.tkn=orgNRemoved+nh4Removed+bioN;
      sludge.mass.nh4=nh4Removed;
      sludge.mass.nox=0;
      sludge.mass.tp=pRemovedForSludge+bioP+(profile.pMode==='convert'?po4Converted:0);
      sludge.mass.po4=po4Removed+(profile.pMode==='convert'?po4Converted:0);
      sludge.mass.fog=fogRemoved;
      sludge.drySolids=sludge.mass.tss;
      const ds=clamp(num(cfg.sludgeDS,1),0.1,80)/100;
      let qSludge=sludge.drySolids>EPS?sludge.drySolids/(1000*ds):0;
      if(qSludge>out.flow*0.35){
        warnings.push('Calculated residual carrier-water flow exceeded 35% of the unit inlet and was capped. Review the separated sludge %DS assumption.');
        qSludge=out.flow*0.35;
      }
      if(qSludge>EPS&&out.flow>EPS){
        const liquid=splitByFlow(out,qSludge,'residual carrier water');
        sludge.flow=qSludge;
        sludge.temperatureC=liquid.temperatureC;
        sludge.pH=liquid.pH;
        for(const k of KEYS){
          if(k==='tss'||k==='vss')continue;
          sludge.mass[k]+=liquid.mass[k];
          out.mass[k]=Math.max(0,out.mass[k]-liquid.mass[k]);
        }
        out.flow=Math.max(0,out.flow-qSludge);
      }
      sludge.dsPct=sludge.flow>EPS?sludge.drySolids/(sludge.flow*1000)*100:0;
    }else{
      out.mass.tss+=bioSolids+chemSolids+convertedPSolids;
      out.mass.vss+=bioSolids*0.8;
      out.mass.cod+=bioCOD;
      out.mass.bod+=bioBOD;
    }

    // Membrane recovery creates a concentrate/liquid-residual port in addition to the treated outlet.
    const recovery=clamp(num(cfg.waterRecovery,100),1,100)/100;
    let liquidResidual=null;
    if(recovery<0.999999&&out.flow>EPS){
      const productFlow=out.flow*recovery;
      const product=copyStream(out);
      product.flow=productFlow;
      liquidResidual={
        flow:Math.max(0,inlet.flow-productFlow-(sludge.flow||0)),mass:zeroMass(),
        temperatureC:inlet.temperatureC,pH:inlet.pH,
        label:`${unit.name||unit.type} concentrate`,sourceUnitId:unit.id,sourceType:unit.type,
        kind:'liquid-residual',drySolids:0,dsPct:0
      };
      for(const k of KEYS)liquidResidual.mass[k]=Math.max(0,inlet.mass[k]-product.mass[k]-(sludge.mass[k]||0));
      out.flow=productFlow;
    }

    normalizeStream(out);
    normalizeStream(sludge);
    if(liquidResidual)normalizeStream(liquidResidual);
    return {
      unit,inlet,outlet:out,sludge,liquidResidual,removed,profile,cfg,warnings,
      metrics:{nh4Converted,noxRemoved,denitCodUsed,alkNitr,bioSolids,chemSolids,convertedPSolids}
    };
  }

  function recyclePortLabel(port){
    return port==='sludge'?'Separated sludge / underflow':port==='residual'?'Concentrate / liquid residual':'Liquid outlet';
  }
  function sourcePortStream(state,port='liquid'){
    if(!state)return makeStream(0);
    // Recycle requests must be based on the raw source-port production, not on
    // the previously calculated waste/forward remainder. Otherwise a
    // source-fraction recycle (for example 90 % RAS) recursively applies to
    // the already-reduced remainder and collapses toward zero.
    if(port==='sludge')return copyStream(state.sludge||makeStream(0));
    if(port==='residual')return copyStream(state.liquidResidual||makeStream(0));
    return copyStream(state.outlet||makeStream(0));
  }
  function requestedRecycleFlow(rec,influentFlow,sourceFlow){
    if(rec?.basis==='fixed')return Math.max(0,num(rec.value));
    if(rec?.basis==='source_fraction'||rec?.basis==='sourceFraction')return Math.max(0,num(sourceFlow))*pct(rec.value);
    return Math.max(0,num(rec?.value))*Math.max(0,num(influentFlow));
  }
  function buildRecycleStream(source,flow,rec){
    const s=splitByFlow(source,flow,rec.name||'Recycle');
    s.recycleId=rec.id;
    s.sourceUnitId=rec.sourceUnitId;
    s.sourcePort=rec.sourcePort||'liquid';
    s.targetUnitId=rec.targetUnitId;
    return s;
  }
  function blendState(previous,next,relax){
    const p=previous||{},n=next||{};
    const blend=(a,b)=>{
      const aa=copyStream(a||makeStream(0)),bb=copyStream(b||makeStream(0)),o=copyStream(bb);
      o.flow=aa.flow*(1-relax)+bb.flow*relax;
      for(const k of KEYS)o.mass[k]=aa.mass[k]*(1-relax)+bb.mass[k]*relax;
      return normalizeStream(o);
    };
    return {
      outlet:blend(p.outlet,n.outlet),
      sludge:blend(p.sludge,n.sludge),
      sludgeAvailable:blend(p.sludgeAvailable||p.sludge,n.sludgeAvailable||n.sludge),
      liquidResidual:blend(p.liquidResidual,n.liquidResidual),
      liquidResidualAvailable:blend(p.liquidResidualAvailable||p.liquidResidual,n.liquidResidualAvailable||n.liquidResidual)
    };
  }
  function stateDifference(a,b){
    return Math.max(
      streamDifference(a?.outlet||makeStream(0),b?.outlet||makeStream(0)),
      streamDifference(a?.sludge||makeStream(0),b?.sludge||makeStream(0)),
      streamDifference(a?.liquidResidual||makeStream(0),b?.liquidResidual||makeStream(0))
    );
  }
  function singlePassStates(influent,ordered,externalReturns=[]){
    const returnsByTarget=new Map();
    for(const x of externalReturns||[]){
      if(!x?.targetUnitId)continue;
      const a=returnsByTarget.get(x.targetUnitId)||[];
      a.push(x.stream||x);
      returnsByTarget.set(x.targetUnitId,a);
    }
    const states={};let forward=null;
    for(let i=0;i<ordered.length;i++){
      const unit=ordered[i],parts=[];
      if(i===0)parts.push(influent);
      if(forward)parts.push(forward);
      parts.push(...(returnsByTarget.get(unit.id)||[]));
      const result=applyWaterUnit(mixStreams(parts,`${unit.name||unit.type} inlet`),unit);
      result.forward=copyStream(result.outlet);
      result.sludgeAvailable=copyStream(result.sludge);
      result.liquidResidualAvailable=copyStream(result.liquidResidual||makeStream(0));
      states[unit.id]=result;
      forward=result.forward;
    }
    return states;
  }

  function solveWaterNetwork(influent,units,recycles=[],externalReturns=[],options={}){
    const ordered=(units||[]).filter(Boolean);
    const unitIndex=new Map(ordered.map((u,i)=>[u.id,i]));
    const warnings=[];
    if(!ordered.length)return {finalEffluent:copyStream(influent),units:[],byId:{},sludgeSources:[],liquidResiduals:[],recycles:[],warnings,iterations:0,converged:true};

    const activeRecycles=(recycles||[])
      .filter(r=>r&&r.enabled!==false&&unitIndex.has(r.sourceUnitId)&&unitIndex.has(r.targetUnitId)&&r.sourceUnitId!==r.targetUnitId)
      .map(r=>{
        const sourcePort=['liquid','sludge','residual'].includes(r.sourcePort)?r.sourcePort:'liquid';
        const basis=r.basis==='fixed'?'fixed':(r.basis==='source_fraction'||r.basis==='sourceFraction')?'source_fraction':'ratio';
        return {...r,sourcePort,basis};
      });
    for(const rec of activeRecycles){
      if(unitIndex.get(rec.sourceUnitId)<unitIndex.get(rec.targetUnitId))warnings.push(`${rec.name||'Recycle'} is configured as a forward transfer. The normal treatment train already carries liquid downstream; verify that this is an intentional bypass or split.`);
    }

    const returnsByTarget=new Map();
    for(const x of externalReturns||[]){
      if(!x||!unitIndex.has(x.targetUnitId))continue;
      const a=returnsByTarget.get(x.targetUnitId)||[];
      a.push(x.stream||x);
      returnsByTarget.set(x.targetUnitId,a);
    }

    const seeded=options.initialStates&&ordered.every(u=>options.initialStates[u.id]?.outlet);
    let previous=seeded?options.initialStates:singlePassStates(influent,ordered,externalReturns);
    let last=null,converged=false;
    const maxIterations=Math.max(1,Math.round(num(options.maxIterations,100)));
    const tol=Math.max(1e-12,num(options.tolerance,1e-7));
    const relax=clamp(num(options.relaxation,0.65),0.05,1);

    for(let iter=1;iter<=maxIterations;iter++){
      const iterationWarnings=[];
      // Build a flow plan for every recycle from the previous iteration and normalize competing withdrawals from the same source port.
      const plans=[];
      const sourceGroups=new Map();
      for(const rec of activeRecycles){
        const source=sourcePortStream(previous[rec.sourceUnitId],rec.sourcePort);
        const requested=requestedRecycleFlow(rec,influent.flow,source.flow);
        const item={rec,source,requested,flow:requested};
        plans.push(item);
        const key=`${rec.sourceUnitId}|${rec.sourcePort||'liquid'}`;
        const group=sourceGroups.get(key)||[];group.push(item);sourceGroups.set(key,group);
      }
      for(const group of sourceGroups.values()){
        const available=Math.max(0,group[0]?.source?.flow||0);
        const requested=group.reduce((a,x)=>a+x.requested,0);
        const reserve=(group[0]?.rec?.sourcePort||'liquid')==='liquid'?0.01:0;
        const maximum=available*Math.max(0,1-reserve);
        const scale=requested>maximum&&requested>EPS?maximum/requested:1;
        if(scale<0.999999){
          const r=group[0].rec;
          iterationWarnings.push(`${r.name||'Recycle'} and other withdrawals from ${recyclePortLabel(r.sourcePort)} were proportionally capped by the available source flow.`);
        }
        for(const x of group)x.flow=x.requested*scale;
      }

      const recycleInputs=new Map();
      for(const plan of plans){
        const stream=buildRecycleStream(plan.source,plan.flow,plan.rec);
        const a=recycleInputs.get(plan.rec.targetUnitId)||[];a.push(stream);recycleInputs.set(plan.rec.targetUnitId,a);
      }

      const byId={},results=[],states={};let forward=null;
      for(let i=0;i<ordered.length;i++){
        const unit=ordered[i],parts=[];
        if(i===0)parts.push(influent);
        if(forward)parts.push(forward);
        parts.push(...(recycleInputs.get(unit.id)||[]),...(returnsByTarget.get(unit.id)||[]));
        const inlet=mixStreams(parts,`${unit.name||unit.type} inlet`);
        const result=applyWaterUnit(inlet,unit);
        result.recycleOut=[];

        let liquidAvailable=copyStream(result.outlet);
        let sludgeAvailable=copyStream(result.sludge);
        let residualAvailable=copyStream(result.liquidResidual||makeStream(0));
        for(const plan of plans.filter(x=>x.rec.sourceUnitId===unit.id)){
          const port=plan.rec.sourcePort||'liquid';
          const source=port==='sludge'?sludgeAvailable:port==='residual'?residualAvailable:liquidAvailable;
          const q=Math.min(source.flow,plan.flow);
          const stream=buildRecycleStream(source,q,plan.rec);
          result.recycleOut.push(stream);
          if(port==='sludge')sludgeAvailable=subtractStream(sludgeAvailable,stream,`${unit.name||unit.type} waste sludge`);
          else if(port==='residual')residualAvailable=subtractStream(residualAvailable,stream,`${unit.name||unit.type} unreturned liquid residual`);
          else liquidAvailable=subtractStream(liquidAvailable,stream,`${unit.name||unit.type} forward effluent`);
        }
        result.forward=liquidAvailable;
        result.sludgeAvailable=sludgeAvailable;
        result.liquidResidualAvailable=residualAvailable;
        forward=result.forward;
        results.push(result);
        byId[unit.id]=result;
        states[unit.id]=result;
      }

      let diff=0;
      for(const u of ordered)diff=Math.max(diff,stateDifference(states[u.id],previous[u.id]));
      last={results,byId,states,forward,iterations:iter,iterationWarnings};
      if(diff<tol){converged=true;break;}
      const blended={};
      for(const u of ordered)blended[u.id]=blendState(previous[u.id],states[u.id],relax);
      previous=blended;
    }

    warnings.push(...(last?.iterationWarnings||[]));
    if(!converged&&activeRecycles.length)warnings.push('The recycle network reached the iteration limit before full convergence. Review recycle ratios, source ports, and unit-removal assumptions.');
    const sludgeSources=[],liquidResiduals=[];
    for(const r of last.results){
      const waste=r.sludgeAvailable||r.sludge;
      if(waste&&waste.mass.tss>EPS){waste.sourceUnitId=r.unit.id;waste.sourceType=r.unit.type;waste.drySolids=waste.mass.tss;waste.dsPct=waste.flow>EPS?waste.mass.tss/(waste.flow*1000)*100:0;sludgeSources.push(waste);}
      const residual=r.liquidResidualAvailable||r.liquidResidual;
      if(residual&&residual.flow>EPS)liquidResiduals.push(residual);
      warnings.push(...r.warnings.map(w=>`${r.profile.name}: ${w}`));
    }
    const finalRecycles=[];for(const r of last.results)finalRecycles.push(...r.recycleOut);
    return {
      finalEffluent:last.forward||copyStream(influent),units:last.results,byId:last.byId,
      sludgeSources,liquidResiduals,recycles:finalRecycles,
      warnings:[...new Set(warnings)],iterations:last.iterations||0,converged
    };
  }

  const SLUDGE_FIELD_META={
    holdHours:{label:'Equalization / storage time',unit:'h',min:0,max:336,step:1},
    targetDS:{label:'Outlet dry solids',unit:'% DS',min:0.2,max:95,step:0.1},
    capture:{label:'Solids capture',unit:'%',min:0,max:100,step:0.1},
    polymerDose:{label:'Polymer dose',unit:'kg/t DS',min:0,max:50,step:0.1},
    parallelUnits:{label:'Parallel equipment units',unit:'No.',min:1,max:20,step:1},
    vsDestruction:{label:'Volatile-solids destruction',unit:'%',min:0,max:90,step:0.1},
    addedSolids:{label:'Conditioning solids added',unit:'% of feed DS',min:0,max:100,step:0.1}
  };
  const SLUDGE_PROFILES={
    pass:{name:'Residuals transfer',description:'No change to sludge quantity or concentration.',defaults:{},fields:[]},
    equalization:{name:'Sludge equalization / blending',description:'Combines intermittent or different sludge sources ahead of common treatment.',defaults:{holdHours:24},fields:['holdHours']},
    storage:{name:'Sludge storage',description:'Provides storage capacity without changing dry-solids mass.',defaults:{holdHours:48},fields:['holdHours']},
    thickener:{name:'Sludge thickening',description:'Increases solids concentration and produces a liquid return stream.',defaults:{targetDS:5,capture:95,polymerDose:4,parallelUnits:1},fields:['targetDS','capture','polymerDose','parallelUnits']},
    digestion:{name:'Sludge digestion',description:'Destroys volatile solids and releases soluble ammonia to the sidestream.',defaults:{vsDestruction:50},fields:['vsDestruction']},
    aerobicDigestion:{name:'Aerobic digestion',description:'Aerobic stabilization with moderate volatile-solids destruction.',defaults:{vsDestruction:35},fields:['vsDestruction']},
    conditioning:{name:'Sludge conditioning / stabilization',description:'Adds conditioning solids without dewatering.',defaults:{addedSolids:10},fields:['addedSolids']},
    dewatering:{name:'Mechanical dewatering',description:'Produces dewatered cake and a centrate or filtrate return stream.',defaults:{targetDS:22,capture:95,polymerDose:9,parallelUnits:1},fields:['targetDS','capture','polymerDose','parallelUnits']},
    drying:{name:'Drying / final solids concentration',description:'Raises cake solids for final handling.',defaults:{targetDS:55,capture:98,polymerDose:0,parallelUnits:1},fields:['targetDS','capture','parallelUnits']},
    destruction:{name:'Thermal solids destruction',description:'Destroys most volatile and fixed solids; ash remains.',defaults:{vsDestruction:85},fields:['vsDestruction']}
  };
  const SLUDGE_TYPE_PROFILE={
    sludge_equalization:'equalization',sludge_storage:'storage',sludge_thickening:'thickener',gravity_thickener:'thickener',daf_thickener:'thickener',rotary_drum_thickener:'thickener',
    aerobic_digestion:'aerobicDigestion',anaerobic_digestion:'digestion',thermal_hydrolysis:'pass',lime_stabilization:'conditioning',
    centrifuge:'dewatering',belt_press:'dewatering',screw_press:'dewatering',filter_press:'dewatering',dewatering:'dewatering',
    drying_beds:'drying',composting:'drying',incineration:'destruction',sidestream_return:'pass',sludge:'pass'
  };
  const SLUDGE_OVERRIDES={
    gravity_thickener:{targetDS:3,capture:95,polymerDose:0},daf_thickener:{targetDS:4,capture:95,polymerDose:4},rotary_drum_thickener:{targetDS:6,capture:96,polymerDose:4},
    centrifuge:{targetDS:22,capture:95,polymerDose:9},belt_press:{targetDS:18,capture:95,polymerDose:6},screw_press:{targetDS:18,capture:95,polymerDose:5},filter_press:{targetDS:35,capture:98,polymerDose:4},
    drying_beds:{targetDS:50,capture:95},composting:{targetDS:60,capture:98},incineration:{vsDestruction:90}
  };
  function sludgeProfileForType(type){return SLUDGE_PROFILES[SLUDGE_TYPE_PROFILE[type]||'pass'];}
  function sludgeDefaultConfig(type){return {...sludgeProfileForType(type).defaults,...(SLUDGE_OVERRIDES[type]||{})};}
  function sludgeEffectiveConfig(unit){return {...sludgeDefaultConfig(unit?.type),...(unit?.config||{})};}
  function sludgeProfileFields(type){return sludgeProfileForType(type).fields.map(k=>({key:k,...SLUDGE_FIELD_META[k]}));}

  function sludgeUnitTransform(input,unit){
    const inlet=copyStream(input),profile=sludgeProfileForType(unit.type),cfg=sludgeEffectiveConfig(unit);let outlet=copyStream(inlet);let returnStream=makeStream(0,{},{});const metrics={polymerKgD:0,equalizationVolumeM3:0,biogasNm3D:0,parallelUnits:1,feedFlowPerUnitM3d:0,feedDrySolidsPerUnitKgD:0,wetCakePerUnitTD:0};const warnings=[];
    const pName=SLUDGE_TYPE_PROFILE[unit.type]||'pass';
    metrics.parallelUnits=Math.max(1,Math.round(num(cfg.parallelUnits,1)));
    metrics.feedFlowPerUnitM3d=inlet.flow/metrics.parallelUnits;
    metrics.feedDrySolidsPerUnitKgD=inlet.mass.tss/metrics.parallelUnits;
    if(pName==='equalization'||pName==='storage')metrics.equalizationVolumeM3=inlet.flow*Math.max(0,num(cfg.holdHours))/24;
    else if(pName==='thickener'||pName==='dewatering'||pName==='drying'){
      const capture=pct(cfg.capture),targetDS=clamp(num(cfg.targetDS,5),0.2,95)/100;const capturedDS=inlet.mass.tss*capture;
      let qOut=capturedDS>EPS?capturedDS/(1000*targetDS):0;qOut=Math.min(inlet.flow,qOut);
      const waterFrac=inlet.flow>EPS?qOut/inlet.flow:0;
      outlet={flow:qOut,mass:zeroMass(),temperatureC:inlet.temperatureC,pH:inlet.pH,label:`${unit.name||unit.type} outlet`};
      returnStream={flow:Math.max(0,inlet.flow-qOut),mass:zeroMass(),temperatureC:inlet.temperatureC,pH:inlet.pH,label:`${unit.name||unit.type} centrate / filtrate`};
      outlet.mass.tss=capturedDS;returnStream.mass.tss=Math.max(0,inlet.mass.tss-capturedDS);
      const vssCapture=inlet.mass.tss>EPS?capturedDS/inlet.mass.tss:0;outlet.mass.vss=inlet.mass.vss*vssCapture;returnStream.mass.vss=Math.max(0,inlet.mass.vss-outlet.mass.vss);
      for(const k of KEYS){if(k==='tss'||k==='vss')continue;const solidsAssociated=['cod','bod','tkn','tp','fog'].includes(k);const retain=solidsAssociated?clamp(0.65*capture+0.35*waterFrac,0,1):waterFrac;outlet.mass[k]=inlet.mass[k]*retain;returnStream.mass[k]=Math.max(0,inlet.mass[k]-outlet.mass[k]);}
      metrics.polymerKgD=inlet.mass.tss/1000*Math.max(0,num(cfg.polymerDose));
      metrics.wetCakePerUnitTD=(outlet.flow*1.05)/metrics.parallelUnits;
    }else if(pName==='digestion'||pName==='aerobicDigestion'||pName==='destruction'){
      const destroyed=outlet.mass.vss*pct(cfg.vsDestruction);outlet.mass.vss-=destroyed;outlet.mass.tss=Math.max(0,outlet.mass.tss-destroyed);outlet.mass.cod=Math.max(0,outlet.mass.cod-Math.min(outlet.mass.cod,destroyed*1.42));outlet.mass.bod=Math.max(0,Math.min(outlet.mass.bod,outlet.mass.cod));outlet.mass.nh4+=destroyed*0.08;outlet.mass.tkn+=destroyed*0.08;metrics.biogasNm3D=pName==='digestion'?destroyed*0.95:0;
    }else if(pName==='conditioning'){
      const add=outlet.mass.tss*pct(cfg.addedSolids);outlet.mass.tss+=add;
    }
    normalizeStream(outlet);normalizeStream(returnStream);
    return {inlet,outlet,returnStream,profile,cfg,metrics,warnings};
  }

  function sourceStreamFromSludge(s,fraction){
    const x=copyStream(s);const f=clamp(num(fraction,1),0,1);x.flow*=f;for(const k of KEYS)x.mass[k]*=f;x.sourceUnitId=s.sourceUnitId;return normalizeStream(x);
  }
  function solveSludgeNetwork(sludgeSources,lines,waterUnits){
    const sourceMap=new Map((sludgeSources||[]).map(s=>[s.sourceUnitId,s]));const warnings=[];const totalAllocation={};
    for(const line of lines||[])for(const src of line.sources||[])totalAllocation[src.unitId]=(totalAllocation[src.unitId]||0)+clamp(num(src.fraction,1),0,1);
    for(const [id,total] of Object.entries(totalAllocation))if(total>1+1e-8)warnings.push(`Sludge from ${id} is allocated at ${(total*100).toFixed(1)}%; line allocations were normalized to 100%.`);
    const lineResults=[];const returnStreams=[];let totalCakeDS=0,totalWetCake=0,totalPolymer=0,totalEq=0,totalReturnedLiquid=0,totalUnreturnedLiquid=0;
    for(const line of lines||[]){
      const parts=[];
      if((line.sources||[]).length>1&&!(line.units||[]).some(u=>u.type==='sludge_equalization'))warnings.push(`${line.name||'Sludge line'} receives multiple sludge sources without a sludge equalization / blending tank.`);
      if((line.sources||[]).length>0&&!(line.units||[]).length)warnings.push(`${line.name||'Sludge line'} has assigned sludge sources but no residuals-treatment operations.`);
      for(const src of line.sources||[]){const s=sourceMap.get(src.unitId);if(!s)continue;const total=totalAllocation[src.unitId]||1;const f=clamp(num(src.fraction,1),0,1)/(total>1?total:1);parts.push(sourceStreamFromSludge(s,f));}
      let current=mixStreams(parts,`${line.name||'Sludge line'} feed`);const unitResults=[];let combinedReturn=makeStream(0,{},{}),polymer=0,eqVolume=0;
      for(const unit of line.units||[]){const r=sludgeUnitTransform(current,unit);unitResults.push(r);current=r.outlet;combinedReturn=mixStreams([combinedReturn,r.returnStream],`${line.name||'Sludge line'} return`);polymer+=r.metrics.polymerKgD;eqVolume+=r.metrics.equalizationVolumeM3;warnings.push(...r.warnings);}
      const ds=current.mass.tss;const wet=current.flow>EPS?current.flow:0;const wetT=wet*1.05;totalCakeDS+=ds;totalWetCake+=wetT;totalPolymer+=polymer;totalEq+=eqVolume;
      const returnFraction=line.returnEnabled===false?0:clamp(num(line.returnFraction,1),0,1);
      const returnedStream=scaleStream(combinedReturn,returnFraction,`${line.name||'Sludge line'} returned centrate / filtrate`);
      const unreturnedReturnStream=scaleStream(combinedReturn,1-returnFraction,`${line.name||'Sludge line'} unreturned liquid residual`);
      totalReturnedLiquid+=returnedStream.flow;totalUnreturnedLiquid+=unreturnedReturnStream.flow;
      if(line.returnTargetUnitId&&returnedStream.flow>EPS)returnStreams.push({lineId:line.id,targetUnitId:line.returnTargetUnitId,stream:returnedStream});
      lineResults.push({line,input:mixStreams(parts),units:unitResults,output:current,returnStream:returnedStream,totalReturnStream:combinedReturn,unreturnedReturnStream,returnFraction,polymerKgD:polymer,equalizationVolumeM3:eqVolume,cakeDrySolidsKgD:ds,wetCakeTD:wetT});
    }
    const unassigned=[];for(const s of sludgeSources||[]){const allocated=Math.min(1,totalAllocation[s.sourceUnitId]||0);if(allocated<1-EPS)unassigned.push(sourceStreamFromSludge(s,1-allocated));}
    const unassignedCombined=mixStreams(unassigned,'Unassigned sludge');
    return {lines:lineResults,returnStreams,unassignedSources:unassigned,unassignedCombined,summary:{cakeDrySolidsKgD:totalCakeDS,wetCakeTD:totalWetCake,polymerKgD:totalPolymer,equalizationVolumeM3:totalEq,unassignedDrySolidsKgD:unassignedCombined.mass.tss,returnedLiquidM3D:totalReturnedLiquid,unreturnedLiquidM3D:totalUnreturnedLiquid},warnings};
  }

  function blendReturns(previous,next,relax=0.6){
    const key=x=>`${x.lineId||''}|${x.targetUnitId}`;const a=new Map((previous||[]).map(x=>[key(x),x])),b=new Map((next||[]).map(x=>[key(x),x]));const keys=new Set([...a.keys(),...b.keys()]);const out=[];
    for(const k of keys){const x=a.get(k),y=b.get(k);if(!x){out.push(y);continue;}if(!y){out.push({...x,stream:scaleStream(x.stream,1-relax)});continue;}const s=copyStream(y.stream);s.flow=x.stream.flow*(1-relax)+y.stream.flow*relax;for(const c of KEYS)s.mass[c]=x.stream.mass[c]*(1-relax)+y.stream.mass[c]*relax;out.push({...y,stream:normalizeStream(s)});}
    return out;
  }
  function returnsDifference(a,b){const key=x=>`${x.lineId||''}|${x.targetUnitId}`;const ma=new Map((a||[]).map(x=>[key(x),x.stream])),mb=new Map((b||[]).map(x=>[key(x),x.stream]));let d=0;for(const k of new Set([...ma.keys(),...mb.keys()]))d=Math.max(d,streamDifference(ma.get(k)||makeStream(0),mb.get(k)||makeStream(0)));return d;}

  function solveIntegratedNetwork({influent,units,recycles=[],sludgeLines=[]},options={}){
    let returns=[];let water=null,sludge=null,converged=false,outerIterations=0,seedStates=null,totalWaterIterations=0;const warnings=[];const maxOuter=num(options.maxOuterIterations,30),tol=num(options.outerTolerance,1e-6),outerRelax=clamp(num(options.outerRelaxation,0.8),0.05,1);
    for(let i=1;i<=maxOuter;i++){
      outerIterations=i;
      water=solveWaterNetwork(influent,units,recycles,returns,{...options,initialStates:seedStates});
      totalWaterIterations+=water.iterations;seedStates=water.byId;
      sludge=solveSludgeNetwork(water.sludgeSources,sludgeLines,units);
      const next=sludge.returnStreams;const d=returnsDifference(returns,next);
      returns=blendReturns(returns,next,outerRelax);
      if(d<tol){converged=true;break;}
    }
    water=solveWaterNetwork(influent,units,recycles,returns,{...options,initialStates:seedStates});totalWaterIterations+=water.iterations;sludge=solveSludgeNetwork(water.sludgeSources,sludgeLines,units);
    warnings.push(...water.warnings,...sludge.warnings);if(!converged&&sludgeLines.some(l=>l.returnEnabled!==false))warnings.push('Integrated water/sludge sidestream iteration reached its limit before full convergence.');
    return {water,sludge,returns,warnings:[...new Set(warnings)],converged,outerIterations,totalWaterIterations};
  }

  return {VERSION:'0.2.3',KEYS,FIELD_META,SLUDGE_FIELD_META,makeStream,copyStream,mixStreams,concentration,totalNConcentration,profileForType,defaultConfig,effectiveConfig,profileFields,canProduceSludge,sludgeProfileForType,sludgeDefaultConfig,sludgeEffectiveConfig,sludgeProfileFields,sludgeUnitTransform,recyclePortLabel,applyWaterUnit,solveWaterNetwork,solveSludgeNetwork,solveIntegratedNetwork};
});
