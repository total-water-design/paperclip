from calculations import CALCS

def _turbo_window_metrics(mode, result):
    """Return locked-turbo Cv-window violations in dimensionless Cv units."""
    prefixes = [""] if mode in {"single", "interstage"} else ["inter_", "feed_"]
    rows=[]
    total=0.0
    for prefix in prefixes:
        req=float(result.get(f"{prefix}cv_required",0.0) or 0.0)
        cvc=float(result.get(f"{prefix}cvc",0.0) or 0.0)
        cvo=float(result.get(f"{prefix}cvo",0.0) or 0.0)
        if req<=0 or cvc<=0 or cvo<=0:
            raise ValueError("Locked turbo Cv window is missing. Lock the multi-case design duty first.")
        if req < cvc:
            violation=cvc-req
            status="backpressure_required"
        elif req > cvo:
            violation=req-cvo
            status="bypass_required"
        else:
            violation=0.0
            status="in_range"
        span=max(cvo-cvc,1e-9)
        total += (violation/span)**2
        rows.append({"prefix":prefix,"cv_required":req,"cvc":cvc,"cvo":cvo,"status":status,"violation":violation})
    return {"rows":rows,"score":total,"feasible":all(x["violation"]<=1e-7 for x in rows)}


def _membrane_limit_penalty(result):
    worst=max(float(result.get("stage1_dp_limit_fraction",0.0) or 0.0), float(result.get("stage2_dp_limit_fraction",0.0) or 0.0))
    return max(0.0,worst-1.0), worst


def run_flux_optimization(mode, data, strategy="maintain_product", max_feed_change_pct=15.0, max_recovery_change_pp=5.0):
    """Search a bounded coupled RO operating envelope without resizing locked turbo hardware.

    The design Cvc/Cvo and off-design reference fields arrive in *data* from the UI's
    locked multi-case design. Only feed flow/recovery setpoints are varied. Every trial
    calls the full coupled membrane/turbo calculation.
    """
    if mode not in {"single","interstage","biturbo"}:
        raise ValueError("Flux optimization applies only to turbocharger configurations.")
    if str(data.get("membrane_coupling","")).lower() not in {"on","true","1","yes"}:
        raise ValueError("Optimize Flux Balance requires RO membrane coupling to be ON.")
    original=CALCS[mode](dict(data))
    before=_turbo_window_metrics(mode,original)
    _, original_dp_worst=_membrane_limit_penalty(original)
    allowed_dp_worst=max(1.0, original_dp_worst*1.02)
    if before["feasible"]:
        return {"feasible":True,"already_in_range":True,"strategy":strategy,"original":original,"recommended":original,"recommended_inputs":{},"window":before,"evaluations":1}
    fu=data.get("flow_unit","m3/h")
    qf0=float(original["feed_flow"]); qp0=float(original["product_flow"]); r0=float(original["recovery"])
    candidates=[]; evals=1
    def evaluate(trial, distance):
        nonlocal evals
        try:
            trial=dict(trial); trial["_solver_fast"]=True
            res=CALCS[mode](trial); evals+=1
            wm=_turbo_window_metrics(mode,res); dp_pen,worst=_membrane_limit_penalty(res)
            # Strongly reject new membrane-limit violations; then minimize Cv violation,
            # operating-point movement and SEC as gentle tie-breakers.
            objective=wm["score"]*1e6 + dp_pen*1e7 + distance*100 + float(res.get("total_sec",0.0) or 0.0)
            candidates.append((wm["feasible"] and dp_pen<=1e-9, objective, distance, trial, res, wm, worst))
        except (ValueError,ZeroDivisionError,OverflowError):
            evals+=1
    strategy=str(strategy or "maintain_product").lower()
    if strategy=="maintain_product":
        lim=max(1.0,min(float(max_feed_change_pct or 15.0),40.0))/100.0
        for i in range(61):
            frac=-lim+2*lim*i/60.0
            if abs(frac)<1e-12: continue
            trial=dict(data); trial["feed_flow"]=qf0*(1.0+frac); trial["target_product_flow"]=qp0; trial["solve_basis"]="product"
            evaluate(trial,abs(frac))
    elif strategy=="allow_production":
        lim=max(0.5,min(float(max_recovery_change_pp or 5.0),20.0))/100.0
        lo=max(0.05,r0-lim); hi=min(0.90,r0+lim)
        for i in range(61):
            rr=lo+(hi-lo)*i/60.0
            if abs(rr-r0)<1e-12: continue
            trial=dict(data); trial["feed_flow"]=qf0; trial["target_recovery"]=100.0*rr; trial["solve_basis"]="recovery"
            evaluate(trial,abs(rr-r0))
    else:
        raise ValueError("Unknown optimization strategy.")
    if not candidates:
        raise ValueError("No valid coupled membrane operating points were found inside the selected optimization limits.")
    feasible=[x for x in candidates if x[0]]
    chosen=min(feasible or candidates,key=lambda x:(x[2],x[1]) if x[0] else (x[1],x[2]))
    ok,objective,distance,trial,fast,wm,worst=chosen
    # Recalculate the selected point in full-detail reporting mode.
    full_trial=dict(trial); full_trial.pop("_solver_fast",None)
    recommended=CALCS[mode](full_trial); evals+=1; final_window=_turbo_window_metrics(mode,recommended)
    _,worst=_membrane_limit_penalty(recommended)
    feasible_final=final_window["feasible"] and worst<=allowed_dp_worst+1e-9
    inputs={"feed_flow":full_trial.get("feed_flow"),"solve_basis":full_trial.get("solve_basis")}
    if strategy=="maintain_product": inputs["target_product_flow"]=full_trial.get("target_product_flow")
    else: inputs["target_recovery"]=full_trial.get("target_recovery")
    return {"feasible":feasible_final,"already_in_range":False,"strategy":strategy,"original":original,"recommended":recommended,"recommended_inputs":inputs,"original_window":before,"window":final_window,"evaluations":evals,"membrane_dp_limit_fraction":worst,"message":("A no-bypass/no-backpressure operating point was found within the selected limits." if feasible_final else "No fully no-bypass/no-backpressure point was found within the selected limits. The closest valid membrane operating point is shown for review only.")}

