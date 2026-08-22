(() => {
'use strict';
const snapshot = JSON.parse(document.getElementById('reportSnapshot')?.textContent || '{}');
const r = snapshot.result || {};
const w = snapshot.water_profile || {};
const input = snapshot.design_input || {};
const project = snapshot.project || {};
const options = snapshot.options || {};
const root = document.getElementById('engineeringReportRoot');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => { if(value===null||value===undefined||(typeof value==='string'&&value.trim()===''))return null; const n=Number(value); return Number.isFinite(n) ? n : null; };
const first = (...values) => { for (const v of values) { const n=number(v); if (n!==null) return n; } return null; };
const textFirst = (...values) => values.find(v => v!==null && v!==undefined && String(v).trim()!=='') ?? '';
const fmt = (value, digits=2, dash='—') => { const n=number(value); return n===null ? dash : n.toLocaleString(undefined,{minimumFractionDigits:digits,maximumFractionDigits:digits}); };
const fmtSmart = value => { const n=number(value); if(n===null)return '—'; const a=Math.abs(n); return fmt(n,a>=1000?0:a>=100?1:a>=10?2:3); };
const pct = (value,d=1) => { const n=number(value); if(n===null)return '—'; return `${fmt(Math.abs(n)<=1.5?n*100:n,d)}%`; };
const stageCount = Math.max(1,Math.min(4,Number(snapshot.stage_count || r.stage_count || 1)));
const flowUnit = textFirst(r.flow_unit,snapshot.unit_system?.flow,'m3/h');
const pressureUnit = textFirst(r.pressure_unit,snapshot.unit_system?.pressure,'bar');
const fluxUnit = textFirst(snapshot.unit_system?.flux,'LMH');
const resultCompositionTds = comp => comp && typeof comp==='object' ? Object.values(comp).reduce((a,v)=>a+(number(v)||0),0) : null;
const stageProfile = stage => Array.isArray(r[`stage${stage}_element_profile`]) ? r[`stage${stage}_element_profile`] : [];
const allElements = () => { const rows=[]; let global=0; for(let stage=1;stage<=stageCount;stage++) stageProfile(stage).forEach((e,i)=>rows.push({...e,stage,local:Number(e.element||i+1),position:++global})); return rows; };
const elements = allElements();
const stageFeedFlow = stage => stage===1 ? first(r.feed_flow,r.stage1_feed_flow) : first(r[`stage${stage}_feed_flow`],r[`reject_flow_${stage-1}`]);
const stagePermFlow = stage => first(r[`stage${stage}_permeate_flow`],r[`product_flow_${stage}`]);
const stageRejectFlow = stage => first(r[`reject_flow_${stage}`],r[`stage${stage}_concentrate_flow`]);
const stageFeedP = stage => first(r[`membrane_pressure_${stage}`],r[`stage${stage}_feed_pressure`]);
const stageRejectP = stage => first(r[`reject_pressure_${stage}`],r[`stage${stage}_concentrate_pressure`]);
const stageFeedTds = stage => first(r[`stage${stage}_feed_tds_ppm`],resultCompositionTds(r[`stage${stage}_feed_composition_mg_l`]),stage===1?w.analysis_tds:null);
const stageConcTds = stage => first(r[`stage${stage}_concentrate_tds_ppm`],resultCompositionTds(r[`stage${stage}_concentrate_composition_mg_l`]));
const stagePermTds = stage => first(r[`stage${stage}_permeate_tds_ppm`],resultCompositionTds(r[`stage${stage}_permeate_composition_mg_l`]));
const finalRejectFlow = stageRejectFlow(stageCount);
const finalRejectP = stageRejectP(stageCount);
const compositePermTds = first(r.composite_permeate_tds_ppm,r.permeate_tds_ppm,resultCompositionTds(r.composite_permeate_composition_mg_l));
const finalConcTds = stageConcTds(stageCount);
const feedTds = first(stageFeedTds(1),w.analysis_tds,w.feed_tds);
const membraneRecipe = stage => {
  let recipe=input[`membrane_recipe_${stage}`];
  if(typeof recipe==='string'){try{recipe=JSON.parse(recipe)}catch(_){recipe=null}}
  if(Array.isArray(recipe)&&recipe.length){const compact=recipe.map(x=>String(x).split('|')[1]||String(x)).filter(Boolean);return [...new Set(compact)].join(' / ')}
  return textFirst(r[`stage${stage}_membrane_model`],input[`membrane_${stage}`],`Stage ${stage} membrane`).split('|')[1] || textFirst(r[`stage${stage}_membrane_model`],input[`membrane_${stage}`]);
};
const infoItem=(label,value)=>value===null||value===undefined||String(value).trim()===''?'':`<div class="info-item"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
const row=(label,value)=>`<dt>${esc(label)}</dt><dd>${value}</dd>`;
const sectionTitle=(title,meta='')=>`<div class="section-title"><h2>${esc(title)}</h2>${meta?`<span>${esc(meta)}</span>`:''}</div>`;
const table=(headers,rows,cls='')=>`<div class="table-wrap"><table class="report-table ${cls}"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
const currentDate = new Date(snapshot.generated_at || Date.now());
const projectName = textFirst(project.project_name,'Total RO Design Project');
const projectId = textFirst(project.project_id,'');
const caseLabel = textFirst(snapshot.case_name,w.envelope_label,`Case ${snapshot.case_id||1}`);
const revision = textFirst(project.revision,'Rev 0');
document.getElementById('runningHeaderMeta').textContent=`${projectName}${projectId?` · ${projectId}`:''} · ${caseLabel} · ${revision} · v${snapshot.app_version||'0.2'}`;
document.getElementById('runningFooterMeta').textContent=`${projectName} · ${caseLabel} · ${revision} · Generated ${currentDate.toLocaleString()}`;

function projectBand(){
  const items=[
    ['Project',projectName],['Project ID',projectId],['Customer',project.client],['Prepared by',project.user],['Location',project.project_location],['Project Country',textFirst(project.project_country,project.project_country_name)],['Project date',project.project_date],['Revision',revision],['Case',caseLabel],['Water source',textFirst(w.water_region_name,w.source_water_type)],['Water type',w.source_water_type],['Feed temperature',number(w.temperature_c)!==null?`${fmt(w.temperature_c,1)} °C`:null],['Feed pH',number(w.feed_ph)!==null?fmt(w.feed_ph,2):null],['Feed TDS',feedTds!==null?`${fmt(feedTds,1)} mg/L`:null],['Design mode',String(input.design_mode||'manual').replace(/^./,x=>x.toUpperCase())],['Unit system',`${flowUnit} · ${pressureUnit} · ${fluxUnit}`]
  ].map(([a,b])=>infoItem(a,b)).join('');
  return `<section class="section">${sectionTitle('1. Project and Design Basis','Only populated reproduction-critical values')}<div class="info-grid">${items}</div></section>`;
}
function summaryGroups(){
  const productPerTrain=first(r.train_product_capacity_m3d,r.product_flow!==undefined?Number(r.product_flow)*24:null);
  const area=first(r.total_membrane_area_m2,r.total_active_area_m2);
  const avgNdp=elements.length?elements.reduce((a,e)=>a+(number(e.ndp_bar)||0),0)/elements.length:first(r.average_ndp_bar,r.ndp_bar);
  const feedOsm=first(r.feed_osmotic_pressure_bar,r.stage1_feed_osmotic_bar,r.stage1_feed_osmotic,r.stage1_osmotic_pressure_bar);
  const concOsm=first(r.final_concentrate_osmotic_pressure_bar,r[`stage${stageCount}_concentrate_osmotic_bar`],r[`stage${stageCount}_concentrate_osmotic`]);
  const totalSec=first(r.total_plant_sec,r.total_sec,r.sec_total,r.specific_energy,r.sec);
  const roSec=first(r.ro_gross_sec,r.gross_sec,r.ro_sec,r.hpp_specific_energy);
  const preSec=first(r.pretreatment_sec,r.pretreatment_specific_energy);
  const erd=textFirst(r.erd_type,r.energy_recovery_type,input.energy_recovery_mode==='with'?'Configured':'None');
  return `<section class="section">${sectionTitle('2. Overall System Summary',`${stageCount} stage${stageCount===1?'':'s'}`)}<div class="summary-grid">
    <article class="summary-group"><h3>Production & configuration</h3><dl>${row('Required plant product',first(r.required_capacity_m3d,input.required_capacity_m3d)!==null?`${fmt(first(r.required_capacity_m3d,input.required_capacity_m3d),0)} m³/d`:'—')}${row('Normal plant capacity',first(r.normal_operating_capacity_m3d)!==null?`${fmt(r.normal_operating_capacity_m3d,0)} m³/d`:'—')}${row('Per-train permeate',productPerTrain!==null?`${fmt(productPerTrain,0)} m³/d`:'—')}${row('Feed / train',`${fmt(r.feed_flow,2)} ${esc(flowUnit)}`)}${row('Concentrate / train',`${fmt(finalRejectFlow,2)} ${esc(flowUnit)}`)}${row('Overall recovery',pct(r.recovery,1))}${row('Trains',`${fmt(first(r.operating_trains,input.operating_trains),0)} operating · ${fmt(first(r.standby_trains,input.standby_trains),0)} standby`)}${row('Array inventory',`${fmt(r.total_pressure_vessels,0)} vessels · ${fmt(r.total_membrane_elements,0)} elements`)}${row('Active area / train',area!==null?`${fmt(area,0)} m²`:'—')}</dl></article>
    <article class="summary-group"><h3>Water quality & osmotic conditions</h3><dl>${row('RO feed TDS',`${fmt(feedTds,1)} mg/L`)}${row('Final concentrate TDS',`${fmt(finalConcTds,1)} mg/L`)}${row('Composite permeate TDS',`${fmt(compositePermTds,2)} mg/L`)}${row('Feed pH',fmt(w.feed_ph,2))}${row('Composite permeate pH',fmt(first(r.composite_permeate_ph,r[`stage${stageCount}_permeate_ph`]),2))}${row('Feed osmotic pressure',feedOsm!==null?`${fmt(feedOsm,2)} bar`:'Not calculated')}${row('Final concentrate osmotic',concOsm!==null?`${fmt(concOsm,2)} bar`:'Not calculated')}${row('Average NDP',avgNdp!==null?`${fmt(avgNdp,2)} bar`:'—')}${row('Temperature',`${fmt(w.temperature_c,1)} °C`)}</dl></article>
    <article class="summary-group"><h3>Pressure & energy</h3><dl>${row('Stage 1 membrane feed',`${fmt(stageFeedP(1),2)} ${esc(pressureUnit)}`)}${row('Final concentrate pressure',`${fmt(finalRejectP,2)} ${esc(pressureUnit)}`)}${row('HPP inlet pressure',`${fmt(first(r.hpp_inlet_pressure,r.suction_pressure,input.suction_pressure),2)} ${esc(pressureUnit)}`)}${row('HPP discharge pressure',`${fmt(first(r.hpp_discharge_pressure,stageFeedP(1)),2)} ${esc(pressureUnit)}`)}${row('Pump efficiency',first(r.hpp_pump_efficiency_used,r.pump_operating_efficiency,r.hpp_efficiency,r.pump_efficiency)!==null?pct(first(r.hpp_pump_efficiency_used,r.pump_operating_efficiency,r.hpp_efficiency,r.pump_efficiency),1):'Not calculated')}${row('Motor efficiency',first(r.hpp_motor_efficiency_used,r.motor_efficiency,r.hpp_motor_efficiency)!==null?pct(first(r.hpp_motor_efficiency_used,r.motor_efficiency,r.hpp_motor_efficiency),1):'Not calculated')}${row('Energy recovery',esc(erd||'None'))}${row('RO gross SEC',roSec!==null?`${fmt(roSec,3)} kWh/m³`:'—')}${row('Pretreatment SEC',preSec!==null?`${fmt(preSec,3)} kWh/m³`:'—')}${row('Total plant SEC',totalSec!==null?`${fmt(totalSec,3)} kWh/m³`:'—')}</dl></article>
  </div></section>`;
}
function stageTable(){
  const rows=[];
  for(let stage=1;stage<=stageCount;stage++){
    const boost=stage>1?first(r[`interstage_boost_${stage}`],r[`stage${stage}_interstage_boost`]):null;
    const back=first(r[`stage${stage}_permeate_backpressure`],input[`permeate_backpressure_${stage}`],stage===1?input.permeate_pressure:null);
    rows.push(`<tr><td class="center"><strong>${stage}</strong></td><td class="label">${esc(membraneRecipe(stage))}</td><td class="num">${fmt(first(r[`stage${stage}_pressure_vessels`],input[`vessels_${stage}`]),0)}</td><td class="num">${fmt(first(r[`stage${stage}_elements_per_vessel`],input[`elements_per_vessel_${stage}`]),0)}</td><td class="num">${fmt(r[`stage${stage}_total_elements`],0)}</td><td class="num">${fmt(stageFeedFlow(stage),2)}</td><td class="num">${fmt(stagePermFlow(stage),2)}</td><td class="num">${fmt(stageRejectFlow(stage),2)}</td><td class="num">${fmt(stageFeedP(stage),2)}</td><td class="num">${fmt(stageRejectP(stage),2)}</td><td class="num">${fmt(first(r[`stage${stage}_stage_dp`],stageFeedP(stage)!==null&&stageRejectP(stage)!==null?stageFeedP(stage)-stageRejectP(stage):null),2)}</td><td class="num">${boost===null?'—':fmt(boost,2)}</td><td class="num">${back===null?'—':fmt(back,2)}</td><td class="num">${pct(r[`stage${stage}_recovery`]??(stage===1?r.recovery:null),1)}</td><td class="num">${fmt(first(r[`stage${stage}_flux_lmh`]),2)}</td><td class="num">${fmt(stageFeedTds(stage),0)}</td><td class="num">${fmt(stageConcTds(stage),0)}</td><td class="num">${fmt(stagePermTds(stage),2)}</td><td class="num">${fmt(first(r[`stage${stage}_polarization_factor_monovalent`],r[`stage${stage}_polarization_factor`]),2)}</td><td class="num">${fmt(first(r[`stage${stage}_polarization_factor_divalent`],r[`stage${stage}_polarization_factor`]),2)}</td></tr>`);
  }
  const heads=['Stage','Membrane / hybrid recipe','Vessels','Elem./vessel','Elements',`Feed<br><small>${esc(flowUnit)}</small>`,`Permeate<br><small>${esc(flowUnit)}</small>`,`Concentrate<br><small>${esc(flowUnit)}</small>`,`Feed P<br><small>${esc(pressureUnit)}</small>`,`Conc. P<br><small>${esc(pressureUnit)}</small>`,`Stage ΔP<br><small>${esc(pressureUnit)}</small>`,`Boost<br><small>${esc(pressureUnit)}</small>`,`Perm. BP<br><small>${esc(pressureUnit)}</small>`,'Recovery',`Avg. flux<br><small>${esc(fluxUnit)}</small>`,'Feed TDS','Conc. TDS','Perm. TDS','CP mono','CP div.'];
  return `<section class="section">${sectionTitle('3. Stage Performance','Actual calculated stage sequence')}${table(heads,rows,'dense')}</section>`;
}
const species=[['ammonium','NH₄⁺'],['sodium','Na⁺'],['potassium','K⁺'],['magnesium','Mg²⁺'],['calcium','Ca²⁺'],['strontium','Sr²⁺'],['barium','Ba²⁺'],['iron_ii','Fe²⁺'],['iron_iii','Fe³⁺'],['manganese_ii','Mn²⁺'],['fluoride','F⁻'],['chloride','Cl⁻'],['sulfate','SO₄²⁻'],['nitrate','NO₃⁻'],['bicarbonate','HCO₃⁻'],['carbonate','CO₃²⁻'],['phosphate','PO₄³⁻'],['boron','B'],['silica','SiO₂'],['bromide','Br⁻']];
function streamComposition(key){
  const raw=Object.fromEntries(species.map(([k])=>[k,number(w[`ion_${k}`])||0]));
  if(key==='raw')return raw;
  if(key==='feed')return r.acid_dosing_enabled?(r.acid_adjusted_feed_composition_mg_l||r.stage1_feed_composition_mg_l||raw):(r.stage1_feed_composition_mg_l||raw);
  if(key==='composite')return r.composite_permeate_composition_mg_l||r[`stage${stageCount}_permeate_composition_mg_l`]||{};
  const m=key.match(/^s(\d+)(c|p)$/);if(m)return r[`stage${m[1]}_${m[2]==='c'?'concentrate':'permeate'}_composition_mg_l`]||{};
  return {};
}
function streamPh(key){
  if(key==='raw')return first(w.feed_ph);
  if(key==='feed')return first(r.acid_adjusted_feed_ph,r.stage1_feed_ph,w.feed_ph);
  if(key==='composite')return first(r.composite_permeate_ph,r[`stage${stageCount}_permeate_ph`]);
  const m=key.match(/^s(\d+)(c|p)$/);return m?first(r[`stage${m[1]}_${m[2]==='c'?'concentrate':'permeate'}_ph`]):null;
}
function streamAlkalinity(key){
  if(key==='raw')return first(w.ion_bicarbonate);
  if(key==='feed')return first(r.acid_adjusted_feed_alkalinity_mg_l_as_hco3,r.stage1_feed_alkalinity_mg_l_as_hco3,w.ion_bicarbonate);
  if(key==='composite')return first(r.composite_permeate_alkalinity_mg_l_as_hco3);
  const m=key.match(/^s(\d+)(c|p)$/);return m?first(r[`stage${m[1]}_${m[2]==='c'?'concentrate':'permeate'}_alkalinity_mg_l_as_hco3`]):null;
}
function waterAnalysis(){
  const concentrateKeys=r.acid_dosing_enabled?[['raw','Raw feed water'],['feed','Adjusted RO feed']]:[['feed','RO feed']];
  for(let i=1;i<=stageCount;i++)concentrateKeys.push([`s${i}c`,i===stageCount?'Final concentrate':`Stage ${i} concentrate`]);
  const permeateKeys=[];for(let i=1;i<=stageCount;i++)permeateKeys.push([`s${i}p`,`Stage ${i} permeate`]);permeateKeys.push(['composite','Composite permeate']);
  const makeRows=keys=>{const rows=species.map(([key,label])=>`<tr><td class="label">${esc(label)}</td>${keys.map(([stream])=>`<td class="num">${fmt(streamComposition(stream)[key],2)}</td>`).join('')}</tr>`);rows.push(`<tr><td class="label"><strong>Species sum / TDS</strong></td>${keys.map(([stream])=>`<td class="num"><strong>${fmt(resultCompositionTds(streamComposition(stream)),2)}</strong></td>`).join('')}</tr>`);rows.push(`<tr><td class="label"><strong>pH</strong></td>${keys.map(([stream])=>`<td class="num"><strong>${fmt(streamPh(stream),2)}</strong></td>`).join('')}</tr>`);rows.push(`<tr><td class="label"><strong>Alkalinity as HCO₃⁻</strong></td>${keys.map(([stream])=>`<td class="num"><strong>${fmt(streamAlkalinity(stream),2)}</strong></td>`).join('')}</tr>`);return rows;};
  const makeTable=keys=>table(['Species',...keys.map(([,label])=>`${esc(label)}<br><small>mg/L</small>`)],makeRows(keys),'chemistry');
  const content=stageCount<=2?makeTable([...concentrateKeys,...permeateKeys]):`<div class="two-table-grid"><div>${makeTable(concentrateKeys)}</div><div>${makeTable(permeateKeys)}</div></div>`;
  return `<section class="section">${sectionTitle('4. Water Analysis',r.acid_dosing_enabled?'Raw source water, acid-adjusted RO feed, concentrate and permeate paths':stageCount<=2?'Concentrate and permeate paths':'Split for readable multi-stage presentation')}${content}</section>`;
}
function chemicalConditioningSection(){
  if(!r.acid_dosing_enabled||!r.acid_dosing)return '';
  const d=r.acid_dosing,acid=String(d.acid_type||r.acid_type||'').toLowerCase().includes('h2so4')?'Sulfuric acid (H₂SO₄)':'Hydrochloric acid (HCl)';
  const sulfate=String(d.acid_type||'').toLowerCase().includes('h2so4');
  const rows=[['Chemical',acid],['Raw feed pH',fmt(first(d.feed_ph,w.feed_ph),2)],['Target pH',fmt(d.target_ph,2)],['Calculated adjusted-feed pH',fmt(first(d.resulting_ph,r.acid_adjusted_feed_ph),2)],['Commercial solution concentration',`${fmt(d.solution_strength_pct,1)} wt%`],['Commercial solution density',`${fmt(d.solution_density_kg_l,3)} kg/L`],['Pure acid dose',`${fmt(d.pure_acid_mg_l,2)} mg/L`],['Commercial solution dose',`${fmt(d.commercial_solution_l_m3,4)} L/m³`],['Pure acid consumption',`${fmt(d.pure_acid_kg_h,2)} kg/h · ${fmt(d.pure_acid_kg_d,1)} kg/day`],['Commercial solution consumption',`${fmt(d.commercial_solution_l_h,2)} L/h · ${fmt(number(d.commercial_solution_l_h)!==null?number(d.commercial_solution_l_h)*24:null,1)} L/day`],['Raw alkalinity',`${fmt(d.feed_alkalinity_mg_l_as_hco3,2)} mg/L as HCO₃⁻`],['Adjusted alkalinity',`${fmt(d.resulting_alkalinity_mg_l_as_hco3,2)} mg/L as HCO₃⁻`],[sulfate?'SO₄²⁻ added':'Cl⁻ added',`${fmt(sulfate?d.sulfate_added_mg_l:d.chloride_added_mg_l,2)} mg/L`]].map(([l,v])=>`<tr><td class="label">${esc(l)}</td><td class="num">${v}</td></tr>`);
  return `<section class="section">${sectionTitle('4A. Chemical Conditioning','Acid addition applied before the membrane calculation')}${table(['Parameter','Calculated value'],rows)}</section>`;
}
function findChemIndex(names){const chem=snapshot.scaling_chemistry||snapshot.chemistry_detail||{};const items=chem.indices||[];const item=items.find(x=>names.some(n=>String(x.name||'').toLowerCase().includes(n)));return item?number(item.value):null;}
function scalingSnapshot(){
  const scalingChem=snapshot.scaling_chemistry||snapshot.chemistry_detail||{};const minerals=(scalingChem.minerals||[]).filter(x=>number(x.concentration_saturation_pct)!==null).sort((a,b)=>(number(b.concentration_saturation_pct)||0)-(number(a.concentration_saturation_pct)||0));
  const limiting=minerals[0];
  const rows=[['LSI',first(r.final_concentrate_lsi,findChemIndex(['langelier','lsi']))],['Stiff & Davis',first(r.final_concentrate_stiff_davis,findChemIndex(['stiff','davis']))],['CaSO₄',first(r.caso4_saturation_pct,minerals.find(x=>String(x.formula).includes('CaSO'))?.concentration_saturation_pct)],['SrSO₄',first(r.srso4_saturation_pct,minerals.find(x=>String(x.formula).includes('SrSO'))?.concentration_saturation_pct)],['BaSO₄',first(r.baso4_saturation_pct,minerals.find(x=>String(x.formula).includes('BaSO'))?.concentration_saturation_pct)],['CaF₂',first(r.caf2_saturation_pct,minerals.find(x=>String(x.formula).includes('CaF'))?.concentration_saturation_pct)],['Silica',first(r.silica_saturation_pct,minerals.find(x=>String(x.name||'').toLowerCase().includes('silica'))?.concentration_saturation_pct)]].map(([label,v])=>`<tr><td class="label">${esc(label)}</td><td class="num ${number(v)!==null&&number(v)>=100?'scaling-attention':''}">${v===null?'—':`${fmt(v,1)}${label.includes('Index')||label==='LSI'||label.includes('Davis')?'':'%'}`}</td></tr>`);
  const highest=first(limiting?.concentration_saturation_pct,r.highest_mineral_saturation_pct);
  const limitingName=textFirst(limiting?.formula,limiting?.name,r.limiting_mineral,'—');
  rows.push(`<tr><td class="label">Highest saturation / limiting mineral</td><td class="num ${number(highest)!==null&&number(highest)>=100?'scaling-attention':''}">${highest===null?'—':`${fmt(highest,1)}% · ${esc(limitingName)}`}</td></tr>`);
  return `<section class="section">${sectionTitle('5. Solubility and Scaling Snapshot','Final concentrate / limiting condition')}${table(['Parameter','Calculated value'],rows)}</section>`;
}
function elementTable(){
  if(!elements.length)return '';
  const rows=[];let lastStage=null;
  elements.forEach(e=>{if(e.stage!==lastStage){rows.push(`<tr class="stage-divider"><td colspan="14">Stage ${e.stage} · ${esc(membraneRecipe(e.stage))}</td></tr>`);lastStage=e.stage}rows.push(`<tr><td class="center">${e.stage}</td><td class="center">${e.local}</td><td class="label">${esc(textFirst(e.membrane_model,e.model,membraneRecipe(e.stage)))}</td><td class="num">${fmt(first(e.feed_flow_m3h,e.feed_flow),2)}</td><td class="num">${fmt(first(e.permeate_flow_m3h,e.permeate_flow),2)}</td><td class="num">${pct(e.recovery,2)}</td><td class="num">${fmt(first(e.feed_pressure_bar,e.feed_pressure),2)}</td><td class="num">${fmt(first(e.dp_bar,e.pressure_drop_bar),3)}</td><td class="num">${fmt(first(e.ndp_bar,e.ndp),2)}</td><td class="num">${fmt(first(e.flux_lmh,e.flux),2)}</td><td class="num">${fmt(first(e.polarization_factor_monovalent,e.polarization_factor),2)}</td><td class="num">${fmt(first(e.polarization_factor_divalent,e.polarization_factor),2)}</td><td class="num">${fmt(first(e.feed_tds_ppm,e.feed_tds),1)}</td><td class="num">${fmt(first(e.permeate_tds_ppm,e.permeate_tds),2)}</td></tr>`)});
  const heads=['Stage','Elem.','Membrane',`Feed<br><small>${esc(flowUnit)}</small>`,`Perm.<br><small>${esc(flowUnit)}</small>`,'Elem. rec.',`Feed P<br><small>${esc(pressureUnit)}</small>`,`ΔP<br><small>${esc(pressureUnit)}</small>`,`NDP<br><small>${esc(pressureUnit)}</small>`,`Flux<br><small>${esc(fluxUnit)}</small>`,'CP mono','CP div.','Feed TDS','Perm. TDS'];
  return `<section class="section">${sectionTitle('6. Element-by-Element Performance',`${elements.length} representative element positions`)}${table(heads,rows,'dense')}</section>`;
}
function chartSvg(series,{title,yLabel,legend=[]}){
  const points=series.flatMap(s=>s.values.map((y,i)=>({x:i+1,y:number(y)}))).filter(p=>p.y!==null);if(!points.length)return '';
  const W=430,H=178,L=42,R=12,T=14,B=30,minX=1,maxX=Math.max(...series.map(s=>s.values.length));let minY=Math.min(...points.map(p=>p.y)),maxY=Math.max(...points.map(p=>p.y));const span=Math.max(maxY-minY,Math.max(Math.abs(maxY),1)*.04);minY-=span*.1;maxY+=span*.1;const x=v=>L+(v-minX)*(W-L-R)/(Math.max(1,maxX-minX));const y=v=>T+(maxY-v)*(H-T-B)/(Math.max(1e-9,maxY-minY));
  const grid=[];for(let i=0;i<=4;i++){const yy=T+(H-T-B)*i/4,val=maxY-(maxY-minY)*i/4;grid.push(`<line class="grid" x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}"/><text x="${L-4}" y="${yy+3}" text-anchor="end">${fmt(val,1)}</text>`)}
  const boundaries=[];let pos=0;for(let st=1;st<stageCount;st++){pos+=stageProfile(st).length;if(pos>0)boundaries.push(`<line x1="${x(pos+.5)}" y1="${T}" x2="${x(pos+.5)}" y2="${H-B}" stroke="#7890a0" stroke-dasharray="3 2"/><text x="${x(pos+.5)+2}" y="${T+8}">S${st+1}</text>`)}
  const paths=series.map((s,si)=>{const valid=s.values.map((v,i)=>({x:i+1,y:number(v)})).filter(p=>p.y!==null);const cls=['series-a','series-b','series-c'][si]||'series-a';const pc=['point-a','point-b','point-c'][si]||'point-a';return `<path class="${cls}" d="${valid.map((p,i)=>`${i?'L':'M'}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(' ')}"/>${valid.map(p=>`<circle class="${pc}" cx="${x(p.x)}" cy="${y(p.y)}" r="2"/>`).join('')}`}).join('');
  const xTicks=Array.from({length:maxX},(_,i)=>`<text x="${x(i+1)}" y="${H-B+13}" text-anchor="middle">${i+1}</text>`).join('');
  return `<article class="chart-card"><h3>${esc(title)}</h3>${legend.length?`<div class="chart-legend">${legend.map((l,i)=>`<span class="legend-line ${i===1?'b':i===2?'c':''}">${esc(l)}</span>`).join('')}</div>`:''}<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}">${grid.join('')}${boundaries.join('')}<line class="axis" x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}"/><line class="axis" x1="${L}" y1="${T}" x2="${L}" y2="${H-B}"/>${paths}${xTicks}<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">Membrane position</text><text transform="translate(10 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text></svg></article>`;
}
function chartsAndCritical(){
  if(!elements.length)return '';
  const flux=elements.map(e=>first(e.flux_lmh,e.flux));
  const mono=elements.map(e=>first(e.polarization_factor_monovalent,e.polarization_factor));
  const div=elements.map(e=>first(e.polarization_factor_divalent,e.polarization_factor));
  const hydraulic=elements.map(e=>first(e.feed_pressure_bar,e.feed_pressure));
  const osm=elements.map(e=>first(e.membrane_surface_osmotic_bar,e.osmotic_pressure_bar,e.osmotic_bar));
  const ndp=elements.map(e=>first(e.ndp_bar,e.ndp));
  const validBy=(key,dir='max')=>elements.filter(e=>number(key(e))!==null).sort((a,b)=>dir==='max'?number(key(b))-number(key(a)):number(key(a))-number(key(b)))[0];
  const maxFlux=validBy(e=>first(e.flux_lmh,e.flux)),minFlux=validBy(e=>first(e.flux_lmh,e.flux),'min'),minNdp=validBy(e=>first(e.ndp_bar,e.ndp),'min'),maxMono=validBy(e=>first(e.polarization_factor_monovalent,e.polarization_factor)),maxDiv=validBy(e=>first(e.polarization_factor_divalent,e.polarization_factor)),maxDp=validBy(e=>first(e.dp_bar,e.pressure_drop_bar));
  const metric=(label,e,val,unit='')=>`<div><span>${esc(label)}</span><strong>${e?`${fmt(val(e),2)}${unit} · S${e.stage} E${e.local}`:'—'}</strong></div>`;
  return `<section class="section">${sectionTitle('7. Membrane Profiles and Critical Elements','Calculated from the report snapshot')}<div class="charts-grid">${chartSvg([{values:flux}],{title:'Flux vs. Membrane Position',yLabel:`Flux (${fluxUnit})`})}${chartSvg([{values:mono},{values:div}],{title:'Polarization Factor vs. Membrane Position',yLabel:'Polarization factor',legend:['Monovalent / neutral','Divalent screening']})}${chartSvg([{values:hydraulic},{values:osm},{values:ndp}],{title:'Hydraulic, Osmotic Pressure and NDP',yLabel:`Pressure (${pressureUnit})`,legend:['Hydraulic pressure','Membrane-surface osmotic','Net driving pressure']})}</div><div class="critical-grid">${metric('Maximum element flux',maxFlux,e=>first(e.flux_lmh,e.flux),` ${fluxUnit}`)}${metric('Minimum element flux',minFlux,e=>first(e.flux_lmh,e.flux),` ${fluxUnit}`)}${metric('Minimum NDP',minNdp,e=>first(e.ndp_bar,e.ndp),` ${pressureUnit}`)}${metric('Maximum CP mono',maxMono,e=>first(e.polarization_factor_monovalent,e.polarization_factor))}${metric('Maximum CP divalent',maxDiv,e=>first(e.polarization_factor_divalent,e.polarization_factor))}${metric('Maximum element ΔP',maxDp,e=>first(e.dp_bar,e.pressure_drop_bar),` ${pressureUnit}`)}</div></section>`;
}
function energyHydraulic(){
  const energyRows=[['RO system SEC',first(r.ro_gross_sec,r.gross_sec,r.ro_sec)],['Pretreatment SEC',first(r.pretreatment_sec,r.pretreatment_specific_energy)],['HPP electrical power',first(r.hpp_electrical_power_kw,r.hpp_power_kw)],['HPP hydraulic power',first(r.hpp_hydraulic_power_kw)],['Interstage booster power',first(r.interstage_booster_power_kw,r.total_interstage_booster_power_kw)],['ERD recovered power',first(r.erd_recovered_power_kw,r.recovered_power_kw)],['Turbocharger contribution',first(r.turbo_recovered_power_kw,r.multistage_turbo_recovered_hydraulic_kw)],['Auxiliary power',first(r.auxiliary_power_kw)],['Total plant SEC',first(r.total_plant_sec,r.total_sec,r.sec_total,r.specific_energy,r.sec)],['Pump efficiency',first(r.hpp_pump_efficiency_used,r.pump_operating_efficiency,r.hpp_efficiency,r.pump_efficiency)],['Motor efficiency',first(r.hpp_motor_efficiency_used,r.motor_efficiency,r.hpp_motor_efficiency)]].filter(([,v])=>number(v)!==null&&Math.abs(number(v))>1e-12).map(([l,v])=>`<tr><td class="label">${esc(l)}</td><td class="num">${l.includes('efficiency')?pct(v,1):`${fmt(v,l.includes('SEC')?3:2)} ${l.includes('SEC')?'kWh/m³':'kW'}`}</td></tr>`);
  const stageNumbers=Array.from({length:stageCount},(_,i)=>i+1),validNumbers=a=>a.map(number).filter(v=>v!==null);
  const stageVesselDps=validNumbers(stageNumbers.map(s=>first(r[`stage${s}_stage_dp`],stageFeedP(s)!==null&&stageRejectP(s)!==null?stageFeedP(s)-stageRejectP(s):null)));
  const stageElementDps=validNumbers(stageNumbers.map(s=>r[`stage${s}_max_actual_dp_per_element`]));
  const stageDpLimits=validNumbers(stageNumbers.map(s=>r[`stage${s}_datasheet_max_dp_per_element`]));
  const stageRejectPerVessel=validNumbers(stageNumbers.map(s=>r[`stage${s}_vessel_reject_flow`]));
  const pressureFromBar=bar=>{const v=number(bar);if(v===null)return null;const u=String(pressureUnit||'bar').toLowerCase();if(u==='psi')return v*14.5037738;if(u==='kpa')return v*100;if(u==='mpa')return v/10;return v;};
  const stagePressureLimits=validNumbers(stageNumbers.map(s=>pressureFromBar(r[`stage${s}_membrane_max_operating_pressure_bar`])));
  const maxVesselDp=first(r.maximum_vessel_dp,r.max_vessel_dp,stageVesselDps.length?Math.max(...stageVesselDps):null);
  const maxElementDp=first(elements.length?Math.max(...elements.map(e=>number(first(e.dp_bar,e.pressure_drop_bar))||0)):null,stageElementDps.length?Math.max(...stageElementDps):null);
  const limitingElementDp=first(r.datasheet_max_dp_per_element,r.max_dp_per_element_limit,stageDpLimits.length?Math.min(...stageDpLimits):null);
  const minRejectPerVessel=first(r.minimum_reject_flow_per_vessel,r.min_reject_flow_per_vessel,stageRejectPerVessel.length?Math.min(...stageRejectPerVessel):null);
  const maxOperatingPressure=first(r.maximum_operating_pressure,r.max_operating_pressure,stagePressureLimits.length?Math.min(...stagePressureLimits):null);
  const hydraulicRows=[['HPP duty',`${fmt(first(r.hpp_flow,r.feed_flow),2)} ${flowUnit} @ ${fmt(first(r.hpp_discharge_pressure,stageFeedP(1)),2)} ${pressureUnit}`],['ERD',esc(textFirst(r.erd_type,r.energy_recovery_type,'None'))],['Final concentrate',`${fmt(finalRejectFlow,2)} ${flowUnit} @ ${fmt(finalRejectP,2)} ${pressureUnit}`],['Maximum vessel ΔP',maxVesselDp!==null?`${fmt(maxVesselDp,2)} ${pressureUnit}`:'—'],['Maximum element ΔP',maxElementDp!==null?`${fmt(maxElementDp,3)} ${pressureUnit}`:'—'],['Element ΔP limit',limitingElementDp!==null?`${fmt(limitingElementDp,2)} ${pressureUnit}`:'—'],['Minimum reject flow / vessel',minRejectPerVessel!==null?`${fmt(minRejectPerVessel,2)} ${flowUnit}`:'—'],['Maximum operating pressure',maxOperatingPressure!==null?`${fmt(maxOperatingPressure,2)} ${pressureUnit}`:'—'],['Hydraulic status',esc(textFirst(r.hydraulic_limit_status,r.hydraulic_status,'Calculated duty point'))]].map(([l,v])=>`<tr><td class="label">${esc(l)}</td><td class="num">${v}</td></tr>`);
  return `<section class="section">${sectionTitle('8. Energy and Hydraulic Summary','Only equipment present in the solved configuration')}<div class="two-table-grid"><div>${table(['Energy item','Value'],energyRows)}</div><div>${table(['Hydraulic item','Value'],hydraulicRows)}</div></div></section>`;
}
function processStreams(){
  const streams=[];let id=1;streams.push({id:id++,description:'RO feed',flow:first(r.feed_flow),pressure:first(r.hpp_inlet_pressure,input.suction_pressure),tds:feedTds,ph:first(w.feed_ph),temp:first(w.temperature_c)});streams.push({id:id++,description:'HPP discharge / Stage 1 feed',flow:first(r.feed_flow),pressure:stageFeedP(1),tds:stageFeedTds(1),ph:first(r.stage1_feed_ph,w.feed_ph),temp:first(w.temperature_c)});
  for(let stage=1;stage<=stageCount;stage++){
    streams.push({id:id++,description:`Stage ${stage} permeate`,flow:stagePermFlow(stage),pressure:first(r[`stage${stage}_permeate_backpressure`],input[`permeate_backpressure_${stage}`],0),tds:stagePermTds(stage),ph:first(r[`stage${stage}_permeate_ph`]),temp:first(w.temperature_c)});
    streams.push({id:id++,description:stage===stageCount?'Final concentrate':`Stage ${stage} concentrate / Stage ${stage+1} feed`,flow:stageRejectFlow(stage),pressure:stageRejectP(stage),tds:stageConcTds(stage),ph:first(r[`stage${stage}_concentrate_ph`]),temp:first(w.temperature_c)});
  }
  streams.push({id:id++,description:'Composite permeate / product',flow:first(r.product_flow),pressure:first(r.permeate_pressure,0),tds:compositePermTds,ph:first(r.composite_permeate_ph),temp:first(w.temperature_c)});
  return streams;
}
function processDiagram(streams){
  const blocks=[{label:'RO Feed',type:'normal'},{label:'HPP',type:'normal'}];for(let s=1;s<=stageCount;s++){blocks.push({label:`Stage ${s}`,type:'normal'});if(s<stageCount&&first(r[`interstage_boost_${s+1}`],r[`stage${s+1}_interstage_boost`])>0)blocks.push({label:'Booster',type:'normal'})}const erd=textFirst(r.erd_type,r.energy_recovery_type);if(erd&&String(erd).toLowerCase()!=='none')blocks.push({label:erd,type:'erd'});blocks.push({label:'Product',type:'product'});const W=900,H=155,pad=20,gap=12,bw=Math.max(75,(W-2*pad-gap*(blocks.length-1))/blocks.length),y=48;let x=pad;const items=[];blocks.forEach((b,i)=>{items.push(`<rect class="block ${b.type==='erd'?'erd':b.type==='product'?'product':''}" x="${x}" y="${y}" rx="5" width="${bw}" height="40"/><text x="${x+bw/2}" y="${y+24}" text-anchor="middle">${esc(b.label)}</text>`);if(i<blocks.length-1)items.push(`<path class="flowline" d="M${x+bw},${y+20} L${x+bw+gap},${y+20}"/>`);x+=bw+gap});items.push(`<path class="flowline" d="M${pad+bw*2+gap},${y+40} C${W*.45},${H-10} ${W*.72},${H-10} ${W-45},${H-20}"/><text x="${W-42}" y="${H-17}" text-anchor="end">Final concentrate</text>`);return `<div class="process-diagram"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Calculated process flow"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#334c60"/></marker></defs>${items.join('')}</svg></div>`;}
function streamsSection(){const streams=processStreams();const rows=streams.map(s=>`<tr><td class="center">${s.id}</td><td class="label">${esc(s.description)}</td><td class="num">${fmt(s.flow,2)}</td><td class="num">${fmt(s.pressure,2)}</td><td class="num">${fmt(s.tds,2)}</td><td class="num">${fmt(s.ph,2)}</td><td class="num">${fmt(s.temp,1)}</td></tr>`);return `<section class="section">${sectionTitle('9. Principal Process Streams','Calculated stream data')}${table(['No.','Stream',`Flow<br><small>${esc(flowUnit)}</small>`,`Pressure<br><small>${esc(pressureUnit)}</small>`,'TDS<br><small>mg/L</small>','pH','Temperature<br><small>°C</small>'],rows,'dense')}</section>`;}
function collectWarnings(){
  const raw=[];for(const key of ['warning_messages','warnings','engineering_warnings','constraint_warnings']){const value=snapshot[key]??r[key];if(Array.isArray(value))value.forEach(x=>raw.push(x));else if(value)raw.push(value)}
  const warnings=raw.map(x=>typeof x==='string'?{severity:'review',message:x}:x).filter(x=>x&&textFirst(x.message,x.description,x.text));
  if(first(r.dp_limit_fraction)>1)warnings.push({severity:'critical',message:`Element pressure-drop utilization is ${pct(r.dp_limit_fraction,1)} of the selected limit. Review vessel hydraulics and array loading.`});
  if(first(r.max_polarization_factor_divalent)>1.2)warnings.push({severity:'review',message:`Maximum divalent polarization factor is ${fmt(r.max_polarization_factor_divalent,2)}. Review tail-element scaling and flux distribution.`});
  if(first(r.product_tds_target)>0&&compositePermTds!==null&&compositePermTds>first(r.product_tds_target))warnings.push({severity:'critical',message:`Composite permeate TDS ${fmt(compositePermTds,2)} mg/L exceeds the target ${fmt(r.product_tds_target,2)} mg/L.`});
  return warnings;
}
function warningSection(){const warnings=collectWarnings();if(!warnings.length)return `<section class="section">${sectionTitle('10. Engineering Warnings and Required Review')}<div class="warning-none">No critical design warnings were identified for the calculated duty point.</div></section>`;const html=warnings.map(x=>{const sev=String(x.severity||x.level||'review').toLowerCase();const cls=sev.includes('critical')||sev.includes('error')?'critical':sev.includes('advis')||sev.includes('info')?'advisory':'review';const label=cls==='critical'?'Critical':cls==='review'?'Review required':'Advisory';return `<li class="warning-item ${cls}"><strong>${label}</strong><span>${esc(textFirst(x.message,x.description,x.text))}</span></li>`}).join('');return `<section class="section">${sectionTitle('10. Engineering Warnings and Required Review')}<ul class="warning-list">${html}</ul></section>`;}
function disclaimer(){return `<section class="section disclaimer"><strong>Preliminary engineering / no-reliance disclaimer.</strong> Total RO Design is an independent preliminary engineering screening and decision-support tool provided AS IS. Outputs are estimates, not engineering advice, a certified design, process/performance guarantee, vendor projection or procurement recommendation, and must be independently verified before design, procurement, operation or contractual reliance. To the maximum extent permitted by applicable law, no warranty is made regarding accuracy, completeness, fitness for purpose, non-infringement or performance. Manufacturer names, trademarks, specifications, publications, equations and correlations remain the property of their respective owners; their inclusion for engineering identification, interoperability, comparison or calculation does not imply sponsorship, authorization or endorsement. No process, equipment, energy-consumption, water-quality or economic result is guaranteed.</section>`;}
function hydraulicEnvelope(){const env=snapshot.hydraulic_envelope;if(!options.include_hydraulic_envelope||!env?.rows?.length)return '';const rows=env.rows.map(x=>`<tr><td class="label">${esc(x.label||x.id)}</td><td class="num">${fmt(x.temperature_c,1)} °C</td><td class="num">${fmt(x.fouling_factor,2)}</td><td class="num">${fmt(x.salt_passage_factor,2)}</td><td class="num">${fmt(x.result?.membrane_pressure_1,2)} ${esc(pressureUnit)}</td><td class="num">${fmt(x.result?.product_flow,2)} ${esc(flowUnit)}</td><td class="num">${fmt(first(x.result?.total_sec,x.result?.specific_energy,x.result?.sec),3)}</td></tr>`);return `<section class="section">${sectionTitle('Hydraulic Envelope','Completed operating-condition study')}${table(['Condition','Temperature','Fouling','Salt passage','Feed pressure','Product flow','SEC'],rows)}</section>`;}
function chemistryAppendix(){const c=snapshot.chemistry_detail;if(!options.include_detailed_chemistry||!c)return '';const charge=c.charge||{},chargeRows=(charge.rows||[]).map(x=>`<tr><td class="label">${esc(x.label)}</td><td class="num">${fmt(x.mg_l,3)}</td><td class="num">${fmt(x.mmol_l,5)}</td><td class="num">${fmt(x.meq_l,5)}</td></tr>`);const indexRows=(c.indices||[]).map(x=>`<tr><td class="label">${esc(x.name)}</td><td>${esc(x.track)}</td><td class="num">${fmt(x.value,3)}</td><td>${esc(x.definition)}</td></tr>`);const mineralRows=(c.minerals||[]).map(x=>`<tr><td class="label">${esc(x.formula)}</td><td>${esc(x.name)}</td><td>${esc(x.governing_track)}</td><td class="num">${fmt(x.si_track_a,3)}</td><td class="num">${fmt(x.si_track_b,3)}</td><td class="num">${fmt(x.concentration_saturation_pct,1)}%</td></tr>`);return `<section class="report-page appendix"><h1 class="appendix-title">Appendix A — Detailed Water Chemistry and Scaling</h1><div class="summary-grid"><article class="summary-group"><h3>Analytical state</h3><dl>${row('Reported TDS',`${fmt(c.reported_tds_mg_l,1)} mg/L`)}${row('Constituent sum',`${fmt(c.tds_sum_mg_l,1)} mg/L`)}${row('Temperature',`${fmt(c.temperature_c,1)} °C`)}${row('pH',fmt(c.ph,2))}${row('Ionic strength',`${fmt(c.ionic_strength_mol_kg,4)} mol/kg`)}${row('Osmotic pressure',`${fmt(c.osmotic?.osmotic_bar,2)} bar`)}</dl></article><article class="summary-group"><h3>Charge balance</h3><dl>${row('Cations',`${fmt(charge.cations_meq_l,4)} meq/L`)}${row('Anions',`${fmt(charge.anions_meq_l,4)} meq/L`)}${row('Imbalance',`${fmt(charge.imbalance_pct,3)}%`)}</dl></article></div>${sectionTitle('Ionic balance')}${table(['Constituent','mg/L','mmol/L','meq/L'],chargeRows,'dense')}${sectionTitle('Scaling and corrosion indices')}${table(['Index','Track','Value','Definition'],indexRows,'dense')}${sectionTitle('Complete mineral saturation table')}${table(['Formula','Mineral','Track','SI A','SI B','Saturation'],mineralRows,'dense')}<p class="appendix-note">Interactive balancing controls are intentionally excluded from the customer report. This appendix records the final calculated chemistry state only.</p></section>`;}
function flattenObject(obj,prefix='',rows=[]){if(!obj||typeof obj!=='object')return rows;for(const [k,v] of Object.entries(obj)){const label=prefix?`${prefix} · ${k}`:k;if(v&&typeof v==='object'&&!Array.isArray(v))flattenObject(v,label,rows);else if(['string','number','boolean'].includes(typeof v)||v===null)rows.push([label,v])}return rows;}
function tailAppendixPages(){
  const t=snapshot.tail_chemistry;
  if(!options.include_tail_chemistry||!t)return [];
  const allRows=flattenObject(t).filter(([,v])=>v!==undefined).slice(0,400);
  const chunkSize=55;
  const chunks=[];
  for(let offset=0;offset<allRows.length;offset+=chunkSize)chunks.push(allRows.slice(offset,offset+chunkSize));
  return chunks.map((chunk,index)=>{
    const rows=chunk.map(([k,v])=>`<tr><td class="label">${esc(k.replaceAll('_',' '))}</td><td class="num">${typeof v==='number'?fmtSmart(v):esc(v)}</td></tr>`);
    const continuation=index?` · Continued ${index+1} of ${chunks.length}`:'';
    const note=index===0?'<p class="appendix-note">Plant feed, tail-element feed/concentrate, local permeate and cumulative permeate streams are retained from the completed solved-case snapshot.</p>':'';
    return `<section class="report-page appendix tail-appendix"><h1 class="appendix-title">Appendix B — Tail-Element Water Chemistry${continuation}</h1>${note}${table(['Calculated parameter / stream value','Value'],rows,'dense')}</section>`;
  });
}
const GLOSSARY_TERMS=Object.freeze([
  ['RO','Reverse Osmosis','Pressure-driven membrane process that separates water from dissolved constituents.'],
  ['NF','Nanofiltration','Pressure-driven membrane process with selective ionic and molecular rejection.'],
  ['UF','Ultrafiltration','Membrane filtration commonly used upstream of RO for suspended and colloidal solids control.'],
  ['IX','Ion Exchange','Selective exchange of dissolved ions using an ion-exchange medium.'],
  ['EDI','Electrodeionization','Continuous ion-removal process combining ion-exchange media and an electric field.'],
  ['ERD','Energy Recovery Device','Equipment that recovers hydraulic energy from a pressurized reject stream.'],
  ['SEC','Specific Energy Consumption','Energy consumed per unit volume of produced water.'],
  ['TDS','Total Dissolved Solids','Reported or calculated concentration of dissolved constituents.'],
  ['SDI','Silt Density Index','Empirical indicator of membrane-feed fouling potential.'],
  ['LSI','Langelier Saturation Index','Calcium-carbonate saturation/corrosion tendency indicator.'],
  ['S&DSI','Stiff & Davis Saturation Index','High-salinity calcium-carbonate scaling tendency index.'],
  ['NDP','Net Driving Pressure','Effective transmembrane driving pressure after osmotic-pressure effects.'],
  ['TMP','Transmembrane Pressure','Pressure difference across a membrane.'],
  ['VFD','Variable Frequency Drive','Motor-speed controller used to adjust pump operating speed.'],
  ['HPP','High-Pressure Pump','Pump supplying the principal RO membrane feed pressure.'],
  ['CP','Concentration Polarization','Increase in solute concentration at the membrane surface relative to the bulk feed.']
]);
function glossaryPage(reportHtml){
  const plain=String(reportHtml||'').replace(/<[^>]*>/g,' ').replace(/&[^;]+;/g,' ');
  const used=GLOSSARY_TERMS.filter(([acronym])=>{
    if(acronym==='S&DSI')return /S(?:&|&amp;)DSI|Stiff\\s*&\\s*Davis/i.test(String(reportHtml||''));
    return new RegExp(`(^|[^A-Za-z0-9])${acronym.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')}([^A-Za-z0-9]|$)`,'i').test(plain);
  });
  if(!used.length)return '';
  const rows=used.map(([a,n,d])=>`<tr><td class="label"><strong>${esc(a)}</strong></td><td>${esc(n)}</td><td>${esc(d)}</td></tr>`);
  return `<section class="report-page appendix glossary-page"><h1 class="appendix-title">Acronyms & Glossary</h1><p class="appendix-note">Only abbreviations used in this report are listed.</p>${table(['Acronym','Expanded name','Definition'],rows,'dense')}</section>`;
}

function titleBand(subtitle){return `<div class="report-title-band"><div><h1>Total RO Design — RO System Design Report</h1><p>${esc(subtitle)}</p></div><div class="status">CALCULATED CASE · ${esc(caseLabel)}<br>v${esc(snapshot.app_version||'0.2')}</div></div>`;}
const reportLogoSrc='/static/branding/suite/total_ro_design_logo.png';
function pageBrandbar(){
  return `<div class="page-brandbar"><img src="${reportLogoSrc}" alt="Total RO Design"><div><strong>RO System Design Report</strong><span>${esc(projectName)} · ${esc(caseLabel)} · ${esc(revision)} · v${esc(snapshot.app_version||'0.2')}</span></div><small>Part of the Total Water Design Suite</small></div>`;
}
function pageFooter(pageNumber,totalPages){
  return `<div class="report-logical-footer"><span>${esc(projectName)} · ${esc(caseLabel)} · ${esc(revision)} · Generated ${esc(currentDate.toLocaleString())}</span><strong>Page ${pageNumber} of ${totalPages}</strong></div>`;
}
function withPageChrome(html,pageNumber,totalPages){
  const branded=html.replace(/(<section\b[^>]*>)/,`$1${pageBrandbar()}`);
  return branded.replace(/<\/section>\s*$/,`${pageFooter(pageNumber,totalPages)}</section>`);
}
function render(){
  const page1=`<section class="report-page core-page page-1">${titleBand('Design basis, overall system, stage performance, water analysis and scaling')}${projectBand()}${summaryGroups()}${stageTable()}${waterAnalysis()}${scalingSnapshot()}</section>`;
  const page2=elements.length?`<section class="report-page core-page page-2">${titleBand('Element-level performance and advanced membrane profiles')}${elementTable()}${chartsAndCritical()}</section>`:'';
  const conditioning=chemicalConditioningSection();
  const page3=conditioning
    ? `<section class="report-page core-page page-3">${titleBand('Energy, hydraulics and chemical conditioning')}${energyHydraulic()}${conditioning}${hydraulicEnvelope()}</section>`
    : `<section class="report-page core-page page-3">${titleBand('Energy, hydraulics, principal streams and engineering review')}${energyHydraulic()}${hydraulicEnvelope()}${streamsSection()}${warningSection()}${disclaimer()}</section>`;
  const page4=conditioning?`<section class="report-page core-page page-4">${titleBand('Principal streams and engineering review')}${streamsSection()}${warningSection()}${disclaimer()}</section>`:'';
  const corePages=[page1,page2,page3,page4].filter(Boolean);
  const chemistry=chemistryAppendix();
  const tailPages=tailAppendixPages();
  const appendixPages=[chemistry,...tailPages].filter(Boolean);
  const glossary=glossaryPage([...corePages,...appendixPages].join(''));
  const pages=[...corePages];
  if(glossary)pages.push(glossary);
  pages.push(...appendixPages);
  const totalPages=pages.length;
  root.innerHTML=`<div class="screen-report-actions"><a href="/ro">Return to Total RO Design</a><button type="button" id="printEngineeringReport">Print / Save PDF</button></div>${pages.map((page,index)=>withPageChrome(page,index+1,totalPages)).join('')}`;
  root.dataset.rendered='true';
  document.getElementById('printEngineeringReport')?.addEventListener('click',()=>window.print());
  if(window.TOTALRO_AUTOPRINT)setTimeout(()=>window.print(),400);
}
render();
})();
