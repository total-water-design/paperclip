"""Reproducible 100-case public-site browser evidence for TOT-1878."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROUTES = ("/", "/platform", "/applications", "/applications/ro", "/applications/pretreatment", "/applications/bio", "/applications/zld", "/applications/balance", "/applications/economics", "/applications/system_integration")
WIDTHS = (1440, 1280, 1024, 768, 390)
THEMES = ("light", "dark")


def slug(route: str) -> str:
    return "home" if route == "/" else route.strip("/").replace("/", "-")


def rendered_accessibility(page: Page) -> dict:
    return page.evaluate("""() => {
      const color = value => {
        if (value === 'transparent') return [0,0,0,0];
        const c = (value.match(/[\\d.]+/g) || []).map(Number);
        return value.startsWith('color(srgb') ? [...c.slice(0,3).map(v => v*255), c[3] ?? 1] : [...c.slice(0,3), c[3] ?? 1];
      };
      const composite = (front, back) => [0,1,2].map(i => front[i]*front[3] + back[i]*(1-front[3])).concat(1);
      const backgrounds = element => {
        for (let node=element; node; node=node.parentElement) {
          const style=getComputedStyle(node);
          if (style.backgroundImage !== 'none') {
            const stops=(style.backgroundImage.match(/rgba?\\([^)]*\\)/g)||[]).map(color);
            if (stops.length) return stops;
          }
          const solid=color(style.backgroundColor);
          if (solid[3]===1) return [solid];
        }
        return [[255,255,255,1]];
      };
      const luminance = c => {
        const linear = c.slice(0,3).map(v => { v/=255; return v<=.04045 ? v/12.92 : Math.pow((v+.055)/1.055,2.4); });
        return .2126*linear[0]+.7152*linear[1]+.0722*linear[2];
      };
      const ratio = (front, back) => {
        const one=luminance(composite(front,back)), two=luminance(back);
        return (Math.max(one,two)+.05)/(Math.min(one,two)+.05);
      };
      const samples = [...document.querySelectorAll('body *')].filter(element => {
        const style=getComputedStyle(element);
        return [...element.childNodes].some(node => node.nodeType===Node.TEXT_NODE && node.textContent.trim()) && element.getClientRects().length && style.visibility!=='hidden' && Number(style.opacity)>0;
      }).map(element => {
        const style=getComputedStyle(element), backs=backgrounds(element);
        const ratios=backs.map(back=>ratio(color(style.color),back));
        return {tag:element.tagName.toLowerCase(), selector:element.id ? `#${element.id}` : String(element.className||'').trim().split(/\\s+/).filter(Boolean).map(c=>`.${c}`).join(''), text:element.textContent.trim().replace(/\\s+/g,' ').slice(0,120), foreground:style.color, backgrounds:backs.map(back=>`rgb(${back.slice(0,3).map(Math.round).join(', ')})`), fontSizePx:Number.parseFloat(style.fontSize), fontWeight:style.fontWeight, ratio:Math.min(...ratios)};
      });
      const normal=samples.filter(item => !(item.fontSizePx>=24 || (item.fontSizePx>=18.66 && Number.parseInt(item.fontWeight,10)>=700)));
      const motionViolations=[...document.querySelectorAll('body *')].filter(element => element.getClientRects().length).map(element => ({selector:element.id ? `#${element.id}` : element.tagName.toLowerCase(), animationDuration:getComputedStyle(element).animationDuration, transitionDuration:getComputedStyle(element).transitionDuration})).filter(item => item.animationDuration.split(',').some(v=>Number.parseFloat(v)>0) || item.transitionDuration.split(',').some(v=>Number.parseFloat(v)>0));
      return {samples, normalTextSampleCount:normal.length, minimumNormalTextContrast:Math.min(...normal.map(item=>item.ratio)), contrastFailures:normal.filter(item=>item.ratio<4.5), reducedMotionMediaMatches:matchMedia('(prefers-reduced-motion: reduce)').matches, motionViolations};
    }""")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BROWSER_ORACLE_BASE_URL", "http://127.0.0.1:5055"))
    parser.add_argument("--output-dir", default="deliverables/tot-1878")
    parser.add_argument("--source-sha", default=os.environ.get("BROWSER_ORACLE_SOURCE_SHA", "unknown"))
    parser.add_argument("--execution-workspace-id", default=os.environ.get("PAPERCLIP_EXECUTION_WORKSPACE_ID", "unknown"))
    parser.add_argument("--run-id", default=os.environ.get("PAPERCLIP_RUN_ID", "unknown"))
    args = parser.parse_args()
    output_dir, records = Path(args.output_dir), []
    screenshots = output_dir / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        browser_version = browser.version
        for width in WIDTHS:
            for theme in THEMES:
                for route in ROUTES:
                    context = browser.new_context(viewport={"width":width,"height":900}, color_scheme=theme, reduced_motion="reduce")
                    page = context.new_page()
                    console_errors, page_errors, failed_responses, failed_requests = [], [], [], []
                    page.on("console", lambda message: console_errors.append({"type":message.type,"text":message.text}) if message.type == "error" else None)
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.on("response", lambda response: failed_responses.append({"url":response.url,"status":response.status,"statusText":response.status_text}) if response.status >= 400 else None)
                    page.on("requestfailed", lambda request: failed_requests.append({"url":request.url,"failure":request.failure or "unknown"}))
                    response = page.goto(args.base_url+route, wait_until="networkidle")
                    page.evaluate("theme => document.documentElement.dataset.theme=theme", theme)
                    page.wait_for_timeout(50)
                    a11y = rendered_accessibility(page)
                    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                    page.keyboard.press("Tab")
                    focus = page.evaluate("""() => { const e=document.activeElement,s=getComputedStyle(e),r=e.getBoundingClientRect(); return {tag:e?.tagName?.toLowerCase()||null,text:e?.textContent?.trim()?.replace(/\\s+/g,' ')?.slice(0,80)||'',isBody:e===document.body,visible:r.width>0&&r.height>0&&s.visibility!=='hidden',indicator:s.outlineStyle!=='none'&&Number.parseFloat(s.outlineWidth)>0,outline:`${s.outlineWidth} ${s.outlineStyle} ${s.outlineColor}`}; }""")
                    favicon = page.evaluate("document.querySelector('link[rel~=icon]')?.href || null")
                    favicon_status = page.request.get(favicon).status if favicon else None
                    screenshot = screenshots / f"{slug(route)}-{width}-{theme}.png"
                    page.screenshot(path=str(screenshot), full_page=True)
                    records.append({"route":route,"width":width,"theme":theme,"pageStatus":response.status if response else None,"finalUrl":page.url,"overflow":overflow,"focus":focus,"favicon":{"url":favicon,"status":favicon_status},"consoleErrors":console_errors,"pageErrors":page_errors,"failedResponses":failed_responses,"failedRequests":failed_requests,"minimumNormalTextContrast":a11y["minimumNormalTextContrast"],"normalTextSampleCount":a11y["normalTextSampleCount"],"contrastFailures":a11y["contrastFailures"],"contrastSamples":a11y["samples"],"reducedMotionMediaMatches":a11y["reducedMotionMediaMatches"],"motionViolations":a11y["motionViolations"],"screenshot":screenshot.as_posix()})
                    context.close()
        browser.close()

    failures = [{"route":i["route"],"width":i["width"],"theme":i["theme"]} for i in records if i["pageStatus"]!=200 or i["overflow"] or i["focus"]["isBody"] or not i["focus"]["visible"] or not i["focus"]["indicator"] or not i["favicon"]["url"] or i["favicon"]["status"]!=200 or i["consoleErrors"] or i["pageErrors"] or i["failedResponses"] or i["failedRequests"] or i["minimumNormalTextContrast"]<4.5 or i["contrastFailures"] or not i["reducedMotionMediaMatches"] or i["motionViolations"]]
    report = {"schemaVersion":2,"sourceSha":args.source_sha,"executionWorkspaceId":args.execution_workspace_id,"paperclipRunId":args.run_id,"baseUrl":args.base_url,"browser":{"name":"chromium","version":browser_version},"routes":list(ROUTES),"widths":list(WIDTHS),"themes":list(THEMES),"expectedCaseCount":len(ROUTES)*len(WIDTHS)*len(THEMES),"actualCaseCount":len(records),"pass":not failures,"failedCases":failures,"cases":records}
    (output_dir/"browser-matrix.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:report[key] for key in ("sourceSha","executionWorkspaceId","paperclipRunId","expectedCaseCount","actualCaseCount","pass","failedCases")},indent=2))
    if failures: raise SystemExit(1)


if __name__ == "__main__":
    main()
