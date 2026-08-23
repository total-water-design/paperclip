"""Browser smoke gate for Total RO Design release validation.

Executed against a real running checkout by the RO release-validation workflow.
Engineering, persistence and report contracts are validated in dedicated checkout
gates; this suite verifies the actual customer browser surface remains usable.
"""
from __future__ import annotations

import os
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("TOTALRO_SMOKE_URL", "http://127.0.0.1:8765")


def _assert_no_page_overflow(page, tolerance=12):
    metrics = page.evaluate(
        """() => {
          const root=document.documentElement;
          const vw=root.clientWidth;
          const overflow=Math.max(0,root.scrollWidth-vw);
          const offenders=Array.from(document.querySelectorAll('body *')).map((el)=>{
            const r=el.getBoundingClientRect();
            return {
              tag:el.tagName,
              id:el.id||'',
              cls:String(el.className||'').slice(0,160),
              left:Math.round(r.left),
              right:Math.round(r.right),
              width:Math.round(r.width),
              scrollWidth:Math.round(el.scrollWidth||0),
              clientWidth:Math.round(el.clientWidth||0),
              display:getComputedStyle(el).display,
              position:getComputedStyle(el).position,
              minWidth:getComputedStyle(el).minWidth,
              widthCss:getComputedStyle(el).width
            };
          }).filter(x=>x.display!=='none' && (x.right>vw+1 || x.width>vw+1 || x.scrollWidth>x.clientWidth+1))
            .sort((a,b)=>Math.max(b.right-vw,b.width-vw,b.scrollWidth-b.clientWidth)-Math.max(a.right-vw,a.width-vw,a.scrollWidth-a.clientWidth))
            .slice(0,25);
          return {overflow,viewport:vw,scrollWidth:root.scrollWidth,offenders};
        }"""
    )
    assert metrics["overflow"] <= tolerance, (
        f"page-level horizontal overflow = {metrics['overflow']}px; "
        f"viewport={metrics['viewport']} scrollWidth={metrics['scrollWidth']}; "
        f"offenders={metrics['offenders']}"
    )


def test_total_ro_browser_smoke():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(15000)
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(f"{BASE_URL}/ro", wait_until="domcontentloaded")

        page.locator("#calculatorApp").wait_for(state="visible")
        page.locator("#fields input, #fields select").first.wait_for(state="visible")
        assert page.locator("#fields input, #fields select").count() >= 5
        assert page.locator("#calculateBtn").count() == 1
        assert page.locator("#calculateBtn").is_visible()

        assert page.locator("#twdsRoProjectBar").count() == 0
        theme = page.locator("#themeSelect")
        assert theme.count() == 1
        assert "system" in theme.locator("option").evaluate_all("els => els.map(e => e.value)")

        for selector in ("#newProjectBtn", "#importProjectBtn", "#saveProjectBtn", "#printTabBtn"):
            assert page.locator(selector).count() == 1, selector

        page.locator('[data-mode="ccro"]').wait_for(state="attached")
        page.locator('[data-mode="batch_ro"]').wait_for(state="attached")
        assert page.locator('[data-mode="ccro"]').count() == 1
        assert page.locator('[data-mode="batch_ro"]').count() == 1
        assert page.get_by_text("ADVANCED RO CONFIGURATIONS", exact=True).count() == 1
        nav_text = page.locator("body").inner_text().lower()
        assert "ccro" in nav_text and "batch ro" in nav_text

        entry_preview = page.locator('[data-tier-preview="entry"]')
        if entry_preview.count():
            entry_preview.click()
            page.wait_for_timeout(200)
            assert page.locator('[data-mode="ccro"]').count() == 1
            assert page.locator('[data-mode="batch_ro"]').count() == 1

        _assert_no_page_overflow(page)

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        assert page.locator("#calculatorApp").is_visible()
        assert page.locator("#calculateBtn").count() == 1
        assert page.locator('[data-mode="ccro"]').count() == 1
        assert page.locator('[data-mode="batch_ro"]').count() == 1
        _assert_no_page_overflow(page, tolerance=24)

        fatal = [x for x in console_errors if "favicon" not in x.lower()]
        assert not fatal, "browser console errors: " + " | ".join(fatal[:10])
        assert not page_errors, "browser page errors: " + " | ".join(page_errors[:10])
        browser.close()
