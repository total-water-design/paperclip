from pathlib import Path

from ro_suite_ui_contract import _augment_html


HOTFIX = Path('static/ro_calculate_hotfix.js')
APP_JS = Path('static/app.js')


def test_hotfix_targets_canonical_calculate_button_only():
    src = HOTFIX.read_text(encoding='utf-8')
    assert "document.querySelector('#calculateBtn')" in src
    assert "setPrimaryLabel = function totalRoSetPrimaryLabel" in src
    assert "document.querySelector('.primary')" not in src
    assert "querySelector('.primary')" not in src


def test_multi_pass_is_secondary_hidden_and_idempotent():
    src = HOTFIX.read_text(encoding='utf-8')
    assert "button.classList.remove('primary')" in src
    assert "button.classList.add('ghost', 'mp-calculate-secondary')" in src
    assert "const desired = 'Calculate multi-pass flowsheet'" in src
    assert "if (label && label.textContent !== desired) label.textContent = desired" in src
    assert "if (button.hidden !== hidden) button.hidden = hidden" in src
    assert "if (button.getAttribute('aria-hidden') !== ariaHidden)" in src
    assert 'restorePlantDesignNavigationIfNeeded' not in src


def test_fresh_normal_submit_clears_stale_cancel_state():
    src = HOTFIX.read_text(encoding='utf-8')
    assert "calculationCancelRequested = false" in src
    assert "activeCalculationController = null" in src
    assert "addEventListener('submit', resetStaleCancellationBeforeNormalSubmit, true)" in src


def test_workspace_labels_are_unambiguous():
    src = HOTFIX.read_text(encoding='utf-8')
    assert "mode === 'water'" in src
    assert "Calculate water chemistry" in src
    assert "mode === 'multistage'" in src
    assert "Calculate Plant Design" in src


def test_water_quality_keeps_calculated_chemistry_in_water_workspace():
    src = HOTFIX.read_text(encoding='utf-8')
    assert 'preserveWaterQualityWorkspaceAfterCalculation' in src
    assert 'const legacyCalc = calc' in src
    assert 'const legacyChangeMode = changeMode' in src
    assert 'changeMode = function totalRoWaterQualityNavigationGuard' in src
    assert "if (target === 'multistage') return" in src
    assert 'changeMode = legacyChangeMode' in src
    assert 'chemistryResultsHtml(lastChemistryResult)' in src
    assert 'clearCanonicalBusyState()' in src
    assert "button.dataset.twdsBusy = '0'" in src
    assert "button.setAttribute('aria-busy', 'false')" in src
    assert 'refreshWorkflowGatesAfterWaterQuality()' in src
    assert "typeof updateWorkflowGates === 'function'" in src
    assert 'calc = wrapped' in src


def test_native_adapter_loads_hotfix_after_host_app():
    html = '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'
    out = _augment_html(html)
    assert '/static/ro_calculate_hotfix.js' in out
    assert out.index('/static/app.js') < out.index('/static/ro_calculate_hotfix.js')
    assert out.index('/static/ro_calculate_hotfix.js') < out.index('/static/ro_suite_contract.js')


def test_legacy_generic_primary_defect_remains_detectable_for_hotfix_coverage():
    """Guard the hotfix until the large legacy app.js can be natively refactored safely."""
    src = APP_JS.read_text(encoding='utf-8')
    assert "function setPrimaryLabel(text){const b=$('.primary')" in src
    assert 'data-mp-calculate="1"' in src
    assert 'class="primary"' in src
