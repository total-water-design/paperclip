"""Runtime acceptance gate for the Total RO Design light-only contract."""
from __future__ import annotations

import os

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("TOTALRO_SMOKE_URL", "http://127.0.0.1:8765")


def _assert_light_only(page):
    page.locator("#calculatorApp").wait_for(state="visible")
    assert page.locator("html").get_attribute("data-theme") == "light"
    assert page.evaluate("() => getComputedStyle(document.documentElement).colorScheme") == "light"
    assert page.locator("#themeSelect").count() == 0
    assert page.locator(".theme-control").count() == 0


def test_ro_is_light_only_on_desktop_mobile_and_after_stored_dark_preference():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script("""() => {
          localStorage.setItem('totalrodesign-theme', 'dark');
          localStorage.setItem('calcospower-theme', 'dark');
        }""")
        page = context.new_page()
        console_errors = []
        page_errors = []
        chemistry_responses = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: chemistry_responses.append(response.status)
            if "/api/chemistry/analyze" in response.url and response.request.method == "POST"
            else None,
        )

        page.goto(f"{BASE_URL}/ro", wait_until="domcontentloaded")
        _assert_light_only(page)
        page.evaluate("""() => {
          if (!seawaterPresets.length) throw new Error('No seawater presets loaded');
          waterProfile=makeWaterProfile(seawaterPresets[0]);
          syncActiveCaseStore();
          renderWaterTab();
          document.querySelector('#calcForm').requestSubmit();
        }""")
        page.wait_for_function("() => !!lastChemistryResult", timeout=60000)
        assert chemistry_responses == [200]
        assert "Osmotic pressure" in page.locator("#results").inner_text()

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        _assert_light_only(page)
        assert not [error for error in console_errors if "favicon" not in error.lower()]
        assert not page_errors
        browser.close()
