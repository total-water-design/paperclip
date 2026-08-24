"""Production WSGI entry point for the RO-first Total Water Design Suite Alpha.

This composition preserves the validated specialist engineering runtime while
adding the frozen Suite Core platform services. Existing TOTALRO_* environment
names remain supported; Suite-owned services use TWDS_* configuration where
appropriate.
"""
import os

os.environ.setdefault("TOTALRO_DEPLOYMENT_MODE", "server")
os.environ.setdefault("TOTALRO_AUTH_ENABLED", "1")
os.environ.setdefault("TOTALRO_COMPUTE_MODE", "cpu")
os.environ.setdefault("TOTALRO_MAX_ENGINEERING_WORKERS", "auto")
# Suite Core uses this sentinel for an unknown host. The newer Alpha metrics
# audit removes the sentinel before resolving the real host from configuration
# or IMDSv2, so an EC2 instance type is never fabricated.
os.environ.setdefault("TOTALRO_EC2_INSTANCE_TYPE", "unknown")
# Hosted Suite policy: two-step verification is mandatory for users and admins.
os.environ["TWDS_MFA_REQUIRED"] = "1"

# Preserve the validated Alpha chemistry upgrade before Flask imports
# calculations.py. This keeps the existing RO public API while retaining the
# current chemistry/speciation behavior.
from runtime_chemistry_upgrade import install_runtime_chemistry  # noqa: E402

CHEMISTRY_UPGRADE = install_runtime_chemistry()

from flask import jsonify, request  # noqa: E402
from app import app, CALCS, _require_feature  # noqa: E402
from auth import db  # noqa: E402

# Validated Total RO / specialist registrations.
from ccro_runtime import register_ccro_runtime  # noqa: E402
from batch_ro_runtime import register_batch_ro_runtime  # noqa: E402
import ro_customer_surface as ro_customer_surface_module  # noqa: E402
from ro_customer_surface import register_ro_customer_surface  # noqa: E402
from ro_suite_ui_contract import register_ro_suite_ui_contract  # noqa: E402
from mobile_access import init_mobile_access  # noqa: E402
from zld_integration import register_total_zld_design  # noqa: E402
import ro_economic_summary_v1 as ro_economic_summary  # noqa: E402
from ro_economic_pump_adapter import install_ro_economic_pump_adapter  # noqa: E402
from ro_economic_ui import register_ro_economic_ui  # noqa: E402

# Frozen Suite Core platform services.
from suite_commercial import init_suite_commercial  # noqa: E402
from suite_communications import init_suite_communications  # noqa: E402
from suite_feedback import init_suite_feedback  # noqa: E402
from suite_feedback_hardening import init_suite_feedback_hardening  # noqa: E402
from suite_feedback_state import init_suite_feedback_state  # noqa: E402
from suite_mfa import init_suite_mfa  # noqa: E402
import suite_metrics as suite_metrics_module  # noqa: E402
from suite_metrics import register_suite_metrics  # noqa: E402
from suite_metrics_hardening import apply_suite_metrics_hardening  # noqa: E402
from suite_metrics_audit import apply_suite_metrics_audit_corrections  # noqa: E402
from suite_reports import init_suite_reports  # noqa: E402

# Dedicated RO process configurations. Conventional RO remains authoritative;
# CCRO and Batch RO are additive configurations within Total RO Design.
register_ccro_runtime(app, CALCS)
register_batch_ro_runtime(app, CALCS)

# The validated RO customer-surface layer is retained for output sanitization,
# but its legacy before-request feedback transport is neutralized. Suite Core's
# database-backed feedback workflow is the authoritative platform workflow.
ro_customer_surface_module._neutral_issue_report = lambda _app: None
register_ro_customer_surface(app)

# Native RO adoption of the Suite UI/UX Contract. The mature RO template remains
# authoritative; no broad structural overlay or obsolete ro_suite_contract.css
# is loaded.
register_ro_suite_ui_contract(app)

# Preserve current Alpha mobile/PWA enforcement foundation and ZLD integration.
init_mobile_access(app)
register_total_zld_design(app)

# Preserve the validated RO economics adapter and routes.
install_ro_economic_pump_adapter(ro_economic_summary)
ro_economic_summary.register_ro_economic_summary(app)
register_ro_economic_ui(app, _require_feature)

# Metrics reconciliation: frozen Suite Core hardening runs first. The legacy
# "unknown" sentinel is then removed so the newer Alpha audit can resolve a real
# configured/IMDSv2 host or report it as unverified. The Alpha audit is applied
# last so its host-identity safeguards remain authoritative.
apply_suite_metrics_hardening()
if str(os.environ.get("TOTALRO_EC2_INSTANCE_TYPE", "")).strip().lower() == "unknown":
    os.environ.pop("TOTALRO_EC2_INSTANCE_TYPE", None)
apply_suite_metrics_audit_corrections(suite_metrics_module)
register_suite_metrics(app)

# Suite Core cross-application services are additive around specialist engines.
# The feedback hardening layer is initialized only after both base feedback
# blueprints exist. It atomically commits the durable GitHub/send claim before
# crossing an external boundary, so concurrent workers cannot emit duplicates.
init_suite_mfa(app)
init_suite_feedback(app)
init_suite_feedback_state(app)
init_suite_feedback_hardening(app)
init_suite_communications(app)
init_suite_reports(app)
init_suite_commercial(app)

app.config["SUITE_FEEDBACK_ENABLED"] = True
app.config["SUITE_MFA_REQUIRED"] = True

# Retire the old RO-specific transport endpoint. The mature RO browser is kept
# compatible by a tiny bridge script that translates its diagnostic payload to
# Suite Core's authoritative /api/suite/feedback/report contract. No feedback
# record is stored or emailed through the legacy endpoint.
_RO_FEEDBACK_BRIDGE = "/static/ro_suite_feedback_bridge.js"


@app.before_request
def _retire_ro_legacy_feedback_transport():
    if request.path == "/api/feedback/report" and request.method == "POST":
        return jsonify({
            "error": "This legacy feedback endpoint has been retired.",
            "canonical_endpoint": "/api/suite/feedback/report",
        }), 410
    return None


@app.after_request
def _inject_ro_suite_feedback_bridge(response):
    if request.path != "/ro" or request.method != "GET" or response.status_code != 200:
        return response
    if "text/html" not in str(response.headers.get("Content-Type", "")).lower():
        return response
    html = response.get_data(as_text=True)
    if _RO_FEEDBACK_BRIDGE in html or "</body>" not in html:
        return response
    response.set_data(html.replace("</body>", f'<script src="{_RO_FEEDBACK_BRIDGE}"></script>\n</body>', 1))
    response.headers["Content-Length"] = str(len(response.get_data()))
    return response


# All Suite Core tables and narrow schema additions are additive. Never drop,
# truncate, recreate, or replace existing customer data during startup.
with app.app_context():
    db.create_all()
