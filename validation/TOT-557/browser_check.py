"""Run the non-production What's New fixture in Chromium and retain raw evidence.

This deliberately hosts an in-memory/local SQLite fixture; it does not connect
to a production database and does not publish records outside that fixture.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from flask import Flask, render_template
from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from auth import User, db, init_auth, login_manager
from suite_communications import init_suite_communications
COPY = {
    "recently_updated": (
        "Available now",
        "Total RO Design is available for preliminary reverse-osmosis design and reporting.",
        "Current availability",
    ),
    "roadmap": (
        "In development",
        "Additional water-treatment design applications are in development and will be introduced when ready.",
        "Work in progress",
    ),
    "commercial_launch": (
        "Commercial access",
        "Commercial access details will be shared when they are available.",
        "No date announced",
    ),
}
STALE_PLACEHOLDERS = (
    "No public release update has been published yet.",
    "No public roadmap items have been approved for display yet.",
    "Commercial launch timing will be published here after it is approved.",
)


def _port() -> int:
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return int(connection.getsockname()[1])


def _app(database_path: Path) -> Flask:
    os.environ["TOTALRO_DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["TOTALRO_AUTH_ENABLED"] = "1"
    os.environ["TOTALRO_CSRF_ENABLED"] = "0"
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
    app.config.update(
        TESTING=True,
        SUITE_VERSION="0.2",
        SECRET_KEY="tot-557-non-production-fixture",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
    )

    @app.get("/")
    def index():
        return render_template("suite_landing.html", suite_headline="Engineering platform", products=[], status_label=lambda value: value, suite_tagline="Water design")

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
        db.session.add(User(email="admin@example.test", full_name="Admin User", password_hash=generate_password_hash("valid-test-password"), role="admin", status="active", terms_accepted_at=datetime.now(timezone.utc)))
        db.session.commit()
    return app


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tot-557-") as temporary_directory:
        app = _app(Path(temporary_directory) / "fixture.db")
        client = app.test_client()
        login = client.post("/login", data={"email": "admin@example.test", "password": "valid-test-password"})
        assert login.status_code == 302, login.status_code
        for slug, (title, summary, release_label) in COPY.items():
            response = client.post(f"/admin/communications/whats-new/{slug}", data={"title": title, "summary": summary, "release_label": release_label, "reviewed": "1", "public": "1"})
            assert response.status_code == 302, response.status_code
        server = make_server("127.0.0.1", _port(), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/"
        evidence = {"fixture": "local SQLite only; no live publication", "url": url, "viewports": {}, "console": [], "page_errors": [], "network": []}
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for name, viewport in {"desktop": {"width": 1440, "height": 1000}, "mobile": {"width": 390, "height": 844}}.items():
                    page = browser.new_page(viewport=viewport)
                    page.on("console", lambda message: evidence["console"].append({"type": message.type, "text": message.text}))
                    page.on("pageerror", lambda error: evidence["page_errors"].append(str(error)))
                    page.on("response", lambda response: evidence["network"].append({"status": response.status, "url": response.url}))
                    response = page.goto(url, wait_until="networkidle")
                    assert response and response.status == 200
                    cards = page.locator(".suite-whats-new-card")
                    assert cards.count() == 3
                    rendered = page.locator("#whats-new").inner_text()
                    rendered_cards = []
                    for index, (title, summary, release_label) in enumerate(COPY.values()):
                        card = cards.nth(index)
                        actual = {
                            "release_label": card.locator("span").text_content(),
                            "title": card.locator("h3").text_content(),
                            "summary": card.locator("p").first.text_content(),
                        }
                        assert actual == {"release_label": release_label, "title": title, "summary": summary}, actual
                        assert title in rendered
                        assert summary in rendered
                        rendered_cards.append(actual)
                    visible_placeholders = [text for text in STALE_PLACEHOLDERS if text in rendered]
                    assert not visible_placeholders, visible_placeholders
                    screenshot = EVIDENCE / f"home-{name}.png"
                    page.screenshot(path=str(screenshot), full_page=True)
                    evidence["viewports"][name] = {
                        "status": response.status,
                        "cards": cards.count(),
                        "card_copy": rendered_cards,
                        "stale_placeholders_visible": visible_placeholders,
                        "screenshot": screenshot.name,
                    }
                    page.close()
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
        assert not evidence["page_errors"], evidence["page_errors"]
        (EVIDENCE / "browser-raw-output.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
