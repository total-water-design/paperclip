"""Chromium integration gate for canonical Calculate error/cancel/restart semantics."""
from __future__ import annotations

import os

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("TOTALRO_SMOKE_URL", "http://127.0.0.1:8765")


def _label(page):
    return page.locator("#calculateBtn .calc-btn-label").inner_text().strip()


def _wait_idle(page, timeout=30000):
    page.wait_for_function(
        """() => !canonicalCalculationInFlight &&
          !document.body.classList.contains('calculating') &&
          !document.querySelector('#calculateBtn')?.disabled &&
          document.querySelector('#calculateBtn')?.getAttribute('aria-busy')==='false' &&
          document.querySelector('#calculateBtn')?.dataset?.twdsBusy==='0' &&
          document.querySelector('#calculationOverlay')?.hidden===true""",
        timeout=timeout,
    )


def _submit_twice(page):
    page.evaluate(
        """() => {
          const form=document.querySelector('#calcForm');
          form.requestSubmit();
          form.requestSubmit();
        }"""
    )


def _assert_idle_contract(page, expected_label):
    state = page.evaluate(
        """() => {
          const button=document.querySelector('#calculateBtn');
          return {
            calculating:document.body.classList.contains('calculating'),
            inFlight:canonicalCalculationInFlight,
            disabled:button.disabled,
            ariaBusy:button.getAttribute('aria-busy'),
            twdsBusy:button.dataset.twdsBusy,
            calculateState:button.getAttribute('data-twds-calculate-state'),
            controller:activeCalculationController,
            cancelRequested:calculationCancelRequested,
            overlayHidden:document.querySelector('#calculationOverlay').hidden,
          };
        }"""
    )
    assert state == {
        "calculating": False,
        "inFlight": False,
        "disabled": False,
        "ariaBusy": "false",
        "twdsBusy": "0",
        "calculateState": None,
        "controller": None,
        "cancelRequested": False,
        "overlayHidden": True,
    }, state
    assert _label(page) == expected_label


def _install_failure(page, endpoint, kind):
    page.evaluate(
        """({endpoint,kind}) => {
          totalroFetch=(url,options={})=>{
            if(String(url).includes(endpoint)){
              window.__injectedRequestCount=(window.__injectedRequestCount||0)+1;
              if(kind==='network')return Promise.reject(new TypeError('Injected network failure'));
              if(kind==='malformed')return Promise.resolve(new Response('not-json',{status:200,headers:{'Content-Type':'text/plain'}}));
              return Promise.resolve(new Response(JSON.stringify({error:'Injected server calculation failure'}),{status:500,headers:{'Content-Type':'application/json'}}));
            }
            return window.__nativeTotalroFetch(url,options);
          };
        }""",
        {"endpoint": endpoint, "kind": kind},
    )


def _install_pending(page, endpoint, fixture_expression):
    page.evaluate(
        """({endpoint,fixtureExpression}) => {
          const fixture=(0,eval)(fixtureExpression);
          window.__pendingRequestCount=0;
          totalroFetch=(url,options={})=>{
            if(String(url).includes(endpoint)){
              window.__pendingRequestCount+=1;
              return new Promise((resolve,reject)=>{
                const abort=()=>reject(new DOMException('Aborted','AbortError'));
                if(options.signal?.aborted){abort();return;}
                options.signal?.addEventListener('abort',abort,{once:true});
                window.__resolvePendingRequest=()=>resolve(new Response(JSON.stringify(fixture),{status:200,headers:{'Content-Type':'application/json'}}));
              });
            }
            return window.__nativeTotalroFetch(url,options);
          };
        }""",
        {"endpoint": endpoint, "fixtureExpression": fixture_expression},
    )


def _restore_fetch(page):
    page.evaluate("() => {totalroFetch=window.__nativeTotalroFetch;}")


def test_total_ro_calculate_error_cancel_restart_lifecycle():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(30000)
        console_errors = []
        page_errors = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(f"{BASE_URL}/ro", wait_until="domcontentloaded")
        page.locator("#calculatorApp").wait_for(state="visible")
        page.locator("#fields input, #fields select").first.wait_for(state="visible")
        page.evaluate(
            """() => {
              if(!seawaterPresets.length)throw new Error('No seawater presets loaded');
              waterProfile=makeWaterProfile(seawaterPresets[0]);
              syncActiveCaseStore();
              renderWaterTab();
            }"""
        )

        # Establish a real successful chemistry fixture and valid Water Quality gate.
        page.locator("#calculateBtn").click()
        page.wait_for_function(
            "() => !!lastChemistryResult && !!caseStore?.[activeCase]?.chemistryResult",
            timeout=90000,
        )
        _wait_idle(page)
        page.evaluate(
            """() => {
              window.__nativeTotalroFetch=totalroFetch;
              window.__chemFixture=deepClone(lastChemistryResult);
            }"""
        )
        assert _label(page) == "Calculate water chemistry"

        # Every request failure must return the canonical Water UI to a usable idle state.
        for kind, expected in [
            ("network", "could not reach"),
            ("server", "Injected server calculation failure"),
            ("malformed", "unreadable response"),
        ]:
            page.evaluate("() => {window.__injectedRequestCount=0;}")
            _install_failure(page, "/api/chemistry/analyze", kind)
            _submit_twice(page)
            _wait_idle(page)
            assert page.evaluate("() => window.__injectedRequestCount") == 1
            assert expected.lower() in page.locator("#error").inner_text().lower()
            assert page.evaluate("() => mode") == "water"
            _assert_idle_contract(page, "Calculate water chemistry")
            _restore_fetch(page)

        # Water cancellation is client-side: abort the fetch, clean up, and prove restart.
        page.evaluate(
            """() => {
              lastChemistryResult=null;
              if(caseStore?.[activeCase])caseStore[activeCase].chemistryResult=null;
              renderWaterTab();
            }"""
        )
        _install_pending(page, "/api/chemistry/analyze", "window.__chemFixture")
        _submit_twice(page)
        page.wait_for_function(
            "() => canonicalCalculationInFlight && document.body.classList.contains('calculating') && window.__pendingRequestCount===1"
        )
        page.evaluate("() => changeMode('multistage')")
        assert page.evaluate("() => mode") == "water"
        page.locator("#cancelCalculationBtn").click()
        _wait_idle(page)
        assert page.evaluate("() => lastChemistryResult") is None
        _assert_idle_contract(page, "Calculate water chemistry")
        _restore_fetch(page)

        page.locator("#calculateBtn").click()
        page.wait_for_function("() => !!lastChemistryResult", timeout=90000)
        _wait_idle(page)
        assert "reported tds" in page.locator("#results").inner_text().lower()
        assert page.locator('[data-mode="multistage"]').is_enabled()

        # Enter Plant explicitly and build a physically consistent regional SWRO case.
        page.locator('[data-mode="multistage"]').click()
        page.wait_for_function("() => mode==='multistage'")
        page.evaluate(
            """() => {
              const design={...defaults.multistage,
                stage_count:1,design_mode:'manual',solve_basis:'pressure',membrane_coupling:'on',
                feed_flow:100,membrane_pressure_1:60,vessels_1:12,elements_per_vessel_1:7,
                suction_pressure:2,permeate_pressure:0,permeate_pressure_1:0,
                fouling_factor:0.9,salt_passage_factor:1.0,pump_eff:0.85,motor_eff:0.97,vfd_eff:0.97,
                pretreatment_discharge_pressure:6,pretreatment_recovery:0.85,
                pretreatment_pump_eff:0.82,pretreatment_motor_eff:0.95,pretreatment_vfd_eff:0.97,
                operating_trains:1};
              modeStates.multistage=design;
              renderFields(design);
              lastResult=null;caseResults.multistage=undefined;
              if(caseStore?.[activeCase]){caseStore[activeCase].baseDesignSeed=null;caseStore[activeCase].caseResults.multistage=undefined;}
            }"""
        )
        assert _label(page) == "Calculate Plant Design"
        mp = page.locator("#multiPassCalculateBtn")
        assert mp.count() == 1 and mp.is_hidden()
        assert "primary" not in (mp.get_attribute("class") or "").split()

        # Plant cancellation uses the same canonical single-flight owner and permits restart.
        _install_pending(page, "/api/calculate/multistage", "({ok:true})")
        _submit_twice(page)
        page.wait_for_function(
            "() => canonicalCalculationInFlight && document.body.classList.contains('calculating') && window.__pendingRequestCount===1"
        )
        page.evaluate("() => changeMode('water')")
        assert page.evaluate("() => mode") == "multistage"
        page.locator("#cancelCalculationBtn").click()
        _wait_idle(page)
        assert page.evaluate("() => lastResult") is None
        _assert_idle_contract(page, "Calculate Plant Design")
        _restore_fetch(page)

        page.locator("#calculateBtn").click()
        page.wait_for_function(
            "() => !!lastResult && !!caseResults?.multistage && !!caseStore?.[activeCase]?.baseDesignSeed",
            timeout=120000,
        )
        _wait_idle(page)
        assert page.evaluate("() => caseStore[activeCase].baseDesignSeed.stale") is False
        assert "Enter required inputs and calculate." not in page.locator("#results").inner_text()
        _assert_idle_contract(page, "Calculate Plant Design")

        fatal = [message for message in console_errors if "favicon" not in message.lower()]
        assert not fatal, "browser console errors: " + " | ".join(fatal[:10])
        assert not page_errors, "browser page errors: " + " | ".join(page_errors[:10])
        browser.close()
