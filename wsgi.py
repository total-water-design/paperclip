"""Production WSGI entry point for Total Water Design Suite v0.25.

The suite hosts the authenticated account/launcher shell and the Total RO Design
v0.2 engineering application in one Flask deployment. Existing TOTALRO_*
environment names are retained for in-place AWS compatibility.
"""
import os

os.environ.setdefault("TOTALRO_DEPLOYMENT_MODE", "server")
os.environ.setdefault("TOTALRO_AUTH_ENABLED", "1")
os.environ.setdefault("TOTALRO_COMPUTE_MODE", "cpu")
os.environ.setdefault("TOTALRO_MAX_ENGINEERING_WORKERS", "auto")

# Install the advanced chemistry layer before Flask imports calculations.py.
# This preserves the existing public API while ensuring every hosted Alpha
# calculation uses the upgraded pH/speciation/neutral-ammonia chemistry.
from runtime_chemistry_upgrade import install_runtime_chemistry  # noqa: E402

CHEMISTRY_UPGRADE = install_runtime_chemistry()

from app import app, CALCS, _require_feature  # noqa: E402
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
import suite_metrics as suite_metrics_module  # noqa: E402
from suite_metrics import register_suite_metrics  # noqa: E402
from suite_metrics_audit import apply_suite_metrics_audit_corrections  # noqa: E402

# Total RO specialist configurations are registered against the current CALCS
# registry without replacing conventional RO, chemistry, project, or Suite
# services. CCRO and Batch RO remain process configurations inside Total RO.
register_ccro_runtime(app, CALCS)
register_batch_ro_runtime(app, CALCS)

# Suite Core is the authoritative owner of feedback transport/storage/workflow.
# The validated RO customer-surface module also contains a legacy issue-report
# interceptor, so disable that interceptor at this integration boundary while
# retaining the RO-owned customer-safe JavaScript/API/report sanitization.
ro_customer_surface_module._neutral_issue_report = lambda _app: None
register_ro_customer_surface(app)

# Adopt the validated non-structural RO UI/UX adapter. The mature RO template
# remains authoritative; this does not create a second Suite/project shell.
register_ro_suite_ui_contract(app)

# The phone-browser gate is disabled unless TOTALRO_REQUIRE_MOBILE_APP_ON_PHONE
# is explicitly enabled. Native attestation verifiers will be injected here
# when the signed iOS and Android shells are introduced.
init_mobile_access(app)

# Total ZLD Design remains an administrator engineering preview while the
# specialist application is in development. Registration is additive and reuses
# the Suite authentication/entitlement infrastructure without replacing RO or
# shared chemistry runtime wiring.
register_total_zld_design(app)

# Normalize heterogeneous solved pump-duty fields before the RO economics routes
# are registered. This prevents aggregate electrical duty from being counted on
# top of component duties and preserves parallel pump-bank unit counts when the
# shared pump engine propagates them. This adapter affects CAPEX interpretation
# only; membrane, pump-performance, chemistry, CCRO, and legacy economics remain
# authoritative and unchanged.
install_ro_economic_pump_adapter(ro_economic_summary)

# RO-scope CAPEX/OPEX and its standardized Total Economic Design handoff are
# additive consumers of solved engineering results. Preserve Alpha's existing
# economics entitlement pattern through the canonical _require_feature guard.
ro_economic_summary.register_ro_economic_summary(app)
register_ro_economic_ui(app, _require_feature)

# Suite Metrics is registered last so all existing Alpha application, chemistry,
# mobile, ZLD and economics wiring remains authoritative. Apply the audited
# concurrency/hourly/host-identity corrections before installing the routes.
apply_suite_metrics_audit_corrections(suite_metrics_module)
register_suite_metrics(app)
