from pathlib import Path

from academy_placement import _is_academy_path, _safe_next

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_saved_placement_profile_requires_explicit_retake_before_form_is_shown():
    template = read("templates/academy/placement.html")
    i18n = read("academy_i18n.py")
    assert "{% if not profile or request.args.get('retake') == '1' %}" in template
    assert "academy_tr('retake')" in template
    assert "retake=1" in template
    assert '"retake": "Retake knowledge check"' in i18n


def test_saved_placement_profile_still_exposes_localized_recommendation_and_continue_action():
    template = read("templates/academy/placement.html")
    i18n = read("academy_i18n.py")
    assert "academy_tr('recommended_path')" in template
    assert "localized_track" in template
    assert "profile.diagnostic_score" in template
    assert "academy_tr('continue_academy')" in template
    assert '"recommended_path": "YOUR RECOMMENDED PATH"' in i18n
    assert '"continue_academy": "Continue to the Academy"' in i18n


def test_placement_diagnostic_cannot_waive_diploma_requirements_in_any_language():
    template = read("templates/academy/placement.html")
    service = read("academy_placement.py")
    i18n = read("academy_i18n.py")
    assert "academy_tr('recommendation_copy')" in template
    assert "Diploma requirements remain the same for everyone" in i18n
    assert "Los requisitos del Diploma son iguales para todos" in i18n
    assert "تبقى متطلبات الدبلوم نفسها للجميع" in i18n
    assert "does not grant engineering" in service
    assert "waive diploma requirements" in service


def test_placement_return_path_is_strictly_academy_local():
    assert _safe_next(None) == "/academy"
    assert _safe_next("/academy") == "/academy"
    assert _safe_next("/academy/levels/L04") == "/academy/levels/L04"
    assert _safe_next("/academy?skip_placement=1") == "/academy?skip_placement=1"
    for unsafe in (
        "/ro",
        "/admin",
        "/academyevil",
        "//evil.example/academy",
        "https://evil.example/academy",
        "javascript:alert(1)",
    ):
        assert _safe_next(unsafe) == "/academy"


def test_first_entry_hook_matches_only_the_academy_namespace():
    assert _is_academy_path("/academy") is True
    assert _is_academy_path("/academy/levels/L01") is True
    assert _is_academy_path("/academy/api/curriculum") is True
    assert _is_academy_path("/academyevil") is False
    assert _is_academy_path("/academy2") is False
    assert _is_academy_path("/ro") is False
