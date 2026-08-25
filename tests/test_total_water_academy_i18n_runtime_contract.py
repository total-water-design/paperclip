from pathlib import Path

from flask import Flask, session

from academy_i18n import current_locale, locale_info, normalize_locale

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_MULTILINGUAL_RELEASE_v1.0.md"


def _app():
    app = Flask(__name__)
    app.secret_key = "academy-i18n-test-secret"
    return app


def test_saved_academy_locale_wins_over_browser_language():
    app = _app()
    with app.test_request_context("/academy", headers={"Accept-Language": "ar-SA,ar;q=0.9"}):
        session["academy_locale"] = "es-419"
        assert current_locale() == "es-419"


def test_browser_locale_is_used_when_no_saved_academy_preference_exists():
    app = _app()
    with app.test_request_context("/academy", headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.4"}):
        assert current_locale() == "ar"
    with app.test_request_context("/academy", headers={"Accept-Language": "es-CL,es;q=0.9,en;q=0.4"}):
        assert current_locale() == "es-419"


def test_unsupported_browser_locale_falls_back_to_english():
    app = _app()
    with app.test_request_context("/academy", headers={"Accept-Language": "ja-JP,ja;q=0.9"}):
        assert current_locale() == "en"


def test_locale_normalization_and_direction_contract():
    assert normalize_locale("es-MX") == "es-419"
    assert normalize_locale("es_AR") == "es-419"
    assert normalize_locale("ar-AE") == "ar"
    assert normalize_locale("en-GB") == "en"
    assert normalize_locale("fr-FR") is None
    assert locale_info("ar")["dir"] == "rtl"
    assert locale_info("en")["dir"] == "ltr"
    assert locale_info("es-419")["dir"] == "ltr"


def test_language_endpoint_is_academy_scoped_and_rejects_external_or_near_match_return_paths():
    source = (ROOT / "academy.py").read_text(encoding="utf-8")
    assert '@academy_bp.post("/language")' in source
    assert 'session["academy_locale"] = locale' in source
    assert 'target == "/academy"' in source
    assert 'target.startswith("/academy/")' in source
    assert 'target.startswith("/academy?")' in source
    assert "parsed.scheme or parsed.netloc" in source
    assert "not academy_local" in source
    assert 'return "/academy"' in source


def test_multilingual_assets_are_loaded_only_by_academy_shell():
    academy_base = (ROOT / "templates" / "academy" / "base.html").read_text(encoding="utf-8")
    shared_shell = (ROOT / "templates" / "shared" / "application_shell.html").read_text(encoding="utf-8")
    assert "academy_i18n.css" in academy_base
    assert "academy_i18n_boot.js" in academy_base
    assert "academy.set_language" in academy_base
    assert "academy_i18n.css" not in shared_shell
    assert "academy_i18n_boot.js" not in shared_shell
    assert "academy.set_language" not in shared_shell


def test_multilingual_release_contract_preserves_canonical_engineering_meaning_and_mobile_pwa_reuse():
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        "only Total Water Design Suite application authorized for the initial multilingual release",
        "one canonical curriculum",
        "three presentation languages",
        "English remains the canonical authored/scoring source",
        "Desktop web, mobile web and installed PWA",
        "Do **not** use national flags",
        "Do **not** select language from geographic location",
        "Modern Standard Arabic",
        "RTL must not automatically reverse the engineering meaning",
        "human review by technically competent Spanish and Arabic reviewers",
    ):
        assert phrase in text


def test_translation_does_not_inherit_pdh_approval_automatically():
    text = DOC.read_text(encoding="utf-8")
    assert "Translation does not alter the continuing-education status of a course" in text
    assert "translated delivery" in text
    for credit in ("PDH", "CEH", "CEU", "license-renewal credit", "accreditation"):
        assert credit in text
