from datetime import datetime, timezone
from threading import Thread
from uuid import uuid4

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import app
from auth import ProductEntitlement, User, db


def test_authenticated_economics_workflow(tmp_path):
    app.config.update(AUTH_ENABLED=True, TESTING=False, WTF_CSRF_ENABLED=True)
    email = f"tot921-browser-{uuid4().hex}@example.test"
    password = "TOT-921 browser test password"
    with app.app_context():
        db.create_all()
        user = User(
            email=email,
            full_name="TOT-921 Browser",
            organization="TWDS",
            role="user",
            licensed_tier="entry",
            status="active",
            terms_accepted_at=datetime.now(timezone.utc),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(ProductEntitlement(
            user_id=user.id,
            product_id="economics",
            enabled=True,
            tier="gold",
            status="active",
        ))
        db.session.commit()

    server = make_server("127.0.0.1", 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{base_url}/login", wait_until="networkidle")
            page.locator('input[name="email"]').fill(email)
            page.locator('input[name="password"]').fill(password)
            page.locator('button[type="submit"]').click()
            page.wait_for_url("**/suite")
            response = page.goto(f"{base_url}/economics-suite", wait_until="networkidle")
            assert response is not None and response.ok
            assert page.url == f"{base_url}/economics-suite"
            assert page.locator('[data-twds-app-shell][data-app-id="economics"]').is_visible()
            page.locator('[data-start-choice="blank"]').click()
            page.get_by_role("radio", name="Project Finance").click()
            page.get_by_role("button", name="Scenarios & Sensitivities").click()
            assert page.get_by_role(
                "heading", name="Compare base, upside, downside and lender cases"
            ).is_visible()
            page.screenshot(path=tmp_path / "authenticated-economics.png", full_page=True)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
