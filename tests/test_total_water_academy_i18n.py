from pathlib import Path

from academy_content import LEVELS, PILOT_MODULE
from academy_i18n import (
    PHRASES_AR,
    PHRASES_ES,
    SUPPORTED_LOCALES,
    UI_AR,
    UI_EN,
    UI_ES,
    locale_info,
    localize,
    normalize_locale,
    tr,
)
from academy_placement import DIAGNOSTIC_QUESTIONS, RATING_LABELS, SELF_RATING_DOMAINS

ROOT = Path(__file__).resolve().parents[1]


def _all_modules(levels):
    return [module for level in levels for module in level["modules"]]


def test_academy_early_multilingual_release_has_exact_three_locales():
    assert tuple(SUPPORTED_LOCALES) == ("en", "es-419", "ar")
    assert locale_info("en")["dir"] == "ltr"
    assert locale_info("es-419")["dir"] == "ltr"
    assert locale_info("ar")["dir"] == "rtl"
    assert normalize_locale("es-MX") == "es-419"
    assert normalize_locale("es_CL") == "es-419"
    assert normalize_locale("ar-SA") == "ar"
    assert normalize_locale("en-US") == "en"


def test_every_ui_key_has_explicit_spanish_and_arabic_translation():
    assert set(UI_EN).issubset(UI_ES)
    assert set(UI_EN).issubset(UI_AR)
    for key, english in UI_EN.items():
        assert UI_ES[key] != english or key in {"diploma", "nav_zld"}
        assert UI_AR[key] != english or key in {"nav_zld"}


def test_all_50_course_titles_are_translated_without_changing_ids_or_hours():
    assert len(_all_modules(LEVELS)) == 50
    for locale in ("es-419", "ar"):
        translated = localize(list(LEVELS), locale)
        canonical_modules = _all_modules(LEVELS)
        localized_modules = _all_modules(translated)
        assert len(localized_modules) == 50
        for original, localized_module in zip(canonical_modules, localized_modules):
            assert localized_module["id"] == original["id"]
            assert localized_module["hours"] == original["hours"]
            assert localized_module["title"] != original["title"]


def test_level_titles_missions_and_structure_are_localized_but_engine_owners_are_not_mutated():
    for locale in ("es-419", "ar"):
        translated = localize(list(LEVELS), locale)
        for original, localized_level in zip(LEVELS, translated):
            assert localized_level["id"] == original["id"]
            assert localized_level["level"] == original["level"]
            assert localized_level["hours"] == original["hours"]
            assert localized_level["title"] != original["title"]
            assert localized_level["mission"] != original["mission"]
            assert localized_level["suite_connections"] == original["suite_connections"]


def test_pilot_localization_preserves_activity_ids_kinds_answer_keys_and_scores():
    for locale in ("es-419", "ar"):
        translated = localize(PILOT_MODULE, locale)
        assert translated["id"] == PILOT_MODULE["id"]
        assert translated["level_id"] == PILOT_MODULE["level_id"]
        assert translated["hours"] == PILOT_MODULE["hours"]
        assert translated["title"] != PILOT_MODULE["title"]
        assert len(translated["steps"]) == len(PILOT_MODULE["steps"])
        for original, localized_step in zip(PILOT_MODULE["steps"], translated["steps"]):
            assert localized_step["id"] == original["id"]
            assert localized_step["kind"] == original["kind"]
            if "answer" in original:
                assert localized_step["answer"] == original["answer"]
            if "pass_percent" in original:
                assert localized_step["pass_percent"] == original["pass_percent"]
            if "minimum_score" in original:
                assert localized_step["minimum_score"] == original["minimum_score"]
            if "choices" in original:
                assert len(localized_step["choices"]) == len(original["choices"])
            if "questions" in original:
                for oq, lq in zip(original["questions"], localized_step["questions"]):
                    assert lq["id"] == oq["id"]
                    assert lq["answer"] == oq["answer"]
                    assert len(lq["choices"]) == len(oq["choices"])


def test_engineering_acronyms_and_unit_strings_are_not_translated_or_reinterpreted():
    for locale in ("es-419", "ar"):
        translated = localize(PILOT_MODULE, locale)
        practical = next(step for step in translated["steps"] if step["id"] == "practical-1")
        units = {item["id"]: item["label"] for item in practical["available_units"]}
        assert units["daf"] == "DAF"
        assert units["uf"] == "UF"
        assert units["ro"] == "RO"
        diagnostic = localize(DIAGNOSTIC_QUESTIONS, locale)
        assert "m³/h" in diagnostic[0]["prompt"]
        assert "pH" in diagnostic[8]["prompt"]
        assert "VFD" in diagnostic[10]["prompt"]
        assert "PLC" in localize("Instrumentation, Process Control & PLC", locale)


def test_placement_diagnostic_translates_presentation_without_changing_scoring_contract():
    for locale in ("es-419", "ar"):
        translated_questions = localize(DIAGNOSTIC_QUESTIONS, locale)
        assert len(translated_questions) == 12
        for original, localized_question in zip(DIAGNOSTIC_QUESTIONS, translated_questions):
            assert localized_question["id"] == original["id"]
            assert localized_question["domain"] == original["domain"]
            assert localized_question["answer"] == original["answer"]
            assert len(localized_question["choices"]) == len(original["choices"])
            assert localized_question["prompt"] != original["prompt"]
        localized_domains = localize(SELF_RATING_DOMAINS, locale)
        assert [key for key, _ in localized_domains] == [key for key, _ in SELF_RATING_DOMAINS]
        localized_ratings = localize(RATING_LABELS, locale)
        assert set(localized_ratings) == set(RATING_LABELS)


def test_brand_and_international_engineering_tokens_remain_canonical():
    for locale in ("es-419", "ar"):
        assert tr("applied_design", locale)
        for token in ("RO", "UF", "MF", "NF", "MBR", "ZLD", "PLC", "VFD", "PID", "CAPEX", "OPEX"):
            # Token can appear in translated phrases but must not be replaced by a localized acronym.
            assert token not in {"OI", "OI/OR"}


def test_spanish_and_arabic_phrase_maps_cover_all_current_course_titles():
    for module in _all_modules(LEVELS):
        assert module["title"] in PHRASES_ES
        assert module["title"] in PHRASES_AR


def test_language_switch_is_academy_scoped_and_uses_post_csrf():
    base = (ROOT / "templates" / "academy" / "base.html").read_text(encoding="utf-8")
    assert "academy.set_language" in base
    assert 'name="csrf_token"' in base
    assert 'name="locale"' in base
    assert "academy_language_options" in base
    assert "English" not in base  # options come from controlled locale metadata
    assert "Español" not in base
    assert "العربية" not in base


def test_arabic_rtl_bootstrap_and_styles_are_academy_only():
    boot = (ROOT / "static" / "academy_i18n_boot.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "academy_i18n.css").read_text(encoding="utf-8")
    base = (ROOT / "templates" / "academy" / "base.html").read_text(encoding="utf-8")
    assert "document.documentElement.dir" in boot
    assert "data-academy-dir" in base
    assert 'html[dir="rtl"]' in css
    assert "academy-side-nav" in css
    assert "academy-note" in css
    assert "academy-choice-list" in css
    assert "academy-technical" in css


def test_interactive_javascript_uses_localized_labels_instead_of_hardcoded_runtime_copy():
    js = (ROOT / "static" / "academy.js").read_text(encoding="utf-8")
    base = (ROOT / "templates" / "academy" / "base.html").read_text(encoding="utf-8")
    assert "academy-i18n-data" in base
    for field in (
        "goodReasoning",
        "reviewReasoning",
        "chooseAnswerFirst",
        "selectProcessBegin",
        "moveEarlier",
        "moveLater",
        "removeUnit",
        "answerAll",
        "moduleComplete",
        "diplomaIssued",
    ):
        assert field in js


def test_pricing_runtime_uses_server_localized_label_templates():
    level = (ROOT / "templates" / "academy" / "level.html").read_text(encoding="utf-8")
    pricing = (ROOT / "static" / "academy_pricing.js").read_text(encoding="utf-8")
    assert "data-label-free" in level
    assert "data-label-target" in level
    assert "data-label-review" in level
    assert "node.dataset.labelFree" in pricing
    assert "node.dataset.labelTarget" in pricing
    assert "node.dataset.labelReview" in pricing


def test_multilingual_release_does_not_translate_specialist_owner_identifiers():
    for locale in ("es-419", "ar"):
        translated = localize(list(LEVELS), locale)
        owners = [owner for level in translated for owner in level["suite_connections"]]
        assert any(owner.startswith("app/") for owner in owners)
        assert any(owner.startswith("engine/") for owner in owners)
        assert all("التطبيق" not in owner and "aplicación" not in owner for owner in owners)
