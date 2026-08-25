from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "TOTAL_WATER_ACADEMY_MODULAR_COMMERCE_PDH_CEH_ROADMAP_v1.0.md"
PRICING_JS = ROOT / "static" / "academy_pricing.js"
INDEX = ROOT / "templates" / "academy" / "index.html"
LEVEL = ROOT / "templates" / "academy" / "level.html"
BASE = ROOT / "templates" / "academy" / "base.html"
I18N = ROOT / "academy_i18n.py"


def _text(path: Path) -> str:
    assert path.exists(), f"Missing Academy modular-commerce asset: {path}"
    return path.read_text(encoding="utf-8")


def test_roadmap_defines_module_as_individual_purchasable_course():
    text = _text(ROADMAP)
    assert "The purchasable unit is the **module/course**" in text
    assert "Choose-Your-Course Journey" in text
    assert "Full Diploma Journey" in text
    assert "individually completed courses" in text


def test_foundation_levels_are_planned_permanently_free():
    text = _text(ROADMAP)
    assert "Level 1 — Water Treatment Foundations & Water Quality" in text
    assert "Level 2 — Core Unit Operations, Balances & Transport Fundamentals" in text
    assert "target_price_usd = 0" in text
    assert "always_free = true" in text


def test_alpha_is_free_but_future_target_prices_are_visible_in_all_locales():
    roadmap = _text(ROADMAP)
    index = _text(INDEX)
    level = _text(LEVEL)
    js = _text(PRICING_JS)
    i18n = _text(I18N)
    assert "all Academy courses remain free to eligible Alpha testers" in roadmap
    assert "TARGET LAUNCH PRICE" in roadmap
    assert "academy_tr('free_alpha')" in index
    assert "data-academy-course-price" in level
    assert "node.dataset.labelTarget" in js
    assert '"free_alpha": "FREE DURING ALPHA"' in i18n
    assert '"price_target": "Free during Alpha · target launch ${price} one-time"' in i18n
    assert "Gratis durante Alpha" in i18n
    assert "مجاني خلال Alpha" in i18n


def test_exact_target_price_catalog_contains_40_paid_courses():
    js = _text(PRICING_JS)
    paid = re.findall(r'"(L(?:0[3-9]|10)-M\d{2})":\s*(\d+)', js)
    assert len(paid) == 40
    prices = {module_id: int(value) for module_id, value in paid}
    assert prices["L03-M01"] == 59
    assert prices["L04-M03"] == 129
    assert prices["L08-M04"] == 149
    assert prices["L10-M05"] == 199
    assert sum(prices.values()) == 3810


def test_free_foundation_catalog_contains_all_10_l01_l02_courses():
    js = _text(PRICING_JS)
    free_ids = set(re.findall(r'"(L0[12]-M\d{2})"', js.split("const FREE_FOUNDATION", 1)[1]))
    assert len(free_ids) == 10
    assert {f"L01-M0{i}" for i in range(1, 5)}.issubset(free_ids)
    assert {f"L02-M0{i}" for i in range(1, 7)}.issubset(free_ids)


def test_academy_does_not_implement_independent_billing_or_entitlements():
    text = _text(ROADMAP)
    assert "Suite Core remains the owner of authentication, entitlements, billing" in text
    assert "Academy must not create an independent payment or entitlement database" in text
    assert "academy.course.<MODULE_ID>" in text
    assert "individual course purchase is the primary commercial requirement" in text


def test_ui_loads_modular_pricing_asset_and_exposes_localized_courses_pricing_navigation():
    base = _text(BASE)
    i18n = _text(I18N)
    assert "academy_pricing.js" in base
    assert "academy_tr('courses_pricing')" in base
    assert "#course-catalog" in base
    assert '"courses_pricing": "Courses & Pricing"' in i18n
    assert '"courses_pricing": "Cursos y precios"' in i18n
    assert '"courses_pricing": "الدورات والأسعار"' in i18n


def test_guided_hours_are_not_automatically_pdh_ceu_credit_in_any_locale():
    roadmap = _text(ROADMAP)
    index = _text(INDEX)
    level = _text(LEVEL)
    i18n = _text(I18N)
    assert "Do not equate guided hours automatically with PDH" in roadmap
    assert "must not call those hours PDH, CEH or IACET CEU" in roadmap
    assert "academy_tr('pdh_ready_copy')" in index
    assert "academy_tr('guided_not_approved')" in level
    assert "We do not yet claim PDH, CEH or IACET CEU approval" in i18n
    assert "Aún no afirmamos aprobación PDH, CEH ni IACET CEU" in i18n
    assert "لا ندّعي حالياً اعتماد PDH أو CEH أو IACET CEU" in i18n


def test_pdh_ready_architecture_requires_outcomes_assessment_and_auditability():
    text = _text(ROADMAP)
    for phrase in (
        "measurable learning outcomes",
        "auditable learner participation",
        "knowledge checks and final assessment",
        "defined passing criteria",
        "end-of-course learner evaluation",
        "completion record/transcript",
        "certificate verification token",
    ):
        assert phrase in text


def test_roadmap_prohibits_universal_credit_claims_before_approval():
    text = _text(ROADMAP)
    assert "PDH approved in all 50 states" in text
    assert "CEH accepted everywhere" in text
    assert "guaranteed license-renewal credit" in text
    assert "PDH/CEH approval is planned and is not yet claimed" in text


def test_roadmap_defines_jurisdiction_approval_matrix():
    text = _text(ROADMAP)
    for phrase in (
        "provider approval required?",
        "course approval required?",
        "self-paced online acceptable?",
        "certificate fields",
        "record-retention period",
        "approval/registration number and expiration date",
    ):
        assert phrase in text


def test_florida_readiness_fields_are_present_without_claiming_approval():
    text = _text(ROADMAP)
    for field in (
        "learner PE/license number",
        "course number",
        "presenter/instructor",
        "completion date",
        "approved continuing-education hours",
        "brief course description",
        "certificate verification token",
    ):
        assert field in text
    assert "not a statement that Academy is currently a Florida-approved CE provider" in text


def test_iacet_is_future_provider_quality_path_not_current_claim():
    text = _text(ROADMAP)
    assert "IACET accredits **providers/organizations**, not an isolated course" in text
    assert "should not call a course an **IACET CEU course**" in text
    assert "one CEU is conventionally based on ten qualifying contact hours" in text


def test_alpha_price_feedback_is_explicitly_requested_but_optional():
    text = _text(ROADMAP)
    assert "Would you personally pay the displayed target price?" in text
    assert "Too low / fair / slightly high / much too high?" in text
    assert "Would PDH/CEH eligibility materially increase the value?" in text
    assert "Do not block learning on pricing feedback" in text


def test_level_9_pricing_is_flagged_for_reconciliation_with_new_curriculum():
    text = _text(ROADMAP)
    assert "Level 9 — Integrated Design / Economics / Project Development" in text
    assert "still being reconciled" in text
    assert "must be reviewed when final Level 9 authoring is frozen" in text
