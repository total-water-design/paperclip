from pathlib import Path

from ro_suite_ui_contract import _augment_html


APP_JS = Path('static/app.js')
SUITE_JS = Path('static/ro_suite_contract.js')
TEMPLATE = Path('templates/index.html')
RETIRED_HOTFIX = Path('static/ro_calculate_hotfix.js')
MOBILE_CSS = Path('static/ro_mobile_compat.css')


def test_template_has_one_semantic_canonical_calculate_button():
    src = TEMPLATE.read_text(encoding='utf-8')
    assert src.count('id="calculateBtn"') == 1
    assert 'id="calculateBtn"' in src and 'type="submit"' in src
    assert '<span class="calc-btn-label">Calculate water chemistry</span>' in src
    assert 'Input workspace only' not in src


def test_native_app_owns_canonical_button_and_single_flight_lifecycle():
    src = APP_JS.read_text(encoding='utf-8')
    assert "function calculateButton(){return document.querySelector('#calculateBtn')}" in src
    assert "function calculateButtonLabel()" in src
    assert "workspaceCalculateLabel(modeKey=mode,fallback='Calculate')" in src
    assert "const resolved=workspaceCalculateLabel(mode,text||button.dataset.twdsIdleLabel||'Calculate')" in src
    assert "let canonicalCalculationInFlight=false" in src
    assert "if(canonicalCalculationInFlight)return" in src
    assert "canonicalCalculationInFlight=true" in src
    assert "setCalculating(true)" in src
    assert "finally{setCalculating(false);canonicalCalculationInFlight=false;}" in src
    assert "document.querySelector('.primary')" not in src
    assert "$('.primary')" not in src


def test_water_calculation_remains_in_water_and_renders_visible_results():
    src = APP_JS.read_text(encoding='utf-8')
    water = src.split('async function calc(){', 1)[1].split("if(mode==='chemistry')", 1)[0]
    assert "/api/chemistry/analyze" in water
    assert 'renderWaterChemistryResult(chem)' in water
    assert 'updateWorkflowGates()' in water
    assert "changeMode('multistage')" not in water
    assert "const waterHasResults=mode==='water'&&Boolean(lastChemistryResult)" in src
    assert "resultsPanel.hidden=waterOnly" in src
    assert 'renderCurrentWaterChemistry()' in src
    assert 'applyWaterChargeAnalysis(result)' in src
    assert "Promise.all([refreshCalculatedCarbonate(),refreshWaterChargeBalance()])" not in src
    assert "if(lastChemistryResult)applyWaterChargeAnalysis(lastChemistryResult);else markWaterChargePending()" in src


def test_set_calculating_is_the_only_canonical_state_owner():
    src = APP_JS.read_text(encoding='utf-8')
    assert "btn.dataset.twdsBusy=active?'1':'0'" in src
    assert "btn.dataset.twdsCalculateState='calculating'" in src
    assert "btn.removeAttribute('data-twds-calculate-state')" in src
    assert "const idleLabel=btn.dataset.twdsIdleLabel||workspaceCalculateLabel(mode)" in src
    assert "setPrimaryLabel(idleLabel)" in src
    for obsolete in (
        'clearCanonicalBusyState',
        'resetStaleCancellationBeforeNormalSubmit',
        'calc = wrapped',
        'setCalculating = wrapped',
        'totalRoWaterQualityNavigationGuard',
    ):
        assert obsolete not in src


def test_multi_pass_is_secondary_by_construction():
    src = APP_JS.read_text(encoding='utf-8')
    assert 'id="multiPassCalculateBtn"' in src
    assert 'class="ghost mp-calculate-secondary"' in src
    assert 'data-mp-calculate="1"' in src
    assert "root.querySelector('[data-mp-calculate]')?.addEventListener" in src
    block = src.split('id="multiPassCalculateBtn"', 1)[1].split('</button>', 1)[0]
    assert 'class="primary"' not in block


def test_suite_contract_is_accessibility_only_for_calculation_state():
    src = SUITE_JS.read_text(encoding='utf-8')
    assert "twds:ro-calculation-state" in src
    assert "form.addEventListener('submit'" not in src
    assert 'setCalcState(' not in src
    assert 'rememberIdleLabel(' not in src
    assert 'button.dataset.twdsBusy' not in src
    assert "button.setAttribute('aria-busy'" not in src


def test_suite_navigation_observer_is_idempotent_and_coalesced():
    src = SUITE_JS.read_text(encoding='utf-8')
    assert 'let advancedPlacementScheduled = false' in src
    assert 'heading.parentElement !== group || heading.nextElementSibling !== first' in src
    assert 'anchor.nextElementSibling !== batch' in src
    assert 'new MutationObserver(scheduleAdvancedRoPlacement)' in src
    assert "first.insertAdjacentElement('beforebegin', heading)" not in src
    assert "heading.insertAdjacentElement('afterend', ccro)" not in src
    assert "(ccro || heading).insertAdjacentElement('afterend', batch)" not in src


def test_obsolete_calculate_hotfix_is_not_loaded_or_retained():
    assert not RETIRED_HOTFIX.exists()
    html = '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'
    out = _augment_html(html)
    assert '/static/ro_calculate_hotfix.js' not in out
    assert '/static/ro_suite_contract.js' in out
    assert out.index('/static/app.js') < out.index('/static/ro_suite_contract.js')


def test_water_reset_invalidates_stored_chemistry_and_results():
    src = APP_JS.read_text(encoding='utf-8')
    assert 'lastChemistryResult=null;lastResult=null;caseResults={};modeStates={}' in src
    assert 'current.chemistryResult=null' in src
    assert 'current.baseDesignSeed=null' in src


def test_mobile_result_tables_are_contained_in_local_scrollers():
    src = MOBILE_CSS.read_text(encoding='utf-8')
    assert '/* Total RO native result-table containment */' in src
    assert '#calculatorApp .table-wrap' in src
    assert 'overflow-x:auto!important' in src
    assert 'contain:inline-size' in src
    assert '#calculatorApp{width:100%!important;max-width:100vw!important;overflow-x:clip!important}' in src



def test_hosted_runtime_safety_contract():
    app = APP_JS.read_text(encoding='utf-8')
    gunicorn = Path('gunicorn.conf.py').read_text(encoding='utf-8')
    assert 'function pollComputeStatus()' in app
    assert 'function startComputePolling()' in app
    assert 'setInterval(pollComputeStatus,1500)' in app
    assert 'setInterval(pollComputeStatus,450)' not in app
    assert "const chemistryRun=mode==='water'" in app
    assert "if(chemistryRun)stopComputePolling();else startComputePolling()" in app
    assert 'Evaluating ion balance, speciation, osmotic pressure and scaling indices.' in app
    assert 'Results will appear when the chemistry analysis completes.' in app
    assert 'max_requests = 0' in gunicorn
    assert 'max_requests_jitter = 0' in gunicorn
    assert 'max_requests = 200' not in gunicorn


def test_test_module_is_named_for_native_lifecycle():
    assert Path(__file__).name == 'test_ro_calculate_lifecycle.py'
