"""Final Chromium certification for the native Total RO Calculate lifecycle.

The customer workflow is driven in real Chromium. After the final long-running
Plant Design click, completion state is returned through a same-origin
``/healthz?finalcert=...`` request and read from the Flask access log. This
avoids any post-solver Playwright transport dependency without changing product
code or calculation behavior.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import queue as queue_module
import re
import time
import traceback
from urllib.parse import parse_qs, urlsplit
import uuid

from playwright.sync_api import sync_playwright

from browser_smoke_total_ro import _assert_no_page_overflow, _label

BASE_URL = os.environ.get("TOTALRO_SMOKE_URL", "http://127.0.0.1:8765")
SERVER_LOG = Path("/tmp/total-ro-final.log")


def _dispatch_click(page, selector: str) -> None:
    page.evaluate(
        """selector => {
          const el=document.querySelector(selector);
          if (!el) throw new Error(`Missing click target: ${selector}`);
          setTimeout(() => el.click(), 0);
        }""",
        selector,
    )


def _read_finalcert_signals(token: str, start_offset: int) -> list[dict]:
    """Read this certification run's same-origin signals from the Flask log."""
    if not SERVER_LOG.exists():
        return []
    try:
        with SERVER_LOG.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(start_offset)
            text = handle.read()
    except OSError:
        return []

    signals: list[dict] = []
    for line in text.splitlines():
        match = re.search(r'"GET ([^ ]+) HTTP/[0-9.]+"', line)
        if not match:
            continue
        try:
            query = parse_qs(urlsplit(match.group(1)).query)
            for raw in query.get("finalcert", []):
                payload = json.loads(raw)
                if payload.get("token") == token:
                    signals.append(payload)
        except Exception:
            continue
    return signals


def _wait_for_phase(token: str, phase: str, start_offset: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for payload in _read_finalcert_signals(token, start_offset):
            if payload.get("phase") == phase:
                return payload
        time.sleep(0.10)
    raise AssertionError(
        f"Timed out waiting for same-origin finalcert phase {phase!r}; "
        f"signals={_read_finalcert_signals(token, start_offset)}"
    )


def _browser_worker(result_queue, token: str, log_offset: int) -> None:
    """Run Chromium isolated so parent can stop it without transport cleanup."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(20000)

            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            page.goto(f"{BASE_URL}/ro", wait_until="domcontentloaded")
            page.locator("#calculatorApp").wait_for(state="visible")
            page.locator("#fields input, #fields select").first.wait_for(state="visible")
            page.locator('[data-mode="ccro"]').wait_for(state="attached")
            page.locator('[data-mode="batch_ro"]').wait_for(state="attached")

            assert page.locator("#calculateBtn").count() == 1
            assert page.locator("button.primary").count() == 1
            assert _label(page) == "Calculate water chemistry"
            _assert_no_page_overflow(page)

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(150)
            assert page.locator("#calculatorApp").is_visible()
            assert page.locator("#calculateBtn").count() == 1
            _assert_no_page_overflow(page, tolerance=24)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.wait_for_timeout(100)

            # Prove the same-origin access-log relay before sensitive work.
            page.evaluate(
                """token => {
                  window.__finalCertImages=[];
                  const img=new Image();
                  img.onerror=()=>{}; img.onload=()=>{};
                  window.__finalCertImages.push(img);
                  img.src='/healthz?finalcert='+encodeURIComponent(JSON.stringify({token,phase:'handshake'}))+'&_='+Date.now();
                }""",
                token,
            )
            handshake = _wait_for_phase(token, "handshake", log_offset, 10)
            assert handshake["phase"] == "handshake"

            # WATER QUALITY — real regional seawater workflow. Chemistry must
            # remain in Water Quality and explicitly unlock Plant Design.
            page.evaluate(
                """() => {
                  if (!seawaterPresets.length) throw new Error('No seawater presets loaded');
                  waterProfile=makeWaterProfile(seawaterPresets[0]);
                  syncActiveCaseStore();
                  renderWaterTab();
                }"""
            )
            page.locator("#calculateBtn").click(no_wait_after=True)
            page.wait_for_function(
                "() => !!lastChemistryResult && !!caseStore?.[activeCase]?.chemistryResult",
                timeout=60000,
            )
            page.wait_for_function(
                "() => mode==='water' && !document.body.classList.contains('calculating') && document.querySelector('#calculateBtn')?.getAttribute('aria-busy')!=='true' && !document.querySelector('#calculateBtn')?.disabled",
                timeout=20000,
            )
            water_text = page.locator("#results").inner_text()
            assert "reported tds" in water_text.lower()
            assert "Osmotic pressure" in water_text
            assert _label(page) == "Calculate water chemistry"
            assert page.locator('button.tab[data-mode="multistage"]').is_enabled()

            # Explicit Water ⇄ Plant navigation and canonical-label ownership.
            for target, expected_mode, expected_label in [
                ('button.tab[data-mode="multistage"]', "multistage", "Calculate Plant Design"),
                ('[data-mode="water"]', "water", "Calculate water chemistry"),
                ('button.tab[data-mode="multistage"]', "multistage", "Calculate Plant Design"),
            ]:
                _dispatch_click(page, target)
                page.wait_for_function(
                    "expected => mode===expected", arg=expected_mode, timeout=30000
                )
                page.wait_for_function(
                    "expected => document.querySelector('#calculateBtn .calc-btn-label')?.textContent?.trim()===expected",
                    arg=expected_label,
                    timeout=10000,
                )
                assert _label(page) == expected_label
                assert page.locator("button.primary").count() == 1

            assert "Plant Design" in page.locator("#modeLabel").inner_text()
            page.locator("#fields [name='feed_flow']").wait_for(state="attached")

            plant_state_js = """() => {
              const d={...defaults.multistage,stage_count:1,design_mode:'manual',solve_basis:'pressure',membrane_coupling:'on',
                feed_flow:100,membrane_pressure_1:60,
                membrane_1:'DuPont FilmTec|SW30HRLE-400|A / standard',vessels_1:12,elements_per_vessel_1:7,
                suction_pressure:2,permeate_pressure:0,permeate_pressure_1:0,
                fouling_factor:0.9,salt_passage_factor:1.0,pump_eff:0.85,motor_eff:0.97,vfd_eff:0.97,
                pretreatment_discharge_pressure:6,pretreatment_recovery:0.85,
                pretreatment_pump_eff:0.82,pretreatment_motor_eff:0.95,pretreatment_vfd_eff:0.97,operating_trains:1};
              modeStates.multistage=d;
              renderFields(d);
            }"""
            page.evaluate(plant_state_js)

            # Multi-Pass is secondary and hidden by native construction when one pass
            # is configured; no post-render correction layer is involved.
            page.wait_for_function(
                """() => {
                  const control=document.querySelector('[data-mp-calculate]');
                  return !!control && !control.classList.contains('primary') && control.id==='multiPassCalculateBtn' && (control.hidden||control.disabled);
                }""",
                timeout=10000,
            )
            mp_control = page.locator("[data-mp-calculate]")
            assert mp_control.count() == 1
            assert "primary" not in (mp_control.get_attribute("class") or "").split()
            assert mp_control.get_attribute("id") == "multiPassCalculateBtn"
            assert mp_control.is_hidden() or mp_control.is_disabled()
            assert "Calculate multi-pass flowsheet" in (mp_control.inner_text() or "")
            missing = page.evaluate(
                "() => Array.from(document.querySelectorAll('#calcForm [required]')).filter(el=>!el.disabled&&!el.readOnly&&String(el.value||'').trim()==='').map(el=>el.name||el.id)"
            )
            assert not missing, missing
            assert (
                page.locator('[name="membrane_1"]').input_value()
                == "DuPont FilmTec|SW30HRLE-400|A / standard"
            )

            # STOP/RESET before the real Plant calculation. The succeeding
            # successful real calculation is the stale-cancellation proof.
            page.evaluate("() => setCalculating(true)")
            page.locator("#cancelCalculationBtn").click(no_wait_after=True)
            page.wait_for_function(
                "() => calculationCancelRequested===true && !!activeCalculationController?.signal?.aborted",
                timeout=15000,
            )
            page.evaluate("() => setCalculating(false)")
            reset_state = page.evaluate(
                "() => ({requested:calculationCancelRequested,controller:activeCalculationController,calculating:document.body.classList.contains('calculating')})"
            )
            assert reset_state["requested"] is False
            assert reset_state["controller"] is None
            assert reset_state["calculating"] is False

            # Re-apply deterministic 60-bar SWRO inputs after synthetic Stop.
            page.evaluate(plant_state_js)
            page.wait_for_function(
                "() => !document.querySelector('[data-mp-calculate]')?.classList.contains('primary')",
                timeout=10000,
            )

            fatal_pre = [x for x in console_errors if "favicon" not in x.lower()]
            assert not fatal_pre, "browser console errors before final Plant run: " + " | ".join(fatal_pre[:10])
            assert not page_errors, "browser page errors before final Plant run: " + " | ".join(page_errors[:10])
            assert _label(page) == "Calculate Plant Design"
            assert page.locator("button.primary").count() == 1

            # Arm same-origin lifecycle markers. calc-finally proves that the
            # 200 response was stored/rendered; final proves normal busy cleanup.
            page.evaluate(
                """token => {
                  window.__finalCertPhase='armed';
                  window.__finalCertRuntimeErrors=[];
                  window.__finalCertImages=window.__finalCertImages||[];
                  const emit=(phase,state={})=>{
                    try{
                      const payload=JSON.stringify({token,phase,...state});
                      const img=new Image();
                      img.onerror=()=>{}; img.onload=()=>{};
                      window.__finalCertImages.push(img);
                      img.src='/healthz?finalcert='+encodeURIComponent(payload)+'&_='+Date.now()+Math.random();
                    }catch(_){}
                  };
                  const snapshot=()=>{
                    const resultText=document.querySelector('#results')?.innerText||'';
                    return {
                      mode,
                      calculating:document.body.classList.contains('calculating'),
                      buttonBusy:document.querySelector('#calculateBtn')?.getAttribute('aria-busy')||'',
                      buttonDisabled:!!document.querySelector('#calculateBtn')?.disabled,
                      label:document.querySelector('#calculateBtn .calc-btn-label')?.textContent?.trim()||'',
                      primaryCount:document.querySelectorAll('button.primary').length,
                      lastResult:!!lastResult,
                      caseResult:!!caseResults?.multistage,
                      storedCaseResult:!!caseStore?.[activeCase]?.caseResults?.multistage,
                      baseSeed:!!caseStore?.[activeCase]?.baseDesignSeed,
                      seedStale:caseStore?.[activeCase]?.baseDesignSeed?.stale ?? null,
                      cancelRequested:calculationCancelRequested,
                      controllerPresent:!!activeCalculationController,
                      resultHasEngineering:/recovery|permeate|product flow|sec/i.test(resultText),
                      resultHasPrompt:/Enter required inputs and calculate[.]/i.test(resultText),
                      resultHasCancelled:/Calculation stopped by user/i.test(resultText),
                      productFlow:Number(lastResult?.product_flow||0),
                      recovery:Number(lastResult?.recovery||0),
                      roSec:Number(lastResult?.ro_sec||0),
                      horizontalOverflow:Math.max(0,
                        (document.documentElement?.scrollWidth||0)-(document.documentElement?.clientWidth||0),
                        (document.body?.scrollWidth||0)-(document.body?.clientWidth||0)),
                      runtimeErrors:(window.__finalCertRuntimeErrors||[]).slice(0,2).map(x=>String(x).slice(0,180))
                    };
                  };
                  const originalConsoleError=console.error.bind(console);
                  console.error=(...args)=>{
                    try{window.__finalCertRuntimeErrors.push(args.map(x=>String(x)).join(' '));}catch(_){}
                    originalConsoleError(...args);
                  };
                  window.addEventListener('error',event=>{
                    try{window.__finalCertRuntimeErrors.push(String(event?.error?.message||event?.message||event));}catch(_){}
                  });
                  window.addEventListener('unhandledrejection',event=>{
                    try{window.__finalCertRuntimeErrors.push(String(event?.reason?.message||event?.reason||event));}catch(_){}
                  });

                  const originalCalc=globalThis.calc;
                  globalThis.calc=async function(...args){
                    try{return await originalCalc.apply(this,args);}
                    finally{emit('calc-finally',snapshot());}
                  };
                  const originalSetCalculating=globalThis.setCalculating;
                  globalThis.setCalculating=function(active){
                    const result=originalSetCalculating.apply(this,arguments);
                    if(active===false && window.__finalCertPhase==='armed'){
                      window.__finalCertPhase='signaled';
                      emit('final',snapshot());
                    }
                    return result;
                  };

                  lastResult=null;
                  caseResults.multistage=undefined;
                  if(caseStore?.[activeCase]?.caseResults)caseStore[activeCase].caseResults.multistage=undefined;
                  if(caseStore?.[activeCase])caseStore[activeCase].baseDesignSeed=null;
                  emit('armed',{mode,label:document.querySelector('#calculateBtn .calc-btn-label')?.textContent?.trim()||''});
                }""",
                token,
            )
            armed = _wait_for_phase(token, "armed", log_offset, 10)
            assert armed["mode"] == "multistage", armed
            assert armed["label"] == "Calculate Plant Design", armed

            result_queue.put({"kind": "pre_final_ok"})

            # FINAL Playwright operation. From this point on, pytest relies only
            # on same-origin access-log signals, not on Playwright transport.
            page.locator("#calculateBtn").click(no_wait_after=True)
            time.sleep(150)

    except BaseException:
        result_queue.put({"kind": "error", "error": traceback.format_exc()})


def test_total_ro_final_browser_certification():
    token = uuid.uuid4().hex
    log_offset = SERVER_LOG.stat().st_size if SERVER_LOG.exists() else 0

    ctx = mp.get_context("fork")
    result_queue = ctx.Queue()
    worker = ctx.Process(target=_browser_worker, args=(result_queue, token, log_offset))
    worker.start()

    final_state = None
    error_message = None
    pre_final_ok = False
    deadline = time.monotonic() + 135

    try:
        while time.monotonic() < deadline:
            # Surface worker errors without blocking access-log polling.
            while True:
                try:
                    message = result_queue.get_nowait()
                except queue_module.Empty:
                    break
                if message.get("kind") == "error":
                    error_message = message.get("error") or repr(message)
                    break
                if message.get("kind") == "pre_final_ok":
                    pre_final_ok = True
            if error_message:
                break

            signals = _read_finalcert_signals(token, log_offset)
            for payload in signals:
                if payload.get("phase") == "final":
                    final_state = payload
                    break
            if final_state is not None:
                break

            if not worker.is_alive() and not pre_final_ok:
                try:
                    message = result_queue.get_nowait()
                    if message.get("kind") == "error":
                        error_message = message.get("error") or repr(message)
                except queue_module.Empty:
                    pass
                if not error_message:
                    error_message = "Chromium worker exited before final certification."
                break
            time.sleep(0.10)
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
        if worker.is_alive():
            worker.kill()
            worker.join(timeout=5)

    signals = _read_finalcert_signals(token, log_offset)
    phases = [payload.get("phase") for payload in signals]

    assert error_message is None, {"error": error_message, "phases": phases, "signals": signals}
    assert pre_final_ok, {"error": "Worker never reached final Plant click", "phases": phases}
    assert final_state is not None, {"error": "No final Chromium lifecycle signal received", "phases": phases, "signals": signals}
    state = final_state

    assert "handshake" in phases and "armed" in phases and "calc-finally" in phases and "final" in phases, phases
    assert state["mode"] == "multistage", state
    assert state["calculating"] is False, state
    assert state["buttonBusy"] != "true", state
    assert state["buttonDisabled"] is False, state
    assert state["label"] == "Calculate Plant Design", state
    assert state["primaryCount"] == 1, state
    assert state["lastResult"] and state["caseResult"] and state["storedCaseResult"], state
    assert state["baseSeed"] and state["seedStale"] is False, state
    assert state["cancelRequested"] is False, state
    assert state["controllerPresent"] is False, state
    assert state["resultHasEngineering"] is True, state
    assert state["resultHasPrompt"] is False, state
    assert state["resultHasCancelled"] is False, state
    assert state["productFlow"] > 0, state
    assert 0 < state["recovery"] < 1, state
    assert state["roSec"] > 0, state
    assert state["horizontalOverflow"] <= 24, state
    assert not state["runtimeErrors"], state

    print("FINAL CHROMIUM: shell/responsive PASS", flush=True)
    print("FINAL CHROMIUM: same-origin lifecycle relay PASS", flush=True)
    print("FINAL CHROMIUM: Water Quality remains Water Quality PASS", flush=True)
    print("FINAL CHROMIUM: explicit Plant Design navigation/mode switching PASS", flush=True)
    print("FINAL CHROMIUM: multi-pass secondary control PASS", flush=True)
    print("FINAL CHROMIUM: Stop/reset before real calculation PASS", flush=True)
    print("FINAL CHROMIUM: real 60-bar Plant Design result/Base Design seed PASS", flush=True)
    print("FINAL CHROMIUM: post-stop calculation recovery PASS", flush=True)
    print("FINAL CHROMIUM: console/page runtime errors NONE", flush=True)
    print("FINAL CHROMIUM: CERTIFICATION PASS", flush=True)
