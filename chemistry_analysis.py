"""Water chemistry analysis for CalcOsPower v16.0.

This module ports the structure and engineering equations of the user's
Scaling_Index_Calculator workbook into Python while deliberately leaving the
existing CalcOsPower osmotic-coefficient model untouched.  Osmotic pressure is
still supplied by water_chemistry/osmotic_model; this module is for charge
balance, pH-dependent speciation, activity coefficients, scaling indices and
mineral saturation.
"""
from __future__ import annotations

from solver import brent_root

from math import exp, log, log10, sqrt
from typing import Dict, Mapping

from water_chemistry import SPECIES, normalize_composition, osmotic_state_from_composition

R = 8.31446261815324
LN10 = log(10.0)

# Spreadsheet basis.  Input is mg/L as the ion shown.
# The source workbook uses this charge-balance definition:
#   2*(cation-anion)/(cation+anion)

CATION_KEYS = [k for k,v in SPECIES.items() if v[3] > 0]
ANION_KEYS = [k for k,v in SPECIES.items() if v[3] < 0]
NEUTRAL_KEYS = [k for k,v in SPECIES.items() if v[3] == 0]

# Temperature-dependent equilibrium constants copied from the workbook's
# CONSTANTS sheet. If A1..A5 are present the PHREEQC-type polynomial is used;
# otherwise van't Hoff is used from logK25 and dH.
EQ = {
    'Kw': (-14.0,55.81,(-283.971,-0.05069842,13323.0,102.24447,-1119669.0)),
    'K1': (-6.3519,9.11,(-356.3094,-0.06091964,21834.37,126.8339,-1684915.0)),
    'K2': (-10.3289,14.9,(-107.8871,-0.03252849,5151.79,38.92561,-563713.9)),
    'KHF': (-3.18,13.32,None), 'KSi1':(-9.83,29.28,None), 'KSi2':(-13.17,25.1,None),
    'KB':(-9.24,13.8,None), 'KN':(-9.252,52.09,None),
    'KP1':(-2.147,-8.05,None), 'KP2':(-7.207,3.53,None), 'KP3':(-12.346,14.7,None),
}

MINERALS = {
    'Calcite': ('CaCO3', -8.48,-10.79,(-171.9065,-0.077993,2839.319,71.595,0.0), 2),
    'Aragonite': ('CaCO3', -8.336,-11.52,(-171.9773,-0.077993,2903.293,71.595,0.0), 2),
    'Vaterite': ('CaCO3', -7.913,-12.33,None,2),
    'Dolomite': ('CaMg(CO3)2', -17.09,-39.48,None,4),
    'Magnesite': ('MgCO3', -8.029,-10.91,None,2),
    'Gypsum': ('CaSO4:2H2O', -4.58,-0.46,(68.2401,0,-3221.51,-25.0627,0),2),
    'Anhydrite': ('CaSO4', -4.36,-18.58,(197.52,0,-8669.8,-69.835,0),2),
    'Barite': ('BaSO4', -9.97,26.57,(136.035,0,-7680.41,-48.595,0),2),
    'Celestite': ('SrSO4', -6.63,-4.34,None,2),
    'Witherite': ('BaCO3', -8.562,0.703,None,2),
    'Strontianite': ('SrCO3', -9.271,-0.4,None,2),
    'Fluorite': ('CaF2', -10.6,20.1,(66.348,0,-4298.2,-25.271,0),3),
    'Sellaite': ('MgF2', -8.13,0,None,3),
    'Silica (amorph.)': ('SiO2', -2.71,14.31,(-0.26,0,-731,0,0),1),
    'Chalcedony': ('SiO2', -3.55,19.13,(-0.09,0,-1032,0,0),1),
    'Quartz': ('SiO2', -3.98,22.36,(0.41,0,-1309,0,0),1),
    'Brucite': ('Mg(OH)2', 16.84,-113.4,None,3),
    'Siderite': ('FeCO3', -10.89,-10.38,None,2),
    'Rhodochrosite': ('MnCO3', -11.13,-5.98,None,2),
    'Ferrihydrite': ('Fe(OH)3(a)', 4.891,0,None,4),
    'Hydroxyapatite': ('Ca5(PO4)3OH', -3.421,-151.3,None,9),
    'Halite': ('NaCl', 1.57,3.72,None,2),
}

# 25 C formation constants for the ion-association track, from workbook.
PAIR_LOGK = {
    'CaCO3':3.224,'CaHCO3':11.435,'CaSO4':2.3,'CaF':0.94,
    'MgCO3':2.98,'MgHCO3':11.399,'MgSO4':2.37,'MgF':1.82,
    'NaCO3':1.27,'NaHCO3':10.079,'NaSO4':0.7,'NaF':-0.24,'KSO4':0.85,
    'SrCO3':2.81,'SrHCO3':11.509,'SrSO4':2.29,
    'BaCO3':2.71,'BaHCO3':11.311,'BaSO4':2.7,
    'FeCO3':4.38,'FeHCO3':12.33,'FeSO4':2.25,'FeF':1.0,
    'MnCO3':4.9,'MnHCO3':11.929,'MnSO4':2.25,
}

# Hydrolysis constants (Me + H2O = MeOH + H+) from workbook.
HYDRO_LOGK = {'Ca':-12.78,'Mg':-11.44,'Sr':-13.29,'Ba':-13.47,'Na':-14.18,'K':-14.46,'Fe':-9.5,'Mn':-10.59}

# Pitzer binary parameters from the workbook.  This port intentionally uses the
# workbook's second-virial framework and omits higher-order unsymmetric mixing,
# matching its VALIDATION note.
PCATS=['H','Na','K','Ca','Mg','Sr','Ba']
PANS=['OH','Cl','SO4','HCO3','CO3','NO3','F']
ZC={'H':1,'Na':1,'K':1,'Ca':2,'Mg':2,'Sr':2,'Ba':2}
ZA={'OH':-1,'Cl':-1,'SO4':-2,'HCO3':-1,'CO3':-2,'NO3':-1,'F':-1}

def _matrix(rows): return {c:{a:float(rows[i][j]) for j,a in enumerate(PANS)} for i,c in enumerate(PCATS)}
B0=_matrix([
[0,.1775,.0298,0,0,.1119,0],[.0864,.0765,.01958,.0277,.0399,.0068,.0215],[.1298,.04835,.04995,.0296,.1488,-.0816,.08089],[-.1747,.3159,.2,.4,0,.2108,0],[0,.35235,.221,.329,0,.367,0],[0,.2858,.2,.4,0,.2393,0],[.17175,.2628,.2,.4,0,-.043,0]])
B1=_matrix([
[0,.2945,0,0,0,.3206,0],[.253,.2664,1.113,.0411,1.389,.1783,.2107],[.32,.2122,.7793,-.013,1.43,.0494,.2021],[-.2303,1.614,3.1973,2.977,0,1.6588,0],[0,1.6815,3.343,.6072,0,1.5825,0],[0,1.667,3.1973,2.977,0,1.5416,0],[1.2,1.4963,3.1973,2.977,0,1.07,0]])
B2=_matrix([[0]*7,[0]*7,[0]*7,[-5.72,0,-54.24,0,0,0,0],[0,0,-37.23,0,0,0,0],[0,0,-54.24,0,0,0,0],[0,0,-54.24,0,0,0,0]])
CPHI=_matrix([
[0,.0008,.0438,0,0,-.00155,0],[.0044,.00127,.00497,0,.0044,-.00072,0],[.0041,-.00084,0,-.008,-.0015,.0066,.00093],[0,-.00034,0,0,0,-.0206,0],[0,.00519,.025,0,0,-.02,0],[0,-.0013,0,0,0,-.0281,0],[0,-.01938,0,0,0,0,0]])
THETA_C={('H','Na'):.036,('H','K'):.005,('H','Ca'):.092,('H','Mg'):.1,('H','Sr'):.065,('H','Ba'):.068,('Na','K'):-.012,('Na','Ca'):.07,('Na','Mg'):.07,('Na','Sr'):.051,('Na','Ba'):.067,('K','Ca'):.032,('Ca','Mg'):.007}
THETA_A={('OH','Cl'):-.05,('OH','SO4'):-.013,('OH','CO3'):.1,('OH','NO3'):-.009,('Cl','SO4'):.02,('Cl','HCO3'):.03,('Cl','CO3'):-.02,('Cl','NO3'):.016,('Cl','F'):.01,('SO4','HCO3'):.01,('SO4','CO3'):.02,('HCO3','CO3'):-.04}


def _logk(name,temp_c, table=EQ):
    logk25, dh, poly = table[name]
    t=float(temp_c)+273.15
    if poly:
        a1,a2,a3,a4,a5=poly
        return a1+a2*t+a3/t+a4*log10(t)+a5/(t*t)
    return logk25 - dh*1000/(LN10*R)*(1/t-1/298.15)

def _mineral_logk(name,temp_c):
    _, logk25, dh, poly, _ = MINERALS[name]
    t=float(temp_c)+273.15
    if poly:
        a1,a2,a3,a4,a5=poly
        return a1+a2*t+a3/t+a4*log10(t)+a5/(t*t)
    return logk25 - dh*1000/(LN10*R)*(1/t-1/298.15)

def _solution_density_kg_l(tds_mg_l: float, temp_c: float) -> float:
    # Same engineering density convention already used by CalcOsPower.
    t=max(0,min(100,float(temp_c)))
    rho=1.0-((t+288.9414)/(508929.2*(t+68.12963)))*(t-3.9863)**2
    return rho + 0.00000075*max(0,float(tds_mg_l))

def _kg_water_per_l(comp,temp_c):
    tds=sum(normalize_composition(comp).values())
    return max(.70,_solution_density_kg_l(tds,temp_c)-tds/1e6)

def _molalities(comp,temp_c):
    c=normalize_composition(comp); kgw=_kg_water_per_l(c,temp_c)
    return {k:(v/1000.0/SPECIES[k][2])/kgw for k,v in c.items()}

def charge_report(comp: Mapping[str,float]) -> dict:
    c=normalize_composition(comp)
    rows=[]; cat=an=0.0
    for key in CATION_KEYS+ANION_KEYS+NEUTRAL_KEYS:
        label,_,mw,z,_=SPECIES[key]; mg=c[key]; mmol=mg/mw; meq=mmol*abs(z)
        if z>0: cat+=meq
        elif z<0: an+=meq
        rows.append({'key':key,'label':label,'charge':z,'mg_l':mg,'mmol_l':mmol,'meq_l':meq})
    denom=cat+an
    err=0.0 if denom<=1e-12 else 2.0*(cat-an)/denom*100.0
    return {'rows':rows,'cations_meq_l':cat,'anions_meq_l':an,'imbalance_pct':err,'status':'good' if abs(err)<2 else ('review' if abs(err)<5 else 'check')}

def scale_to_tds(comp: Mapping[str,float], target_tds: float) -> dict:
    c=normalize_composition(comp); current=sum(c.values()); target=max(0,float(target_tds))
    if current<=0: return {'composition':c,'factor':1.0,'old_tds':current,'new_tds':current}
    f=target/current
    return {'composition':{k:v*f for k,v in c.items()},'factor':f,'old_tds':current,'new_tds':target}

def _legacy_balance_composition(comp: Mapping[str,float], ion_key: str) -> dict:
    if ion_key not in ('sodium','chloride','calcium','magnesium','sulfate'):
        raise ValueError('Balancing ion must be sodium, chloride, calcium, magnesium, or sulfate.')
    c=normalize_composition(comp); r=charge_report(c); diff=r['cations_meq_l']-r['anions_meq_l']; z=SPECIES[ion_key][3]
    # diff>0 => need negative charge; diff<0 => need positive charge.
    if abs(diff)<1e-12: return {'composition':c,'adjustment_mg_l':0.0,'ion':ion_key,'charge_before':r,'charge_after':r}
    if diff>0 and z>0: raise ValueError('The analysis has excess cation charge; select chloride or sulfate.')
    if diff<0 and z<0: raise ValueError('The analysis has excess anion charge; select sodium, calcium, or magnesium.')
    delta_meq=abs(diff); delta_mg=delta_meq*SPECIES[ion_key][2]/abs(z)
    c[ion_key]+=delta_mg
    return {'composition':c,'adjustment_mg_l':delta_mg,'ion':ion_key,'charge_before':r,'charge_after':charge_report(c)}

def _davies_gamma(z,I):
    if z==0: return 10**(.1*I)
    A=.510026752578591; s=sqrt(max(I,0))
    return 10**(-A*z*z*(s/(1+s)-.3*I))

def _legacy_carbonate_speciation(comp: Mapping[str,float], temp_c:float, ph:float, source_ph:float|None=None) -> dict:
    """Re-equilibrate carbonate species while preserving inorganic-carbon total.

    The current HCO3/CO3 values are interpreted as a previously equilibrated
    state at source_ph.  CO2 is reconstructed from that state, then CT is
    redistributed at the requested pH.  This means changing pH changes the
    species without inventing/removing carbon.
    """
    c=normalize_composition(comp); m=_molalities(c,temp_c); source_ph=float(ph if source_ph is None else source_ph)
    k1=10**_logk('K1',temp_c); k2=10**_logk('K2',temp_c)
    def alpha(p):
        h=10**(-p); den=h*h+k1*h+k1*k2
        return (h*h/den,k1*h/den,k1*k2/den)
    a0s,a1s,a2s=alpha(source_ph)
    known=m['bicarbonate']+m['carbonate']
    ct=known/max(a1s+a2s,1e-30)
    a0,a1,a2=alpha(float(ph))
    kgw=_kg_water_per_l(c,temp_c)
    out=dict(c)
    out['bicarbonate']=ct*a1*kgw*SPECIES['bicarbonate'][2]*1000
    out['carbonate']=ct*a2*kgw*SPECIES['carbonate'][2]*1000
    return {'composition':out,'total_inorganic_carbon_mol_kg':ct,'co2_mol_kg':ct*a0,'hco3_mol_kg':ct*a1,'co3_mol_kg':ct*a2}

def weak_species_speciation(comp: Mapping[str,float], temp_c: float, ph: float) -> dict:
    """pH-dependent analytical-component speciation for weak acid/base systems.

    Analytical totals are preserved. Boron input is mg/L as elemental B; silica
    is mg/L as SiO2; phosphate is mg/L as PO4; ammonium is mg/L as NH4; fluoride
    is mg/L as F. Returned species are mol/kg water.  This is deliberately kept
    separate from the membrane osmotic model.
    """
    c=normalize_composition(comp); m=_molalities(c,temp_c); h=max(10.0**(-float(ph)),1e-30)
    out={}
    # Boric acid: H3BO3 <-> H+ + B(OH)4-
    kb=10**_logk('KB',temp_c); btot=m['boron']; den=h+kb
    out['boron']={'total':btot,'H3BO3':btot*h/den,'B(OH)4-':btot*kb/den}
    # Silicic acid: H4SiO4 <-> H+ + H3SiO4- <-> 2H+ + H2SiO4--
    k1=10**_logk('KSi1',temp_c); k2=10**_logk('KSi2',temp_c); stot=m['silica']
    den=h*h+k1*h+k1*k2
    out['silica']={'total':stot,'H4SiO4':stot*h*h/den,'H3SiO4-':stot*k1*h/den,'H2SiO4--':stot*k1*k2/den}
    # Phosphoric acid three-step system. Input is analytical PO4-equivalent total.
    kp1,kp2,kp3=(10**_logk(x,temp_c) for x in ('KP1','KP2','KP3')); ptot=m['phosphate']
    den=h**3+kp1*h*h+kp1*kp2*h+kp1*kp2*kp3
    out['phosphate']={'total':ptot,'H3PO4':ptot*h**3/den,'H2PO4-':ptot*kp1*h*h/den,'HPO4--':ptot*kp1*kp2*h/den,'PO4---':ptot*kp1*kp2*kp3/den}
    # Ammonium: NH4+ <-> H+ + NH3
    kn=10**_logk('KN',temp_c); ntot=m['ammonium']; den=h+kn
    out['ammonia']={'total':ntot,'NH4+':ntot*h/den,'NH3':ntot*kn/den}
    # Hydrofluoric acid: HF <-> H+ + F-. Input is analytical F total.
    khf=10**_logk('KHF',temp_c); ftot=m['fluoride']; den=h+khf
    out['fluoride']={'total':ftot,'HF':ftot*h/den,'F-':ftot*khf/den}
    return out

def _pitzer_B(beta0,beta1,beta2,alpha1,alpha2,sqrtI):
    def g(x):
        if abs(x)<1e-12:return 1.0
        return 2*(1-(1+x)*exp(-x))/(x*x)
    return beta0+beta1*g(alpha1*sqrtI)+(beta2*g(alpha2*sqrtI) if alpha2 else 0.0)

def _pitzer_Bprime(beta1,beta2,alpha1,alpha2,I):
    if I<=1e-16:return 0.0
    s=sqrt(I)
    def gp(x):
        if abs(x)<1e-9:return 0.0
        return -2*(1-(1+x+x*x/2)*exp(-x))/(x*x)
    return (beta1*gp(alpha1*s)+(beta2*gp(alpha2*s) if alpha2 else 0.0))/I

def pitzer_gammas(stoich:dict) -> dict:
    mc={x:max(0,stoich.get(x,0.0)) for x in PCATS}; ma={x:max(0,stoich.get(x,0.0)) for x in PANS}
    I=.5*(sum(mc[x]*ZC[x]**2 for x in PCATS)+sum(ma[x]*ZA[x]**2 for x in PANS)); s=sqrt(max(I,1e-30)); Z=sum(mc[x]*abs(ZC[x]) for x in PCATS)+sum(ma[x]*abs(ZA[x]) for x in PANS)
    Aphi=.391459999171875; b=1.2
    f_gamma=-Aphi*(s/(1+b*s)+(2/b)*log(1+b*s))
    sumC=0.0; B={};Bp={};C={}
    for c in PCATS:
        for a in PANS:
            alpha1=1.4 if abs(ZC[c]*ZA[a])==4 else 2.0; alpha2=12.0 if abs(ZC[c]*ZA[a])==4 else 0.0
            B[c,a]=_pitzer_B(B0[c][a],B1[c][a],B2[c][a],alpha1,alpha2,s)
            Bp[c,a]=_pitzer_Bprime(B1[c][a],B2[c][a],alpha1,alpha2,I)
            C[c,a]=CPHI[c][a]/(2*sqrt(abs(ZC[c]*ZA[a]))) if ZC[c]*ZA[a] else 0
            f_gamma += mc[c]*ma[a]*Bp[c,a]
            sumC += mc[c]*ma[a]*C[c,a]
    # Like-sign mixing using workbook theta set; higher electrostatic E-theta omitted by design.
    def theta(dic,x,y): return dic.get((x,y),dic.get((y,x),0.0))
    out={}
    for c in PCATS:
        ln=(ZC[c]**2)*f_gamma + abs(ZC[c])*sumC
        ln += sum(ma[a]*(2*B[c,a]+Z*C[c,a]) for a in PANS)
        ln += sum(mc[c2]*2*theta(THETA_C,c,c2) for c2 in PCATS if c2!=c)
        out[c]=exp(ln)
    for a in PANS:
        ln=(ZA[a]**2)*f_gamma + abs(ZA[a])*sumC
        ln += sum(mc[c]*(2*B[c,a]+Z*C[c,a]) for c in PCATS)
        ln += sum(ma[a2]*2*theta(THETA_A,a,a2) for a2 in PANS if a2!=a)
        out[a]=exp(ln)
    return {'gamma':out,'ionic_strength':I,'Z':Z,'F':f_gamma,'sum_mc_ma_C':sumC}


# ---------------------------------------------------------------------------
# v17.2 carbonate / alkalinity state engine
# ---------------------------------------------------------------------------
# The analytical ``bicarbonate`` field is now TOTAL ALKALINITY expressed as
# mg/L HCO3-equivalent. ``carbonate`` is retained only as an optional
# lab-reported QC value; it never drives equilibrium or mineral saturation.
# Exactly two of {pH, TA, CT} define the carbonate state.

CARBONATE_PH_MIN = 2.0
CARBONATE_PH_MAX = 12.0
HCO3_EQ_MW = SPECIES['bicarbonate'][2]
CO2_MW = 44.0095


def _analytical_composition(comp: Mapping[str, float] | None) -> dict:
    """Normalize analytical inputs while allowing legitimately negative TA."""
    comp = comp or {}
    out = {}
    for k in SPECIES:
        v = comp.get(k, 0.0)
        v = 0.0 if v in (None, '') else float(v)
        out[k] = v if k == 'bicarbonate' else max(0.0, v)
    return out


def _base_noncarbonate_composition(comp: Mapping[str, float]) -> dict:
    c = _analytical_composition(comp)
    c['bicarbonate'] = 0.0
    c['carbonate'] = 0.0
    return c


def _ta_mol_kg_from_mg_l_as_hco3(comp: Mapping[str, float], temp_c: float) -> float:
    c = _analytical_composition(comp)
    base = _base_noncarbonate_composition(c)
    kgw = _kg_water_per_l(base, temp_c)
    # mg/L as HCO3-equivalent -> mol-equivalent/L -> mol-equivalent/kg water
    return (float(c['bicarbonate']) / 1000.0 / HCO3_EQ_MW) / max(kgw, 1e-30)


def analytical_alkalinity_mol_kg(comp: Mapping[str, float], temp_c: float=25.0) -> float:
    """Public conversion for analytical TA stored as mg/L HCO3-equivalent."""
    return _ta_mol_kg_from_mg_l_as_hco3(comp, temp_c)


def _ta_mg_l_as_hco3(ta_mol_kg: float, comp: Mapping[str, float], temp_c: float) -> float:
    base = _base_noncarbonate_composition(comp)
    kgw = _kg_water_per_l(base, temp_c)
    return float(ta_mol_kg) * kgw * HCO3_EQ_MW * 1000.0


def _carbonate_gamma_state(base_m: dict, temp_c: float, ph: float, hco3: float, co3: float):
    """Pitzer gammas for the carbonate state, iterated with H/OH molalities."""
    a_h = 10.0 ** (-float(ph))
    kw = 10.0 ** _logk('Kw', temp_c)
    h = a_h
    oh = kw / max(a_h, 1e-30)
    pit = None
    for _ in range(12):
        sto = {
            'H': h, 'Na': base_m['sodium'], 'K': base_m['potassium'],
            'Ca': base_m['calcium'], 'Mg': base_m['magnesium'],
            'Sr': base_m['strontium'], 'Ba': base_m['barium'],
            'OH': oh, 'Cl': base_m['chloride'], 'SO4': base_m['sulfate'],
            'HCO3': max(0.0, hco3), 'CO3': max(0.0, co3),
            'NO3': base_m['nitrate'], 'F': base_m['fluoride'],
        }
        pit = pitzer_gammas(sto)
        pg = pit['gamma']
        new_h = a_h / max(pg.get('H', 1.0), 1e-30)
        new_oh = kw / max(a_h * pg.get('OH', 1.0), 1e-30)
        if abs(new_h-h) <= 1e-12*max(1.0, h) and abs(new_oh-oh) <= 1e-10*max(1.0, oh):
            h, oh = new_h, new_oh
            break
        h, oh = new_h, new_oh
    return pit, h, oh


def _phosphate_alkalinity(weak: dict) -> float:
    p = weak.get('phosphate', {})
    # Conventional phosphate alkalinity relative to H2PO4-:
    # [HPO4--] + 2[PO4---] - [H3PO4].
    return float(p.get('HPO4--', 0.0)) + 2.0*float(p.get('PO4---', 0.0)) - float(p.get('H3PO4', 0.0))


def _state_at_ph_ct(comp: Mapping[str, float], temp_c: float, ph: float, ct_mol_kg: float) -> dict:
    """Solve activity-consistent carbonate distribution for fixed pH and CT."""
    ph = float(ph); ct = max(0.0, float(ct_mol_kg))
    analytical = _analytical_composition(comp)
    base = _base_noncarbonate_composition(analytical)
    base_m = _molalities(base, temp_c)
    a_h = 10.0 ** (-ph)
    k1 = 10.0 ** _logk('K1', temp_c)
    k2 = 10.0 ** _logk('K2', temp_c)
    # Ideal alpha is only an initial guess; final values use Pitzer activities.
    den = a_h*a_h + k1*a_h + k1*k2
    hco3 = ct * (k1*a_h/den) if den > 0 else 0.0
    co3 = ct * (k1*k2/den) if den > 0 else 0.0
    co2 = max(0.0, ct-hco3-co3)
    pit = None; h = a_h; oh = 0.0
    for _ in range(40):
        pit, h, oh = _carbonate_gamma_state(base_m, temp_c, ph, hco3, co3)
        pg = pit['gamma']
        g_hco3 = max(pg.get('HCO3', 1.0), 1e-30)
        g_co3 = max(pg.get('CO3', 1.0), 1e-30)
        # gamma_CO2 = 1.0 because neutral CO2 is outside this Pitzer ion set.
        r1 = k1 / max(a_h*g_hco3, 1e-30)  # mHCO3 / mCO2
        r2 = k2*g_hco3 / max(a_h*g_co3, 1e-30)  # mCO3 / mHCO3
        new_co2 = ct / max(1.0 + r1 + r1*r2, 1e-30)
        new_hco3 = new_co2*r1
        new_co3 = new_hco3*r2
        err = max(abs(new_hco3-hco3), abs(new_co3-co3))
        hco3 = 0.5*hco3 + 0.5*new_hco3
        co3 = 0.5*co3 + 0.5*new_co3
        co2 = max(0.0, ct-hco3-co3)
        if err < 1e-12*max(1.0, ct):
            hco3, co3, co2 = new_hco3, new_co3, new_co2
            pit, h, oh = _carbonate_gamma_state(base_m, temp_c, ph, hco3, co3)
            break
    weak = weak_species_speciation(base, temp_c, ph)
    borate = float(weak.get('boron', {}).get('B(OH)4-', 0.0))
    phosphate_alk = _phosphate_alkalinity(weak)
    ta_other = borate + oh - h + phosphate_alk
    ta = hco3 + 2.0*co3 + ta_other
    pg = pit['gamma'] if pit else {}
    kgw = _kg_water_per_l(base, temp_c)
    comp_eq = dict(base)
    comp_eq['bicarbonate'] = hco3*kgw*SPECIES['bicarbonate'][2]*1000.0
    comp_eq['carbonate'] = co3*kgw*SPECIES['carbonate'][2]*1000.0
    return {
        'ph': ph, 'total_alkalinity_mol_kg': ta,
        'total_alkalinity_mg_l_as_hco3': _ta_mg_l_as_hco3(ta, base, temp_c),
        'ta_min_mol_kg': ta_other,
        'ta_min_mg_l_as_hco3': _ta_mg_l_as_hco3(ta_other, base, temp_c),
        'total_inorganic_carbon_mol_kg': ct,
        'co2_mol_kg': co2, 'hco3_mol_kg': hco3, 'co3_mol_kg': co3,
        'co2_mg_l': co2*kgw*CO2_MW*1000.0,
        'hco3_mg_l': comp_eq['bicarbonate'], 'co3_mg_l': comp_eq['carbonate'],
        'h_mol_kg': h, 'oh_mol_kg': oh,
        'gamma_hco3': float(pg.get('HCO3', 1.0)),
        'gamma_co3': float(pg.get('CO3', 1.0)),
        'gamma_h': float(pg.get('H', 1.0)), 'gamma_oh': float(pg.get('OH', 1.0)),
        'a_hco3': hco3*float(pg.get('HCO3', 1.0)),
        'a_co3': co3*float(pg.get('CO3', 1.0)),
        'pitzer': pit, 'weak_systems': weak, 'composition': comp_eq,
    }


def solve_carbonate_state(comp: Mapping[str, float], temp_c: float=25.0, *, ph: float|None=None,
                           total_alkalinity_mol_kg: float|None=None,
                           total_inorganic_carbon_mol_kg: float|None=None) -> dict:
    """Given any two of {pH, TA, CT}, solve and return the complete carbonate state.

    * pH + TA -> CT (feed and fixed-pH charge balancing)
    * TA + CT -> pH using bounded bisection on pH 2..12 (acid/concentrate/permeate)
    * pH + CT -> TA (diagnostics and conservation checks)
    """
    known = sum(x is not None for x in (ph, total_alkalinity_mol_kg, total_inorganic_carbon_mol_kg))
    if known != 2:
        raise ValueError('Carbonate state requires exactly two of pH, total alkalinity (TA), and total inorganic carbon (CT).')
    analytical = _analytical_composition(comp)
    if ph is not None and total_inorganic_carbon_mol_kg is not None:
        return _state_at_ph_ct(analytical, temp_c, float(ph), max(0.0, float(total_inorganic_carbon_mol_kg)))
    if ph is not None and total_alkalinity_mol_kg is not None:
        phv = float(ph); target = float(total_alkalinity_mol_kg)
        # CT is monotonic at fixed pH.  Use a safeguarded bracketed root rather
        # than the former relaxed fixed-point loop.  The chemistry equations and
        # tolerances are unchanged; this only reduces repeated Pitzer evaluations.
        states = {}
        def state_at_ct(ct_value):
            key = float(ct_value)
            if key not in states:
                states[key] = _state_at_ph_ct(analytical, temp_c, phv, max(0.0, key))
            return states[key]
        probe = state_at_ct(0.0)
        if target < probe['ta_min_mol_kg'] - 1e-12:
            raise ValueError(
                f'Total alkalinity is below the physical minimum at fixed pH {phv:.2f}. '
                f'Minimum is {probe["ta_min_mg_l_as_hco3"]:.3f} mg/L as HCO3-equivalent; '
                'select another balancing ion or review the analysis.'
            )
        f0 = probe['total_alkalinity_mol_kg'] - target
        if abs(f0) <= 1e-12:
            return probe
        hi = max(target-probe['ta_min_mol_kg'], 1e-9)
        def residual_ct(ct_value):
            return state_at_ct(ct_value)['total_alkalinity_mol_kg'] - target
        fhi = residual_ct(hi)
        for _ in range(24):
            if f0*fhi <= 0:
                break
            hi *= 2.0
            fhi = residual_ct(hi)
        if f0*fhi > 0:
            raise ValueError('Could not bracket inorganic carbon at the supplied fixed pH and alkalinity.')
        ct_root, _ = brent_root(residual_ct, 0.0, hi, xtol=1e-12, rtol=1e-10, max_iter=60)
        return state_at_ct(ct_root)
    # TA + CT -> pH.  Brent-Dekker is bracketed and safeguarded like bisection,
    # but normally needs far fewer full activity/Pitzer evaluations.
    target = float(total_alkalinity_mol_kg)
    ct = max(0.0, float(total_inorganic_carbon_mol_kg))
    lo, hi = CARBONATE_PH_MIN, CARBONATE_PH_MAX
    states = {}
    def state_at_ph(ph_value):
        key = float(ph_value)
        if key not in states:
            states[key] = _state_at_ph_ct(analytical, temp_c, key, ct)
        return states[key]
    def residual_ph(ph_value):
        return state_at_ph(ph_value)['total_alkalinity_mol_kg'] - target
    flo = residual_ph(lo); fhi = residual_ph(hi)
    if flo == 0: return state_at_ph(lo)
    if fhi == 0: return state_at_ph(hi)
    if flo*fhi > 0:
        raise ValueError(
            f'Could not bracket carbonate pH between {CARBONATE_PH_MIN:.0f} and {CARBONATE_PH_MAX:.0f} '
            'for the supplied TA and CT. Review alkalinity/carbon inputs.'
        )
    ph_root, _ = brent_root(residual_ph, lo, hi, xtol=1e-8, rtol=1e-10, max_iter=60)
    return state_at_ph(ph_root)



def membrane_carbonate_split(feed_comp: Mapping[str,float], temp_c:float, feed_state:dict,
                              recovery:float, ionic_rejection:float,
                              permeate_template:Mapping[str,float], concentrate_template:Mapping[str,float]) -> dict:
    """Conserve TA and CT across an RO stage while allowing CO2 to pass freely.

    TA is transported with the ionic salt-passage fraction; neutral CO2 is
    assigned unit passage. The downstream permeate and concentrate pH values
    are then solved from TA + CT with the same bounded carbonate solver.
    """
    y=min(max(float(recovery),0.0),0.999999999)
    rej=min(max(float(ionic_rejection),0.0),0.999999999)
    fcomp=feed_state.get('composition') or normalize_composition(feed_comp)
    kgwf=_kg_water_per_l(fcomp,temp_c)
    ta_l=feed_state['total_alkalinity_mol_kg']*kgwf
    ct_l=feed_state['total_inorganic_carbon_mol_kg']*kgwf
    co2_l=feed_state['co2_mol_kg']*kgwf
    # Ionic alkalinity/carbon follows salt passage; neutral CO2 passes freely.
    ta_p_l=ta_l*(1.0-rej)
    ct_p_l=co2_l + max(0.0,ct_l-co2_l)*(1.0-rej)
    if y<=1e-12:
        ta_c_l,ct_c_l=ta_l,ct_l
    else:
        ta_c_l=(ta_l-y*ta_p_l)/max(1.0-y,1e-30)
        ct_c_l=(ct_l-y*ct_p_l)/max(1.0-y,1e-30)
    pbase=_base_noncarbonate_composition(permeate_template)
    cbase=_base_noncarbonate_composition(concentrate_template)
    kgwp=_kg_water_per_l(pbase,temp_c); kgwc=_kg_water_per_l(cbase,temp_c)
    ta_p=ta_p_l/max(kgwp,1e-30); ct_p=ct_p_l/max(kgwp,1e-30)
    ta_c=ta_c_l/max(kgwc,1e-30); ct_c=ct_c_l/max(kgwc,1e-30)
    pst=solve_carbonate_state(pbase,temp_c,total_alkalinity_mol_kg=ta_p,total_inorganic_carbon_mol_kg=ct_p)
    cst=solve_carbonate_state(cbase,temp_c,total_alkalinity_mol_kg=ta_c,total_inorganic_carbon_mol_kg=ct_c)
    return {'feed':feed_state,'permeate':pst,'concentrate':cst,'ionic_rejection':rej,'recovery':y}


def mix_carbonate_streams(streams, temp_c:float) -> dict:
    """Flow-weight carbonate states and solve the mixed-stream pH from TA + CT."""
    valid=[x for x in streams if float(x.get('flow',0) or 0)>0 and x.get('composition') and x.get('state')]
    if not valid: raise ValueError('At least one positive-flow carbonate stream is required for mixing.')
    qt=sum(float(x['flow']) for x in valid)
    mix={k:0.0 for k in SPECIES}
    ta_l=ct_l=0.0
    for x in valid:
        q=float(x['flow']); comp=normalize_composition(x['composition']); st=x['state']; kgw=_kg_water_per_l(comp,temp_c)
        for k in SPECIES: mix[k]+=q*comp[k]/qt
        ta_l+=q*float(st['total_alkalinity_mol_kg'])*kgw/qt
        ct_l+=q*float(st['total_inorganic_carbon_mol_kg'])*kgw/qt
    base=_base_noncarbonate_composition(mix); kgw=_kg_water_per_l(base,temp_c)
    st=solve_carbonate_state(base,temp_c,total_alkalinity_mol_kg=ta_l/max(kgw,1e-30),total_inorganic_carbon_mol_kg=ct_l/max(kgw,1e-30))
    return st

def carbonate_speciation(comp: Mapping[str,float], temp_c:float, ph:float, source_ph:float|None=None) -> dict:
    """Compatibility wrapper: analytical bicarbonate is TA; carbonate is QC only."""
    analytical = _analytical_composition(comp)
    ta = _ta_mol_kg_from_mg_l_as_hco3(analytical, temp_c)
    st = solve_carbonate_state(analytical, temp_c, ph=float(ph), total_alkalinity_mol_kg=ta)
    return {
        'composition': st['composition'],
        'analytical_composition': analytical,
        'total_alkalinity_mol_kg': st['total_alkalinity_mol_kg'],
        'total_alkalinity_mg_l_as_hco3': st['total_alkalinity_mg_l_as_hco3'],
        'total_inorganic_carbon_mol_kg': st['total_inorganic_carbon_mol_kg'],
        'co2_mol_kg': st['co2_mol_kg'], 'hco3_mol_kg': st['hco3_mol_kg'], 'co3_mol_kg': st['co3_mol_kg'],
        'co2_mg_l': st['co2_mg_l'], 'hco3_mg_l': st['hco3_mg_l'], 'co3_mg_l': st['co3_mg_l'],
        'ta_min_mol_kg': st['ta_min_mol_kg'], 'ta_min_mg_l_as_hco3': st['ta_min_mg_l_as_hco3'],
        'pitzer': st['pitzer'], 'weak_systems': st['weak_systems'],
    }


def _equilibrated_charge_report(comp: Mapping[str,float], temp_c:float, ph:float):
    analytical = _analytical_composition(comp)
    ta = _ta_mol_kg_from_mg_l_as_hco3(analytical, temp_c)
    st = solve_carbonate_state(analytical, temp_c, ph=float(ph), total_alkalinity_mol_kg=ta)
    return st, charge_report(st['composition'])


def balance_composition(comp: Mapping[str,float], ion_key: str, temp_c:float=25.0, ph:float=8.0) -> dict:
    """Balance at fixed pH; alkalinity balance is re-speciated at every trial."""
    allowed = ('sodium','chloride','calcium','magnesium','sulfate','alkalinity')
    if ion_key not in allowed:
        raise ValueError('Balancing choice must be sodium, chloride, calcium, magnesium, sulfate, or alkalinity.')
    c = _analytical_composition(comp)
    st0, r0 = _equilibrated_charge_report(c, temp_c, ph)
    diff0 = r0['cations_meq_l'] - r0['anions_meq_l']
    if abs(diff0) < 1e-10:
        return {'composition':c,'equilibrium_composition':st0['composition'],'adjustment_mg_l':0.0,'ion':ion_key,'charge_before':r0,'charge_after':r0,'ph_held_constant':float(ph)}

    def charge_diff(test_comp):
        st, rep = _equilibrated_charge_report(test_comp, temp_c, ph)
        return rep['cations_meq_l']-rep['anions_meq_l'], st, rep

    if ion_key == 'alkalinity':
        ta0 = _ta_mol_kg_from_mg_l_as_hco3(c, temp_c)
        # The true lower bound is TA_min at fixed pH, which may be negative.
        zero_ct = solve_carbonate_state(c, temp_c, ph=float(ph), total_inorganic_carbon_mol_kg=0.0)
        ta_min = zero_ct['total_alkalinity_mol_kg']
        if diff0 > 0:  # excess cations -> increase alkalinity
            lo, hi = ta0, max(ta0+abs(diff0)/1000.0, ta0+1e-6)
            for _ in range(30):
                tc=dict(c); tc['bicarbonate']=_ta_mg_l_as_hco3(hi, c, temp_c)
                d,_,_=charge_diff(tc)
                if d <= 0: break
                hi = ta0 + 2*(hi-ta0)
            else: raise ValueError('Could not bracket an alkalinity addition that closes the charge balance.')
        else:  # excess anions -> remove alkalinity, but never below CT>=0 bound
            lo, hi = ta_min, ta0
            tc=dict(c); tc['bicarbonate']=_ta_mg_l_as_hco3(lo, c, temp_c)
            dmin,_,_=charge_diff(tc)
            if dmin < 0:
                raise ValueError(
                    'Analysis cannot be charge-balanced using alkalinity at the specified pH. '
                    'Required alkalinity would fall below the physical CT ≥ 0 limit; select another balancing ion or review the analysis.'
                )
        best=None
        for _ in range(80):
            mid=0.5*(lo+hi); tc=dict(c); tc['bicarbonate']=_ta_mg_l_as_hco3(mid, c, temp_c)
            d,st,rep=charge_diff(tc); best=(tc,st,rep,mid,d)
            if abs(d)<1e-11: break
            # charge difference decreases as TA increases
            if d>0: lo=mid
            else: hi=mid
        tc,st,rep,ta1,_=best
        return {'composition':tc,'equilibrium_composition':st['composition'],'adjustment_mg_l':tc['bicarbonate']-c['bicarbonate'],
                'ion':'alkalinity','charge_before':r0,'charge_after':rep,'ph_held_constant':float(ph),
                'ta_before_mg_l_as_hco3':c['bicarbonate'],'ta_after_mg_l_as_hco3':tc['bicarbonate'],
                'ta_min_mg_l_as_hco3':zero_ct['ta_min_mg_l_as_hco3']}

    z = SPECIES[ion_key][3]
    if diff0>0 and z>0: raise ValueError('The analysis has excess cation charge; select chloride, sulfate, or alkalinity.')
    if diff0<0 and z<0: raise ValueError('The analysis has excess anion charge; select sodium, calcium, magnesium, or reduce alkalinity.')
    lo, hi = 0.0, max(abs(diff0)*SPECIES[ion_key][2]/max(abs(z),1), 1e-6)
    for _ in range(30):
        tc=dict(c); tc[ion_key]=c[ion_key]+hi
        d,_,_=charge_diff(tc)
        if d*diff0 <= 0: break
        hi *= 2.0
    else: raise ValueError(f'Could not bracket a {ion_key} adjustment that closes the charge balance.')
    best=None
    for _ in range(80):
        mid=0.5*(lo+hi); tc=dict(c); tc[ion_key]=c[ion_key]+mid
        d,st,rep=charge_diff(tc); best=(tc,st,rep,mid,d)
        if abs(d)<1e-11: break
        if d*diff0>0: lo=mid
        else: hi=mid
    tc,st,rep,delta,_=best
    return {'composition':tc,'equilibrium_composition':st['composition'],'adjustment_mg_l':delta,'ion':ion_key,
            'charge_before':r0,'charge_after':rep,'ph_held_constant':float(ph)}

def analyze_ui_payload(payload: Mapping[str, object]) -> dict:
    """Run the exact chemistry mapping used by the UI/API payload."""
    comp={}
    for k in SPECIES:
        v=payload.get('ion_'+k,payload.get(k,0.0))
        v=0.0 if v in (None,'') else float(v)
        comp[k]=v if k=='bicarbonate' else max(0.0,v)
    return analyze_water(comp,float(payload.get('temperature_c',25.0)),float(payload.get('feed_ph',8.0)),
                         payload.get('source_ph'),payload.get('reported_tds'))


def analyze_water(comp:Mapping[str,float], temp_c:float=25.0, ph:float=8.0, source_ph:float|None=None, reported_tds:float|None=None) -> dict:
    # 1) Feed analytical basis: pH + TOTAL ALKALINITY -> CT and equilibrium species.
    # ``bicarbonate`` in the analytical payload is mg/L as HCO3-equivalent TA.
    # ``carbonate`` is lab-reported QC only and never drives equilibrium.
    analytical=_analytical_composition(comp)
    ta_input=_ta_mol_kg_from_mg_l_as_hco3(analytical,temp_c)
    carb_state=solve_carbonate_state(analytical,temp_c,ph=float(ph),total_alkalinity_mol_kg=ta_input)
    c=carb_state['composition']; m=_molalities(c,temp_c); weak=weak_species_speciation(c,temp_c,ph)
    # 2) Davies carbonate/water activity iteration.
    I=.5*sum(m[k]*SPECIES[k][3]**2 for k in SPECIES if SPECIES[k][3])
    g1=_davies_gamma(1,I);g2=_davies_gamma(2,I);g3=_davies_gamma(3,I); gn=_davies_gamma(0,I)
    h_activity=10**(-float(ph)); h=h_activity/max(g1,1e-30); kw=10**_logk('Kw',temp_c); oh=kw/(h_activity*max(g1,1e-30))
    # activities and a lightweight free-ion association correction using workbook constants.
    free=dict(m)
    hco3=m['bicarbonate']; co3=m['carbonate']; so4=m['sulfate']; fl=m['fluoride']
    for _ in range(20):
        old=free.copy()
        def denom(metal):
            K=lambda n:10**PAIR_LOGK[n]
            d=1.0
            key={'calcium':'Ca','magnesium':'Mg','sodium':'Na','potassium':'K','strontium':'Sr','barium':'Ba','iron_ii':'Fe','manganese_ii':'Mn'}[metal]
            if key in HYDRO_LOGK:d+=10**HYDRO_LOGK[key]*max(oh,0)/max(h,1e-30)
            for suffix,val in [('CO3',free.get('carbonate',co3)),('HCO3',free.get('bicarbonate',hco3)),('SO4',free.get('sulfate',so4)),('F',free.get('fluoride',fl))]:
                name=key+suffix
                if name in PAIR_LOGK:
                    # HCO3 workbook formation reaction includes H+ with carbonate; use direct HCO3 effective form here.
                    d+=K(name)*val*(h if suffix=='HCO3' else 1.0)
            return max(d,1.0)
        for metal in ('calcium','magnesium','sodium','potassium','strontium','barium','iron_ii','manganese_ii'):
            free[metal]=m.get(metal,0)/denom(metal)
        # approximate anion depletion from dominant pairs; mass-balance iteration.
        so4_bound=sum(max(0,m.get(k,0)-free.get(k,m.get(k,0))) for k in ('calcium','magnesium','sodium','potassium','strontium','barium'))*.25
        free['sulfate']=max(0,m['sulfate']-min(m['sulfate']*.95,so4_bound))
        free['carbonate']=m['carbonate']/max(1.0,1+50*(free.get('calcium',0)+free.get('magnesium',0)))
        free['bicarbonate']=m['bicarbonate']/max(1.0,1+0.5*(free.get('calcium',0)+free.get('magnesium',0)))
        free['fluoride']=m['fluoride']/max(1.0,1+10*(free.get('calcium',0)+free.get('magnesium',0)))
        if sum(abs(free[k]-old.get(k,0)) for k in free)<1e-12:break
    gammas={k:_davies_gamma(SPECIES[k][3],I) for k in SPECIES}
    act={k:max(0,free.get(k,m.get(k,0)))*gammas[k] for k in SPECIES}
    act['H']=h_activity;act['OH']=oh*g1
    # Pitzer total-ion track.
    sto={'H':h,'Na':m['sodium'],'K':m['potassium'],'Ca':m['calcium'],'Mg':m['magnesium'],'Sr':m['strontium'],'Ba':m['barium'],'OH':oh,'Cl':m['chloride'],'SO4':m['sulfate'],'HCO3':m['bicarbonate'],'CO3':m['carbonate'],'NO3':m['nitrate'],'F':m['fluoride']}
    pit=pitzer_gammas(sto); pg=pit['gamma']; pact={x:sto[x]*pg[x] for x in sto}
    # Silica acid/base split on Davies track.
    h4=weak['silica']['H4SiO4']; h3=weak['silica']['H3SiO4-']; a_h4=h4*gn
    # Indices.
    pK2=-_logk('K2',temp_c); pKsp=-_mineral_logk('Calcite',temp_c)
    ca_total=max(m['calcium'],1e-30); alk_m=max(carb_state['total_alkalinity_mol_kg'],1e-30)
    alk_caco3=alk_m*50000*_kg_water_per_l(c,temp_c)
    ca_hard=m['calcium']*50000*_kg_water_per_l(c,temp_c)
    pHs=pK2-pKsp-log10(max(ca_total*g2,1e-30))-log10(max(alk_m*g1,1e-30))
    lsi=float(ph)-pHs
    calcite_si=log10(max(act['calcium']*act['carbonate'],1e-300))-_mineral_logk('Calcite',temp_c)
    rsi=2*pHs-float(ph)
    pHeq=1.465*log10(max(alk_caco3,1e-30))+4.54; psi=2*pHs-pHeq
    Ksd=pK2-pKsp-log10(max(pg['Ca'],1e-30))-log10(max(pg['HCO3'],1e-30))
    sdsi=float(ph)-(-log10(max(m['calcium'],1e-30)))-(-log10(max(alk_m,1e-30)))-Ksd
    cr=charge_report(c); larson=(cr['rows'][0]['meq_l']*0) # placeholder overwritten below
    meq={x['key']:x['meq_l'] for x in cr['rows']}
    larson=(meq.get('chloride',0)+meq.get('sulfate',0))/max(meq.get('bicarbonate',0)+meq.get('carbonate',0),1e-30)
    aggressive=float(ph)+log10(max(alk_caco3*ca_hard,1e-30))
    csmr=c['chloride']/max(c['sulfate'],1e-30)
    indices=[
        {'name':'LSI — Langelier Saturation Index','track':'A (Davies)','value':lsi,'definition':'pH − pHs, total Ca and alkalinity, Davies γ'},
        {'name':'LSI — rigorous (= calcite SI, free ions)','track':'A (speciated)','value':calcite_si,'definition':'log10(aCa · aCO3 / Ksp)'},
        {'name':'RSI — Ryznar Stability Index','track':'A (Davies)','value':rsi,'definition':'2·pHs − pH'},
        {'name':'S&DSI — Stiff & Davis Stability Index','track':'B (Pitzer)','value':sdsi,'definition':'pH − pCa − pAlk − K; K from Pitzer γ'},
        {'name':'PSI — Puckorius Scaling Index','track':'A (Davies)','value':psi,'definition':'2·pHs − pHeq'},
        {'name':'Larson–Skold Index','track':'—','value':larson,'definition':'(Cl + SO4)/(HCO3 + CO3), meq basis'},
        {'name':'Aggressive Index (AI)','track':'—','value':aggressive,'definition':'pH + log10(alkalinity × Ca hardness as CaCO3)'},
        {'name':'Chloride / sulfate mass ratio (CSMR)','track':'—','value':csmr,'definition':'mg/L Cl ÷ mg/L SO4'},
    ]
    # Mineral saturation; Track B uses total-ion Pitzer activities where supported.
    minerals=[]
    def aA(key):return max(act.get(key,0),1e-300)
    def aP(key):return max(pact.get(key,0),1e-300)
    for name,(formula,_,_,_,nu) in MINERALS.items():
        lk=_mineral_logk(name,temp_c); logA=logB=None
        if formula in ('CaCO3',): logA=log10(aA('calcium'))+log10(aA('carbonate')); logB=log10(aP('Ca'))+log10(aP('CO3'))
        elif formula=='CaMg(CO3)2': logA=log10(aA('calcium'))+log10(aA('magnesium'))+2*log10(aA('carbonate')); logB=log10(aP('Ca'))+log10(aP('Mg'))+2*log10(aP('CO3'))
        elif formula=='MgCO3': logA=log10(aA('magnesium'))+log10(aA('carbonate'));logB=log10(aP('Mg'))+log10(aP('CO3'))
        elif formula.startswith('CaSO4'): logA=log10(aA('calcium'))+log10(aA('sulfate'));logB=log10(aP('Ca'))+log10(aP('SO4'))
        elif formula=='BaSO4': logA=log10(aA('barium'))+log10(aA('sulfate'));logB=log10(aP('Ba'))+log10(aP('SO4'))
        elif formula=='SrSO4': logA=log10(aA('strontium'))+log10(aA('sulfate'));logB=log10(aP('Sr'))+log10(aP('SO4'))
        elif formula=='BaCO3': logA=log10(aA('barium'))+log10(aA('carbonate'));logB=log10(aP('Ba'))+log10(aP('CO3'))
        elif formula=='SrCO3': logA=log10(aA('strontium'))+log10(aA('carbonate'));logB=log10(aP('Sr'))+log10(aP('CO3'))
        elif formula=='CaF2': logA=log10(aA('calcium'))+2*log10(aA('fluoride'));logB=log10(aP('Ca'))+2*log10(aP('F'))
        elif formula=='MgF2': logA=log10(aA('magnesium'))+2*log10(aA('fluoride'));logB=log10(aP('Mg'))+2*log10(aP('F'))
        elif formula=='SiO2': logA=log10(max(a_h4,1e-300))
        elif formula=='Mg(OH)2': logA=log10(aA('magnesium'))+2*log10(max(act['OH'],1e-300));logB=log10(aP('Mg'))+2*log10(max(pact['OH'],1e-300))
        elif formula=='FeCO3': logA=log10(aA('iron_ii'))+log10(aA('carbonate'))
        elif formula=='MnCO3': logA=log10(aA('manganese_ii'))+log10(aA('carbonate'))
        elif formula=='NaCl': logA=log10(aA('sodium'))+log10(aA('chloride'));logB=log10(aP('Na'))+log10(aP('Cl'))
        elif formula=='Fe(OH)3(a)': logA=log10(aA('iron_iii'))+3*log10(max(act['OH'],1e-300))
        elif formula=='Ca5(PO4)3OH': logA=5*log10(aA('calcium'))+3*log10(max(weak['phosphate']['PO4---']*g3,1e-300))+log10(max(act['OH'],1e-300))
        if logA is None: continue
        siA=logA-lk; siB=(logB-lk) if logB is not None else None; governing=siB if siB is not None else siA
        omega=10**governing if -300<governing<300 else (0.0 if governing<0 else float('inf'))
        conc_sat=100*(omega**(1/nu)) if omega!=float('inf') else float('inf')
        minerals.append({'name':name,'formula':formula,'log_ksp':lk,'si_track_a':siA,'si_track_b':siB,'omega':omega,'iap_saturation_pct':100*omega if omega!=float('inf') else float('inf'),'concentration_saturation_pct':conc_sat,'governing_track':'B (Pitzer)' if siB is not None else 'A (Davies/speciated)'})
    osm=osmotic_state_from_composition(c,temp_c,float(ph))
    calc_tds=sum(c.values())
    reported=calc_tds if reported_tds is None else max(0.0,float(reported_tds))
    tds_diff=reported-calc_tds
    return {'composition':c,'charge':cr,'tds_sum_mg_l':calc_tds,'reported_tds_mg_l':reported,
            'tds_difference_mg_l':tds_diff,'tds_difference_pct':(0.0 if reported<=1e-12 else 100.0*tds_diff/reported),
            'temperature_c':float(temp_c),'ph':float(ph),'ionic_strength_mol_kg':I,
            'davies_gamma':{'z1':g1,'z2':g2,'z3':g3,'neutral':gn},'pitzer':pit,
            'analytical_composition':analytical,
            'analytical_alkalinity_mg_l_as_hco3':analytical['bicarbonate'],
            'reported_carbonate_mg_l':analytical['carbonate'],
            'carbonate_qc':{'reported_mg_l':analytical['carbonate'],'calculated_mg_l':carb_state['co3_mg_l'],
                            'difference_pct':(None if analytical['carbonate']<=0 else 100.0*(analytical['carbonate']-carb_state['co3_mg_l'])/carb_state['co3_mg_l']),
                            'warning':bool(analytical['carbonate']>0 and abs(analytical['carbonate']-carb_state['co3_mg_l'])/max(carb_state['co3_mg_l'],1e-30)>0.20)},
            'speciation':{'total_alkalinity_mol_kg':carb_state['total_alkalinity_mol_kg'],
                          'total_alkalinity_mg_l_as_hco3':carb_state['total_alkalinity_mg_l_as_hco3'],
                          'ta_min_mol_kg':carb_state['ta_min_mol_kg'],'ta_min_mg_l_as_hco3':carb_state['ta_min_mg_l_as_hco3'],
                          'total_inorganic_carbon_mol_kg':carb_state['total_inorganic_carbon_mol_kg'],
                          'co2_mol_kg':carb_state['co2_mol_kg'],'co2_mg_l':carb_state['co2_mg_l'],
                          'hco3_mol_kg':m['bicarbonate'],'hco3_mg_l':carb_state['hco3_mg_l'],
                          'co3_mol_kg':m['carbonate'],'co3_mg_l':carb_state['co3_mg_l'],'oh_mol_kg':oh,'h_mol_kg':h,
                          'free_mol_kg':free,'activities':act,'weak_systems':weak},
            'indices':indices,'minerals':minerals,'alkalinity_as_caco3_mg_l':alk_caco3,
            'calcium_hardness_as_caco3_mg_l':ca_hard,'osmotic':osm,
            'basis_note':'Osmotic pressure uses the existing validated CalcOsPower osmotic model unchanged. Carbonate chemistry uses pH + total alkalinity (mg/L as HCO3-equivalent) with activity-consistent K1/K2 speciation; lab-reported carbonate is QC only. Scaling/speciation remains a separate Davies + workbook-parameterized Pitzer activity track.'}


def acid_dose_to_target_ph(comp: Mapping[str, float], temp_c: float, feed_ph: float, target_ph: float,
                           acid_type: str = 'hcl', solution_strength_pct: float | None = None,
                           solution_density_kg_l: float | None = None, reference_flow_m3h: float | None = None) -> dict:
    """Dose HCl or H2SO4 to a target pH while conserving inorganic carbon.

    The analytical bicarbonate field is CalcOsPower total alkalinity expressed as
    HCO3-equivalent. Strong-acid equivalents lower TA; CT is conserved (closed CO2
    system), and the acid counter-ion is added to the analytical composition before
    the final activity-consistent carbonate state is solved.
    """
    acid = str(acid_type or '').strip().lower().replace('₂','2').replace('₄','4')
    aliases = {'hydrochloric':'hcl','hydrochloric acid':'hcl','sulfuric':'h2so4','sulphuric':'h2so4',
               'sulfuric acid':'h2so4','sulphuric acid':'h2so4'}
    acid = aliases.get(acid, acid)
    if acid not in {'hcl','h2so4'}:
        raise ValueError('Acid type must be HCl or H2SO4.')
    feed_ph = float(feed_ph); target_ph = float(target_ph); temp_c = float(temp_c)
    if not (2.0 <= target_ph <= 12.0):
        raise ValueError('Target pH must be between 2 and 12.')
    if target_ph > feed_ph + 1e-9:
        raise ValueError('Acid dosing target pH must be at or below the current feed pH.')
    analytical = _analytical_composition(comp)
    feed_ta = analytical_alkalinity_mol_kg(analytical, temp_c)
    feed_state = solve_carbonate_state(analytical, temp_c, ph=feed_ph, total_alkalinity_mol_kg=feed_ta)
    ct = float(feed_state['total_inorganic_carbon_mol_kg'])
    if abs(target_ph-feed_ph) < 1e-9:
        target_state = feed_state
        acid_eq_kg = 0.0
        dosed = dict(analytical)
    else:
        acid_eq_guess = max(0.0, feed_ta - solve_carbonate_state(
            analytical, temp_c, ph=target_ph, total_inorganic_carbon_mol_kg=ct
        )['total_alkalinity_mol_kg'])
        dosed = dict(analytical)
        # Counter-ion addition changes ionic strength, so solve the dose
        # self-consistency with a safeguarded Brent root instead of relaxed
        # fixed-point iteration. The chemistry equations themselves are unchanged.
        def _dose_state(eq_kg):
            trial = dict(analytical)
            kgw_l = _kg_water_per_l(trial, temp_c)
            eq_l = max(0.0,float(eq_kg)) * kgw_l
            if acid == 'hcl':
                mol_l = eq_l
                trial['chloride'] = analytical['chloride'] + mol_l * 35.453 * 1000.0
            else:
                mol_l = eq_l / 2.0
                trial['sulfate'] = analytical['sulfate'] + mol_l * 96.06 * 1000.0
            st = solve_carbonate_state(trial, temp_c, ph=target_ph, total_inorganic_carbon_mol_kg=ct)
            required = max(0.0, feed_ta - float(st['total_alkalinity_mol_kg']))
            return trial, st, required
        def _dose_residual(eq_kg):
            return float(eq_kg) - _dose_state(eq_kg)[2]
        lo=0.0; hi=max(feed_ta*1.5,acid_eq_guess*2.0,1e-8)
        flo=_dose_residual(lo); fhi=_dose_residual(hi)
        for _ in range(12):
            if flo*fhi <= 0: break
            hi*=2.0; fhi=_dose_residual(hi)
        if flo*fhi <= 0:
            acid_eq_kg, _acid_root_iterations = brent_root(_dose_residual,lo,hi,xtol=1e-12,rtol=1e-10,max_iter=60)
        else:
            # Extremely unusual chemistry: preserve the previous physical estimate
            # instead of failing acid dosing only because the numerical bracket is poor.
            acid_eq_kg=acid_eq_guess; _acid_root_iterations=0
        dosed, target_state, _ = _dose_state(acid_eq_kg)
        kgw_l = _kg_water_per_l(dosed, temp_c)
        eq_l = acid_eq_kg * kgw_l
        mol_acid_l = eq_l if acid == 'hcl' else eq_l/2.0
        mw = 36.46094 if acid == 'hcl' else 98.07848
        pure_mg_l = mol_acid_l * mw * 1000.0
        # Analytical TA is stored as HCO3-equivalent, not equilibrium HCO3 species.
        dosed['bicarbonate'] = float(target_state['total_alkalinity_mg_l_as_hco3'])
        dosed['carbonate'] = 0.0

    if abs(target_ph-feed_ph) < 1e-9:
        pure_mg_l = 0.0
        mol_acid_l = 0.0
        target_state = feed_state
        dosed['bicarbonate'] = float(feed_state['total_alkalinity_mg_l_as_hco3'])
    default_strength = 32.0 if acid == 'hcl' else 93.0
    default_density = 1.16 if acid == 'hcl' else 1.83
    strength = default_strength if solution_strength_pct in (None,'') else float(solution_strength_pct)
    density = default_density if solution_density_kg_l in (None,'') else float(solution_density_kg_l)
    if not (0 < strength <= 100): raise ValueError('Commercial acid strength must be between 0 and 100 wt%.')
    if density <= 0: raise ValueError('Commercial acid solution density must be greater than zero.')
    pure_kg_m3 = pure_mg_l / 1000.0
    solution_kg_m3 = pure_kg_m3 / (strength/100.0)
    solution_l_m3 = solution_kg_m3 / density
    out = {
        'acid_type': 'HCl' if acid == 'hcl' else 'H2SO4',
        'feed_ph': feed_ph, 'target_ph': target_ph, 'resulting_ph': float(target_state['ph']),
        'acid_equivalents_mmol_l': mol_acid_l * (1.0 if acid == 'hcl' else 2.0) * 1000.0,
        'pure_acid_mg_l': pure_mg_l, 'pure_acid_kg_m3': pure_kg_m3,
        'solution_strength_pct': strength, 'solution_density_kg_l': density,
        'commercial_solution_kg_m3': solution_kg_m3, 'commercial_solution_l_m3': solution_l_m3,
        'feed_alkalinity_mg_l_as_hco3': float(feed_state['total_alkalinity_mg_l_as_hco3']),
        'resulting_alkalinity_mg_l_as_hco3': float(target_state['total_alkalinity_mg_l_as_hco3']),
        'total_inorganic_carbon_mol_kg': ct, 'composition': dosed,
        'chloride_added_mg_l': max(0.0, dosed['chloride']-analytical['chloride']),
        'sulfate_added_mg_l': max(0.0, dosed['sulfate']-analytical['sulfate']),
        'basis_note': 'Strong-acid engineering dose with closed-system inorganic-carbon conservation; H2SO4 is treated as two acid equivalents per mole at normal RO pretreatment pH.'
        ,'dose_solver':'Brent safeguarded root','dose_solver_iterations':int(locals().get('_acid_root_iterations',0))
    }
    if reference_flow_m3h not in (None,''):
        q = float(reference_flow_m3h)
        if q <= 0: raise ValueError('Reference feed flow must be greater than zero when provided.')
        out['reference_flow_m3h'] = q
        out['pure_acid_kg_h'] = pure_kg_m3*q
        out['pure_acid_kg_d'] = pure_kg_m3*q*24.0
        out['commercial_solution_kg_h'] = solution_kg_m3*q
        out['commercial_solution_l_h'] = solution_l_m3*q
    return out
