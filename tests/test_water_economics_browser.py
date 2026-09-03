from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


SCREENSHOTS = Path(__file__).resolve().parents[1] / "validation" / "TOT-271-screenshots"


@pytest.mark.parametrize("width", [1440, 1280, 1024, 768, 390])
def test_economics_workflow_is_responsive_and_error_free(width):
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    console_errors = []
    page_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        response = page.goto("http://127.0.0.1:5271/economics-suite", wait_until="networkidle")
        assert response is not None and response.ok
        page.locator('[data-start-choice="blank"]').click()
        assert page.get_by_role("heading", name="Choose the detail appropriate to this decision").is_visible()
        assert page.locator(".ted-nav-btn").count() == 6
        page.get_by_role("radio", name="Project Finance").click()
        assert page.locator('[data-twds-app-shell][data-economics-mode="project-finance"]').count() == 1
        page.get_by_role("button", name="Scenarios & Sensitivities").click()
        assert page.get_by_role("heading", name="Compare base, upside, downside and lender cases").is_visible()
        page.screenshot(path=SCREENSHOTS / f"economics-{width}.png", full_page=True)
        browser.close()
    assert page_errors == []
    assert console_errors == []
