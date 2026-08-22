"""Axial-piston positive-displacement pump database adapter."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def _load():
    pumps=[]
    for path in sorted((ROOT/"data").glob("pd_*.json")):
        pumps.extend(json.loads(path.read_text(encoding="utf-8")).get("pumps",[]))
    return pumps
PUMPS=_load(); BY_MODEL={r["model"]:r for r in PUMPS}

def evaluate(row,flow_m3h,required_dp_bar,available_inlet_bar=0.0,motor_eff=0.95,vfd_eff=0.98):
    q=float(flow_m3h); dp=float(required_dp_bar)
    if q<=0 or dp<=0:return None
    rpm=q/max(float(row["kq_m3h_per_rpm"]),1e-12)
    if rpm<float(row["min_rpm"])-1e-9 or rpm>float(row["max_rpm"])+1e-9:return None
    outlet=float(available_inlet_bar)+dp
    if outlet<float(row["min_outlet_barg"])-1e-9 or outlet>float(row["max_outlet_barg"])+1e-9:return None
    inlet_min=float(row["min_inlet_barg"]); inlet_max=float(row["max_inlet_barg"]); notes=str(row.get("source_notes") or "")
    if ("Above 3000" in notes and rpm>3000) or ("Above 1500" in notes and rpm>1500): inlet_min=max(inlet_min,2.0)
    if float(available_inlet_bar)<inlet_min-1e-9 or float(available_inlet_bar)>inlet_max+1e-9:return None
    shaft=16.7*q*dp/max(float(row["motor_calc_factor"]),1e-12)
    eta=float(row["efficiency"]); eta=eta/100.0 if eta>1.5 else eta
    wire=shaft/max(float(motor_eff)*float(vfd_eff),1e-12); maxout=float(row["max_outlet_barg"])
    return {"source_id":row["model"],"technology":"PD","product_family":row["model"],"stage_config":"positive displacement",
            "pump_series":"PD","model":row["model"],"flow_m3h":q,"required_dp_bar":dp,"actual_dp_bar":dp,
            "required_head_m":None,"actual_head_m":None,"head_margin_pct":0.0,"speed_ratio":rpm/max(float(row["reference_rpm"]),1e-12),
            "frequency_hz":None,"reference_rpm_60":float(row["reference_rpm"]),"speed_rpm":rpm,"raw_efficiency":eta,
            "pump_efficiency":eta,"motor_efficiency":float(motor_eff),"vfd_efficiency":float(vfd_eff),
            "overall_wire_efficiency":eta*float(motor_eff)*float(vfd_eff),"hydraulic_kw":q*dp/36.0,
            "shaft_kw":shaft,"wire_kw":wire,"sec_kwh_m3":wire/q,"shaft_torque_nm":float(row["torque_max_nm"])*dp/max(maxout,1e-12),
            "min_speed_limited":False,"min_flow_60hz_m3h":float(row["flow_min_m3h"]),"max_flow_60hz_m3h":float(row["flow_max_m3h"])}

def select(flow_m3h,required_dp_bar,available_inlet_bar=0.0,motor_eff=0.95,vfd_eff=0.98,flow_margin=0.05,head_margin=0.05,top_n=5,max_duty_units=10):
    q=float(flow_m3h);dp=float(required_dp_bar);qd=q*(1+max(0.0,float(flow_margin)));dpd=dp*(1+max(0.0,float(head_margin)));options=[]
    for row in PUMPS:
        for units in range(1,max(1,int(max_duty_units))+1):
            if evaluate(row,qd/units,dpd,available_inlet_bar,motor_eff,vfd_eff) is None:continue
            op=evaluate(row,q/units,dp,available_inlet_bar,motor_eff,vfd_eff)
            if op is None:continue
            op["duty_units"]=units;op["installed_units"]=units;op["wire_kw_per_pump"]=op["wire_kw"]
            op["wire_kw"]*=units;op["hydraulic_kw"]*=units;op["shaft_kw"]*=units;op["sec_kwh_m3"]=op["wire_kw"]/q
            op["design_margin_flow_m3h"]=qd;op["design_margin_dp_bar"]=dpd;options.append(op)
    options.sort(key=lambda x:(x["wire_kw"],x["duty_units"],x["model"]))
    for i,op in enumerate(options,1):op["selection_rank"]=i
    keep=options[:max(1,int(top_n))]
    return {"ok":bool(keep),"selected":keep[0] if keep else None,"options":keep,"database_records":len(PUMPS),
            "reason":"" if keep else "No positive-displacement pump/duty-unit combination covers the requested duty."}
