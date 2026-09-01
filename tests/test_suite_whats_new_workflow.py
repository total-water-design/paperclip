from datetime import datetime, timezone

import pytest
from flask import Flask, render_template
from werkzeug.security import generate_password_hash

from auth import User, db, init_auth, login_manager
from suite_communications import WhatsNewCard, init_suite_communications


@pytest.fixture()
def communications_app(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTALRO_DATABASE_URL", f"sqlite:///{(tmp_path / 'communications.db').as_posix()}")
    monkeypatch.setenv("TOTALRO_AUTH_ENABLED", "1")
    monkeypatch.setenv("TOTALRO_CSRF_ENABLED", "0")
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(TESTING=True, SUITE_VERSION="0.2")

    @app.get("/")
    def index():
        return render_template(
            "suite_landing.html", suite_headline="Engineering platform", products=[],
            status_label=lambda value: value, suite_tagline="Water design",
        )

    @app.get("/suite")
    def suite_dashboard():
        return "suite"

    @app.get("/ro")
    def ro_application():
        return "ro"

    init_auth(app)
    login_manager.session_protection = None
    app.add_url_rule("/_test/security", endpoint="suite_mfa.admin_security", view_func=lambda: "security")
    app.add_url_rule("/_test/products", endpoint="suite_commercial.admin_products", view_func=lambda: "products")
    init_suite_communications(app)
    with app.app_context():
        admin = User(
            email="admin@example.test", full_name="Admin User", password_hash=generate_password_hash("valid-test-password"),
            role="admin", status="active", terms_accepted_at=datetime.now(timezone.utc),
        )
        db.session.add(admin)
        db.session.commit()
    return app, "valid-test-password"


def _login(client, password):
    response = client.post("/login", data={"email": "admin@example.test", "password": password})
    assert response.status_code == 302


def test_empty_cards_are_safe_in_http_and_api_responses(communications_app):
    app, admin_id = communications_app
    client = app.test_client()

    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert html.count("Last updated: Not published") == 3
    assert html.count("No approved update") == 3

    _login(client, admin_id)
    payload = client.get("/api/suite/whats-new").get_json()
    assert set(payload["cards"]) == {"recently_updated", "roadmap", "commercial_launch"}
    assert all(card["public_ready"] is False for card in payload["cards"].values())
    assert all(card["updated_at"] is None for card in payload["cards"].values())


def test_admin_can_publish_all_three_reviewed_cards_without_deployment(communications_app):
    app, admin_id = communications_app
    client = app.test_client()
    _login(client, admin_id)

    admin_page = client.get("/admin/communications")
    assert admin_page.status_code == 200
    admin_html = admin_page.get_data(as_text=True)
    assert admin_html.count("Public-information content reviewed") == 3
    assert admin_html.count("Approved to show publicly") >= 3

    rejected = client.post("/admin/communications/whats-new/recently_updated", data={
        "title": "New in Alpha", "summary": "Reviewed public improvements.",
        "release_label": "Alpha 0.2", "public": "1",
    })
    assert rejected.status_code == 302
    with app.app_context():
        assert db.session.query(WhatsNewCard).count() == 0

    card_copy = {
        "recently_updated": ("New in Alpha", "Reviewed improvements already available."),
        "roadmap": ("In progress", "Approved areas currently being developed."),
        "commercial_launch": ("Launch timing", "The current approved commercial timing."),
    }
    for slug, (title, summary) in card_copy.items():
        response = client.post(f"/admin/communications/whats-new/{slug}", data={
            "title": title, "summary": summary, "release_label": "Alpha 0.2",
            "reviewed": "1", "public": "1",
        })
        assert response.status_code == 302

    api_response = client.get("/api/suite/whats-new")
    assert api_response.status_code == 200
    cards = api_response.get_json()["cards"]
    assert all(card["public_ready"] is True for card in cards.values())
    assert all(card["status"] == "approved" for card in cards.values())
    assert all(card["release_label"] == "Alpha 0.2" for card in cards.values())
    assert all(card["updated_at"] for card in cards.values())

    homepage = client.get("/")
    html = homepage.get_data(as_text=True)
    assert homepage.status_code == 200
    for title, summary in card_copy.values():
        assert title in html
        assert summary in html
    assert html.count("Alpha 0.2") >= 3
    assert html.count("Last updated:") == 3
    assert "83a2733" not in html


def test_unknown_card_slug_is_rejected(communications_app):
    app, admin_id = communications_app
    client = app.test_client()
    _login(client, admin_id)
    response = client.post("/admin/communications/whats-new/internal-notes", data={})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Unknown What's New card."}
