const assert=require('assert');
const path=require('path');
const MBR=require(path.join(__dirname,'..','Source','web','mbr_equipment_sizing.js'));

function stream(flow,quality){
  const mass={};
  for(const k of ['cod','bod','tss','vss','tkn','nh4','nox','tp','po4','fog','alk'])mass[k]=(Number(quality[k])||0)*flow/1000;
  return {flow,mass,temperatureC:12,pH:7};
}

const snapshot={
  market:{
    avgFlowM3d:5000,
    peakHourlyEqM3d:10000,
    tempC:12,
    influentBOD:220,
    influentCOD:430,
    influentTSS:250,
    influentAmmonia:40,
    influentTKN:45,
    effluentBOD:5,
    effluentAmmonia:1,
    effluentTN:10
  },
  treatmentTrain:[{type:'mbr'}],
  recycles:[{name:'Internal mixed-liquor recycle',basis:'ratio',value:2,enabled:true}]
};
const network={water:{finalEffluent:stream(5000,{bod:5,cod:40,tss:0.5,vss:0.3,tkn:2,nh4:1,nox:8,tp:0.5,po4:0.2,alk:80})}};

const d=MBR.defaults();
const r=MBR.size({snapshot,network,config:d});
assert(r.basis.hasMbr,'MBR must be detected in train');
assert(r.membrane.normalNetFluxLMH>0,'net flux must be positive');
assert(r.membrane.normalNetFluxLMH<d.grossFluxLMH,'cleaning/backwash must reduce gross to net flux');
assert(r.membrane.installedAreaM2>=r.membrane.requiredInstalledAreaM2,'installed area must cover required area after module/train rounding');
assert(Number.isInteger(r.membrane.totalModules)&&r.membrane.totalModules>0,'module count must be a positive integer');
assert(r.membrane.n1Pass,'N+1 calculation must satisfy configured peak net flux after sizing');
assert(r.backwash.enabled&&r.backwash.flowM3h>0&&r.backwash.tankWorkingVolumeM3>0,'HF backwash equipment must be sized');
assert(r.pumps.permeate.motorDesignKw>0,'permeate pump duty must be positive');
assert(r.pumps.recycle.flowM3h>0&&Math.abs(r.pumps.recycle.ratio-2)<1e-12,'project internal recycle must drive recycle pump sizing');
assert(r.aeration.oxygenDemand.oxygenKgD>0,'planning oxygen demand must be positive');
assert(r.aeration.biologicalAirNm3h>0&&r.aeration.biologicalBlowerMotorDesignKw>0,'biological blower must be sized');
assert(r.aeration.membraneAirNm3h>0&&r.aeration.membraneBlowerMotorDesignKw>0,'membrane scour blower must be sized');
assert(r.cleaning.maintenanceNaOClKg>0&&r.cleaning.recoveryNaOClKg>0,'cleaning reagent quantities must be positive');
assert(r.pretreatment.screen.passes,'default HF fine screen must pass historical planning constraint');

const lowMlss=MBR.alphaFactor(MBR.normalizeConfig({...d,mlssGL:6}));
const highMlss=MBR.alphaFactor(MBR.normalizeConfig({...d,mlssGL:16}));
assert(lowMlss>highMlss,'literature alpha correlation must derate oxygen transfer as MLSS increases');

const fs=MBR.size({snapshot,network,config:{...d,membraneConfiguration:'FS',backwashEnabled:false,screenOpeningMm:2.5}});
assert(!fs.backwash.enabled&&fs.backwash.flowM3h===0,'FS planning mode must allow no backwash');
assert(fs.pretreatment.screen.passes,'2.5 mm FS screen must fall inside historical planning range');
const fsBad=MBR.screenConstraint(MBR.normalizeConfig({...d,membraneConfiguration:'FS',backwashEnabled:false,screenOpeningMm:4}));
assert(!fsBad.passes,'screen larger than historical FS planning maximum must be flagged');

const noMbr=MBR.size({snapshot:{...snapshot,treatmentTrain:[{type:'cas'}]},network,config:d});
assert(noMbr.reviews.some(x=>x.includes('No MBR/anMBR unit')),'planning scenario without MBR must be explicitly identified');

const p1=MBR.blowerPowerKw(1000,30,MBR.normalizeConfig(d));
const p2=MBR.blowerPowerKw(1000,60,MBR.normalizeConfig(d));
assert(p2>p1&&p1>0,'blower power must rise with discharge pressure');

// Judd Chapter 3 worked design reports about 9,887 m² for a 5,000 m³/d case
// at approximately 21 LMH net flux. With cleaning downtime intentionally removed
// here to isolate Q/J area sizing, the independent calculation should reproduce
// the published order of magnitude to within 1%.
const worked=MBR.size({
  snapshot:{...snapshot,market:{...snapshot.market,avgFlowM3d:5000,peakHourlyEqM3d:5000}},
  network,
  config:{
    ...d,
    grossFluxLMH:21,
    peakGrossFluxLMH:21,
    filtrationMinutes:10,
    relaxationMinutes:0,
    backwashEnabled:false,
    maintenanceCleanMinutes:0,
    recoveryCleanHours:0,
    redundancyMode:'No train redundancy',
    installedTrains:4,
    moduleAreaM2:1,
    modulesPerRack:1
  }
});
assert(Math.abs(worked.membrane.requiredInstalledAreaM2-9887)/9887<0.01,
  `worked-example membrane area should match Judd Chapter 3 order of magnitude: ${worked.membrane.requiredInstalledAreaM2}`);

console.log('Total Bio Design MBR equipment sizing regression: PASS');
