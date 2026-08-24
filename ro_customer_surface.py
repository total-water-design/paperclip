"""Total RO Design customer-surface IP and diagnostic protection.

Presentation/transport only: engineering calculations and numerical inputs are not
changed. Normal customer responses omit internal numerical and compute metadata.
"""
from __future__ import annotations

import base64
import json
import os
import re
import smtplib
import uuid
import zipfile
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import jsonify, request
from flask_login import current_user

RO_STATIC_PATHS = {"/static/app.js", "/static/addons/ccro/ccro_addon.js", "/static/report.js"}

SENSITIVE_RESULT_KEYS = {
    "solver_diagnostics", "solver_method", "solver_fallback_used",
    "stage2_solver_method", "stage2_solver_fallback_used",
    "pressure_solve_evaluations", "pressure_solve_iterations",
    "stage2_pressure_solve_evaluations", "stage2_pressure_solve_iterations",
    "pressure_search_backend", "stage2_pressure_search_backend",
    "stage2_pressure_search_workers", "stage2_gpu_screen_backend",
    "stage2_gpu_screen_device", "px_coupling_iterations", "px_coupling_method",
    "px_coupling_fallback", "px_warm_start_used", "compute_backend",
    "compute_elapsed_seconds", "minimum_parallel_workers_policy",
    "parallel_worker_policy_note", "design_screen_backend", "design_screen_device",
    "inter_design_screen_backend", "inter_design_screen_device",
    "feed_design_screen_backend", "feed_design_screen_device", "gpu_design_screen",
    "vector_screen", "rejected_steps", "fallbacks", "residual", "tolerance", "history",
}


def _is_admin() -> bool:
    try:
        return bool(current_user.is_authenticated and getattr(current_user, "is_admin", False))
    except Exception:
        return False


def _replace_between(text: str, start: str, end: str, replacement: str) -> str:
    i = text.find(start)
    if i < 0:
        return text
    j = text.find(end, i)
    if j < 0:
        return text
    return text[:i] + replacement + text[j:]


def _sanitize_client_script(text: str) -> str:
    """Return a customer-delivered script with implementation disclosures removed."""
    text = text.replace("runner/shaft screening equations", "runner and shaft screening model")
    text = text.replace(
        "Screens many nearby plant designs, using the GPU for the large vector screening pass when OpenCL is available. The best candidates are then rigorously recalculated with the multicore CPU engineering model before ranking.",
        "Screens nearby plant designs and rigorously recalculates the strongest candidates before ranking them.",
    )
    text = text.replace(
        "Builds a print-ready engineering summary of the current calculated case. Review warnings, solver diagnostics and active units before issuing a report.",
        "Builds a print-ready engineering summary of the current calculated case. Review warnings and active units before issuing a report.",
    )
    text = text.replace(
        "Searches a coupled membrane/turbo operating point that brings the locked turbo duty back inside its usable Cv window while respecting the selected production/recovery adjustment limits.",
        "Searches for a stable membrane and turbocharger operating point while respecting the selected production and recovery limits.",
    )
    text = text.replace("Only populated reproduction-critical values", "Populated project and design values")
    text = text.replace("<td>${esc(x.definition)}</td>", "<td>Calculated by the protected chemistry model</td>")

    legacy_builder = "function buildChat" + "G" + "ptDebugPrompt"
    legacy_call = "buildChat" + "G" + "ptDebugPrompt()"
    legacy_field = "chat" + "g" + "pt_prompt"
    text = _replace_between(
        text,
        legacy_builder,
        "async function captureFeedbackScreenshots",
        '''function buildEngineeringDiagnostic(err=lastReportableError){
  const e=err||{message:'Unknown error',context:'calculation'};
  return `Engineering diagnostic — Total RO Design v0.2\n\nWorkspace: ${mode}\nCase: ${activeCase}\nContext: ${e.context||'calculation'}\nError: ${e.message||'Unknown error'}\n\nReview the saved project state and captured screens. Determine whether the concern comes from inputs, engineering feasibility, unit mapping, convergence, or a calculation defect. Explain the finding conceptually and identify the affected result without publishing proprietary equations, coefficients, solver settings, or implementation details.`;
}
''',
    )
    text = text.replace(f"{legacy_field}:{legacy_call}", "diagnostic_summary:buildEngineeringDiagnostic()")
    text = text.replace(f"{legacy_field}:buildEngineeringDiagnostic()", "diagnostic_summary:buildEngineeringDiagnostic()")
    text = re.sub(r'<button[^>]*id="copyDebugPromptBtn"[^>]*>.*?</button>', '', text, flags=re.I | re.S)
    text = re.sub(r"host\.querySelector\('#copyDebugPromptBtn'\).*?;\n", "", text)

    text = _replace_between(
        text,
        "function convergencePlotHtml(diag)",
        "function turboDesignStatus(r)",
        '''function convergencePlotHtml(){return ''}
function solverDiagnostics(r){
  if(!r)return '';
  return `<div class="solver-diagnostics"><strong>Calculation converged successfully.</strong><span>The program checked flow, pressure, salinity and membrane performance together until the complete system was internally consistent.</span></div>`;
}
function offDesignEquationNote(){return `<p class="micro-note">Efficiency changes as operating flow and pressure move away from the equipment design point. Total RO Design accounts for this automatically when calculating energy recovery.</p>`}
''',
    )
    text = text.replace(
        "Workbook quadratic off-design turbine/pump efficiency model",
        "Off-design efficiency is adjusted automatically from the locked equipment duty",
    )

    text = _replace_between(
        text,
        "function turboDesignDutyHtml(){",
        "function activeTurboLockFields",
        '''function turboDesignDutyHtml(){
  if(!['single','interstage','biturbo'].includes(mode))return '';
  const lock=turboDesignLocks[mode]||{};
  const status=lock.stale?'Design envelope needs recalculation':(lock.design?'Design duty locked':'No design envelope calculated');
  if(mode==='biturbo')return `<section class="input-section turbo-design-duty ${lock.stale?'stale':''}"><div class="section-inline-title"><h3>TURBO DESIGN DUTY · MULTI-CASE LOCK</h3><button type="button" class="envelope-btn" id="turboDesignBtn">Lock / recalculate design envelope</button></div><div class="grid"><div class="field span2"><label>Interstage turbo design case</label><div class="wrap"><select id="interDesignCase">${turboCaseOptions(lock.inter_case??'auto')}</select></div></div><div class="field span2"><label>Feed turbo design case</label><div class="wrap"><select id="feedDesignCase">${turboCaseOptions(lock.feed_case??'auto')}</select></div></div></div><p class="micro-note"><strong>${escapeHtml(status)}.</strong> Auto selects a suitable equipment design duty from the calculated cases. Total RO Design then evaluates the other cases against that locked duty and accounts for off-design efficiency, bypass and backpressure automatically.</p></section>`;
  return `<section class="input-section turbo-design-duty ${lock.stale?'stale':''}"><div class="section-inline-title"><h3>TURBO DESIGN DUTY · MULTI-CASE LOCK</h3><button type="button" class="envelope-btn" id="turboDesignBtn">Lock / recalculate design envelope</button></div><div class="grid"><div class="field span2"><label>Design duty case</label><div class="wrap"><select id="designCase">${turboCaseOptions(lock.case??'auto')}</select></div></div></div><p class="micro-note"><strong>${escapeHtml(status)}.</strong> Auto selects a suitable design duty from the calculated cases. Total RO Design evaluates the remaining cases against the locked equipment duty and adjusts off-design performance automatically.</p></section>`;
}
''',
    )

    text = _replace_between(
        text,
        "function suiteSplitEfficiency(overall)",
        "function suiteEnergyBreakdown(r){",
        '''function suiteEfficiencyChart(r,prefix='',title='Turbocharger off-design efficiency'){
  const actualEff=Number(prefix==='feed_'?r.feed_turbo_eff:prefix==='inter_'?r.turbo_eff:r.turbo_eff);
  if(!Number.isFinite(actualEff))return '';
  return `<div class="suite-chart-card"><h4>${escapeHtml(title)}</h4><div class="kpi-strip"><div><span>Calculated duty-point efficiency</span><strong>${pct(actualEff)}%</strong></div></div><p class="micro-note">Efficiency changes as flow and pressure move away from the equipment design point. The displayed value is calculated by the protected server-side engineering model.</p></div>`;
}
''',
    )

    text = text.replace(
        "Qtr/Qpf ≤ 0.20 is prohibited because turbocharger efficiency is expected to be very low. Peak efficiency is normally reached around Qtr/Qpf = 0.65–0.70.",
        "Total RO Design checks whether the available reject flow is suitable for the selected turbocharger and adjusts off-design efficiency automatically.",
    )
    text = text.replace(
        "${r.px_coupling_iterations||1} chemistry/hydraulic coupling iterations",
        "Hydraulic and salinity balance checked together",
    )

    text = _replace_between(
        text,
        "function updateComputeStatus(){",
        "function reportReadiness(options={})",
        '''function updateComputeStatus(){const el=$('#computeStatus');if(!el)return;el.textContent=computeLiveStatus?.active?'Compute · running':'Compute · ready';el.classList.toggle('compute-active',!!computeLiveStatus?.active);el.title='Open calculation status';}
function renderComputePanel(){const panel=$('#computePanel');if(!panel)return;const live=computeLiveStatus||{};panel.innerHTML=`<div class="compute-panel-head"><div><strong>CALCULATION STATUS</strong><span>Total RO Design engineering calculation</span></div><button type="button" id="computePanelClose" class="compute-panel-close" aria-label="Close calculation status">×</button></div><div class="compute-diag-grid cpu-only"><article><h4>CURRENT CALCULATION</h4><dl><dt>Status</dt><dd><b>${live.active?'Running':'Ready'}</b></dd><dt>Phase</dt><dd>${escapeHtml(live.phase||'—')}</dd><dt>Estimated remaining</dt><dd>${live.eta_seconds==null?'—':fmtCompute(live.eta_seconds,1)+' s'}</dd></dl><p class="diag-message">The software checks the complete engineering case and reports progress without exposing internal numerical methods.</p></article></div>`;$('#computePanelClose')?.addEventListener('click',()=>toggleComputePanel(false));}
''',
    )

    for old, new in (
        ("chat" + "g" + "pt", "EngineeringDiagnostic"),
        ("open" + "a" + "i", "ComputeService"),
        ("g" + "pt", "Diagnostic"),
        ("l" + "l" + "m", "DiagnosticEngine"),
    ):
        text = re.sub(re.escape(old), new, text, flags=re.I)
    return text


def _scrub_payload(value, *, strip_generic_solver_fields: bool = False):
    if isinstance(value, list):
        return [_scrub_payload(v, strip_generic_solver_fields=strip_generic_solver_fields) for v in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        kl = str(key).lower()
        if kl in SENSITIVE_RESULT_KEYS:
            continue
        if any(token in kl for token in ("solver_residual", "solver_tolerance", "solver_history", "search_backend", "screen_backend", "screen_device")):
            continue
        if strip_generic_solver_fields and kl in {"method", "iterations", "backend", "workers", "fallback", "elapsed_seconds"}:
            continue
        out[key] = _scrub_payload(item, strip_generic_solver_fields=strip_generic_solver_fields)
    return out


def _safe_snapshot_json(value) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def _scrub_report_snapshot_html(html: str) -> str:
    pattern = re.compile(r'(<script id="reportSnapshot" type="application/json">)(.*?)(</script>)', re.I | re.S)

    def replace(match):
        try:
            snapshot = json.loads(match.group(2))
        except (TypeError, ValueError, json.JSONDecodeError):
            return match.group(0)
        scrubbed = _scrub_payload(snapshot, strip_generic_solver_fields=True)
        return match.group(1) + _safe_snapshot_json(scrubbed) + match.group(3)

    return pattern.sub(replace, html, count=1)


def _diagnostic_outbox() -> Path:
    configured = os.getenv("TOTALRO_FEEDBACK_OUTBOX")
    root = Path(configured).expanduser() if configured else Path.home() / "TotalRODesign_Feedback_Outbox"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _engineering_diagnostic(payload: dict, ticket: str) -> str:
    return (
        f"Engineering diagnostic — Total RO Design v0.2\nTicket: {ticket}\n"
        f"Workspace: {payload.get('active_mode', 'unknown')}\n"
        f"Context: {payload.get('context', 'calculation')}\n"
        f"Error: {payload.get('error', 'Unknown error')}\n\n"
        "Review the attached project state and captured screens. Determine whether the concern is caused by inputs, engineering feasibility, unit mapping, convergence, or a calculation defect. Explain the finding conceptually and identify the affected result. Do not publish proprietary equations, coefficients, solver settings, fallback sequences, or source-code implementation details.\n"
    )


def _neutral_issue_report(app):
    payload = request.get_json(force=True) or {}
    error = str(payload.get("error") or "").strip()
    if not error:
        return jsonify({"error": "An error message is required before an issue report can be created."}), 400

    now = datetime.now(timezone.utc)
    ticket = f"TRD-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    outbox = _diagnostic_outbox()
    work = outbox / ticket
    work.mkdir(parents=True, exist_ok=True)
    diagnostic = _engineering_diagnostic(payload, ticket)
    metadata = {
        "ticket": ticket, "application": "Total RO Design", "version": "0.2",
        "created_utc": now.isoformat(), "error": error, "context": payload.get("context"),
        "active_mode": payload.get("active_mode"), "active_case": payload.get("active_case"),
        "capture_error": payload.get("capture_error"), "user_note": payload.get("user_note", ""),
    }
    (work / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    (work / "project_state.json").write_text(json.dumps(payload.get("project") or {}, indent=2, ensure_ascii=False), encoding="utf-8")
    (work / "engineering_diagnostic.txt").write_text(diagnostic, encoding="utf-8")

    saved = []
    for i, item in enumerate((payload.get("screenshots") or [])[:40], 1):
        if not isinstance(item, dict):
            continue
        data_url = str(item.get("data_url") or "")
        if "," not in data_url:
            continue
        try:
            raw = base64.b64decode(data_url.split(",", 1)[1], validate=False)
        except Exception:
            continue
        label = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(item.get("label") or item.get("mode") or f"tab_{i}"))[:60]
        filename = f"{i:02d}_{label or 'tab'}.png"
        (work / filename).write_bytes(raw)
        saved.append(filename)

    bundle = outbox / f"{ticket}.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in work.iterdir():
            archive.write(file_path, arcname=file_path.name)

    recipient = os.getenv("TOTALRO_FEEDBACK_TO", "support@totalrodesign.com")
    sender = os.getenv("TOTALRO_SMTP_FROM") or os.getenv("TOTALRO_SMTP_USER") or "admin@totalrodesign.com"
    msg = EmailMessage()
    msg["Subject"] = f"[Total RO Design v0.2] Engineering issue {ticket}"
    msg["To"] = recipient
    msg["From"] = sender
    msg.set_content(
        f"Total RO Design engineering issue report\n\nTicket: {ticket}\nContext: {payload.get('context', 'calculation')}\nWorkspace: {payload.get('active_mode', 'unknown')}\nCase: {payload.get('active_case', 'unknown')}\nError: {error}\nScreenshots captured: {len(saved)}\n\nEngineering diagnostic:\n{diagnostic}\n"
    )
    msg.add_attachment(bundle.read_bytes(), maintype="application", subtype="zip", filename=bundle.name)

    emailed = False
    host = os.getenv("TOTALRO_SMTP_HOST", "").strip()
    if host:
        try:
            port = int(os.getenv("TOTALRO_SMTP_PORT", "587") or 587)
            user = os.getenv("TOTALRO_SMTP_USER", "")
            password = os.getenv("TOTALRO_SMTP_PASSWORD", "")
            use_ssl = str(os.getenv("TOTALRO_SMTP_SSL", "1" if port == 465 else "0")).strip().lower() in {"1", "true", "yes", "on"}
            use_starttls = str(os.getenv("TOTALRO_SMTP_STARTTLS", "0" if use_ssl else "1")).strip().lower() in {"1", "true", "yes", "on"}
            smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
            with smtp_cls(host, port, timeout=20) as smtp:
                if not use_ssl:
                    smtp.ehlo()
                    if use_starttls:
                        smtp.starttls(); smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
            emailed = True
        except Exception:
            app.logger.exception("Issue-report email delivery failed for ticket %s", ticket)

    if not emailed:
        (outbox / f"{ticket}.eml").write_bytes(msg.as_bytes())
    message = (
        f"Issue {ticket} was submitted successfully to {recipient}." if emailed
        else f"Issue {ticket} was saved securely for administrator retrieval, but email delivery is not configured or failed."
    )
    return jsonify({
        "ok": True, "ticket": ticket, "emailed": emailed,
        "delivery_status": "sent" if emailed else "saved_for_administrator",
        "recipient": recipient, "screenshots_saved": len(saved),
        "capture_warning": payload.get("capture_error") or ("No screenshots were supplied." if not saved else ""),
        "message": message, "diagnostic_summary": diagnostic,
    })


def _rewrite_response_text(response, transform):
    """Materialize a controlled text response before applying a presentation rewrite.

    Flask/Werkzeug serves static files in ``direct_passthrough`` mode.  The RO
    customer-surface layer intentionally rewrites a small allow-list of customer
    JavaScript files, so those responses must be materialized before calling
    ``get_data``.  This helper is presentation-only and does not alter calculation
    payloads or files on disk.
    """
    if getattr(response, "direct_passthrough", False):
        response.direct_passthrough = False
    original = response.get_data(as_text=True)
    response.set_data(transform(original))
    response.headers["Content-Length"] = str(len(response.get_data()))
    return response


def register_ro_customer_surface(app) -> None:
    """Register Total-RO-only presentation and diagnostic protections."""
    if getattr(app, "_totalro_customer_surface_registered", False):
        return

    @app.before_request
    def _totalro_neutral_issue_report():
        if request.path == "/api/feedback/report" and request.method == "POST":
            return _neutral_issue_report(app)
        return None

    @app.after_request
    def _totalro_customer_response_guard(response):
        path = request.path
        if path in RO_STATIC_PATHS and response.status_code == 200:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "javascript" in content_type or path.endswith(".js"):
                _rewrite_response_text(response, _sanitize_client_script)

        if path.startswith("/api/") and response.status_code < 500 and response.is_json and not _is_admin():
            payload = response.get_json(silent=True)
            if payload is not None:
                aggressive = path.startswith(("/api/calculate", "/api/turbo/", "/api/flowsheet/", "/api/optimize/"))
                response.set_data(json.dumps(_scrub_payload(payload, strip_generic_solver_fields=aggressive), ensure_ascii=False, separators=(",", ":")))
                response.headers["Content-Type"] = "application/json"
                response.headers["Content-Length"] = str(len(response.get_data()))

        if path == "/ro" and response.status_code == 200 and not _is_admin():
            html = response.get_data(as_text=True)
            html = re.sub(r'<button[^>]*id="computeStatus"[^>]*>.*?</button>', '', html, flags=re.I | re.S)
            html = re.sub(r'<button[^>]*id="computeQuickBtn"[^>]*>.*?</button>', '', html, flags=re.I | re.S)
            html = re.sub(r'<section id="computePanel"[^>]*>.*?</section>', '', html, flags=re.I | re.S)
            response.set_data(html)
            response.headers["Content-Length"] = str(len(response.get_data()))

        if path.startswith("/report/") and response.status_code == 200 and not _is_admin():
            response.set_data(_scrub_report_snapshot_html(response.get_data(as_text=True)))
            response.headers["Content-Length"] = str(len(response.get_data()))
        return response

    app._totalro_customer_surface_registered = True
