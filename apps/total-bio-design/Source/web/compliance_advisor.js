(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports){module.exports=api;}
  else{root.TotalBioComplianceAdvisor=api;}
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const METHOD_NAMES={
    daf:'Dissolved Air Flotation (DAF)',
    mbbr_bod:'MBBR carbon-removal stage',
    mbbr_nit:'MBBR nitrification stage',
    mbr:'Membrane bioreactor (MBR)',
    ammonia_stripping:'Ammonia stripping',
    secondary:'Secondary clarifier',
    tertiary:'Tertiary sand filter',
    cloth_filter:'Cloth media filter',
    uf:'Ultrafiltration',
    gac:'Granular activated carbon',
    aop_uv_h2o2:'UV/H₂O₂ advanced oxidation',
    pre_anoxic:'Pre-anoxic denitrification',
    post_anoxic:'Post-anoxic denitrification',
    anammox:'Anammox / deammonification',
    bio_p_ao:'A/O biological phosphorus removal',
    tertiary_p_filter:'Tertiary phosphorus filter',
    chem_p:'Chemical phosphorus removal',
    p_postprecip:'Post-precipitation',
    grease_interceptor:'Grease interceptor',
    oil_water:'Oil-water separator'
  };

  const SETS={
    biologicalCarbon:new Set(['cas','extended_aeration','oxidation_ditch','aerated_lagoon','sbr','aerobic_granular','mbr','mbbr_bod','mbbr_ifas','trickling_filter','rbc','baf','mabr','submerged_fixed_film','uasb','egsb','ic_reactor','anaerobic_contact','anaerobic_filter','anaerobic_lagoon','anmbr']),
    separation:new Set(['secondary','lamella_secondary','daf_secondary','mbr','anmbr','microfiltration','uf','ceramic_membrane','tertiary','dual_media_filter','cloth_filter','disc_filter']),
    nitrification:new Set(['cas','extended_aeration','oxidation_ditch','sbr','aerobic_granular','mbr','mbbr_nit','mbbr_ifas','baf','mabr','partial_nitritation']),
    denitrification:new Set(['denit','pre_anoxic','post_anoxic','mbbr_denit','step_feed_bnr','bardenpho','a2o','vip_bnr']),
    biologicalP:new Set(['ebpr','bio_p_ao','a2o','vip_bnr']),
    chemicalP:new Set(['chem_p','p_preprecip','p_coprecip','p_postprecip','ferric_p','ferric_sulfate_p','ferrous_p','alum_p','pacl_p','lime_p','electrocoag_p','tertiary_p_filter','ballasted_p']),
    fog:new Set(['daf','igf','api_separator','cpi_separator','grease_interceptor','oil_water'])
  };

  function finiteTarget(x){
    if(x===null||x===undefined||(typeof x==='string'&&x.trim()===''))return null;
    const n=Number(x);
    return Number.isFinite(n)&&n>=0?n:null;
  }

  function assess(finalStream,targets,processApi){
    if(!processApi)throw new Error('Process-network API is required for compliance assessment.');
    const defs=[
      ['Total COD','cod',targets?.cod],
      ['BOD₅','bod',targets?.bod],
      ['TSS','tss',targets?.tss],
      ['Ammonia-N','nh4',targets?.nh4],
      ['Total nitrogen','tn',targets?.tn],
      ['Total phosphorus','tp',targets?.tp],
      ['FOG','fog',targets?.fog]
    ];
    return defs.map(([name,key,targetRaw])=>{
      const target=finiteTarget(targetRaw);
      const predicted=key==='tn'?processApi.totalNConcentration(finalStream):processApi.concentration(finalStream,key);
      const pass=target===null||predicted<=target;
      return {name,key,predicted,target,hasTarget:target!==null,pass,status:target===null?'NO TARGET':pass?'PASS':'FAIL',ratio:target?predicted/target:null};
    });
  }

  const contains=(types,set)=>types.some(t=>set.has(t));
  function rec(type,summary,rationale){return {type,name:METHOD_NAMES[type]||type,summary,rationale};}
  function unique(items){const seen=new Set();return items.filter(x=>x&&x.type&&!seen.has(x.type)&&seen.add(x.type));}

  function suggestionsFor(failure,unitTypes=[],context={}){
    if(!failure||failure.pass||!failure.hasTarget)return [];
    const types=Array.isArray(unitTypes)?unitTypes:[];
    const out=[];
    switch(failure.key){
      case 'bod':
        if(!contains(types,SETS.biologicalCarbon))out.push(rec('mbbr_bod','Add biological carbon removal before final solids separation.','A dedicated aerobic MBBR stage provides compact, independently configurable BOD polishing.'));
        if(!contains(types,SETS.separation))out.push(rec('secondary','Add final biomass and suspended-solids separation.','Biological solids can carry particulate BOD into the final effluent unless they are separated.'));
        out.push(rec('mbbr_bod','Add an additional MBBR BOD-polishing stage.','A second biological stage can reduce residual biodegradable organics before the final separator.'));
        if(failure.target!==null&&failure.target<=5)out.push(rec('uf','Add membrane or fine-filtration polishing.','A low BOD target often requires stronger control of residual particulate BOD after biological treatment.'));
        break;
      case 'cod':
        if(!contains(types,SETS.biologicalCarbon))out.push(rec('mbbr_bod','Add biological COD/BOD removal.','A biological carbon-removal stage addresses the biodegradable COD fraction.'));
        if(!types.includes('daf'))out.push(rec('daf','Add DAF pretreatment when COD is associated with FOG or suspended solids.','DAF can remove floatable and particulate COD before the biological reactors.'));
        out.push(rec('gac','Add activated-carbon polishing.','GAC is a practical polishing option for residual dissolved or slowly biodegradable organic matter.'));
        out.push(rec('aop_uv_h2o2','Consider advanced oxidation for refractory COD.','AOP should be considered only after confirming that the residual COD is refractory and suitable for oxidation.'));
        break;
      case 'tss':
        if(!contains(types,SETS.separation))out.push(rec('secondary','Add secondary clarification.','The current train does not include a dedicated final biomass-separation step.'));
        if(failure.target!==null&&failure.target<=2)out.push(rec('uf','Add ultrafiltration after biological solids separation.','Very low TSS targets generally require membrane or equivalent high-rate tertiary separation.'));
        out.push(rec('cloth_filter','Add tertiary cloth-media filtration.','A tertiary filter captures residual suspended solids escaping the secondary separator.'));
        out.push(rec('tertiary','Add tertiary granular filtration.','Sand or dual-media filtration provides conventional final TSS polishing.'));
        break;
      case 'nh4':
        if(!contains(types,SETS.nitrification))out.push(rec('mbbr_nit','Add a dedicated nitrification stage.','An aerobic attached-growth stage provides additional nitrifier inventory and can be placed in series.'));
        else out.push(rec('mbbr_nit','Add a second-stage MBBR nitrification polisher.','Additional attached-growth area can reduce residual ammonia downstream of the main aerobic stage.'));
        out.push(rec('mbr','Consider an MBR or high-SRT biological configuration.','A high-solids-retention-time configuration can improve nitrification reliability when temperature and loading are challenging.'));
        out.push(rec('ammonia_stripping','Consider ammonia stripping for high-strength industrial wastewater.','Physical ammonia removal is a special-case alternative requiring pH, emissions, and off-gas review.'));
        break;
      case 'tn': {
        const nh4Assessment=(context.assessments||[]).find(x=>x.key==='nh4');
        if(!contains(types,SETS.nitrification)||(nh4Assessment&&nh4Assessment.hasTarget&&!nh4Assessment.pass))out.push(rec('mbbr_nit','Complete nitrification before adding more denitrification capacity.','Total nitrogen cannot be reduced effectively if a significant ammonia load remains unoxidized.'));
        if(!contains(types,SETS.denitrification))out.push(rec('pre_anoxic','Add pre-anoxic denitrification with internal recycle.','A pre-anoxic zone uses influent carbon to remove nitrate returned from the aerobic/nitrification stage.'));
        else out.push(rec('post_anoxic','Add post-anoxic polishing.','A downstream anoxic stage can remove residual nitrate; external carbon may be required.'));
        out.push(rec('anammox','Evaluate sidestream anammox for concentrated recycle loads.','Anammox is most relevant when dewatering returns contribute a high ammonia load.'));
        break;
      }
      case 'tp':
        if(!contains(types,SETS.biologicalP))out.push(rec('bio_p_ao','Add an anaerobic/aerobic biological phosphorus-removal configuration.','EBPR can reduce chemical demand when sufficient readily biodegradable COD/VFA is available.'));
        if(failure.target!==null&&failure.target<=1)out.push(rec('tertiary_p_filter','Add tertiary chemical phosphorus filtration.','Low phosphorus limits usually require precipitation followed by reliable solids capture.'));
        if(!contains(types,SETS.chemicalP))out.push(rec('chem_p','Add chemical phosphorus precipitation and separation.','Ferric, alum, PACl, lime, or another selected chemistry can provide a controllable phosphorus-removal barrier.'));
        else out.push(rec('p_postprecip','Add a post-precipitation polishing step.','A final chemical polishing stage can address residual soluble orthophosphate.'));
        break;
      case 'fog':
        if(!contains(types,SETS.fog))out.push(rec('daf','Add DAF pretreatment.','DAF is a common industrial pretreatment for emulsified FOG and associated suspended solids.'));
        out.push(rec('grease_interceptor','Add source-control grease separation.','A grease interceptor can reduce foodservice FOG loading before equalization and biological treatment.'));
        out.push(rec('oil_water','Add an oil-water separator for free oil.','Free oil should be removed upstream when it is distinct from emulsified FOG.'));
        break;
      default: break;
    }
    return unique(out).slice(0,3);
  }

  const PRETREATMENT=new Set(['screening','fine_screen','step_screen','rotary_drum_screen','grit','equalization','neutralization','coag_floc','electrocoagulation','daf','igf','api_separator','cpi_separator','grease_interceptor','oil_water','primary','lamella_primary']);
  const BIO=new Set(['uasb','egsb','ic_reactor','anaerobic_contact','anaerobic_filter','anaerobic_lagoon','anmbr','ebpr','denit','cas','extended_aeration','sbr','oxidation_ditch','aerobic_granular','mbr','aerated_lagoon','mbbr_bod','mbbr_nit','mbbr_denit','mbbr_ifas','trickling_filter','rbc','baf','mabr','submerged_fixed_film','pre_anoxic','post_anoxic','step_feed_bnr','bardenpho','partial_nitritation','anammox','deammonification','bio_p_ao','a2o','vip_bnr']);
  const SEPARATION=new Set(['secondary','lamella_secondary','daf_secondary','microscreen','microfiltration','uf','ceramic_membrane']);
  const DISINFECTION=new Set(['uv','chlorination','hypochlorite','chlorine_dioxide','ozone_disinfection','peracetic_acid','dechlorination']);

  function recommendedInsertionIndex(type,units=[]){
    const list=Array.isArray(units)?units:[];
    const types=list.map(u=>typeof u==='string'?u:u.type);
    const first=(set)=>{const i=types.findIndex(t=>set.has(t));return i<0?types.length:i;};
    const last=(set)=>{let out=-1;types.forEach((t,i)=>{if(set.has(t))out=i;});return out;};
    if(PRETREATMENT.has(type))return first(BIO);
    if(['pre_anoxic','bio_p_ao','ebpr'].includes(type)){
      const aerobic=new Set(['cas','extended_aeration','oxidation_ditch','sbr','aerobic_granular','mbr','mbbr_bod','mbbr_nit','mbbr_ifas','baf','mabr']);
      return first(aerobic);
    }
    if(['mbbr_bod','mbbr_nit','cas','extended_aeration','mbr'].includes(type))return first(SEPARATION);
    if(type==='post_anoxic')return first(SEPARATION);
    if(type==='secondary'){
      const i=last(BIO);return i>=0?i+1:first(DISINFECTION);
    }
    if(['tertiary','cloth_filter','uf','gac','aop_uv_h2o2','tertiary_p_filter','chem_p','p_postprecip'].includes(type))return first(DISINFECTION);
    return types.length;
  }

  return {VERSION:'0.2.3',METHOD_NAMES,assess,suggestionsFor,recommendedInsertionIndex};
});
