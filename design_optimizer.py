"""Background plant-design screening/validation for CalcOsPower v18.3.

The optimizer does not introduce new process physics. It generates nearby design
candidates, screens them cheaply, then validates the best candidates with the
existing authoritative CalcOsPower calculation engine.
"""
from __future__ import annotations
import itertools, math, time
from typing import Any

from calculations import CALCS, flow_to_m3h
from compute_engine import calculate_batch, turbo_metrics_batch, design_proxy_scores_batch, gpu_break_even_threshold
from membrane_db import get_membrane


def _f(d,k,default=0.0):
    try: return float(d.get(k,default) if d.get(k,default) not in (None,"") else default)
    except Exception: return float(default)


def _stage_count(data): return max(1,min(4,int(_f(data,"stage_count",1))))


def _candidate_grid(data: dict[str,Any], max_screen: int) -> list[dict[str,Any]]:
    n=_stage_count(data)
    vessel_mult=[0.90,0.95,1.0,1.05,1.10]
    recovery0=_f(data,"target_recovery",45.0)
    recoveries=sorted({max(5.0,min(95.0,recovery0+x)) for x in (-3,-1.5,0,1.5,3)})
    # Keep existing topology/interstage equipment. Only resize vessel inventory
    # and overall recovery around the user's current design basis.
    combos=itertools.product(vessel_mult, repeat=n)
    rows=[]
    for vm in combos:
        for rec in recoveries:
            c=dict(data); c["solve_basis"]="recovery"; c["target_recovery"]=rec
            for i,m in enumerate(vm,1):
                base=max(1,int(round(_f(data,f"vessels_{i}",1))))
                c[f"vessels_{i}"]=max(1,int(round(base*m)))
            rows.append(c)
            if len(rows)>=max_screen: return rows
    return rows


def _proxy_metrics(c: dict[str,Any]) -> tuple[float,float,float]:
    n=_stage_count(c); membranes=0.0; area=0.0
    for i in range(1,n+1):
        v=max(1,int(_f(c,f"vessels_{i}",1))); e=max(1,int(_f(c,f"elements_per_vessel_{i}",7)))
        membranes += v*e
        try: area += v*e*float(get_membrane(str(c.get(f"membrane_{i}",c.get("membrane_1","")))).get("active_area_m2",37.0))
        except Exception: area += v*e*37.0
    rec=max(1e-6,_f(c,"target_recovery",45.0)/100.0)
    return membranes,area,rec

def _proxy_score(c: dict[str,Any], objective: str) -> float:
    n=_stage_count(c); membranes=0; area=0.0
    for i in range(1,n+1):
        v=max(1,int(_f(c,f"vessels_{i}",1))); e=max(1,int(_f(c,f"elements_per_vessel_{i}",7)))
        membranes += v*e
        try: area += v*e*float(get_membrane(str(c.get(f"membrane_{i}",c.get("membrane_1","")))).get("active_area_m2",37.0))
        except Exception: area += v*e*37.0
    rec=max(1e-6,_f(c,"target_recovery",45.0)/100.0)
    if objective=="min_membranes": return membranes
    # Screening proxy only: prefer adequate area and higher recovery without
    # claiming this is the authoritative SEC. Full SEC ranking happens later.
    return membranes/max(rec,1e-6) + 0.00001*area


def _full_score(result: dict[str,Any], objective: str) -> float:
    if objective=="min_membranes": return float(result.get("total_elements",result.get("stage1_total_elements",1e12)) or 1e12)
    if objective=="min_pressure": return float(result.get("membrane_pressure_1",1e12) or 1e12)
    if objective=="balanced":
        sec=float(result.get("total_sec",1e6) or 1e6); p=float(result.get("membrane_pressure_1",1000) or 1000)
        elems=sum(float(result.get(f"stage{i}_total_elements",0) or 0) for i in range(1,int(result.get("stage_count",1) or 1)+1))
        return sec + 0.001*p + 0.00001*elems
    return float(result.get("total_sec",1e12) or 1e12)


def run_design_optimization(data: dict[str,Any], objective: str="min_sec", screen_candidates: int=4096,
                            validate_candidates: int=24, mode: str="multistage") -> dict[str,Any]:
    started=time.perf_counter(); objective=str(objective or "min_sec")
    if mode not in CALCS: raise ValueError("Unknown optimization calculation mode.")
    screen_candidates=max(32,min(20000,int(screen_candidates or 4096)))
    validate_candidates=max(4,min(64,int(validate_candidates or 24)))
    candidates=_candidate_grid(dict(data),screen_candidates)
    # GPU screening is now available for the multistage Background Design Optimizer
    # as well as turbo modes. Only the lightweight candidate surrogate runs on GPU;
    # the engineering authority remains the full CPU CalcOsPower process solver.
    gpu_info={"backend":"not-applicable","threshold":gpu_break_even_threshold(),"points":0}
    proxy_scores=None
    if mode=="multistage" and candidates:
        metrics=[_proxy_metrics(c) for c in candidates]
        # The Background Optimizer is explicitly a large batch workload. Request
        # OpenCL once there is enough parallel work to amortize a kernel launch;
        # unsupported systems fall back transparently to the CPU vector path.
        pref="gpu" if len(candidates)>=512 else "auto"
        gs=design_proxy_scores_batch([m[0] for m in metrics],[m[1] for m in metrics],[m[2] for m in metrics],objective,preference=pref)
        proxy_scores=gs.get("scores")
        gpu_info={"backend":gs.get("backend","cpu-vector"),"threshold":gs.get("threshold",gpu_break_even_threshold()),
                  "points":len(candidates),"device":gs.get("device"),"platform":gs.get("platform"),
                  "kernel_ms":gs.get("kernel_ms"),"fallback_reason":gs.get("gpu_fallback_reason")}
    elif mode in {"single","interstage","biturbo"} and candidates:
        fu=str(data.get("flow_unit","m3/h")); qf0=flow_to_m3h(_f(data,"feed_flow",1.0),fu)
        qpf=[]; qtr=[]; dp=[]; sg=[]; keep=[]
        for c in candidates:
            r=max(0.0,min(0.95,_f(c,"target_recovery",45.0)/100.0)); reject=qf0*(1-r)
            # This is only a flow-match screen. The authoritative turbo duties
            # are recalculated by CALCS for the shortlisted candidates.
            if mode=="single": pump=qf0; turb=reject
            else: pump=max(reject,1e-9); turb=max(reject*(1.0-r),1e-9)
            rr=turb/max(pump,1e-9)
            if rr<=0.20: continue
            qpf.append(pump); qtr.append(turb); dp.append(max(1.0,_f(c,"pex",10.0))); sg.append(1.02); keep.append(c)
        if keep:
            tm=turbo_metrics_batch(qpf,qtr,dp,sg,preference="auto")
            gpu_info={"backend":tm.get("backend","cpu-vector"),"threshold":gpu_break_even_threshold(),"points":len(keep),"device":tm.get("device")}
            candidates=keep
    if proxy_scores is not None and len(proxy_scores)==len(candidates):
        ranked=[c for _,c in sorted(zip(proxy_scores,candidates),key=lambda row:row[0])[:validate_candidates]]
    else:
        ranked=sorted(candidates,key=lambda c:_proxy_score(c,objective))[:validate_candidates]
    tasks=[{"id":str(i),"mode":mode,"data":c} for i,c in enumerate(ranked)]
    batch=calculate_batch(tasks)
    valid=[]; errors=[]
    for item,c in zip(batch.get("results",[]),ranked):
        if item and item.get("ok") and isinstance(item.get("result"),dict):
            valid.append({"score":_full_score(item["result"],objective),"result":item["result"],"input":c})
        else: errors.append((item or {}).get("error","candidate failed"))
    valid.sort(key=lambda x:x["score"])
    top=[]
    for rank,row in enumerate(valid[:5],1):
        r=row["result"]; inp=row["input"]; n=_stage_count(inp)
        top.append({"rank":rank,"score":row["score"],"total_sec":r.get("total_sec"),"ro_sec":r.get("ro_sec"),
                    "feed_pressure":r.get("membrane_pressure_1"),"product_flow":r.get("product_flow"),"recovery":r.get("recovery"),
                    "vessels":[int(_f(inp,f"vessels_{i}",1)) for i in range(1,n+1)],"target_recovery":inp.get("target_recovery"),
                    "input":inp})
    return {"ok":bool(top),"objective":objective,"screened":len(candidates),"validated":len(valid),"failed":len(errors),"top":top,
            "gpu_screen":gpu_info,"cpu_backend":batch.get("backend"),"workers":batch.get("workers"),
            "elapsed_seconds":time.perf_counter()-started,"note":"GPU screens large independent candidate arrays when OpenCL is available; all recommended designs are validated with the full CPU process solver."}
