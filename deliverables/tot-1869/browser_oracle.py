"""Fresh-context public-site browser evidence for TOT-1869."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5055"
ROUTES = ["/", "/platform", "/applications", "/applications/ro", "/applications/pretreatment", "/applications/bio", "/applications/zld", "/applications/balance", "/applications/economics", "/applications/system_integration"]
WIDTHS = (1440, 1280, 1024, 768, 390)
results = []
with sync_playwright() as play:
    browser = play.chromium.launch(headless=True)
    for width in WIDTHS:
        for theme in ("light", "dark"):
            for route in ROUTES:
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors, responses = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: responses.append((response.url, response.status)))
                page.goto(BASE + route, wait_until="networkidle")
                page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                page.keyboard.press("Tab")
                focused = page.evaluate("Boolean(document.activeElement)")
                favicon_errors = [item for item in responses if item[0].endswith('/favicon.ico') and item[1] >= 400]
                results.append({"route": route, "width": width, "theme": theme, "overflow": overflow, "focused": focused, "page_errors": errors, "favicon_errors": favicon_errors})
                page.close()
    browser.close()
Path("deliverables/tot-1869/browser-oracle.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
assert all(not item["overflow"] and item["focused"] and not item["page_errors"] and not item["favicon_errors"] for item in results)
