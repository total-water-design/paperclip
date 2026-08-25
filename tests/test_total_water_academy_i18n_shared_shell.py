from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_academy_loads_local_shell_translation_without_modifying_shared_shell():
    base = read("templates/academy/base.html")
    shared = read("templates/shared/application_shell.html")
    assert "academy_i18n.js" in base
    assert "academy_i18n.js" not in shared
    assert "academy_i18n_boot.js" not in shared
    assert "academy_i18n.css" not in shared


def test_spanish_and_arabic_shell_copy_covers_visible_shared_chrome():
    script = read("static/academy_i18n.js")
    shared = read("templates/shared/application_shell.html") + "\n" + read("templates/shared/suite_components.html")
    for english, spanish, arabic in (
        ("Feedback", "Comentarios", "الملاحظات"),
        ("Appearance", "Apariencia", "المظهر"),
        ("System", "Sistema", "النظام"),
        ("Light", "Claro", "فاتح"),
        ("Dark", "Oscuro", "داكن"),
        ("My account", "Mi cuenta", "حسابي"),
        ("Manage users", "Administrar usuarios", "إدارة المستخدمين"),
        ("Project database", "Base de datos de proyectos", "قاعدة بيانات المشاريع"),
        ("Sign out", "Cerrar sesión", "تسجيل الخروج"),
        ("Tell us what you found", "Cuéntanos qué encontraste", "أخبرنا بما وجدته"),
        ("Feedback type", "Tipo de comentario", "نوع الملاحظة"),
        ("Description", "Descripción", "الوصف"),
        ("Submit feedback", "Enviar comentarios", "إرسال الملاحظات"),
    ):
        assert english in shared
        assert spanish in script
        assert arabic in script


def test_feedback_category_values_remain_canonical_while_labels_translate():
    script = read("static/academy_i18n.js")
    for value in ("calculation", "usability", "data", "report", "bug", "suggestion", "general"):
        assert f"{value}:" in script
    # Translation changes labels only; Suite Core still receives its canonical category values.
    assert "option[value=" in script
    assert "option.textContent = label" in script


def test_academy_shell_i18n_does_not_change_suite_engineering_or_account_state():
    script = read("static/academy_i18n.js")
    for forbidden in (
        "fetch('/api/",
        'fetch("/api/',
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "ProductEntitlement",
        "targetPriceUsd",
    ):
        assert forbidden not in script
    assert "textContent" in script
    assert "placeholder" in script
    assert "aria-label" in script


def test_dynamic_feedback_progress_and_receipt_messages_get_localized_on_academy_pages():
    script = read("static/academy_i18n.js")
    assert "MutationObserver" in script
    assert "Please describe the feedback before submitting." in script
    assert "Preparing feedback…" in script
    assert "Submitting feedback…" in script
    assert "Feedback could not be submitted." in script
    assert "Thank you\\. Your feedback was received successfully\\. Reference:" in script
    assert "Feedback (TWDS-[A-Z0-9-]+) was received" in script
    assert "Describe el comentario antes de enviarlo." in script
    assert "Gracias. Tus comentarios se recibieron correctamente." in script
    assert "يرجى وصف الملاحظة قبل الإرسال." in script
    assert "شكراً لك. تم استلام ملاحظاتك بنجاح." in script
