(function(root,factory){
  const catalog=factory();
  if(typeof module==='object' && module.exports){module.exports=catalog;}
  else{root.TotalBioUnitCatalog=catalog;}
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  return [
  {
    "type": "screening",
    "name": "Coarse / Manual Screening",
    "tag": "Headworks",
    "tab": "MarketIntake",
    "badge": "SC",
    "group": "Pretreatment",
    "keywords": "bar rack coarse screen manual screen"
  },
  {
    "type": "fine_screen",
    "name": "Fine Screening",
    "tag": "Fine headworks",
    "tab": "UnitOperationDetail",
    "badge": "FS",
    "group": "Pretreatment",
    "keywords": "perforated plate wedge wire step screen"
  },
  {
    "type": "step_screen",
    "name": "Step Screen",
    "tag": "Automatic screening",
    "tab": "UnitOperationDetail",
    "badge": "SS",
    "group": "Pretreatment",
    "keywords": "mechanical screen escalator screen"
  },
  {
    "type": "rotary_drum_screen",
    "name": "Rotary Drum Screen",
    "tag": "Fine solids removal",
    "tab": "UnitOperationDetail",
    "badge": "RDS",
    "group": "Pretreatment",
    "keywords": "rotary screen drum microscreen"
  },
  {
    "type": "comminutor",
    "name": "Comminutor / Macerator",
    "tag": "Size reduction",
    "tab": "UnitOperationDetail",
    "badge": "COM",
    "group": "Pretreatment",
    "keywords": "grinder macerator solids reduction"
  },
  {
    "type": "grit",
    "name": "Grit Removal",
    "tag": "Headworks",
    "tab": "UnitOperationDetail",
    "badge": "GR",
    "group": "Pretreatment",
    "keywords": "vortex aerated grit chamber sand removal"
  },
  {
    "type": "equalization",
    "name": "Flow Equalization",
    "tag": "Hydraulic buffering",
    "tab": "MarketIntake",
    "badge": "EQ",
    "group": "Pretreatment",
    "keywords": "equalization tank balancing surge attenuation"
  },
  {
    "type": "neutralization",
    "name": "pH Adjustment / Neutralization",
    "tag": "Chemical conditioning",
    "tab": "UnitOperationDetail",
    "badge": "pH",
    "group": "Pretreatment",
    "keywords": "acid caustic alkalinity ph correction"
  },
  {
    "type": "coag_floc",
    "name": "Coagulation / Flocculation",
    "tag": "Chemical pretreatment",
    "tab": "UnitOperationDetail",
    "badge": "CF",
    "group": "Pretreatment",
    "keywords": "rapid mix flocculator coagulant polymer"
  },
  {
    "type": "electrocoagulation",
    "name": "Electrocoagulation",
    "tag": "Metals / colloids / oil",
    "tab": "UnitOperationDetail",
    "badge": "EC",
    "group": "Pretreatment",
    "keywords": "electrochemical coagulation industrial wastewater"
  },
  {
    "type": "daf",
    "name": "Dissolved Air Flotation",
    "tag": "DAF pretreatment",
    "tab": "UnitOperationDetail",
    "badge": "DAF",
    "group": "Pretreatment",
    "keywords": "flotation fats oils grease algae solids pretreatment"
  },
  {
    "type": "igf",
    "name": "Induced Gas Flotation",
    "tag": "Industrial flotation",
    "tab": "UnitOperationDetail",
    "badge": "IGF",
    "group": "Pretreatment",
    "keywords": "dissolved gas flotation oil produced water"
  },
  {
    "type": "api_separator",
    "name": "API Oil-Water Separator",
    "tag": "Free oil removal",
    "tab": "UnitOperationDetail",
    "badge": "API",
    "group": "Pretreatment",
    "keywords": "american petroleum institute oil separator"
  },
  {
    "type": "cpi_separator",
    "name": "CPI / Plate Oil-Water Separator",
    "tag": "Enhanced oil removal",
    "tab": "UnitOperationDetail",
    "badge": "CPI",
    "group": "Pretreatment",
    "keywords": "corrugated plate interceptor tilted plate oil separator"
  },
  {
    "type": "grease_interceptor",
    "name": "Grease Interceptor",
    "tag": "FOG removal",
    "tab": "UnitOperationDetail",
    "badge": "FOG",
    "group": "Pretreatment",
    "keywords": "grease trap kitchen foodservice fats oils grease"
  },
  {
    "type": "oil_water",
    "name": "Oil-Water Separator",
    "tag": "Oil & grease removal",
    "tab": "UnitOperationDetail",
    "badge": "OW",
    "group": "Pretreatment",
    "keywords": "industrial oily wastewater separator"
  },
  {
    "type": "primary",
    "name": "Primary Clarifier",
    "tag": "Primary settling",
    "tab": "UnitOperationDetail",
    "badge": "PC",
    "group": "Pretreatment",
    "keywords": "primary sedimentation settling tank"
  },
  {
    "type": "lamella_primary",
    "name": "Lamella / Inclined Plate Clarifier",
    "tag": "Compact primary settling",
    "tab": "UnitOperationDetail",
    "badge": "LPC",
    "group": "Pretreatment",
    "keywords": "tube settler plate settler high rate clarification"
  },
  {
    "type": "uasb",
    "name": "UASB / EGSB",
    "tag": "Anaerobic",
    "tab": "UASB_EGSB",
    "badge": "AN",
    "group": "Biological",
    "flags": [
      "uasb"
    ],
    "keywords": "upflow anaerobic sludge blanket expanded granular sludge bed"
  },
  {
    "type": "egsb",
    "name": "EGSB Reactor",
    "tag": "High-rate anaerobic",
    "tab": "UASB_EGSB",
    "badge": "EGSB",
    "group": "Biological",
    "flags": [
      "uasb"
    ],
    "keywords": "expanded granular sludge bed"
  },
  {
    "type": "ic_reactor",
    "name": "Internal Circulation Reactor",
    "tag": "High-rate anaerobic",
    "tab": "UASB_EGSB",
    "badge": "IC",
    "group": "Biological",
    "flags": [
      "uasb"
    ],
    "keywords": "IC anaerobic reactor internal circulation"
  },
  {
    "type": "anaerobic_contact",
    "name": "Anaerobic Contact Process",
    "tag": "Anaerobic suspended growth",
    "tab": "UnitOperationDetail",
    "badge": "ACP",
    "group": "Biological",
    "keywords": "anaerobic contact reactor clarifier recycle"
  },
  {
    "type": "anaerobic_filter",
    "name": "Anaerobic Filter",
    "tag": "Fixed-film anaerobic",
    "tab": "UnitOperationDetail",
    "badge": "AF",
    "group": "Biological",
    "keywords": "anaerobic packed bed fixed film"
  },
  {
    "type": "anaerobic_lagoon",
    "name": "Anaerobic Lagoon",
    "tag": "Lagoon treatment",
    "tab": "UnitOperationDetail",
    "badge": "AL",
    "group": "Biological",
    "keywords": "anaerobic pond high strength wastewater"
  },
  {
    "type": "anmbr",
    "name": "Anaerobic Membrane Bioreactor",
    "tag": "AnMBR",
    "tab": "UnitOperationDetail",
    "badge": "AnMBR",
    "group": "Biological",
    "keywords": "anaerobic membrane bioreactor"
  },
  {
    "type": "ebpr",
    "name": "Anaerobic Zone",
    "tag": "EBPR selector",
    "tab": "EBPR",
    "badge": "EP",
    "group": "Biological",
    "flags": [
      "ebpr"
    ],
    "keywords": "enhanced biological phosphorus removal selector"
  },
  {
    "type": "denit",
    "name": "Anoxic Zone",
    "tag": "Denitrification",
    "tab": "Denitrification",
    "badge": "DN",
    "group": "Biological",
    "flags": [
      "denit"
    ],
    "keywords": "anoxic denitrification nitrate removal"
  },
  {
    "type": "cas",
    "name": "Aerobic Zone",
    "tag": "CAS",
    "tab": "CAS",
    "badge": "AS",
    "group": "Biological",
    "flags": [
      "cas"
    ],
    "keywords": "conventional activated sludge aerobic basin"
  },
  {
    "type": "extended_aeration",
    "name": "Extended Aeration",
    "tag": "Long-SRT activated sludge",
    "tab": "CAS",
    "badge": "EA",
    "group": "Biological",
    "flags": [
      "cas"
    ],
    "keywords": "package plant extended aeration complete mix"
  },
  {
    "type": "sbr",
    "name": "Sequencing Batch Reactor",
    "tag": "SBR",
    "tab": "UnitOperationDetail",
    "badge": "SBR",
    "group": "Biological",
    "keywords": "fill react settle decant batch reactor"
  },
  {
    "type": "oxidation_ditch",
    "name": "Oxidation Ditch",
    "tag": "Extended aeration",
    "tab": "CAS",
    "badge": "OD",
    "group": "Biological",
    "flags": [
      "cas"
    ],
    "keywords": "carousel ditch activated sludge"
  },
  {
    "type": "aerobic_granular",
    "name": "Aerobic Granular Sludge",
    "tag": "AGS",
    "tab": "UnitOperationDetail",
    "badge": "AGS",
    "group": "Biological",
    "keywords": "granular activated sludge aerobic granules"
  },
  {
    "type": "mbr",
    "name": "Membrane Bioreactor",
    "tag": "MBR",
    "tab": "MBR",
    "badge": "MBR",
    "group": "Biological",
    "flags": [
      "mbr"
    ],
    "keywords": "submerged membrane bioreactor"
  },
  {
    "type": "aerated_lagoon",
    "name": "Aerated Lagoon",
    "tag": "Lagoon treatment",
    "tab": "UnitOperationDetail",
    "badge": "ALG",
    "group": "Biological",
    "keywords": "aerated pond lagoon"
  },
  {
    "type": "mbbr_bod",
    "name": "MBBR",
    "tag": "BOD removal",
    "tab": "MBBR_IFAS",
    "badge": "MB",
    "group": "Attached Growth",
    "flags": [
      "mbbr"
    ],
    "keywords": "moving bed biofilm reactor carbon removal"
  },
  {
    "type": "mbbr_nit",
    "name": "MBBR",
    "tag": "Nitrification",
    "tab": "MBBR_IFAS",
    "badge": "MB",
    "group": "Attached Growth",
    "flags": [
      "mbbr"
    ],
    "keywords": "moving bed biofilm reactor ammonia nitrification"
  },
  {
    "type": "mbbr_denit",
    "name": "MBBR",
    "tag": "Denitrification",
    "tab": "MBBR_IFAS",
    "badge": "MB",
    "group": "Attached Growth",
    "flags": [
      "mbbr",
      "denit"
    ],
    "keywords": "moving bed biofilm reactor anoxic denitrification"
  },
  {
    "type": "mbbr_ifas",
    "name": "IFAS",
    "tag": "Carrier retrofit",
    "tab": "MBBR_IFAS",
    "badge": "IF",
    "group": "Attached Growth",
    "flags": [
      "mbbr",
      "cas"
    ],
    "keywords": "integrated fixed-film activated sludge"
  },
  {
    "type": "trickling_filter",
    "name": "Trickling Filter",
    "tag": "Fixed film",
    "tab": "UnitOperationDetail",
    "badge": "TF",
    "group": "Attached Growth",
    "keywords": "rock media plastic media biofilter"
  },
  {
    "type": "rbc",
    "name": "Rotating Biological Contactor",
    "tag": "RBC",
    "tab": "UnitOperationDetail",
    "badge": "RBC",
    "group": "Attached Growth",
    "keywords": "rotating discs fixed film"
  },
  {
    "type": "baf",
    "name": "Biological Aerated Filter",
    "tag": "BAF",
    "tab": "UnitOperationDetail",
    "badge": "BAF",
    "group": "Attached Growth",
    "keywords": "submerged aerated biofilter"
  },
  {
    "type": "mabr",
    "name": "Membrane Aerated Biofilm Reactor",
    "tag": "MABR",
    "tab": "UnitOperationDetail",
    "badge": "MABR",
    "group": "Attached Growth",
    "keywords": "oxygen transfer membrane biofilm"
  },
  {
    "type": "submerged_fixed_film",
    "name": "Submerged Fixed-Film Reactor",
    "tag": "SAFF / fixed media",
    "tab": "UnitOperationDetail",
    "badge": "SFF",
    "group": "Attached Growth",
    "keywords": "submerged aerated fixed film SAFF"
  },
  {
    "type": "pre_anoxic",
    "name": "Pre-Anoxic Denitrification",
    "tag": "MLE configuration",
    "tab": "Denitrification",
    "badge": "Pre",
    "group": "Nitrogen Removal",
    "flags": [
      "denit",
      "cas"
    ],
    "keywords": "modified ludzak ettinger internal recycle"
  },
  {
    "type": "post_anoxic",
    "name": "Post-Anoxic Denitrification",
    "tag": "Polishing denitrification",
    "tab": "Denitrification",
    "badge": "Post",
    "group": "Nitrogen Removal",
    "flags": [
      "denit"
    ],
    "keywords": "external carbon post anoxic"
  },
  {
    "type": "step_feed_bnr",
    "name": "Step-Feed BNR",
    "tag": "Staged feed activated sludge",
    "tab": "Denitrification",
    "badge": "SF",
    "group": "Nitrogen Removal",
    "flags": [
      "denit",
      "cas"
    ],
    "keywords": "step feed nitrogen removal"
  },
  {
    "type": "bardenpho",
    "name": "Bardenpho Process",
    "tag": "Multi-zone BNR",
    "tab": "Denitrification",
    "badge": "BAR",
    "group": "Nitrogen Removal",
    "flags": [
      "denit",
      "cas"
    ],
    "keywords": "four stage five stage bardenpho"
  },
  {
    "type": "partial_nitritation",
    "name": "Partial Nitritation",
    "tag": "Nitrite pathway",
    "tab": "Anammox",
    "badge": "PN",
    "group": "Nitrogen Removal",
    "flags": [
      "anammox"
    ],
    "keywords": "nitritation nitrite shunt"
  },
  {
    "type": "anammox",
    "name": "Anammox",
    "tag": "PN/A",
    "tab": "Anammox",
    "badge": "AM",
    "group": "Nitrogen Removal",
    "flags": [
      "anammox"
    ],
    "keywords": "anaerobic ammonium oxidation deammonification"
  },
  {
    "type": "deammonification",
    "name": "Single-Stage Deammonification",
    "tag": "PN/A reactor",
    "tab": "Anammox",
    "badge": "DMX",
    "group": "Nitrogen Removal",
    "flags": [
      "anammox"
    ],
    "keywords": "partial nitritation anammox sidestream mainstream"
  },
  {
    "type": "ammonia_stripping",
    "name": "Ammonia Stripping",
    "tag": "Physical NH₃ removal",
    "tab": "UnitOperationDetail",
    "badge": "AST",
    "group": "Nitrogen Removal",
    "keywords": "air stripping tower ammonia high ph"
  },
  {
    "type": "zeolite_nh4",
    "name": "Zeolite Ammonium Removal",
    "tag": "Ion exchange",
    "tab": "UnitOperationDetail",
    "badge": "ZEO",
    "group": "Nitrogen Removal",
    "keywords": "clinoptilolite ammonium ion exchange"
  },
  {
    "type": "breakpoint_chlorination",
    "name": "Breakpoint Chlorination",
    "tag": "Chemical ammonia removal",
    "tab": "UnitOperationDetail",
    "badge": "BPC",
    "group": "Nitrogen Removal",
    "keywords": "chlorine ammonia oxidation breakpoint"
  },
  {
    "type": "bio_p_ao",
    "name": "A/O Biological Phosphorus Removal",
    "tag": "EBPR process",
    "tab": "EBPR",
    "badge": "A/O",
    "group": "Phosphorus Removal",
    "flags": [
      "ebpr",
      "cas"
    ],
    "keywords": "anaerobic aerobic enhanced biological phosphorus phosphate removal"
  },
  {
    "type": "a2o",
    "name": "A²/O Biological Nutrient Removal",
    "tag": "N + P removal",
    "tab": "EBPR",
    "badge": "A2O",
    "group": "Phosphorus Removal",
    "flags": [
      "ebpr",
      "denit",
      "cas"
    ],
    "keywords": "anaerobic anoxic oxic biological nutrient removal"
  },
  {
    "type": "vip_bnr",
    "name": "VIP / UCT Biological P Removal",
    "tag": "EBPR configuration",
    "tab": "EBPR",
    "badge": "VIP",
    "group": "Phosphorus Removal",
    "flags": [
      "ebpr",
      "denit",
      "cas"
    ],
    "keywords": "virginia initiative plant UCT modified UCT phosphorus"
  },
  {
    "type": "vfa_fermentation",
    "name": "Primary Sludge Fermentation",
    "tag": "VFA generation",
    "tab": "UnitOperationDetail",
    "badge": "VFA",
    "group": "Phosphorus Removal",
    "keywords": "fermenter rbCOD volatile fatty acids EBPR carbon"
  },
  {
    "type": "chem_p",
    "name": "Chemical Phosphorus Removal",
    "tag": "General precipitation",
    "tab": "EBPR",
    "badge": "CP",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "chemical phosphate precipitation coagulant"
  },
  {
    "type": "p_preprecip",
    "name": "Pre-Precipitation",
    "tag": "Upstream chemical P removal",
    "tab": "EBPR",
    "badge": "PreP",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "chemical dosing before primary clarifier phosphate"
  },
  {
    "type": "p_coprecip",
    "name": "Simultaneous / Co-Precipitation",
    "tag": "Chemical P in bioreactor",
    "tab": "EBPR",
    "badge": "CoP",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "co-precipitation simultaneous precipitation activated sludge"
  },
  {
    "type": "p_postprecip",
    "name": "Post-Precipitation",
    "tag": "Tertiary chemical P removal",
    "tab": "EBPR",
    "badge": "PostP",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "chemical dosing after secondary clarification"
  },
  {
    "type": "ferric_p",
    "name": "Ferric Chloride P Precipitation",
    "tag": "FeCl₃ dosing",
    "tab": "EBPR",
    "badge": "FeCl3",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "ferric chloride phosphate precipitation"
  },
  {
    "type": "ferric_sulfate_p",
    "name": "Ferric Sulfate P Precipitation",
    "tag": "Ferric sulfate dosing",
    "tab": "EBPR",
    "badge": "Fe2",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "ferric sulphate phosphate precipitation"
  },
  {
    "type": "ferrous_p",
    "name": "Ferrous Salt P Precipitation",
    "tag": "Ferrous dosing",
    "tab": "EBPR",
    "badge": "Fe2+",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "ferrous sulfate chloride phosphate precipitation"
  },
  {
    "type": "alum_p",
    "name": "Alum P Precipitation",
    "tag": "Aluminum sulfate",
    "tab": "EBPR",
    "badge": "Alum",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "alum aluminium sulfate phosphate precipitation"
  },
  {
    "type": "pacl_p",
    "name": "PACl P Precipitation",
    "tag": "Polyaluminum chloride",
    "tab": "EBPR",
    "badge": "PACl",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "polyaluminium chloride phosphate removal"
  },
  {
    "type": "lime_p",
    "name": "Lime Phosphorus Precipitation",
    "tag": "High-pH precipitation",
    "tab": "EBPR",
    "badge": "Ca",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "calcium hydroxide lime phosphate precipitation"
  },
  {
    "type": "electrocoag_p",
    "name": "Electrocoagulation for P Removal",
    "tag": "Electrochemical P removal",
    "tab": "EBPR",
    "badge": "ECP",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "electrocoagulation phosphate removal iron aluminum electrodes"
  },
  {
    "type": "struvite",
    "name": "Struvite Precipitation / Recovery",
    "tag": "MgNH₄PO₄ recovery",
    "tab": "UnitOperationDetail",
    "badge": "STR",
    "group": "Phosphorus Removal",
    "keywords": "struvite phosphorus recovery magnesium ammonium phosphate"
  },
  {
    "type": "hap_recovery",
    "name": "Calcium Phosphate / HAP Recovery",
    "tag": "P recovery",
    "tab": "UnitOperationDetail",
    "badge": "HAP",
    "group": "Phosphorus Removal",
    "keywords": "hydroxyapatite calcium phosphate crystallization recovery"
  },
  {
    "type": "vivianite",
    "name": "Vivianite Recovery",
    "tag": "Iron phosphate recovery",
    "tab": "UnitOperationDetail",
    "badge": "VIV",
    "group": "Phosphorus Removal",
    "keywords": "vivianite iron phosphorus recovery sludge"
  },
  {
    "type": "p_adsorption",
    "name": "Phosphate Adsorption Media",
    "tag": "Tertiary P polishing",
    "tab": "UnitOperationDetail",
    "badge": "PA",
    "group": "Phosphorus Removal",
    "keywords": "iron oxide alumina lanthanum adsorption media phosphate"
  },
  {
    "type": "reactive_media_p",
    "name": "Reactive Media P Filter",
    "tag": "Sorptive filtration",
    "tab": "UnitOperationDetail",
    "badge": "RM",
    "group": "Phosphorus Removal",
    "keywords": "slag sand iron media reactive filter phosphate"
  },
  {
    "type": "tertiary_p_filter",
    "name": "Tertiary Phosphorus Filter",
    "tag": "Coagulation + filtration",
    "tab": "EBPR",
    "badge": "PF",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "low phosphorus tertiary filter chemical precipitation"
  },
  {
    "type": "ballasted_p",
    "name": "Ballasted Flocculation for P Removal",
    "tag": "High-rate P clarification",
    "tab": "EBPR",
    "badge": "BF",
    "group": "Phosphorus Removal",
    "flags": [
      "chemP"
    ],
    "keywords": "microsand ballasted clarification phosphorus"
  },
  {
    "type": "secondary",
    "name": "Secondary Clarifier",
    "tag": "Solids separation",
    "tab": "CAS",
    "badge": "CL",
    "group": "Separation & Membranes",
    "flags": [
      "secondary"
    ],
    "keywords": "final clarifier activated sludge settling"
  },
  {
    "type": "lamella_secondary",
    "name": "Lamella Secondary Clarifier",
    "tag": "Compact biomass separation",
    "tab": "UnitOperationDetail",
    "badge": "LSC",
    "group": "Separation & Membranes",
    "flags": [
      "secondary"
    ],
    "keywords": "inclined plate tube settler secondary clarification"
  },
  {
    "type": "daf_secondary",
    "name": "Dissolved Air Flotation",
    "tag": "Biomass separation",
    "tab": "UnitOperationDetail",
    "badge": "DAF",
    "group": "Separation & Membranes",
    "flags": [
      "secondary"
    ],
    "keywords": "flotation secondary solids algae biomass separation"
  },
  {
    "type": "microscreen",
    "name": "Microscreen / Drum Filter",
    "tag": "Fine solids removal",
    "tab": "UnitOperationDetail",
    "badge": "MS",
    "group": "Separation & Membranes",
    "keywords": "tertiary microscreen rotary drum"
  },
  {
    "type": "hydrocyclone",
    "name": "Hydrocyclone",
    "tag": "Density separation",
    "tab": "UnitOperationDetail",
    "badge": "HC",
    "group": "Separation & Membranes",
    "keywords": "cyclone grit granule separation"
  },
  {
    "type": "microfiltration",
    "name": "Microfiltration",
    "tag": "MF membrane",
    "tab": "UnitOperationDetail",
    "badge": "MF",
    "group": "Separation & Membranes",
    "keywords": "membrane solids separation"
  },
  {
    "type": "uf",
    "name": "Ultrafiltration",
    "tag": "UF membrane",
    "tab": "UnitOperationDetail",
    "badge": "UF",
    "group": "Separation & Membranes",
    "keywords": "membrane polishing solids pathogen removal"
  },
  {
    "type": "ceramic_membrane",
    "name": "Ceramic Membrane Filtration",
    "tag": "Robust MF / UF",
    "tab": "UnitOperationDetail",
    "badge": "CM",
    "group": "Separation & Membranes",
    "keywords": "ceramic ultrafiltration microfiltration industrial"
  },
  {
    "type": "tertiary",
    "name": "Tertiary Sand Filter",
    "tag": "Granular filtration",
    "tab": "MarketIntake",
    "badge": "SF",
    "group": "Polishing & Advanced",
    "keywords": "rapid sand filter tertiary filtration"
  },
  {
    "type": "dual_media_filter",
    "name": "Dual-Media Filter",
    "tag": "Anthracite / sand",
    "tab": "UnitOperationDetail",
    "badge": "DMF",
    "group": "Polishing & Advanced",
    "keywords": "multimedia filter granular filtration"
  },
  {
    "type": "cloth_filter",
    "name": "Cloth Media Filter",
    "tag": "Tertiary filtration",
    "tab": "UnitOperationDetail",
    "badge": "CF",
    "group": "Polishing & Advanced",
    "keywords": "pile cloth disk filter tertiary"
  },
  {
    "type": "disc_filter",
    "name": "Disc Filter",
    "tag": "Tertiary filtration",
    "tab": "UnitOperationDetail",
    "badge": "DF",
    "group": "Polishing & Advanced",
    "keywords": "disc filtration tertiary solids"
  },
  {
    "type": "cartridge_filter",
    "name": "Cartridge / Bag Filtration",
    "tag": "Fine filtration",
    "tab": "UnitOperationDetail",
    "badge": "CAR",
    "group": "Polishing & Advanced",
    "keywords": "bag filter cartridge filter"
  },
  {
    "type": "gac",
    "name": "Granular Activated Carbon",
    "tag": "Organic polishing",
    "tab": "UnitOperationDetail",
    "badge": "GAC",
    "group": "Polishing & Advanced",
    "keywords": "activated carbon adsorption organics color odor"
  },
  {
    "type": "pac_contact",
    "name": "Powdered Activated Carbon Contact",
    "tag": "PAC treatment",
    "tab": "UnitOperationDetail",
    "badge": "PAC",
    "group": "Polishing & Advanced",
    "keywords": "powdered activated carbon contact tank"
  },
  {
    "type": "ozone",
    "name": "Ozonation",
    "tag": "Oxidation / polishing",
    "tab": "UnitOperationDetail",
    "badge": "O3",
    "group": "Polishing & Advanced",
    "keywords": "ozone oxidation color micropollutants"
  },
  {
    "type": "aop_uv_h2o2",
    "name": "UV / H₂O₂ Advanced Oxidation",
    "tag": "AOP",
    "tab": "UnitOperationDetail",
    "badge": "AOP",
    "group": "Polishing & Advanced",
    "keywords": "advanced oxidation peroxide UV micropollutants"
  },
  {
    "type": "fenton",
    "name": "Fenton / Photo-Fenton Oxidation",
    "tag": "AOP",
    "tab": "UnitOperationDetail",
    "badge": "FEN",
    "group": "Polishing & Advanced",
    "keywords": "hydrogen peroxide iron advanced oxidation COD"
  },
  {
    "type": "ion_exchange",
    "name": "Ion Exchange",
    "tag": "Selective polishing",
    "tab": "UnitOperationDetail",
    "badge": "IX",
    "group": "Polishing & Advanced",
    "keywords": "resin selective ion removal"
  },
  {
    "type": "constructed_wetland",
    "name": "Constructed Wetland",
    "tag": "Nature-based polishing",
    "tab": "UnitOperationDetail",
    "badge": "CW",
    "group": "Polishing & Advanced",
    "keywords": "reed bed wetland lagoon polishing"
  },
  {
    "type": "uv",
    "name": "UV Disinfection",
    "tag": "Disinfection",
    "tab": "MarketIntake",
    "badge": "UV",
    "group": "Disinfection",
    "keywords": "ultraviolet disinfection pathogen inactivation"
  },
  {
    "type": "chlorination",
    "name": "Chlorination",
    "tag": "Disinfection",
    "tab": "MarketIntake",
    "badge": "Cl",
    "group": "Disinfection",
    "keywords": "chlorine gas hypochlorite disinfection"
  },
  {
    "type": "hypochlorite",
    "name": "Sodium Hypochlorite Disinfection",
    "tag": "NaOCl dosing",
    "tab": "MarketIntake",
    "badge": "NaOCl",
    "group": "Disinfection",
    "keywords": "bleach chlorine disinfection"
  },
  {
    "type": "chlorine_dioxide",
    "name": "Chlorine Dioxide Disinfection",
    "tag": "ClO₂ dosing",
    "tab": "UnitOperationDetail",
    "badge": "ClO2",
    "group": "Disinfection",
    "keywords": "chlorine dioxide oxidation disinfection"
  },
  {
    "type": "ozone_disinfection",
    "name": "Ozone Disinfection",
    "tag": "O₃ contact",
    "tab": "UnitOperationDetail",
    "badge": "O3",
    "group": "Disinfection",
    "keywords": "ozone pathogen disinfection contactor"
  },
  {
    "type": "peracetic_acid",
    "name": "Peracetic Acid Disinfection",
    "tag": "PAA dosing",
    "tab": "UnitOperationDetail",
    "badge": "PAA",
    "group": "Disinfection",
    "keywords": "peracetic acid wastewater disinfection"
  },
  {
    "type": "dechlorination",
    "name": "Dechlorination",
    "tag": "Residual removal",
    "tab": "MarketIntake",
    "badge": "DCl",
    "group": "Disinfection",
    "keywords": "sodium bisulfite sulfite chlorine residual removal"
  },
  {
    "type": "sludge_equalization",
    "name": "Sludge Equalization / Blending Tank",
    "tag": "Common sludge buffer",
    "tab": "Sludge",
    "badge": "SEQ",
    "group": "Residuals",
    "keywords": "sludge equalization blending buffer tank common dewatering intermittent sources"
  },
  {
    "type": "sludge_thickening",
    "name": "Sludge Thickening",
    "tag": "Residuals",
    "tab": "Sludge",
    "badge": "ST",
    "group": "Residuals",
    "keywords": "solids concentration thickening"
  },
  {
    "type": "gravity_thickener",
    "name": "Gravity Thickener",
    "tag": "Gravity thickening",
    "tab": "Sludge",
    "badge": "GT",
    "group": "Residuals",
    "keywords": "circular gravity sludge thickener"
  },
  {
    "type": "daf_thickener",
    "name": "DAF Sludge Thickener",
    "tag": "Flotation thickening",
    "tab": "Sludge",
    "badge": "DAT",
    "group": "Residuals",
    "keywords": "dissolved air flotation sludge thickening"
  },
  {
    "type": "rotary_drum_thickener",
    "name": "Rotary Drum Thickener",
    "tag": "Mechanical thickening",
    "tab": "Sludge",
    "badge": "RDT",
    "group": "Residuals",
    "keywords": "rotary drum sludge thickener polymer"
  },
  {
    "type": "aerobic_digestion",
    "name": "Aerobic Digestion",
    "tag": "Stabilization",
    "tab": "Sludge",
    "badge": "AD",
    "group": "Residuals",
    "keywords": "aerobic sludge digestion stabilization"
  },
  {
    "type": "anaerobic_digestion",
    "name": "Anaerobic Digestion",
    "tag": "Stabilization / biogas",
    "tab": "Sludge",
    "badge": "DG",
    "group": "Residuals",
    "keywords": "mesophilic thermophilic digestion biogas"
  },
  {
    "type": "thermal_hydrolysis",
    "name": "Thermal Hydrolysis",
    "tag": "Pretreatment before digestion",
    "tab": "Sludge",
    "badge": "THP",
    "group": "Residuals",
    "keywords": "thermal hydrolysis sludge digestion"
  },
  {
    "type": "lime_stabilization",
    "name": "Lime Stabilization",
    "tag": "Biosolids stabilization",
    "tab": "Sludge",
    "badge": "LS",
    "group": "Residuals",
    "keywords": "alkaline stabilization biosolids"
  },
  {
    "type": "sludge_storage",
    "name": "Sludge Holding / Storage",
    "tag": "Storage",
    "tab": "Sludge",
    "badge": "SH",
    "group": "Residuals",
    "keywords": "sludge holding tank storage"
  },
  {
    "type": "centrifuge",
    "name": "Centrifuge Dewatering",
    "tag": "Mechanical dewatering",
    "tab": "Sludge",
    "badge": "CF",
    "group": "Residuals",
    "keywords": "decanter centrifuge sludge dewatering"
  },
  {
    "type": "belt_press",
    "name": "Belt Filter Press",
    "tag": "Mechanical dewatering",
    "tab": "Sludge",
    "badge": "BFP",
    "group": "Residuals",
    "keywords": "belt press sludge dewatering"
  },
  {
    "type": "screw_press",
    "name": "Screw Press",
    "tag": "Mechanical dewatering",
    "tab": "Sludge",
    "badge": "SP",
    "group": "Residuals",
    "keywords": "volute screw press sludge dewatering"
  },
  {
    "type": "filter_press",
    "name": "Plate-and-Frame Filter Press",
    "tag": "Mechanical dewatering",
    "tab": "Sludge",
    "badge": "FP",
    "group": "Residuals",
    "keywords": "plate frame recessed chamber sludge dewatering"
  },
  {
    "type": "drying_beds",
    "name": "Sludge Drying Beds",
    "tag": "Passive dewatering",
    "tab": "Sludge",
    "badge": "DB",
    "group": "Residuals",
    "keywords": "sand drying bed biosolids"
  },
  {
    "type": "composting",
    "name": "Biosolids Composting",
    "tag": "Final solids management",
    "tab": "Sludge",
    "badge": "COM",
    "group": "Residuals",
    "keywords": "compost biosolids stabilization"
  },
  {
    "type": "incineration",
    "name": "Sludge Incineration",
    "tag": "Thermal destruction",
    "tab": "Sludge",
    "badge": "INC",
    "group": "Residuals",
    "keywords": "biosolids combustion thermal oxidation"
  },
  {
    "type": "sidestream_return",
    "name": "Sidestream / Centrate Return",
    "tag": "Recycle stream",
    "tab": "Sludge",
    "badge": "SR",
    "group": "Residuals",
    "keywords": "centrate filtrate reject water return load"
  },
  {
    "type": "dewatering",
    "name": "Sludge Dewatering",
    "tag": "Residuals",
    "tab": "Sludge",
    "badge": "DW",
    "group": "Residuals",
    "keywords": "generic sludge dewatering"
  },
  {
    "type": "sludge",
    "name": "Sludge Handling",
    "tag": "Residuals",
    "tab": "Sludge",
    "badge": "SL",
    "group": "Residuals",
    "keywords": "sludge handling residuals"
  },
  {
    "type": "custom_unit",
    "name": "Custom Unit Operation",
    "tag": "User-defined duty",
    "tab": "UnitOperationDetail",
    "badge": "+",
    "group": "Other",
    "keywords": "custom process user defined operation"
  }
];
});
