"""Fresh-context public-site browser evidence for TOT-1869.

This is intentionally independent of the Flask test client: it measures the
rendered public shell in Chromium, including computed foreground/background
contrast for the affected public-link and eyebrow selectors.
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5055"
ROUTES = ["/", "/platform", "/applications", "/applications/ro", "/applications/pretreatment", "/applications/bio", "/applications/zld", "/applications/balance", "/applications/economics", "/applications/system_integration"]
WIDTHS = (1440, 1280, 1024, 768, 390)
results = []


def rendered_accessibility(page):
    return page.evaluate("""() => {
      const rgb = value => {
        const channels = (value.match(/\\d+(?:\\.\\d+)?/g) || []).slice(0, 3).map(Number);
        return value.startsWith('color(srgb') ? channels.map(channel => channel * 255) : channels;
      };
      const luminance = value => {
        const channels = rgb(value).map(channel => {
          channel /= 255;
          return channel <= .04045 ? channel / 12.92 : Math.pow((channel + .055) / 1.055, 2.4);
        });
        return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
      };
      const background = element => {
        for (let node = element; node; node = node.parentElement) {
          const color = getComputedStyle(node).backgroundColor;
          if (!/rgba\\(0,\\s*0,\\s*0,\\s*0\\)/.test(color) && !/^transparent$/.test(color)) return color;
        }
        return 'rgb(255, 255, 255)';
      };
      const contrast = (foreground, back) => {
        const one = luminance(foreground), two = luminance(back);
        return (Math.max(one, two) + .05) / (Math.min(one, two) + .05);
      };
      const targets = [...document.querySelectorAll(
        '.suite-eyebrow, .public-header a, .public-footer a, .breadcrumbs a, .public-section a, .website-page a'
      )].filter(element => element.getClientRects().length &&
        !element.classList.contains('suite-primary-button') &&
        !element.classList.contains('suite-secondary-button') &&
        !element.classList.contains('suite-header-cta'));
      const samples = targets.map(element => {
        const style = getComputedStyle(element), back = background(element);
        return {selector: element.className || element.tagName, text: element.textContent.trim().slice(0, 80),
                foreground: style.color, background: back, ratio: contrast(style.color, back)};
      });
      return {samples, minimumContrast: Math.min(...samples.map(item => item.ratio)),
              reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches};
    }""")


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
                page.emulate_media(reduced_motion="reduce")
                a11y = rendered_accessibility(page)
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                page.keyboard.press("Tab")
                focused = page.evaluate("Boolean(document.activeElement)")
                favicon_errors = [item for item in responses if item[0].endswith('/favicon.ico') and item[1] >= 400]
                record = {"route": route, "width": width, "theme": theme, "overflow": overflow,
                          "focused": focused, "page_errors": errors, "favicon_errors": favicon_errors,
                          "minimum_contrast": a11y["minimumContrast"], "contrast_samples": a11y["samples"],
                          "reduced_motion": a11y["reducedMotion"]}
                results.append(record)
                if route == "/":
                    page.screenshot(path=f"deliverables/tot-1869/home-{width}-{theme}.png", full_page=True)
                page.close()
    browser.close()
Path("deliverables/tot-1869/browser-oracle.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
assert all(not item["overflow"] and item["focused"] and not item["page_errors"] and not item["favicon_errors"]
           and item["minimum_contrast"] >= 4.5 and item["reduced_motion"] for item in results)
