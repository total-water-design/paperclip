(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports){module.exports=api;}
  else{root.TotalBioMbrEquipment=api;}
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const LITERATURE=Object.freeze({
    source:'Simon Judd, The MBR Book, 1st ed., Elsevier, 2006',
    status:'Historical literature planning basis — verify current membrane supplier limits before design release.',
    screenHF:[0.8,1.5],
    screenFS:[2,3],
    relaxationMinutes:[1,2],
    filtrationMinutes:[8,15],
    backwashFluxRatio:[2,3],
    maintenanceCleanDays:[3,7],
    maintenanceNaOClMgL:[200,500],
    recoveryNaOClWtPct:[0.2,0.3],
    recoveryCitricWtPct:[0.2,0.3],
    recoveryOxalicWtPct:[0.5,1],
    typicalMunicipalNetFluxLMH:25,
    denitRecycleRatio:[1,3],
    denitRecycleRatioUpper:4,
    alphaMlssExponent:0.083,
    beta:0.95,
    theta:1.024,
    fineBubbleCleanOtePerM:0.05,
    oxygenMassFractionAir:0.232,
    standardAirDensityKgNm3:1.293,
    gammaAir:1.4
  });

  const n=(x,d=0)=>Number.isFinite(Number(x))?Number(x):d;
  const pos=(x,d=0)=>{const v=n(x,d);return v>0?v:d;};
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  const ceilDiv=(x,y)=>y>0?Math.ceil(x/y):0;
  const round=(x,d=3)=>{const p=10**d;return Math.round((n(x)+Number.EPSILON)*p)/p;};

  function defaults(){
    return {
      membraneConfiguration:'HF',
      grossFluxLMH:25,
      peakGrossFluxLMH:30,
      filtrationMinutes:10,
      relaxationMinutes:1,
      backwashEnabled:true,
      backwashMinutes:0.5,
      backwashFluxRatio:2,
      maintenanceCleanIntervalDays:7,
      maintenanceCleanMinutes:60,
      recoveryCleanIntervalDays:182.5,
      recoveryCleanHours:4,
      moduleAreaM2:250,
      modulesPerRack:1,
      installedTrains:4,
      redundancyMode:'N+1 train during peak/cleaning',
      simultaneousBackwashes:1,
      backwashTankMarginPct:20,
      screenOpeningMm:1,
      mlssGL:8,
      biomassYieldKgVssKgBod:0.4,
      denitrifiedNkgD:0,
      cleanOtePerM:0.05,
      diffuserSubmergenceM:3,
      beta:0.95,
      theta:1.024,
      alphaMode:'Gunder 2001 MLSS correlation',
      alphaManual:0.5,
      atmosphericPressureKPa:101.325,
      ambientTemperatureC:20,
      membraneAirHeaderPressureKPaG:45,
      biologicalAirHeaderPressureKPaG:55,
      blowerEfficiency:0.65,
      permeatePumpHeadM:10,
      backwashPumpHeadM:15,
      recyclePumpHeadM:5,
      pumpEfficiency:0.70,
      maintenanceCleaningFluxLMH:45,
      maintenanceNaOClMgL:300,
      recoveryCleaningFluxLMH:45,
      recoveryNaOClWtPct:0.25,
      recoveryCitricWtPct:0.25,
      membraneSadMNm3Hm2:0.47,
      membraneAerationFraction:1,
      motorDesignMarginPct:10
    };
  }

  function normalizeConfig(raw={}){
    const d=defaults();
    const c={...d,...raw};
    c.membraneConfiguration=String(c.membraneConfiguration||'HF').toUpperCase()==='FS'?'FS':'HF';
    if(raw.backwashEnabled===undefined)c.backwashEnabled=c.membraneConfiguration==='HF';
    c.grossFluxLMH=pos(c.grossFluxLMH,d.grossFluxLMH);
    c.peakGrossFluxLMH=pos(c.peakGrossFluxLMH,Math.max(c.grossFluxLMH,d.peakGrossFluxLMH));
    c.filtrationMinutes=pos(c.filtrationMinutes,d.filtrationMinutes);
    c.relaxationMinutes=Math.max(0,n(c.relaxationMinutes,d.relaxationMinutes));
    c.backwashMinutes=c.backwashEnabled?Math.max(0,n(c.backwashMinutes,d.backwashMinutes)):0;
    c.backwashFluxRatio=c.backwashEnabled?pos(c.backwashFluxRatio,d.backwashFluxRatio):0;
    c.maintenanceCleanIntervalDays=pos(c.maintenanceCleanIntervalDays,d.maintenanceCleanIntervalDays);
    c.maintenanceCleanMinutes=Math.max(0,n(c.maintenanceCleanMinutes,d.maintenanceCleanMinutes));
    c.recoveryCleanIntervalDays=pos(c.recoveryCleanIntervalDays,d.recoveryCleanIntervalDays);
    c.recoveryCleanHours=Math.max(0,n(c.recoveryCleanHours,d.recoveryCleanHours));
    c.moduleAreaM2=pos(c.moduleAreaM2,d.moduleAreaM2);
    c.modulesPerRack=Math.max(1,Math.round(pos(c.modulesPerRack,d.modulesPerRack)));
    c.installedTrains=Math.max(2,Math.round(pos(c.installedTrains,d.installedTrains)));
    c.simultaneousBackwashes=Math.max(1,Math.round(pos(c.simultaneousBackwashes,d.simultaneousBackwashes)));
    c.backwashTankMarginPct=Math.max(0,n(c.backwashTankMarginPct,d.backwashTankMarginPct));
    c.screenOpeningMm=pos(c.screenOpeningMm,c.membraneConfiguration==='HF'?1:2);
    c.mlssGL=pos(c.mlssGL,d.mlssGL);
    c.biomassYieldKgVssKgBod=Math.max(0,n(c.biomassYieldKgVssKgBod,d.biomassYieldKgVssKgBod));
    c.denitrifiedNkgD=Math.max(0,n(c.denitrifiedNkgD,d.denitrifiedNkgD));
    c.cleanOtePerM=pos(c.cleanOtePerM,d.cleanOtePerM);
    c.diffuserSubmergenceM=pos(c.diffuserSubmergenceM,d.diffuserSubmergenceM);
    c.beta=clamp(n(c.beta,d.beta),0.05,1.2);
    c.theta=clamp(n(c.theta,d.theta),1,1.08);
    c.alphaManual=clamp(n(c.alphaManual,d.alphaManual),0.05,1);
    c.atmosphericPressureKPa=pos(c.atmosphericPressureKPa,d.atmosphericPressureKPa);
    c.ambientTemperatureC=n(c.ambientTemperatureC,d.ambientTemperatureC);
    c.membraneAirHeaderPressureKPaG=pos(c.membraneAirHeaderPressureKPaG,d.membraneAirHeaderPressureKPaG);
    c.biologicalAirHeaderPressureKPaG=pos(c.biologicalAirHeaderPressureKPaG,d.biologicalAirHeaderPressureKPaG);
    c.blowerEfficiency=clamp(n(c.blowerEfficiency,d.blowerEfficiency),0.2,0.95);
    c.permeatePumpHeadM=Math.max(0,n(c.permeatePumpHeadM,d.permeatePumpHeadM));
    c.backwashPumpHeadM=Math.max(0,n(c.backwashPumpHeadM,d.backwashPumpHeadM));
    c.recyclePumpHeadM=Math.max(0,n(c.recyclePumpHeadM,d.recyclePumpHeadM));
    c.pumpEfficiency=clamp(n(c.pumpEfficiency,d.pumpEfficiency),0.2,0.95);
    c.maintenanceCleaningFluxLMH=pos(c.maintenanceCleaningFluxLMH,d.maintenanceCleaningFluxLMH);
    c.maintenanceNaOClMgL=Math.max(0,n(c.maintenanceNaOClMgL,d.maintenanceNaOClMgL));
    c.recoveryCleaningFluxLMH=pos(c.recoveryCleaningFluxLMH,d.recoveryCleaningFluxLMH);
    c.recoveryNaOClWtPct=Math.max(0,n(c.recoveryNaOClWtPct,d.recoveryNaOClWtPct));
    c.recoveryCitricWtPct=Math.max(0,n(c.recoveryCitricWtPct,d.recoveryCitricWtPct));
    c.membraneSadMNm3Hm2=Math.max(0,n(c.membraneSadMNm3Hm2,d.membraneSadMNm3Hm2));
    c.membraneAerationFraction=clamp(n(c.membraneAerationFraction,d.membraneAerationFraction),0,1);
    c.motorDesignMarginPct=Math.max(0,n(c.motorDesignMarginPct,d.motorDesignMarginPct));
    return c;
  }

  function chemicalAvailability(c){
    const maintLossHPerDay=(c.maintenanceCleanMinutes/60)/c.maintenanceCleanIntervalDays;
    const recoveryLossHPerDay=c.recoveryCleanHours/c.recoveryCleanIntervalDays;
    return clamp(1-(maintLossHPerDay+recoveryLossHPerDay)/24,0.5,1);
  }

  function netFluxFromCycle(grossFluxLMH,c){
    const filterH=c.filtrationMinutes/60;
    const relaxH=c.relaxationMinutes/60;
    const bwH=c.backwashEnabled?c.backwashMinutes/60:0;
    const cycleH=filterH+relaxH+bwH;
    const grossProductLPerM2=grossFluxLMH*filterH;
    const backwashUseLPerM2=c.backwashEnabled?grossFluxLMH*c.backwashFluxRatio*bwH:0;
    const physicalNet=cycleH>0?Math.max(0,grossProductLPerM2-backwashUseLPerM2)/cycleH:0;
    return physicalNet*chemicalAvailability(c);
  }

  function alphaFactor(c){
    if(String(c.alphaMode||'').toLowerCase().includes('manual'))return c.alphaManual;
    return clamp(Math.exp(-LITERATURE.alphaMlssExponent*c.mlssGL),0.05,1);
  }

  function fieldOte(c,waterTemperatureC){
    const alpha=alphaFactor(c);
    const tempFactor=Math.pow(c.theta,n(waterTemperatureC,20)-20);
    const cleanOte=clamp(c.cleanOtePerM*c.diffuserSubmergenceM,0.01,0.6);
    return {
      alpha,
      beta:c.beta,
      temperatureFactor:tempFactor,
      cleanWaterOte:cleanOte,
      fieldOte:clamp(cleanOte*alpha*c.beta*tempFactor,0.005,0.5)
    };
  }

  function pumpPowerKw(flowM3h,headM,efficiency){
    const q= Math.max(0,n(flowM3h))/3600;
    const h= Math.max(0,n(headM));
    const eta=clamp(n(efficiency,0.7),0.05,1);
    return 1000*9.80665*q*h/eta/1000;
  }

  function blowerPowerKw(flowNm3h,gaugePressureKPa,c){
    const qn=Math.max(0,n(flowNm3h));
    if(qn<=0)return 0;
    const p1=c.atmosphericPressureKPa*1000;
    const p2=(c.atmosphericPressureKPa+Math.max(0,n(gaugePressureKPa)))*1000;
    if(p2<=p1)return 0;
    const gamma=LITERATURE.gammaAir;
    const eta=c.blowerEfficiency;
    const tK=c.ambientTemperatureC+273.15;
    const qActualM3s=(qn/3600)*(tK/273.15)*(101.325/c.atmosphericPressureKPa);
    return (gamma/(gamma-1))*p1*qActualM3s*(Math.pow(p2/p1,(gamma-1)/gamma)-1)/eta/1000;
  }

  function streamConcentration(stream,key){
    const q=n(stream?.flow);
    return q>0?n(stream?.mass?.[key])*1000/q:0;
  }

  function projectBasis(snapshot={},network={}){
    const m=snapshot.market||{};
    const avg=pos(m.avgFlowM3d,pos(m.designFlowM3d,n(network?.water?.finalEffluent?.flow)));
    const peak=pos(m.peakHourlyEqM3d,avg);
    const final=network?.water?.finalEffluent||null;
    const influentBod=Math.max(0,n(m.influentBOD));
    const effluentBod=Math.max(0,n(final?streamConcentration(final,'bod'):m.effluentBOD));
    const influentNh4=Math.max(0,n(m.influentAmmonia));
    const effluentNh4=Math.max(0,n(final?streamConcentration(final,'nh4'):m.effluentAmmonia));
    const influentTkn=Math.max(0,n(m.influentTKN));
    const effluentTn=Math.max(0,n(final&&typeof globalThis!=='undefined'&&globalThis.TotalBioProcessNetwork?.totalNConcentration?globalThis.TotalBioProcessNetwork.totalNConcentration(final):m.effluentTN));
    const recycles=Array.isArray(snapshot.recycles)?snapshot.recycles:[];
    const internal=recycles.find(r=>r&&r.enabled!==false&&r.basis==='ratio'&&String(r.name||'').toLowerCase().includes('internal')) || recycles.find(r=>r&&r.enabled!==false&&r.basis==='ratio');
    const recycleRatio=Math.max(0,n(internal?.value));
    const hasMbr=Array.isArray(snapshot.treatmentTrain)&&snapshot.treatmentTrain.some(u=>['mbr','anmbr'].includes(String(u?.type||'').toLowerCase()));
    return {avgFlowM3d:avg,peakFlowM3d:peak,temperatureC:n(m.tempC,20),influentBodMgL:influentBod,effluentBodMgL:effluentBod,influentNh4MgL:influentNh4,effluentNh4MgL:effluentNh4,influentTknMgL:influentTkn,effluentTnMgL:effluentTn,recycleRatio,hasMbr};
  }

  function oxygenDemand(basis,c){
    const q=basis.avgFlowM3d;
    const bodRemovedKgD=Math.max(0,(basis.influentBodMgL-basis.effluentBodMgL)*q/1000);
    const nitrifiedNkgD=Math.max(0,(basis.influentNh4MgL-basis.effluentNh4MgL)*q/1000);
    const sludgeVssKgD=Math.max(0,c.biomassYieldKgVssKgBod*bodRemovedKgD);
    const denitrifiedNkgD=Math.min(Math.max(0,c.denitrifiedNkgD),Math.max(0,basis.influentTknMgL*q/1000));
    const oxygenKgD=Math.max(0,bodRemovedKgD-1.42*sludgeVssKgD+4.33*nitrifiedNkgD-2.83*denitrifiedNkgD);
    return {bodRemovedKgD,nitrifiedNkgD,sludgeVssKgD,denitrifiedNkgD,oxygenKgD};
  }

  function screenConstraint(c){
    const range=c.membraneConfiguration==='HF'?LITERATURE.screenHF:LITERATURE.screenFS;
    return {recommendedMinMm:range[0],recommendedMaxMm:range[1],selectedMm:c.screenOpeningMm,passes:c.screenOpeningMm<=range[1]};
  }

  function size(input={}){
    const snapshot=input.snapshot||{};
    const network=input.network||{};
    const c=normalizeConfig(input.config||{});
    const basis=projectBasis(snapshot,network);
    const warnings=[];
    const reviews=[];

    if(!basis.hasMbr)reviews.push('No MBR/anMBR unit is present in the current treatment train; equipment results are a planning scenario until an MBR is added.');
    if(!(basis.avgFlowM3d>0))warnings.push('Average/design flow is required for MBR equipment sizing.');
    if(!(basis.peakFlowM3d>0))warnings.push('Peak hydraulic flow is required; average flow was used as the peak fallback.');

    const normalNetFlux=netFluxFromCycle(c.grossFluxLMH,c);
    const peakNetFlux=netFluxFromCycle(c.peakGrossFluxLMH,c);
    if(!(normalNetFlux>0)||!(peakNetFlux>0))warnings.push('Cleaning/backwash settings reduce net flux to zero; revise the filtration cycle.');

    const avgArea=normalNetFlux>0?basis.avgFlowM3d*1000/24/normalNetFlux:0;
    const peakArea=peakNetFlux>0?basis.peakFlowM3d*1000/24/peakNetFlux:0;
    let requiredArea=Math.max(avgArea,peakArea);
    if(String(c.redundancyMode).toUpperCase().includes('N+1')&&c.installedTrains>1){
      requiredArea=Math.max(requiredArea,peakArea*c.installedTrains/(c.installedTrains-1));
    }

    const rawModulesPerTrain=ceilDiv(requiredArea,c.moduleAreaM2*c.installedTrains);
    const racksPerTrain=ceilDiv(rawModulesPerTrain,c.modulesPerRack);
    const modulesPerTrain=racksPerTrain*c.modulesPerRack;
    const totalModules=modulesPerTrain*c.installedTrains;
    const installedArea=totalModules*c.moduleAreaM2;
    const totalRacks=racksPerTrain*c.installedTrains;
    const activeAreaN1=installedArea*(c.installedTrains-1)/c.installedTrains;
    const oneTrainOfflinePeakFlux=activeAreaN1>0?basis.peakFlowM3d*1000/24/activeAreaN1:0;
    const n1Pass=!String(c.redundancyMode).toUpperCase().includes('N+1')||oneTrainOfflinePeakFlux<=peakNetFlux+1e-9;
    if(!n1Pass)warnings.push('One-train-offline peak flux exceeds the configured peak net-flux capacity.');

    const backwashFlux=c.backwashEnabled?c.grossFluxLMH*c.backwashFluxRatio:0;
    const backwashFlowM3h=c.backwashEnabled?backwashFlux*installedArea/1000:0;
    const backwashEventM3=c.backwashEnabled?backwashFlowM3h*(c.backwashMinutes/60):0;
    const backwashTankWorkingM3=backwashEventM3*c.simultaneousBackwashes*(1+c.backwashTankMarginPct/100);

    const permeatePumpFlowM3h=basis.peakFlowM3d/24;
    const recyclePumpFlowM3h=basis.avgFlowM3d*basis.recycleRatio/24;
    const permeatePumpPowerKw=pumpPowerKw(permeatePumpFlowM3h,c.permeatePumpHeadM,c.pumpEfficiency);
    const backwashPumpPowerKw=pumpPowerKw(backwashFlowM3h,c.backwashPumpHeadM,c.pumpEfficiency);
    const recyclePumpPowerKw=pumpPowerKw(recyclePumpFlowM3h,c.recyclePumpHeadM,c.pumpEfficiency);

    const oxy=oxygenDemand(basis,c);
    const ote=fieldOte(c,basis.temperatureC);
    const oxygenKgPerNm3Air=LITERATURE.standardAirDensityKgNm3*LITERATURE.oxygenMassFractionAir;
    const bioAirNm3h=ote.fieldOte>0?oxy.oxygenKgD/(24*oxygenKgPerNm3Air*ote.fieldOte):0;
    const membraneAirNm3h=c.membraneSadMNm3Hm2*installedArea*c.membraneAerationFraction;
    const bioBlowerPowerKw=blowerPowerKw(bioAirNm3h,c.biologicalAirHeaderPressureKPaG,c);
    const membraneBlowerPowerKw=blowerPowerKw(membraneAirNm3h,c.membraneAirHeaderPressureKPaG,c);

    const maintenanceSolutionM3=c.maintenanceCleaningFluxLMH*installedArea/1000*(c.maintenanceCleanMinutes/60);
    const maintenanceNaOClKg=maintenanceSolutionM3*c.maintenanceNaOClMgL/1000;
    const recoverySolutionM3=c.recoveryCleaningFluxLMH*installedArea/1000*c.recoveryCleanHours;
    const recoveryNaOClKg=recoverySolutionM3*1000*(c.recoveryNaOClWtPct/100);
    const recoveryCitricKg=recoverySolutionM3*1000*(c.recoveryCitricWtPct/100);

    const screen=screenConstraint(c);
    if(!screen.passes)warnings.push(`${c.membraneConfiguration} planning screen opening exceeds the historical MBR reference range (${screen.recommendedMinMm}–${screen.recommendedMaxMm} mm). Confirm the current membrane supplier requirement.`);
    if(c.mlssGL>15)reviews.push('MLSS above about 15 g/L is in a range where the source reports increased viscosity/aeration and fouling concerns; confirm with current membrane supplier and oxygen-transfer data.');
    if(c.mlssGL>17)warnings.push('MLSS exceeds the upper end of the reported 10–17 g/L viscosity-transition range; oxygen-transfer and membrane hydraulics require project-specific verification.');
    if(c.grossFluxLMH>50)reviews.push('Gross operating flux is substantially above the historical municipal planning value; confirm sustainable/current vendor flux and cleaning protocol.');
    if(ote.fieldOte<0.03)reviews.push('Calculated process oxygen-transfer efficiency is below 3%; verify MLSS, diffuser submergence, alpha factor and current aeration data.');
    reviews.push(LITERATURE.status);
    reviews.push('Cleaning solution volumes are through-membrane planning quantities. Final CIP tank recirculation volume and chemical compatibility must follow the selected current membrane supplier.');

    const margin=1+c.motorDesignMarginPct/100;
    return {
      basis:{...basis},
      config:c,
      literature:LITERATURE,
      membrane:{
        chemicalAvailability:chemicalAvailability(c),
        normalNetFluxLMH:normalNetFlux,
        peakNetFluxLMH:peakNetFlux,
        averageRequiredAreaM2:avgArea,
        peakRequiredAreaM2:peakArea,
        requiredInstalledAreaM2:requiredArea,
        installedAreaM2:installedArea,
        moduleAreaM2:c.moduleAreaM2,
        modulesPerRack:c.modulesPerRack,
        racksPerTrain,
        modulesPerTrain,
        totalRacks,
        totalModules,
        installedTrains:c.installedTrains,
        oneTrainOfflinePeakFluxLMH:oneTrainOfflinePeakFlux,
        n1Pass
      },
      backwash:{
        enabled:c.backwashEnabled,
        fluxLMH:backwashFlux,
        flowM3h:backwashFlowM3h,
        eventVolumeM3:backwashEventM3,
        tankWorkingVolumeM3:backwashTankWorkingM3
      },
      pumps:{
        permeate:{flowM3h:permeatePumpFlowM3h,headM:c.permeatePumpHeadM,shaftKw:permeatePumpPowerKw,motorDesignKw:permeatePumpPowerKw*margin},
        backwash:{flowM3h:backwashFlowM3h,headM:c.backwashPumpHeadM,shaftKw:backwashPumpPowerKw,motorDesignKw:backwashPumpPowerKw*margin},
        recycle:{flowM3h:recyclePumpFlowM3h,headM:c.recyclePumpHeadM,shaftKw:recyclePumpPowerKw,motorDesignKw:recyclePumpPowerKw*margin,ratio:basis.recycleRatio}
      },
      aeration:{
        oxygenDemand:oxy,
        transfer:ote,
        biologicalAirNm3h:bioAirNm3h,
        membraneAirNm3h:membraneAirNm3h,
        biologicalBlowerShaftKw:bioBlowerPowerKw,
        biologicalBlowerMotorDesignKw:bioBlowerPowerKw*margin,
        membraneBlowerShaftKw:membraneBlowerPowerKw,
        membraneBlowerMotorDesignKw:membraneBlowerPowerKw*margin
      },
      cleaning:{
        maintenanceSolutionM3,
        maintenanceNaOClKg,
        recoverySolutionM3,
        recoveryNaOClKg,
        recoveryCitricKg,
        maintenanceIntervalDays:c.maintenanceCleanIntervalDays,
        recoveryIntervalDays:c.recoveryCleanIntervalDays
      },
      pretreatment:{screen},
      warnings,
      reviews
    };
  }

  return Object.freeze({LITERATURE,defaults,normalizeConfig,netFluxFromCycle,alphaFactor,fieldOte,pumpPowerKw,blowerPowerKw,projectBasis,oxygenDemand,screenConstraint,size,round});
});
