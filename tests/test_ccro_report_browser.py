from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ccro_data():
    return {
        "flow_unit": "m3/h", "pressure_unit": "bar", "water_mode": "tds",
        "feed_tds": 2500, "analysis_tds": 2500, "temperature_c": 25, "feed_ph": 7.8,
        "membrane_1": "DuPont FilmTec|SW30HRLE-400|A / standard",
        "vessels_1": 4, "elements_per_vessel_1": 3, "permeate_pressure_1": 0,
        "ccro_target_average_recovery": 65,
        "ccro_closed_circuit_permeate_flow": 8,
        "ccro_concentrate_recycle_per_vessel": 4.54,
        "ccro_pf_feed_ratio": 1.20, "ccro_pf_recovery": 20,
        "ccro_system_volume_m3": 1.0, "ccro_loop_extra_dp": 0.3,
        "suction_pressure": 2, "pump_eff": .85, "motor_eff": .97, "vfd_eff": .97,
        "ccro_circulation_pump_eff": .82, "ccro_circulation_motor_eff": .96, "ccro_circulation_vfd_eff": .97,
        "pretreatment_discharge_pressure": 6, "pretreatment_recovery": .85,
        "pretreatment_pump_eff": .82, "pretreatment_motor_eff": .95, "pretreatment_vfd_eff": .97,
        "fouling_factor": .90, "salt_passage_factor": 1.0,
    }


def _wait_http(url, timeout=30):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(.2)
    raise RuntimeError(f"Server did not become ready: {url}")


def test_ccro_cycle_selection_and_entry_report_round_trip():
    port = _port()
    env = os.environ.copy()
    env.update({
        "TOTALRO_AUTH_ENABLED": "0",
        "TOTALRO_DEPLOYMENT_MODE": "desktop",
        "TOTALRO_COMPUTE_MODE": "cpu",
        "TOTALRO_MAX_ENGINEERING_WORKERS": "1",
        "PYTHONPATH": str(ROOT),
    })
    code = f"from wsgi import app; app.run(host='127.0.0.1',port={port},debug=False,use_reloader=False)"
    proc = subprocess.Popen([sys.executable, "-c", code], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        _wait_http(f"http://127.0.0.1:{port}/")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            calculate_requests = []
            page.on("request", lambda req: calculate_requests.append(req.url) if "/api/calculate/ccro" in req.url else None)
            page.goto(f"http://127.0.0.1:{port}/ro", wait_until="networkidle")

            data = _ccro_data()
            response = page.request.post(f"http://127.0.0.1:{port}/api/calculate/ccro", data=data)
            assert response.ok, response.text()
            result = response.json()
            assert result["ccro"] is True
            assert len(result.get("ccro_cycle_graph_profiles") or []) >= 2
            baseline_requests = len(calculate_requests)

            page.evaluate(
                """args => {
                  waterProfile={...args.water};
                  mode='ccro';activeCase=1;
                  caseStore[1]=caseStore[1]||{};
                  caseStore[1].waterProfile={...args.water};
                  caseStore[1].modeStates={...(caseStore[1].modeStates||{}),ccro:{...args.state}};
                  caseStore[1].caseResults={...(caseStore[1].caseResults||{}),ccro:args.result};
                  modeStates=caseStore[1].modeStates;caseResults=caseStore[1].caseResults;
                  caseStore[1].lastReportableMode='ccro';
                  caseStore[1].ccroSelectedGraphCycle=args.result.ccro_cycle_graph_profiles.at(-1).cycle;
                  lastResult=args.result;
                  updateWorkspaceChrome();
                  updateWaterWorkspaceTabs();
                  show(args.result);
                  persistActiveCase();
                  modeStates=caseStore[1].modeStates;caseResults=caseStore[1].caseResults;
                  modeStates.ccro._last_calculated_signature=window.TotalROCCRO.calculationSignatureForMode('ccro',modeStates.ccro);
                  syncActiveCaseStore();
                }""",
                {"water": data, "state": data, "result": result},
            )
            selector = page.locator("#ccroCycleGraphSelect")
            assert selector.count() == 1
            selector.wait_for(state="visible")
            final_html = page.locator("#ccroCycleGraphSection").inner_html()
            profiles = result["ccro_cycle_graph_profiles"]
            early_cycle = str(profiles[0]["cycle"])
            selector.select_option(early_cycle)
            early_html = page.locator("#ccroCycleGraphSection").inner_html()
            assert early_html != final_html
            assert len(calculate_requests) == baseline_requests

            page.evaluate("""() => { entitlementContext={role:'admin',licensed_tier:'platinum',effective_tier:'entry',is_admin:true,features:{}};effectiveTier='entry';applyTierEntitlements();openEngineeringReportDialog(); }""")
            note = page.locator("#reportReadinessNote")
            assert "ready" in (note.get_attribute("class") or "").lower(), note.inner_text()
            button = page.locator("#generateEngineeringReportBtn")
            assert button.is_enabled()

            with page.expect_popup() as popup_info:
                button.click()
            report_page = popup_info.value
            report_page.wait_for_load_state("networkidle")
            body = report_page.locator("body").inner_text()
            assert "Closed Circuit Reverse Osmosis" in body
            assert f"CCRO Cycle {early_cycle}" in body
            assert "Selected Graph Cycle" in body
            assert "Flux vs. Membrane Position" in body
            assert "Hydraulic / Osmotic / NDP Profile" in body
            assert "Stage 1" not in body
            pages = report_page.locator(".report-page")
            assert pages.count() == 2
            assert "Page 1 of 2" in pages.nth(0).inner_text()
            assert "Page 2 of 2" in pages.nth(1).inner_text()
            assert report_page.locator("svg").count() >= 3
            for i in range(report_page.locator("svg").count()):
                box = report_page.locator("svg").nth(i).bounding_box()
                assert box and box["width"] > 50 and box["height"] > 50
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
