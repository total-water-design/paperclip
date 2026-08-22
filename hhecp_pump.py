"""Horizontal High Efficiency Centrifugal Pump (HHECP) database adapter."""
from __future__ import annotations
import json, math
from pathlib import Path

G = 9.80665
ROOT = Path(__file__).resolve().parent
MAX_DP_BAR = 82.0

def _load():
    models, regs = [], []
    for path in sorted((ROOT / "data").glob("hhecp_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        models.extend(data.get("exact_models", []))
        regs.extend(data.get("regressions", []))
    return models, regs

EXACT_MODELS, REGRESSIONS = _load()
REG = {(r["model"], r["metric"]): r for r in REGRESSIONS}

def _poly(coeff, x):
    c=[float(v or 0.0) for v in coeff]; x=float(x)
    return ((c[3]*x+c[2])*x+c[1])*x+c[0]

def _bar_to_head(dp, rho):
    return float(dp)*100000.0/max(float(rho)*G,1e-12)

def _head_to_bar(head, rho):
    return float(rho)*G*float(head)/100000.0

def _model_code(nominal, stages):
    return f"HHECP-{int(nominal)}{int(stages):02d}"

def _expand():
    families={}
    for row in EXACT_MODELS:
        families.setdefault(int(row["nominal_flow_m3h"]),[]).append(row)
    out=[]
    for nominal, rows in sorted(families.items()):
        parent=max(rows,key=lambda r:(int(r["stages"]),float(r["reference_efficiency_pct"])))
        parent_stages=int(parent["stages"])
        dp_per_stage=float(parent["reference_dp_bar"])/parent_stages
        max_stage=max(1,int(math.ceil(MAX_DP_BAR/dp_per_stage)))
        exact_by_stage={int(r["stages"]):r for r in rows}
        for stages in range(1,max_stage+1):
            code=_model_code(nominal,stages)
            if stages in exact_by_stage:
                src=exact_by_stage[stages]; source=src["model"]; ratio=1.0; basis="original_digitized"
                model=dict(src)
            else:
                src=parent; source=parent["model"]; ratio=stages/parent_stages; basis="stage_derived"
                model=dict(parent)
                model["stages"]=stages
                model["reference_dp_bar"]=float(parent["reference_dp_bar"])*ratio
                model["reference_head_m"]=float(parent["reference_head_m"])*ratio
                model["reference_power_kw"]=float(parent["reference_power_kw"])*ratio
                model["pump_weight_kg"]=None
            model["model"]=code; model["_basis"]=basis; model["_parent_model"]=source; model["_stage_ratio"]=ratio
            curves={}
            for metric in ("Differential Head","Efficiency","Absorbed Power","NPSHR"):
                rr=REG[(source,metric)]
                coeff=[float(v or 0.0) for v in rr["coeff"]]
                if basis=="stage_derived" and metric in ("Differential Head","Absorbed Power"):
                    coeff=[v*ratio for v in coeff]
                curves[metric]={"coeff":coeff,"q_min":float(rr["q_min_m3h"]),"q_max":float(rr["q_max_m3h"])}
            model["_curves"]=curves
            out.append(model)
    return out

MODELS=_expand()
BY_CODE={r["model"]:r for r in MODELS}

def _solve_speed(model,q,hreq,min_ratio,max_ratio):
    coeff=model["_curves"]["Differential Head"]["coeff"]
    def h(r): return r*r*_poly(coeff,q/r)
    if h(max_ratio)+1e-9<hreq: return None
    if h(min_ratio)>=hreq: return min_ratio,h(min_ratio),True
    lo,hi=min_ratio,max_ratio
    for _ in range(60):
        mid=(lo+hi)/2
        if h(mid)>=hreq: hi=mid
        else: lo=mid
    r=(lo+hi)/2
    return r,h(r),False

def evaluate(model, flow_m3h, required_dp_bar, density_kg_m3=998.0,
             motor_eff=0.95, vfd_eff=0.98, min_vfd_hz=30.0, max_vfd_hz=60.0):
    q=float(flow_m3h); dp=float(required_dp_bar); rho=max(1.0,float(density_kg_m3))
    if q<=0 or dp<=0 or dp>MAX_DP_BAR+1e-9: return None
    rmin=float(min_vfd_hz)/60.0; rmax=float(max_vfd_hz)/60.0
    solved=_solve_speed(model,q,_bar_to_head(dp,rho),rmin,rmax)
    if solved is None: return None
    ratio,head,min_limited=solved; qref=q/max(ratio,1e-12)
    hc=model["_curves"]["Differential Head"]
    if qref<hc["q_min"]-1e-9 or qref>hc["q_max"]+1e-9: return None
    eta=_poly(model["_curves"]["Efficiency"]["coeff"],qref)/100.0
    if not (0.05<eta<=0.95) or not math.isfinite(eta): return None
    shaft=ratio**3*_poly(model["_curves"]["Absorbed Power"]["coeff"],qref)
    hyd=rho*G*(q/3600.0)*head/1000.0
    shaft=max(shaft,hyd/max(eta,1e-12))
    if not math.isfinite(shaft) or shaft<=0: return None
    wire=shaft/max(float(motor_eff)*float(vfd_eff),1e-12)
    actual_dp=_head_to_bar(head,rho)
    if actual_dp>MAX_DP_BAR+1e-6: return None
    npsh=ratio**2*_poly(model["_curves"]["NPSHR"]["coeff"],qref)
    return {
        "source_id":model["model"],"technology":"HHECP","product_family":model["model"],
        "stage_config":f'{int(model["stages"])} stages',"pump_series":"HHECP","model":model["model"],
        "nominal_flow_m3h":float(model["nominal_flow_m3h"]),"stages":int(model["stages"]),
        "data_basis":model["_basis"],"parent_model":model["_parent_model"],"flow_m3h":q,
        "required_dp_bar":dp,"actual_dp_bar":actual_dp,"required_head_m":_bar_to_head(dp,rho),
        "actual_head_m":head,"head_margin_pct":100.0*(head/max(_bar_to_head(dp,rho),1e-12)-1.0),
        "speed_ratio":ratio,"frequency_hz":60.0*ratio,"reference_rpm_60":float(model["reference_rpm"]),
        "speed_rpm":float(model["reference_rpm"])*ratio,"equivalent_flow_60hz_m3h":qref,
        "raw_efficiency":eta,"pump_efficiency":eta,"motor_efficiency":float(motor_eff),
        "vfd_efficiency":float(vfd_eff),"overall_wire_efficiency":eta*float(motor_eff)*float(vfd_eff),
        "hydraulic_kw":hyd,"shaft_kw":shaft,"wire_kw":wire,"sec_kwh_m3":wire/q,
        "npshr_m":max(0.0,npsh),"min_speed_limited":bool(min_limited),
        "min_flow_60hz_m3h":hc["q_min"],"max_flow_60hz_m3h":hc["q_max"],
    }

def select(flow_m3h, required_dp_bar, density_kg_m3=998.0, motor_eff=0.95, vfd_eff=0.98,
           min_vfd_hz=30.0, max_vfd_hz=60.0, flow_margin=0.05, head_margin=0.05,
           top_n=5, max_duty_units=10):
    q=float(flow_m3h); dp=float(required_dp_bar)
    qd=q*(1+max(0.0,float(flow_margin))); dpd=dp*(1+max(0.0,float(head_margin)))
    if dpd>MAX_DP_BAR+1e-9:
        return {"ok":False,"reason":f"HHECP design differential pressure exceeds {MAX_DP_BAR:g} bar.","options":[]}
    options=[]
    for model in MODELS:
        for units in range(1,max(1,int(max_duty_units))+1):
            if evaluate(model,qd/units,dpd,density_kg_m3,motor_eff,vfd_eff,min_vfd_hz,max_vfd_hz) is None: continue
            op=evaluate(model,q/units,dp,density_kg_m3,motor_eff,vfd_eff,min_vfd_hz,max_vfd_hz)
            if op is None: continue
            op["duty_units"]=units; op["installed_units"]=units; op["wire_kw_per_pump"]=op["wire_kw"]
            op["wire_kw"]*=units; op["hydraulic_kw"]*=units; op["shaft_kw"]*=units; op["sec_kwh_m3"]=op["wire_kw"]/q
            op["design_margin_flow_m3h"]=qd; op["design_margin_dp_bar"]=dpd
            options.append(op)
    options.sort(key=lambda x:(x["wire_kw"],x["duty_units"],x["stages"],x["nominal_flow_m3h"]))
    for i,op in enumerate(options,1): op["selection_rank"]=i
    keep=options[:max(1,int(top_n))]
    return {"ok":bool(keep),"selected":keep[0] if keep else None,"options":keep,"database_records":len(MODELS),
            "reason":"" if keep else "No HHECP model/stage/duty-unit combination covers the requested duty."}

def curve_points(source_id,speed_ratio,density_kg_m3=998.0,motor_eff=0.95,vfd_eff=0.98,samples=25):
    model=BY_CODE[str(source_id)]; r=max(1e-9,float(speed_ratio))
    hc=model["_curves"]["Differential Head"]; qmin=hc["q_min"]*r; qmax=hc["q_max"]*r; out=[]
    for i in range(max(2,int(samples))):
        q=qmin+(qmax-qmin)*i/max(1,int(samples)-1); qref=q/r
        head=max(0.0,r*r*_poly(hc["coeff"],qref)); eta=_poly(model["_curves"]["Efficiency"]["coeff"],qref)/100.0
        shaft=r**3*_poly(model["_curves"]["Absorbed Power"]["coeff"],qref)
        hyd=float(density_kg_m3)*G*(q/3600.0)*head/1000.0
        if eta>0.05: shaft=max(shaft,hyd/eta); wire=shaft/max(float(motor_eff)*float(vfd_eff),1e-12)
        else: wire=None
        out.append({"flow_m3h":q,"head_m":head,"pump_dp_bar":_head_to_bar(head,density_kg_m3),
                    "efficiency":eta if eta>0 else None,"hydraulic_kw":hyd,"shaft_kw":shaft if shaft>0 else None,
                    "wire_kw":wire,"frequency_hz":60.0*r,"speed_ratio":r,"speed_rpm":float(model["reference_rpm"])*r})
    return out
