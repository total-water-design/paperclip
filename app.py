from flask import Flask, render_template, request, jsonify, redirect, url_for, abort, send_file
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import HTTPException
from calculations import CALCS, flow_to_m3h, pressure_to_bar, turbo_efficiency
from membrane_db import list_membranes, META
from economics import economic_analysis
from compute_engine import (calculate_batch, hardware_info, turbo_metrics_batch, compute_status,
                            gpu_self_test, begin_compute_run, update_compute_run, finish_compute_run,
                            request_compute_cancel, CalculationCancelled,
                            DEFAULT_CPU_WORKERS, MIN_SINGLE_CPU_WORKERS, select_worker_count, calibrate_gpu_break_even,
                            CPU_ONLY_MODE, COMPUTE_MODE)
import json
import os
import base64
import io
import smtplib
import zipfile
import uuid
import secrets
import time
import threading
import re
from functools import wraps
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from chemistry_analysis import analyze_water, analyze_ui_payload, scale_to_tds, balance_composition, carbonate_speciation, acid_dose_to_target_ph
from water_chemistry import SPECIES
from design_optimizer import run_design_optimization
from auth import (init_auth, product_entitlement_for, serialized_product_entitlements,
                  user_can_access_product, db, record_telemetry)
from suite_catalog import PRODUCT_BY_ID, PRODUCTS, SUITE_HEADLINE, SUITE_NAME, SUITE_TAGLINE, SUITE_VERSION, product_catalog, status_label
from report_snapshot import validate_report_snapshot
from economics_reporting import build_snapshot, snapshot_json, build_workbook, build_pdf
from flowsheet import solve_payload, FlowsheetConvergenceError
from entitlements import (
    EntitlementContext, EntitlementError, FEATURE_MIN_TIER,
    clamp_preview_tier, normalize_tier,
)

app = Flask(__name__)
init_auth(app)
APP_NAME = "Total RO Design"
APP_VERSION = "0.2"
SUITE_RELEASE = f"{SUITE_NAME} v{SUITE_VERSION}"
app.config["SUITE_VERSION"] = SUITE_VERSION
FEEDBACK_TO = os.getenv("TOTALRO_FEEDBACK_TO", "support@totalrodesign.com")
ACCOUNT_ROLE = str(os.getenv("TOTALRO_ACCOUNT_ROLE", "admin") or "admin").strip().lower()
LICENSED_TIER = normalize_tier(os.getenv("TOTALRO_LICENSED_TIER", "platinum"), "platinum")


class EconomicsAuthorizationError(PermissionError):
    """Raised when the governed Economics API has no valid caller grant."""

    def __init__(self, message: str, *, status_code: int = 403):
        self.status_code = status_code
        super().__init__(message)

# The current compute monitor/cancel engine is process-wide.  Until jobs are
# moved to a dedicated queue, the authenticated Alpha permits one active heavy
# engineering calculation at a time so users cannot overwrite or cancel each
# other's state. Lightweight chemistry and read-only requests remain concurrent.
_calculation_gate = threading.Lock()
_calculation_owner_lock = threading.RLock()
_active_calculation_owner = None

# Report snapshots are immutable JSON documents created from one fully solved
# case.  The short-lived in-memory store prevents the PDF renderer from reading
# scattered live UI state while pages are being composed.
_report_snapshot_lock = threading.RLock()
_report_snapshots: dict[str, dict] = {}
_REPORT_SNAPSHOT_TTL_SECONDS = int(os.getenv("TOTALRO_REPORT_SNAPSHOT_TTL_SECONDS", "1800") or 1800)
_economics_report_lock = threading.RLock()
_economics_report_snapshots: dict[str, dict] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _request_owner_key():
    if app.config.get("AUTH_ENABLED", False) and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return "desktop"


def _calculation_guard(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        global _active_calculation_owner
        owner = _request_owner_key()
        if not app.config.get("AUTH_ENABLED", False):
            with _calculation_owner_lock:
                _active_calculation_owner = owner
            try:
                return view(*args, **kwargs)
            finally:
                with _calculation_owner_lock:
                    _active_calculation_owner = None
        if not _calculation_gate.acquire(blocking=False):
            with _calculation_owner_lock:
                same_owner = _active_calculation_owner == owner
            return jsonify({
                "error": "Server calculation in progress. Please retry when the current engineering job is complete." if not same_owner else "Your previous engineering calculation is still running.",
                "error_type": "CalculationBusy",
                "guidance": "Wait for the active calculation to finish. The hosted Alpha admits one heavy engineering job at a time so it can use all configured CPU workers.",
            }), 409
        with _calculation_owner_lock:
            _active_calculation_owner = owner
        try:
            return view(*args, **kwargs)
        finally:
            with _calculation_owner_lock:
                _active_calculation_owner = None
            _calculation_gate.release()
    return wrapped


def _entitlement_context() -> EntitlementContext:
    """Resolve entitlements from the authenticated account when enabled.

    Desktop/local mode retains the environment-based administrator preview used
    by the existing Windows Alpha.  Server mode ignores environment role/tier
    claims once a user is authenticated.
    """
    if app.config.get("AUTH_ENABLED", False) and current_user.is_authenticated:
        role = str(getattr(current_user, "role", "user") or "user").strip().lower()
        ro_entitlement = product_entitlement_for(current_user, "ro")
        licensed_tier = normalize_tier(
            getattr(ro_entitlement, "tier", None) or getattr(current_user, "licensed_tier", "entry"),
            "entry",
        )
    else:
        role = ACCOUNT_ROLE if ACCOUNT_ROLE in {"admin", "user"} else "user"
        licensed_tier = LICENSED_TIER
    requested = request.headers.get("X-TotalRO-Effective-Tier")
    effective = clamp_preview_tier(requested, licensed_tier, role)
    return EntitlementContext(
        role=role,
        licensed_tier=licensed_tier,
        effective_tier=effective,
    )


def _require_feature(feature_id: str) -> EntitlementContext:
    context = _entitlement_context()
    context.require(feature_id)
    return context


def _require_economics_authorization() -> EntitlementContext:
    """Authorize the Economics API without trusting local-preview defaults.

    The desktop application deliberately supports an administrator preview
    without accounts.  A governed deployment must never inherit that fallback:
    if authentication is disabled there, no request header can manufacture an
    Economics grant.  Authenticated callers use their Economics product grant,
    independently of the legacy RO entitlement bridge.
    """
    if not app.config.get("AUTH_ENABLED", False):
        deployment_mode = str(app.config.get("DEPLOYMENT_MODE", "desktop") or "desktop").strip().lower()
        if deployment_mode in {"server", "aws", "production"}:
            raise EconomicsAuthorizationError(
                "Authentication must be enabled before the governed Economics API can be used.",
                status_code=401,
            )
        return _require_feature("economics")

    if not current_user.is_authenticated:
        raise EconomicsAuthorizationError("Authentication is required for the Economics API.", status_code=401)

    entitlement = product_entitlement_for(current_user, "economics")
    if not entitlement or not entitlement.enabled or not entitlement.is_current():
        raise EconomicsAuthorizationError("An active Total Water Economics product entitlement is required.")

    role = str(getattr(current_user, "role", "user") or "user").strip().lower()
    licensed_tier = normalize_tier(getattr(entitlement, "tier", None), "entry")
    context = EntitlementContext(
        role=role,
        licensed_tier=licensed_tier,
        effective_tier=clamp_preview_tier(
            request.headers.get("X-TotalRO-Effective-Tier"), licensed_tier, role,
        ),
    )
    context.require("economics")
    return context

def _feedback_outbox_dir():
    configured=os.getenv("TOTALRO_FEEDBACK_OUTBOX")
    root=Path(configured).expanduser() if configured else (Path.home()/"TotalRODesign_Feedback_Outbox")
    root.mkdir(parents=True,exist_ok=True)
    return root

def _feedback_prompt(payload, ticket):
    return str(payload.get("chatgpt_prompt") or f"""ChatGPT investigation prompt: Investigate a potential Total RO Design v{APP_VERSION} calculation error.
Ticket: {ticket}
Workspace: {payload.get('active_mode','unknown')}
Context: {payload.get('context','calculation')}
Error: {payload.get('error','Unknown error')}

Review the attached project-state JSON and screenshots from all captured Total RO Design tabs. Reproduce the engineering calculation, identify whether the issue is an input/feasibility problem, numerical-convergence problem, unit/variable mapping problem, or a calculation defect, and show the expected equations and corrected result before proposing a code change. Preserve the current calculation architecture unless the evidence requires a change.
""")

@app.get('/api/entitlements')
def entitlements_api():
    """Return the account tier and administrator preview feature matrix."""
    data = _entitlement_context().as_dict()
    if app.config.get("AUTH_ENABLED", False) and current_user.is_authenticated:
        data["account"] = {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "organization": current_user.organization,
            "status": current_user.status,
        }
        data["products"] = serialized_product_entitlements(current_user)
    return jsonify(data)


@app.get('/healthz')
def healthz():
    """Unauthenticated load-balancer/service health endpoint."""
    return jsonify({"ok": True, "application": SUITE_NAME, "suite_version": SUITE_VERSION, "component": APP_NAME, "component_version": APP_VERSION})


@app.errorhandler(EntitlementError)
def entitlement_error(exc):
    return jsonify({
        'error': str(exc),
        'error_type': 'EntitlementError',
        'feature_id': exc.feature_id,
        'required_tier': exc.required_tier,
        'effective_tier': exc.effective_tier,
        'guidance': f"Switch the administrator preview to {exc.required_tier.title()} or use an account licensed for that tier.",
    }), 403


@app.errorhandler(EconomicsAuthorizationError)
def economics_authorization_error(exc):
    return jsonify({
        "error": str(exc),
        "error_type": "EconomicsAuthorizationError",
        "feature_id": "economics",
    }), exc.status_code


@app.post('/api/feedback/report')
def feedback_report_api():
    payload=request.get_json(force=True) or {}
    error=str(payload.get('error') or '').strip()
    if not error:
        return jsonify({'error':'An error message is required before a feedback report can be created.'}),400
    now=datetime.now(timezone.utc)
    ticket=f"TRD-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    outbox=_feedback_outbox_dir(); work=outbox/ticket; work.mkdir(parents=True,exist_ok=True)
    prompt=_feedback_prompt(payload,ticket)
    metadata={
        'ticket':ticket,'application':APP_NAME,'version':APP_VERSION,'created_utc':now.isoformat(),
        'recipient':FEEDBACK_TO,'error':error,'context':payload.get('context'),'active_mode':payload.get('active_mode'),
        'active_case':payload.get('active_case'),'capture_error':payload.get('capture_error'),'user_note':payload.get('user_note','')
    }
    (work/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    (work/'project_state.json').write_text(json.dumps(payload.get('project') or {},indent=2,ensure_ascii=False),encoding='utf-8')
    (work/'chatgpt_debug_prompt.txt').write_text(prompt,encoding='utf-8')
    screenshots=payload.get('screenshots') or []
    saved=[]
    for i,item in enumerate(screenshots[:40],1):
        if not isinstance(item,dict): continue
        data_url=str(item.get('data_url') or '')
        if ',' not in data_url: continue
        try:
            raw=base64.b64decode(data_url.split(',',1)[1],validate=False)
        except Exception:
            continue
        label=''.join(c if c.isalnum() or c in '-_' else '_' for c in str(item.get('label') or item.get('mode') or f'tab_{i}'))[:60]
        fn=f"{i:02d}_{label or 'tab'}.png"; (work/fn).write_bytes(raw); saved.append(fn)
    bundle=outbox/f"{ticket}.zip"
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for f in work.iterdir(): z.write(f,arcname=f.name)
    msg=EmailMessage(); msg['Subject']=f"[{APP_NAME} v{APP_VERSION}] Calculation issue {ticket}"
    msg['To']=FEEDBACK_TO; sender=os.getenv('TOTALRO_SMTP_FROM') or os.getenv('TOTALRO_SMTP_USER') or f"admin@totalrodesign.com"; msg['From']=sender
    msg.set_content(f"""Total RO Design automated issue report

Ticket: {ticket}
Context: {payload.get('context','calculation')}
Workspace: {payload.get('active_mode','unknown')}
Case: {payload.get('active_case','unknown')}
Error: {error}
Screenshots captured: {len(saved)}

ChatGPT investigation prompt:
{prompt}
""")
    msg.add_attachment(bundle.read_bytes(),maintype='application',subtype='zip',filename=bundle.name)
    emailed=False
    host=os.getenv('TOTALRO_SMTP_HOST','').strip()
    if host:
        try:
            port=int(os.getenv('TOTALRO_SMTP_PORT','587') or 587)
            user=os.getenv('TOTALRO_SMTP_USER','')
            password=os.getenv('TOTALRO_SMTP_PASSWORD','')
            use_ssl=_env_bool('TOTALRO_SMTP_SSL', port == 465)
            use_starttls=_env_bool('TOTALRO_SMTP_STARTTLS', not use_ssl)
            if use_ssl:
                with smtplib.SMTP_SSL(host,port,timeout=20) as smtp:
                    if user: smtp.login(user,password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(host,port,timeout=20) as smtp:
                    smtp.ehlo()
                    if use_starttls:
                        smtp.starttls(); smtp.ehlo()
                    if user: smtp.login(user,password)
                    smtp.send_message(msg)
            emailed=True
        except Exception:
            # Preserve the diagnostic in the protected outbox, but never expose
            # SMTP credentials, server details, or filesystem paths to the user.
            app.logger.exception('Feedback email delivery failed for ticket %s', ticket)
    eml=outbox/f"{ticket}.eml"
    if not emailed: eml.write_bytes(msg.as_bytes())
    delivery_status = 'sent' if emailed else 'saved_for_administrator'
    public_message = (
        f'Issue {ticket} was submitted successfully to {FEEDBACK_TO}.'
        if emailed else
        f'Issue {ticket} was saved securely for administrator retrieval, but email delivery is not configured or failed.'
    )
    return jsonify({
        'ok': True,
        'ticket': ticket,
        'emailed': emailed,
        'delivery_status': delivery_status,
        'recipient': FEEDBACK_TO,
        'screenshots_saved': len(saved),
        'capture_warning': payload.get('capture_error') or ('No screenshots were supplied.' if not saved else ''),
        'message': public_message,
        # Server paths are deliberately omitted from the customer response.
        'chatgpt_prompt': prompt,
    })

@app.errorhandler(Exception)
def api_unhandled_exception(exc):
    """Keep the local desktop server alive and return JSON for unexpected API errors.

    A solver exception should never turn into an HTML 500 page or abruptly leave
    the browser with only 'Failed to fetch'. Engineering ValueErrors are handled
    by their routes; this is the last-resort runtime guard.
    """
    if isinstance(exc, HTTPException):
        return exc
    app.logger.exception("Unhandled Total RO Design exception", exc_info=exc)
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'The calculation engine encountered an internal error. Save the project and submit an issue report if it repeats.',
            'error_type': type(exc).__name__,
            'guidance': 'Review the requested duty point and retry. If it repeats, save the project and report the case.'
        }), 500
    return 'Total RO Design internal error', 500

@app.route('/')
def index():
    """Public master-brand landing page."""
    return render_template(
        'suite_landing.html',
        products=product_catalog(),
        suite_headline=SUITE_HEADLINE,
        suite_tagline=SUITE_TAGLINE,
        status_label=status_label,
    )


@app.get('/api/suite/catalog')
def suite_catalog_api():
    data = {
        'suite': {'name': SUITE_NAME, 'version': SUITE_VERSION, 'headline': SUITE_HEADLINE, 'tagline': SUITE_TAGLINE},
        'products': product_catalog(),
    }
    if current_user.is_authenticated:
        data['entitlements'] = serialized_product_entitlements(current_user)
    return jsonify(data)


@app.get('/api/suite/session')
def suite_session_api():
    if app.config.get('AUTH_ENABLED', False) and not current_user.is_authenticated:
        return jsonify({'error':'Authentication required.','error_type':'AuthenticationRequired','login_url':url_for('auth.login')}),401
    return jsonify({'csrf_token':generate_csrf(),'account':({'id':getattr(current_user,'id',None),'email':getattr(current_user,'email',''),'full_name':getattr(current_user,'full_name',''),'organization':getattr(current_user,'organization',''),'country_code':getattr(current_user,'country_code','') or '', 'country':getattr(current_user,'country_name','') or '', 'role':getattr(current_user,'role',''),'is_admin':bool(getattr(current_user,'is_admin',False))} if current_user.is_authenticated else None)})


@app.get('/api/suite/_auth/bio')
def suite_bio_auth():
    if not app.config.get('AUTH_ENABLED', False): return ('',204)
    if not current_user.is_authenticated: return ('',401)
    if getattr(current_user,'is_admin',False): return ('',204)
    return ('',204) if user_can_access_product(current_user,'bio') else ('',403)


@app.get('/suite')
def suite_dashboard():
    if app.config.get('AUTH_ENABLED', False) and current_user.is_authenticated:
        products = serialized_product_entitlements(current_user)
    else:
        # Desktop/local mode retains the existing environment tier and grants
        # access to the currently available RO product without requiring an
        # account database.
        products = []
        for product in product_catalog():
            is_ro = product['product_id'] == 'ro'
            products.append({
                **product,
                'entitlement': {
                    'enabled': is_ro,
                    'tier': LICENSED_TIER if is_ro else 'entry',
                    'status': 'active' if is_ro else 'inactive',
                    'starts_at': None,
                    'expires_at': None,
                    'current': is_ro,
                },
                'accessible': bool(is_ro and product['status'] == 'available'),
            })
    return render_template(
        'suite_dashboard.html',
        products=products,
        status_label=status_label,
    )


@app.get('/economics-suite')
def economics_application():
    """Serve the authenticated Total Water Economics workflow."""
    return render_template('economics_suite.html')


def _purge_expired_report_snapshots(now: float | None = None) -> None:
    now = float(now or time.time())
    with _report_snapshot_lock:
        expired = [token for token, item in _report_snapshots.items()
                   if float(item.get("expires_at", 0)) <= now]
        for token in expired:
            _report_snapshots.pop(token, None)


def _validate_report_snapshot(snapshot: dict) -> list[str]:
    """Compatibility wrapper around the dependency-free report validator."""
    return validate_report_snapshot(snapshot)


@app.post('/api/report/snapshot')
def create_report_snapshot():
    _require_feature('basic_report')
    payload = request.get_json(force=True, silent=False) or {}
    snapshot = payload.get('snapshot') if isinstance(payload.get('snapshot'), dict) else payload
    # Round-trip through JSON to detach the stored record from request objects and
    # to reject non-serializable/internal runtime values.
    try:
        frozen = json.loads(json.dumps(snapshot, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        return jsonify({'error': f'The solved case contains a value that cannot be reported: {exc}'}), 400
    errors = _validate_report_snapshot(frozen)
    if errors:
        return jsonify({'error': errors[0], 'errors': errors, 'error_type': 'ReportReadinessError'}), 409
    _purge_expired_report_snapshots()
    token = secrets.token_urlsafe(24)
    owner = _request_owner_key()
    created = time.time()
    with _report_snapshot_lock:
        _report_snapshots[token] = {
            'owner': owner, 'created_at': created,
            'expires_at': created + _REPORT_SNAPSHOT_TTL_SECONDS,
            'snapshot': frozen,
        }
    return jsonify({
        'ok': True, 'token': token,
        'preview_url': url_for('engineering_report', token=token),
        'print_url': url_for('engineering_report', token=token, autoprint=1),
        'expires_in_seconds': _REPORT_SNAPSHOT_TTL_SECONDS,
    })


@app.get('/report/<token>')
def engineering_report(token):
    _require_feature('basic_report')
    _purge_expired_report_snapshots()
    with _report_snapshot_lock:
        record = _report_snapshots.get(token)
    if not record:
        return render_template('report/report_unavailable.html', reason='This report snapshot expired or does not exist.'), 404
    owner = _request_owner_key()
    if record.get('owner') != owner and not bool(getattr(current_user, 'is_admin', False)):
        abort(403)
    snapshot = record['snapshot']
    return render_template(
        'report/engineering_report.html',
        snapshot=snapshot,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')),
        autoprint=request.args.get('autoprint') == '1',
    )


@app.get('/ro')
def ro_application():
    if app.config.get('AUTH_ENABLED', False) and not user_can_access_product(current_user, 'ro'):
        return render_template(
            'product_access_denied.html',
            product=PRODUCT_BY_ID['ro'].as_dict(),
            entitlement=next((x for x in serialized_product_entitlements(current_user) if x['product_id'] == 'ro'), None),
        ), 403
    return render_template('index.html', suite_version=SUITE_VERSION)


@app.get('/<product_route>')
def future_product(product_route):
    route_map = {p.route.lstrip('/'): p for p in PRODUCTS if p.product_id != 'ro'}
    product = route_map.get(product_route)
    if not product:
        abort(404)
    return render_template('product_status.html', product=product.as_dict(), status_label=status_label(product.status))

@app.before_request
def _gate_ro_product_access():
    """Enforce the RO product entitlement server-side for every RO route/API."""
    if not app.config.get('AUTH_ENABLED', False) or not current_user.is_authenticated:
        return None
    path = request.path
    ro_request = path == '/ro' or (path.startswith('/api/') and not path.startswith('/api/suite/') and not path.startswith('/api/projects'))
    if ro_request and not user_can_access_product(current_user, 'ro'):
        if path.startswith('/api/'):
            return jsonify({
                'error': 'Total RO Design is not included in this account.',
                'error_type': 'ProductEntitlementError',
                'product_id': 'ro',
                'guidance': 'Contact your organization administrator or support@totalrodesign.com to request access.',
            }), 403
        return redirect(url_for('suite_dashboard'))
    return None


@app.get('/api/membranes')
def membranes():
    return jsonify({'membranes': list_membranes(), 'metadata': META.get('metadata', {})})

@app.get('/api/seawater-presets')
def seawater_presets():
    path = Path(__file__).resolve().parent / 'data' / 'seawater_presets.json'
    return jsonify(json.loads(path.read_text(encoding='utf-8')))



def _composition_from_payload(payload):
    return {k: float(payload.get('ion_'+k, payload.get(k, 0.0)) or 0.0) for k in SPECIES}

@app.post('/api/chemistry/analyze')
def chemistry_analyze_api():
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(analyze_ui_payload(payload))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400

@app.post('/api/chemistry/scale-tds')
def chemistry_scale_tds_api():
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(scale_to_tds(_composition_from_payload(payload), payload.get('target_tds',0.0)))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400

@app.post('/api/chemistry/balance')
def chemistry_balance_api():
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(balance_composition(_composition_from_payload(payload), str(payload.get('ion','')), payload.get('temperature_c',25.0), payload.get('feed_ph',8.0)))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400

@app.post('/api/chemistry/speciate-ph')
def chemistry_speciate_ph_api():
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(carbonate_speciation(_composition_from_payload(payload), payload.get('temperature_c',25.0), payload.get('feed_ph',8.0), payload.get('source_ph')))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400

@app.post('/api/chemistry/acid-dose')
def chemistry_acid_dose_api():
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(acid_dose_to_target_ph(
            _composition_from_payload(payload), payload.get('temperature_c',25.0),
            payload.get('feed_ph',8.0), payload.get('target_ph',7.0),
            payload.get('acid_type','hcl'), payload.get('solution_strength_pct'),
            payload.get('solution_density_kg_l'), payload.get('reference_flow_m3h')
        ))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400


@app.post('/api/compute/calibrate-gpu')
def compute_gpu_calibrate_api():
    if CPU_ONLY_MODE:
        return jsonify({'ok': False, 'disabled': True, 'compute_mode': COMPUTE_MODE, 'reason': 'Optional OpenCL calibration is disabled in the hosted CPU deployment.'}), 409
    try:
        return jsonify(calibrate_gpu_break_even())
    except Exception as exc:
        return jsonify({'ok':False,'error':str(exc)}),500

@app.post('/api/optimize/plant')
@_calculation_guard
def optimize_plant_api():
    _require_feature('design_optimizer')
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(run_design_optimization(
            dict(payload.get('data') or {}),
            payload.get('objective','min_sec'),
            payload.get('screen_candidates',4096),
            payload.get('validate_candidates',24),
            payload.get('mode','multistage')
        ))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({'error':str(exc)}),400

@app.post('/api/economics')
def economics():
    _require_economics_authorization()
    try:
        return jsonify(economic_analysis(request.get_json(force=True)))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/economics/report-snapshot')
def create_economics_report_snapshot():
    """Calculate once and freeze the sole source for every report format."""
    _require_feature('economics')
    try:
        model_input = request.get_json(force=True) or {}
        snapshot = build_snapshot(model_input, economic_analysis(model_input))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return jsonify({'error': str(exc)}), 400
    token = secrets.token_urlsafe(32)
    with _economics_report_lock:
        _economics_report_snapshots[token] = snapshot
    base = f"/api/economics/report/{token}"
    return jsonify({'token': token, 'snapshot_id': snapshot['snapshot_id'], 'calculation_id': snapshot['calculation_id'], 'json_url': base + '.json', 'xlsx_url': base + '.xlsx', 'executive_pdf_url': base + '/executive.pdf', 'full_pdf_url': base + '/full.pdf'}), 201


def _economics_snapshot(token: str) -> dict:
    _require_feature('economics')
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", token or ""):
        abort(404)
    with _economics_report_lock:
        snapshot = _economics_report_snapshots.get(token)
    if snapshot is None: abort(404)
    return snapshot


@app.get('/api/economics/report/<token>.json')
def economics_snapshot_export(token):
    snapshot = _economics_snapshot(token)
    return app.response_class(snapshot_json(snapshot), mimetype='application/json', headers={'Content-Disposition': 'attachment; filename="total-water-economics-snapshot.json"'})


@app.get('/api/economics/report/<token>.xlsx')
def economics_workbook_export(token):
    return send_file(io.BytesIO(build_workbook(_economics_snapshot(token))), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='total-water-economics.xlsx')


@app.get('/api/economics/report/<token>/<report_type>.pdf')
def economics_pdf_export(token, report_type):
    if report_type not in {'executive', 'full'}: abort(404)
    return send_file(io.BytesIO(build_pdf(_economics_snapshot(token), report_type)), mimetype='application/pdf', as_attachment=True, download_name=f'total-water-economics-{report_type}.pdf')

@app.get('/api/compute/capabilities')
def compute_capabilities():
    return jsonify(hardware_info())

@app.get('/api/compute/status')
def compute_status_api():
    status = compute_status()
    if app.config.get("AUTH_ENABLED", False) and status.get("active"):
        owner = _request_owner_key()
        with _calculation_owner_lock:
            active_owner = _active_calculation_owner
        if active_owner and active_owner != owner and not getattr(current_user, "is_admin", False):
            return jsonify({
                "active": True,
                "owned_by_another_user": True,
                "phase": "Another user's engineering calculation is running",
                "progress_total": 0,
                "progress_completed": 0,
            })
    return jsonify(status)

@app.post('/api/compute/cancel')
def compute_cancel_api():
    owner = _request_owner_key()
    with _calculation_owner_lock:
        active_owner = _active_calculation_owner
    if app.config.get("AUTH_ENABLED", False):
        if active_owner and active_owner != owner and not getattr(current_user, "is_admin", False):
            return jsonify({"error": "You cannot cancel another user's calculation."}), 403
    payload = request.get_json(silent=True) or {}
    run_id = payload.get('run_id')
    try:
        run_id = None if run_id in (None, '') else int(run_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'run_id must be an integer when supplied.'}), 400
    return jsonify(request_compute_cancel(
        run_id, hard=True, owner=owner, allow_pending=active_owner == owner
    ))

@app.post('/api/compute/gpu-test')
@_calculation_guard
def compute_gpu_test_api():
    if CPU_ONLY_MODE:
        return jsonify({'ok': False, 'disabled': True, 'compute_mode': COMPUTE_MODE, 'reason': 'Optional OpenCL validation is disabled in the hosted CPU deployment.'}), 409
    payload = request.get_json(silent=True) or {}
    begin_compute_run('gpu-self-test', 1, 1, 'opencl-gpu', owner=_request_owner_key())
    try:
        result = gpu_self_test(payload.get('points', 32768))
        update_compute_run(completed_delta=1, failed_delta=0 if result.get('ok') else 1, backend=result.get('backend', 'opencl-gpu'))
        finish_compute_run(fallback=not bool(result.get('ok')), fallback_reason=result.get('reason', ''))
        return jsonify(result)
    except Exception as exc:
        update_compute_run(completed_delta=1, failed_delta=1)
        finish_compute_run(fallback=True, fallback_reason=str(exc))
        return jsonify({'ok': False, 'error': str(exc)}), 500



def _result_internal(result, key, kind):
    value = result.get(key)
    if value is None or value == "":
        raise ValueError(f"Design result is missing {key}.")
    if kind == "flow":
        return flow_to_m3h(value, result.get("flow_unit", "m3/h"))
    if kind == "pressure":
        return pressure_to_bar(value, result.get("pressure_unit", "bar"))
    return float(value)


def _pick_design_result(first_results, cv_key, requested="auto"):
    ok = [x for x in first_results if x.get("ok") and isinstance(x.get("result"), dict) and x["result"].get(cv_key) is not None]
    if not ok:
        raise ValueError(f"No successful turbo cases contain {cv_key}.")
    if requested not in (None, "", "auto"):
        wanted = str(requested)
        for item in ok:
            if str(item.get("case_id", item.get("id", ""))) == wanted:
                return item
        raise ValueError(f"Requested design case {requested} did not calculate successfully.")
    return min(ok, key=lambda x: float(x["result"][cv_key]))


def _locked_design_fields(mode, design_item, prefix=""):
    r = design_item["result"]
    curve = str(design_item.get("data", {}).get("curve", "cfd")) == "cfd"
    if mode == "single":
        q_pump = _result_internal(r, "feed_flow", "flow")
        q_turb = _result_internal(r, "reject_flow_1", "flow")
        p_pump = _result_internal(r, "membrane_pressure_1", "pressure")
        p_turb = _result_internal(r, "reject_pressure_1", "pressure")
        cv = float(r["cv_required"])
    elif mode == "interstage":
        q_pump = _result_internal(r, "reject_flow_1", "flow")
        q_turb = _result_internal(r, "reject_flow_2", "flow")
        p_pump = _result_internal(r, "membrane_pressure_2", "pressure")
        p_turb = _result_internal(r, "reject_pressure_2", "pressure")
        cv = float(r["cv_required"])
    elif mode == "biturbo" and prefix == "inter_":
        q_pump = _result_internal(r, "reject_flow_1", "flow")
        q_turb = _result_internal(r, "reject_flow_2", "flow")
        p_pump = _result_internal(r, "membrane_pressure_2", "pressure")
        p_turb = _result_internal(r, "reject_pressure_2", "pressure")
        cv = float(r["inter_cv_required"])
    elif mode == "biturbo" and prefix == "feed_":
        q_pump = _result_internal(r, "feed_flow", "flow")
        q_turb = _result_internal(r, "reject_flow_1", "flow")
        p_pump = _result_internal(r, "membrane_pressure_1", "pressure")
        p_turb = _result_internal(r, "brine_discharge_pressure", "pressure")
        cv = float(r["feed_cv_required"])
    else:
        raise ValueError("Unsupported turbo design mapping.")
    aux_key = f"{prefix}aux_range" if prefix else "aux_range"
    aux_range = float(design_item.get("data", {}).get(aux_key, 0.85) or 0.85)
    return {
        f"{prefix}off_design_model": "spreadsheet",
        f"{prefix}cvc": cv,
        f"{prefix}aux_range": aux_range,
        f"{prefix}design_qf": q_pump,
        f"{prefix}design_qr": q_turb,
        f"{prefix}design_pm": p_pump,
        f"{prefix}design_pr": p_turb,
        f"{prefix}design_overall_eff": turbo_efficiency(q_pump, curve),
    }


def _gpu_refresh_turbo_design_metrics(mode, rows):
    """Vector-check turbo Cv duties across a multi-case design pass.

    Hosted CPU mode uses the vectorized CPU implementation. Optional local
    OpenCL screening remains available in workstation builds and is always
    validated against the same authoritative CPU equations.
    """
    specs=[]
    for row in rows:
        if not row.get("ok") or not isinstance(row.get("result"), dict):
            continue
        r=row["result"]; d=row.get("data") or {}
        fu=d.get("flow_unit", "m3/h"); pu=d.get("pressure_unit", "bar")
        try:
            if mode == "single":
                specs.append((row, "", flow_to_m3h(float(r["feed_flow"]),fu), flow_to_m3h(float(r["turbine_flow"]),fu), pressure_to_bar(float(r["turbine_dp"]),pu), float(r.get("sg",1.025))))
            elif mode == "interstage":
                specs.append((row, "", flow_to_m3h(float(r["reject_flow_1"]),fu), flow_to_m3h(float(r["turbine_flow"]),fu), pressure_to_bar(float(r["turbine_dp"]),pu), float(r.get("sg",1.025))))
            elif mode == "biturbo":
                specs.append((row, "inter_", flow_to_m3h(float(r["reject_flow_1"]),fu), flow_to_m3h(float(r["interstage_turbine_flow"]),fu), pressure_to_bar(float(r["interstage_turbine_dp"]),pu), float(r.get("inter_sg",1.025))))
                specs.append((row, "feed_", flow_to_m3h(float(r["feed_flow"]),fu), flow_to_m3h(float(r["feed_turbine_flow"]),fu), pressure_to_bar(float(r["feed_turbine_dp"]),pu), float(r.get("feed_sg",1.025))))
        except (KeyError, TypeError, ValueError):
            continue
    if len(specs) < 2:
        return {"backend":"cpu-inline", "points":len(specs), "device":None}
    metrics=turbo_metrics_batch([x[2] for x in specs],[x[3] for x in specs],[x[4] for x in specs],[x[5] for x in specs],preference="auto")
    cvs=metrics.get("cv",[])
    for spec,cv in zip(specs,cvs):
        row,prefix,*_=spec
        key=f"{prefix}cv_required" if prefix else "cv_required"
        cpu=float(row["result"].get(key,cv) or cv)
        # OpenCL is accepted only after the compute-engine CPU validation; keep a
        # second engineering guard here before using it for design selection.
        if abs(float(cv)-cpu) <= max(2e-5,2e-5*max(abs(cpu),1.0)):
            row["result"][key]=float(cv)
        row["result"][f"{prefix}design_screen_backend" if prefix else "design_screen_backend"]=metrics.get("backend","cpu-vector")
        row["result"][f"{prefix}design_screen_device" if prefix else "design_screen_device"]=metrics.get("device")
    return {"backend":metrics.get("backend","cpu-vector"),"points":len(specs),"device":metrics.get("device")}


def _run_turbo_design_cases(mode, cases, design_case="auto", inter_design_case="auto", feed_design_case="auto", workers=None):
    if mode not in {"single", "interstage", "biturbo"}:
        raise ValueError("Turbo design-case mode must be single, interstage or biturbo.")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must contain at least one case payload.")
    first_tasks=[]
    normalized=[]
    for idx, item in enumerate(cases, start=1):
        cid=item.get("case_id", idx)
        data=dict(item.get("data") or {})
        # First pass deliberately removes any previous lock so every case exposes its natural required Cvt.
        for k in ("off_design_model","design_qf","design_qr","design_pm","design_pr","design_overall_eff",
                  "inter_off_design_model","inter_design_qf","inter_design_qr","inter_design_pm","inter_design_pr","inter_design_overall_eff",
                  "feed_off_design_model","feed_design_qf","feed_design_qr","feed_design_pm","feed_design_pr","feed_design_overall_eff"):
            data.pop(k, None)
        for k in ("cvc","inter_cvc","feed_cvc"):
            data[k] = ""
        normalized.append({"case_id":cid,"data":data})
        first_tasks.append({"id":str(cid),"mode":mode,"data":data})
    first_batch=calculate_batch(first_tasks, workers=workers)
    by_id={str(x.get("id")):x for x in first_batch.get("results",[])}
    first=[]
    for item in normalized:
        row=dict(by_id.get(str(item["case_id"]), {"id":str(item["case_id"]),"ok":False,"error":"Calculation missing"}))
        row["case_id"]=item["case_id"]; row["data"]=item["data"]
        first.append(row)

    turbo_vector_screen=_gpu_refresh_turbo_design_metrics(mode, first)
    design_summary={"selection_rule":"minimum required Cvt", "vector_screen":turbo_vector_screen}
    if mode in {"single","interstage"}:
        d=_pick_design_result(first,"cv_required",design_case)
        fields=_locked_design_fields(mode,d)
        design_summary.update({"case_id":d["case_id"],"cv_required":float(d["result"]["cv_required"]),
                               "cvc":fields["cvc"],"cvo":float(d["result"].get("cv_open", d["result"].get("cvo",0)) or 0),
                               "overall_eff":fields["design_overall_eff"],
                               "selection_rule":"manual override" if str(design_case)!="auto" else "minimum required Cvt"})
        locked_by_case=[(item,fields) for item in normalized]
    else:
        di=_pick_design_result(first,"inter_cv_required",inter_design_case)
        df=_pick_design_result(first,"feed_cv_required",feed_design_case)
        fi=_locked_design_fields("biturbo",di,"inter_")
        ff=_locked_design_fields("biturbo",df,"feed_")
        fields={**fi,**ff}
        design_summary={
            "selection_rule":"minimum required Cvt per turbine unless manually overridden",
            "vector_screen":turbo_vector_screen,
            "interstage":{"case_id":di["case_id"],"cv_required":float(di["result"]["inter_cv_required"]),"cvc":fi["inter_cvc"],"overall_eff":fi["inter_design_overall_eff"],"selection_rule":"manual override" if str(inter_design_case)!="auto" else "minimum required Cvt"},
            "feed":{"case_id":df["case_id"],"cv_required":float(df["result"]["feed_cv_required"]),"cvc":ff["feed_cvc"],"overall_eff":ff["feed_design_overall_eff"],"selection_rule":"manual override" if str(feed_design_case)!="auto" else "minimum required Cvt"},
        }
        locked_by_case=[(item,fields) for item in normalized]

    second_tasks=[]
    for item, lock in locked_by_case:
        data=dict(item["data"]); data.update(lock)
        second_tasks.append({"id":str(item["case_id"]),"mode":mode,"data":data})
    final_batch=calculate_batch(second_tasks, workers=workers)
    final_results=[]
    for row in final_batch.get("results",[]):
        cid=row.get("id")
        if row.get("ok") and isinstance(row.get("result"),dict):
            r=row["result"]; r["turbo_design_locked"]=True
            if mode in {"single","interstage"}:
                r["design_case_id"]=design_summary["case_id"]
                r["is_design_case"]=str(cid)==str(design_summary["case_id"])
            else:
                r["inter_design_case_id"]=design_summary["interstage"]["case_id"]
                r["feed_design_case_id"]=design_summary["feed"]["case_id"]
                r["is_inter_design_case"]=str(cid)==str(design_summary["interstage"]["case_id"])
                r["is_feed_design_case"]=str(cid)==str(design_summary["feed"]["case_id"])
        final_results.append(row)
    backend_label=str(final_batch.get("backend") or "cpu")
    if turbo_vector_screen.get("backend") == "opencl-gpu":
        backend_label += " + opencl-gpu"
    return {"mode":mode,"design":design_summary,"locked_fields":fields,"results":final_results,
            "first_pass":[{"case_id":x["case_id"],"ok":x.get("ok",False),"cv_required":(x.get("result") or {}).get("cv_required"),
                           "inter_cv_required":(x.get("result") or {}).get("inter_cv_required"),"feed_cv_required":(x.get("result") or {}).get("feed_cv_required"),
                           "error":x.get("error","")} for x in first],
            "backend":backend_label,"workers":final_batch.get("workers"),
            "gpu_design_screen":turbo_vector_screen,
            "fallback":final_batch.get("fallback",False),"elapsed_seconds":first_batch.get("elapsed_seconds",0)+final_batch.get("elapsed_seconds",0)}

@app.post('/api/turbo/design-cases')
@_calculation_guard
def turbo_design_cases_api():
    # Gold ERD users use this endpoint to lock a turbine design duty across
    # configured cases.  The Platinum Scenario Matrix is separately gated at
    # /api/calculate-batch and in the UI.
    _require_feature('erd')
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(_run_turbo_design_cases(str(payload.get("mode","")), payload.get("cases") or [],
                                               payload.get("design_case","auto"), payload.get("inter_design_case","auto"),
                                               payload.get("feed_design_case","auto"), payload.get("workers")))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return jsonify({"error":str(exc)}),400




from flux_optimizer import run_flux_optimization

@app.post('/api/turbo/optimize-flux')
@_calculation_guard
def turbo_optimize_flux_api():
    _require_feature('erd')
    payload=request.get_json(force=True) or {}
    try:
        return jsonify(run_flux_optimization(str(payload.get("mode","")), dict(payload.get("data") or {}), payload.get("strategy","maintain_product"), payload.get("max_feed_change_pct",15.0), payload.get("max_recovery_change_pp",5.0)))
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return jsonify({"error":str(exc)}),400

@app.post('/api/flowsheet/solve')
@_calculation_guard
def flowsheet_solve_api():
    context=_require_feature('multi_pass')
    payload=request.get_json(force=True) or {}
    if payload.get('recycles'): _require_feature('advanced_recycle')
    if any(isinstance(p,dict) and isinstance(p.get('split_permeate'),dict) and p['split_permeate'].get('enabled') for p in (payload.get('passes') or [])):
        _require_feature('split_partial_permeate')
    start=time.perf_counter(); cpu0=time.process_time()
    try:
        result=solve_payload(payload,effective_tier=context.effective_tier)
        record_telemetry('calculation_completed',application='ro',module='multi_pass_flowsheet',success=True,duration_ms=(time.perf_counter()-start)*1000,cpu_seconds=time.process_time()-cpu0,metadata={'tier':context.effective_tier,'solver':result.get('method',''),'iterations':result.get('iterations')})
        db.session.commit()
        return jsonify(result)
    except PermissionError as exc:
        return jsonify({'error':str(exc),'error_type':'EntitlementError'}),403
    except (FlowsheetConvergenceError,ValueError,NotImplementedError) as exc:
        record_telemetry('calculation_failed',application='ro',module='multi_pass_flowsheet',success=False,duration_ms=(time.perf_counter()-start)*1000,cpu_seconds=time.process_time()-cpu0,metadata={'tier':context.effective_tier,'reason':type(exc).__name__})
        db.session.commit()
        return jsonify({'error':str(exc),'error_type':type(exc).__name__}),409 if isinstance(exc,FlowsheetConvergenceError) else 400


@app.post('/api/calculate-batch')
@_calculation_guard
def calculate_batch_api():
    _require_feature('scenario_matrix')
    payload = request.get_json(force=True) or {}
    tasks = payload.get('tasks') or []
    if not isinstance(tasks, list):
        return jsonify({'error': 'tasks must be an array.'}), 400
    try:
        workers = payload.get('workers')
        return jsonify(calculate_batch(tasks, workers=workers))
    except CalculationCancelled as exc:
        return jsonify({'error': str(exc), 'cancelled': True}), 409
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return jsonify({'error': str(exc)}), 400

@app.post('/api/compute/turbo-batch')
@_calculation_guard
def compute_turbo_batch_api():
    _require_feature('erd')
    payload = request.get_json(force=True) or {}
    try:
        return jsonify(turbo_metrics_batch(
            payload.get('qf') or [], payload.get('qr') or [],
            payload.get('dp_bar') or [], payload.get('sg') or [],
            preference=payload.get('preference', 'auto')
        ))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return jsonify({'error': str(exc)}), 400

@app.post('/api/calculate/<mode>')
@_calculation_guard
def calculate(mode):
    if mode not in CALCS:
        return jsonify({'error': 'Unknown calculation mode.'}), 404
    payload = request.get_json(force=True) or {}
    # Plant Design is always a real membrane projection. Legacy projects may
    # contain membrane_coupling=off, but the normal multistage workflow ignores
    # that obsolete value and uses the coupled membrane mass balance.
    if mode == 'multistage':
        payload['membrane_coupling'] = 'on'
    requested_feature = str(payload.get('_entitlement_feature') or '').strip()
    if requested_feature:
        if requested_feature not in FEATURE_MIN_TIER:
            return jsonify({'error': f'Unknown entitlement feature: {requested_feature}'}), 400
        _require_feature(requested_feature)
    if mode in {'single','px','interstage_px','interstage','biturbo','dweer','pelton'}:
        _require_feature('erd')
    if mode == 'multistage' and str(payload.get('design_mode','manual') or 'manual').lower() == 'auto':
        _require_feature('auto_design')
    if mode == 'multistage' and str(payload.get('pump_curve_basis','auto') or 'auto').lower() in {'vcmp','vcmp_auto','database'}:
        _require_feature('vcmp_pump_selection')
    truthy = lambda v: v is True or str(v).lower() in {'1','true','yes','on','coupled'}
    basis = str(payload.get('solve_basis','pressure') or 'pressure').lower()
    accelerated_interstage = (mode == 'interstage' and truthy(payload.get('membrane_coupling'))
                              and truthy(payload.get('solve_stage_pressures'))
                              and not truthy(payload.get('_disable_nested_cpu_pool')) and not truthy(payload.get('_disable_inner_parallel')))
    calc_started_at=time.perf_counter(); calc_cpu0=time.process_time()
    try:
        # A fixed-pressure duty has one sequential membrane state. Do not create
        # neighboring dummy/sensitivity jobs merely to inflate CPU utilization.
        # Multicore is engaged only when the solver has independent pressure
        # candidates, scenarios or technology cases to evaluate.
        root_basis = basis in {'product','permeate','flow','recovery','r'}
        stage_count = max(1, min(4, int(float(payload.get('stage_count', 1) or 1))))
        design_mode = str(payload.get('design_mode', 'manual') or 'manual').lower()
        interstage_control = str(payload.get('interstage_control_objective', 'manual') or 'manual').lower()
        # v18.3.9: routine Plant Design duty points must remain in-process.  The
        # Windows spawn cost of creating a worker pool can dwarf the actual RO
        # calculation (e.g. a 1-stage 45% recovery solve).  Parallel pressure
        # search is reserved for Auto Design / genuinely coupled automatic
        # interstage-control work and remains available as a solver fallback.
        simple_manual_plant_root = (
            mode in {'multistage','dweer','pelton'} and root_basis and design_mode != 'auto'
            and (stage_count == 1 or interstage_control == 'manual')
            and not truthy(payload.get('scenario_matrix_enabled'))
        )
        if simple_manual_plant_root:
            payload['_prefer_serial_root'] = True
            planned_jobs=1; planned_workers=1; planned_backend='cpu-main'
        elif root_basis or accelerated_interstage:
            planned_jobs=max(2,MIN_SINGLE_CPU_WORKERS)
            planned_workers=select_worker_count(planned_jobs, DEFAULT_CPU_WORKERS, enforce_quarter_floor=True)
            planned_backend='cpu-multiprocess' if planned_workers>1 else 'cpu-main'
        else:
            planned_jobs=1; planned_workers=1; planned_backend='cpu-main'
        begin_compute_run(f'{mode}-single', planned_jobs, planned_workers, planned_backend,
                          owner=_request_owner_key())
        result = CALCS[mode](payload)
        # A one-job serial root solve has no inner worker batch to advance the
        # monitor, so complete that single engineering job here. Parallel trial
        # batches continue to update progress from compute_engine.
        if planned_jobs == 1 or (basis == 'pressure' and not accelerated_interstage):
            update_compute_run(completed_delta=1, backend=result.get('pressure_search_backend', planned_backend), workers=1 if planned_jobs==1 else planned_workers)
        final = finish_compute_run()
        result['compute_backend'] = result.get('pressure_search_backend') or result.get('stage2_pressure_search_backend') or planned_backend
        if result.get('stage2_gpu_screen_backend') == 'opencl-gpu':
            result['compute_backend'] += ' + opencl-gpu'
        result['compute_elapsed_seconds'] = final.get('duration_seconds', 0.0)
        result['minimum_parallel_workers_policy']=MIN_SINGLE_CPU_WORKERS
        result['parallel_worker_policy_note']='50%-CPU floor applies only when enough independent jobs exist; fixed-pressure single-state solves do not create dummy work.'
        record_telemetry('calculation_completed',application='ro',module=mode,success=True,duration_ms=(time.perf_counter()-calc_started_at)*1000,cpu_seconds=time.process_time()-calc_cpu0,metadata={'tier':_entitlement_context().effective_tier,'solver':result.get('solver_method') or result.get('pressure_search_backend',''),'iterations':result.get('pressure_solve_iterations')})
        db.session.commit()
        return jsonify(result)
    except CalculationCancelled as exc:
        finish_compute_run(cancelled=True, fallback_reason=str(exc))
        record_telemetry('calculation_failed',application='ro',module=mode,success=False,duration_ms=(time.perf_counter()-calc_started_at)*1000,cpu_seconds=time.process_time()-calc_cpu0,metadata={'reason':'cancelled'}); db.session.commit()
        return jsonify({'error': str(exc), 'cancelled': True}), 409
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        update_compute_run(completed_delta=1, failed_delta=1)
        finish_compute_run(fallback=True, fallback_reason=str(exc))
        record_telemetry('calculation_failed',application='ro',module=mode,success=False,duration_ms=(time.perf_counter()-calc_started_at)*1000,cpu_seconds=time.process_time()-calc_cpu0,metadata={'reason':type(exc).__name__}); db.session.commit()
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        update_compute_run(completed_delta=1, failed_delta=1)
        finish_compute_run(fallback=True, fallback_reason=str(exc))
        app.logger.exception("Unexpected %s calculation failure", mode, exc_info=exc)
        return jsonify({
            'error': 'The engineering calculation encountered an internal error. Save the project and submit an issue report if it repeats.',
            'error_type': 'InternalCalculationError',
            'guidance': 'Review the requested membrane, flow and pressure duty, then retry. Detailed diagnostics were written to the server log.'
        }), 500

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
