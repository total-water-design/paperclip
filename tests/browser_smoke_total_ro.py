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
              tag:el.tagName,id:el.id||'',cls:String(el.className||'').slice(0,160),
              left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width),
              scrollWidth:Math.round(el.scrollWidth||0),clientWidth:Math.round(el.clientWidth||0),
              display:getComputedStyle(el).display,position:getComputedStyle(el).position,
              minWidth:getComputedStyle(el).minWidth,widthCss:getComputedStyle(el).width
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


def _label(page):
    return page.locator('#calculateBtn .calc-btn-label').inner_text().strip()


def _dom_click(page, selector):
    page.evaluate("selector => document.querySelector(selector).click()", selector)


def _arm_calculation_state_recorder(page):
    page.evaluate("""() => {
      window.__calcStateTransitions=[];
      const capture=()=>{
        const button=document.querySelector('#calculateBtn');
        const overlay=document.querySelector('#calculationOverlay');
        window.__calcStateTransitions.push({
          calculating:document.body.classList.contains('calculating'),
          disabled:Boolean(button?.disabled),
          ariaBusy:button?.getAttribute('aria-busy'),
          twdsBusy:button?.dataset?.twdsBusy,
          overlayHidden:Boolean(overlay?.hidden)
        });
      };
      window.__calcStateObserver?.disconnect?.();
      window.__calcStateObserver=new MutationObserver(capture);
      window.__calcStateObserver.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class','hidden','disabled','aria-busy','data-twds-busy','data-twds-calculate-state']});
      capture();
    }""")


def _assert_calculation_state_cycle(page):
    transitions=page.evaluate("() => window.__calcStateTransitions || []")
    assert any(x['calculating'] and x['disabled'] and x['ariaBusy']=='true' and not x['overlayHidden'] for x in transitions), transitions
    final=page.evaluate("""() => {
      const button=document.querySelector('#calculateBtn');
      const overlay=document.querySelector('#calculationOverlay');
      return {calculating:document.body.classList.contains('calculating'),disabled:button.disabled,ariaBusy:button.getAttribute('aria-busy'),twdsBusy:button.dataset.twdsBusy,overlayHidden:overlay.hidden};
    }""")
    assert final=={'calculating':False,'disabled':False,'ariaBusy':'false','twdsBusy':'0','overlayHidden':True}, final


def test_total_ro_browser_smoke():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(20000)
        console_errors = []
        page_errors = []
        chemistry_responses = []
        ro_responses = []

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: chemistry_responses.append(response.status)
            if "/api/chemistry/analyze" in response.url and response.request.method == "POST"
            else ro_responses.append(response.status)
            if "/api/calculate/multistage" in response.url and response.request.method == "POST"
            else None,
        )
        page.goto(f"{BASE_URL}/ro", wait_until="domcontentloaded")

        print('BROWSER HOTFIX: shell', flush=True)
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
            _dom_click(page, '[data-tier-preview="entry"]')
            page.wait_for_timeout(100)
            assert page.locator('[data-mode="ccro"]').count() == 1
            assert page.locator('[data-mode="batch_ro"]').count() == 1

        # A. WATER QUALITY — one canonical action, real chemistry request, visible results.
        print('BROWSER HOTFIX: water setup', flush=True)
        assert _label(page) == 'Calculate water chemistry'
        assert page.locator('button.primary').count() == 1
        page.evaluate("""() => {
          if (!seawaterPresets.length) throw new Error('No seawater presets loaded');
          waterProfile=makeWaterProfile(seawaterPresets[0]);
          syncActiveCaseStore();
          renderWaterTab();
        }""")
        assert _label(page) == 'Calculate water chemistry'
        chemistry_before = len(chemistry_responses)
        print('BROWSER HOTFIX: water click', flush=True)
        _arm_calculation_state_recorder(page)
        page.evaluate("() => {const form=document.querySelector('#calcForm');form.requestSubmit();form.requestSubmit();}")
        page.wait_for_function(
            "() => !!lastChemistryResult && !!caseStore?.[activeCase]?.chemistryResult",
            timeout=60000,
        )
        page.wait_for_function("() => mode === 'water'", timeout=15000)
        page.wait_for_function(
            "() => /Reported TDS/i.test(document.querySelector('#results')?.innerText || '') && /Osmotic pressure/i.test(document.querySelector('#results')?.innerText || '')",
            timeout=15000,
        )
        assert len(chemistry_responses) == chemistry_before + 1
        assert chemistry_responses[-1] == 200
        assert 'Water Quality' in page.locator('#modeLabel').inner_text()
        assert _label(page) == 'Calculate water chemistry'
        assert page.locator('.results').is_visible()
        assert not page.locator('[data-mode="multistage"]').is_disabled()
        _assert_calculation_state_cycle(page)
        print('BROWSER HOTFIX: water result visible', flush=True)

        # Plant Design is an explicit navigation action, not an implicit chemistry side effect.
        _dom_click(page, '[data-mode="multistage"]')
        page.wait_for_function("() => mode === 'multistage'", timeout=15000)
        assert 'Plant Design' in page.locator('#modeLabel').inner_text()
        assert _label(page) == 'Calculate Plant Design'

        # B/C. PLANT DESIGN — Multi-Pass stays secondary/hidden for one pass.
        print('BROWSER HOTFIX: plant setup', flush=True)
        mp = page.locator('[data-mp-calculate]')
        assert mp.count() == 1
        assert 'primary' not in (mp.get_attribute('class') or '').split()
        assert mp.get_attribute('id') == 'multiPassCalculateBtn'
        assert mp.is_hidden()
        assert page.locator('button.primary').count() == 1

        # Build a deterministic one-stage form state directly, then exercise the real
        # form/button handler. This avoids unrelated change-event chemistry rerenders.
        page.evaluate("""() => {
          const d={...defaults.multistage,
            stage_count:1,design_mode:'manual',solve_basis:'pressure',membrane_coupling:'on',
            feed_flow:100,membrane_pressure_1:60,vessels_1:12,elements_per_vessel_1:7,
            suction_pressure:2,permeate_pressure:0,permeate_pressure_1:0,
            fouling_factor:0.9,salt_passage_factor:1.0,pump_eff:0.85,motor_eff:0.97,vfd_eff:0.97,
            pretreatment_discharge_pressure:6,pretreatment_recovery:0.85,
            pretreatment_pump_eff:0.82,pretreatment_motor_eff:0.95,pretreatment_vfd_eff:0.97,
            operating_trains:1
          };
          modeStates.multistage=d;
          renderFields(d);
        }""")
        assert _label(page) == 'Calculate Plant Design'
        mp = page.locator('[data-mp-calculate]')
        assert mp.is_hidden() and 'primary' not in (mp.get_attribute('class') or '').split()
        missing = page.evaluate("() => Array.from(document.querySelectorAll('#calcForm [required]')).filter(el=>!el.disabled && !el.readOnly && String(el.value||'').trim()==='').map(el=>el.name||el.id)")
        assert not missing, f'mandatory Plant Design fields unexpectedly blank: {missing}'

        ro_before = len(ro_responses)
        print('BROWSER HOTFIX: plant click', flush=True)
        _arm_calculation_state_recorder(page)
        page.evaluate("() => {const form=document.querySelector('#calcForm');form.requestSubmit();form.requestSubmit();}")
        page.wait_for_function(
            "() => !!lastResult && !!caseResults?.multistage && !!caseStore?.[activeCase]?.baseDesignSeed && !document.body.classList.contains('calculating')",
            timeout=90000,
        )
        assert len(ro_responses) == ro_before + 1
        assert ro_responses[-1] == 200
        results_text = page.locator('#results').inner_text()
        assert 'Enter required inputs and calculate.' not in results_text
        assert 'Calculation stopped by user' not in page.locator('body').inner_text()
        assert _label(page) == 'Calculate Plant Design'
        _assert_calculation_state_cycle(page)
        print('BROWSER HOTFIX: plant result visible', flush=True)

        # D. Stop is explicit, and the next normal submit starts from a clean state.
        print('BROWSER HOTFIX: stop/reset', flush=True)
        page.evaluate("() => setCalculating(true)")
        _dom_click(page, '#cancelCalculationBtn')
        page.wait_for_timeout(150)
        cancelled = page.evaluate("() => ({requested: calculationCancelRequested, aborted: !!activeCalculationController?.signal?.aborted})")
        assert cancelled['requested'] and cancelled['aborted']
        page.evaluate("() => setCalculating(false)")
        reset = page.evaluate("() => ({requested: calculationCancelRequested, controller: activeCalculationController})")
        assert reset['requested'] is False and reset['controller'] is None

        # Clear only stored result state so the next wait proves a fresh post-cancel run completed.
        page.evaluate("""() => {
          lastResult=null;
          caseResults.multistage=undefined;
          if (caseStore?.[activeCase]?.caseResults) caseStore[activeCase].caseResults.multistage=undefined;
        }""")
        after_stop_before = len(ro_responses)
        print('BROWSER HOTFIX: after-stop click', flush=True)
        _dom_click(page, '#calculateBtn')
        page.wait_for_function(
            "() => !!lastResult && !!caseResults?.multistage && !document.body.classList.contains('calculating')",
            timeout=90000,
        )
        assert len(ro_responses) > after_stop_before
        assert ro_responses[-1] == 200
        assert 'Calculation stopped by user' not in page.locator('body').inner_text()
        print('BROWSER HOTFIX: after-stop result visible', flush=True)

        # E. Repeated explicit mode switching restores correct label/ownership.
        print('BROWSER HOTFIX: mode switching', flush=True)
        _dom_click(page, '[data-mode="water"]')
        page.wait_for_function("() => mode === 'water'", timeout=15000)
        assert _label(page) == 'Calculate water chemistry'
        assert page.locator('button.primary').count() == 1
        _dom_click(page, '[data-mode="multistage"]')
        page.wait_for_function("() => mode === 'multistage'", timeout=15000)
        assert _label(page) == 'Calculate Plant Design'
        assert page.locator('button.primary').count() == 1
        _dom_click(page, '[data-mode="water"]')
        page.wait_for_function("() => mode === 'water'", timeout=15000)
        assert _label(page) == 'Calculate water chemistry'
        _dom_click(page, '[data-mode="multistage"]')
        page.wait_for_function("() => mode === 'multistage'", timeout=15000)
        assert _label(page) == 'Calculate Plant Design'

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
