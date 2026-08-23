(() => {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const THEME_KEY = 'twds-theme';
  const VALID_THEMES = new Set(['system', 'light', 'dark']);
  const CALC_LABELS = Object.freeze({
    validating: 'Validating…',
    calculating: 'Calculating…',
    converging: 'Converging…',
    converged: 'Converged',
    attention: 'Needs attention',
    failed: 'Calculation failed',
    stale: 'Recalculate'
  });

  function resolveTheme(pref) {
    if (pref === 'light' || pref === 'dark') return pref;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applySuiteTheme(pref) {
    const requested = VALID_THEMES.has(pref) ? pref : 'system';
    const resolved = resolveTheme(requested);
    document.documentElement.dataset.themePreference = requested;
    document.documentElement.dataset.theme = resolved;
    try { localStorage.setItem(THEME_KEY, requested); } catch (_) {}
    const select = $('#themeSelect');
    if (select && select.value !== requested) select.value = requested;
    const icon = $('#themeIcon');
    if (icon) icon.src = resolved === 'light' ? '/static/icons_v18/sun.svg' : '/static/icons_v18/moon.svg';
  }

  function initTheme() {
    const select = $('#themeSelect');
    if (!select) return;
    if (!select.querySelector('option[value="system"]')) {
      const option = document.createElement('option');
      option.value = 'system';
      option.textContent = 'System';
      select.insertBefore(option, select.firstChild);
    }
    Array.from(select.options).forEach((option) => {
      if (option.value === 'light') option.textContent = 'Light';
      if (option.value === 'dark') option.textContent = 'Dark';
    });
    let saved = 'system';
    try { saved = localStorage.getItem(THEME_KEY) || localStorage.getItem('totalrodesign-theme') || 'system'; } catch (_) {}
    if (!VALID_THEMES.has(saved)) saved = 'system';
    applySuiteTheme(saved);
    select.addEventListener('change', () => applySuiteTheme(select.value));
    if (window.matchMedia) {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', () => {
        if (document.documentElement.dataset.themePreference === 'system') applySuiteTheme('system');
      });
    }
  }

  function calculateButton() { return $('#calculateBtn'); }
  function calculateLabel() { return calculateButton()?.querySelector('.calc-btn-label'); }

  function rememberIdleLabel() {
    const button = calculateButton();
    const label = calculateLabel();
    if (!button || !label || button.dataset.twdsBusy === '1') return;
    const text = label.textContent.trim();
    if (text && !Object.values(CALC_LABELS).includes(text)) button.dataset.twdsIdleLabel = text;
  }

  function setCalcState(state, detail = '') {
    const button = calculateButton();
    const label = calculateLabel();
    if (!button || !label) return;
    if (state === 'idle') {
      button.dataset.twdsBusy = '0';
      label.textContent = button.dataset.twdsIdleLabel || 'Calculate';
      button.removeAttribute('data-twds-calculate-state');
      button.setAttribute('aria-busy', 'false');
    } else {
      if (button.dataset.twdsBusy !== '1') rememberIdleLabel();
      button.dataset.twdsBusy = '1';
      button.dataset.twdsCalculateState = state;
      button.setAttribute('aria-busy', ['validating', 'calculating', 'converging'].includes(state) ? 'true' : 'false');
      if (CALC_LABELS[state]) label.textContent = CALC_LABELS[state];
    }
    const live = $('#twdsRoCalculationLive');
    if (live) live.textContent = detail || CALC_LABELS[state] || '';
  }

  function initCalculationState() {
    const form = $('#calcForm');
    const button = calculateButton();
    if (!form || !button) return;
    rememberIdleLabel();
    const live = document.createElement('div');
    live.id = 'twdsRoCalculationLive';
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    live.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)';
    document.body.appendChild(live);
    button.setAttribute('aria-describedby', live.id);

    form.addEventListener('submit', () => setCalcState('validating'));

    const overlay = $('#calculationOverlay');
    if (overlay) {
      new MutationObserver(() => {
        if (!overlay.hidden) {
          const title = $('#calculationTitle')?.textContent || '';
          setCalcState(/converg/i.test(title) ? 'converging' : 'calculating', title);
        } else if (!document.body.classList.contains('calculating')) {
          setCalcState('idle');
        }
      }).observe(overlay, {attributes: true, childList: true, subtree: true, characterData: true});
    }

    const error = $('#error');
    if (error) {
      new MutationObserver(() => {
        const text = error.textContent.trim();
        if (text) setCalcState('failed', text);
      }).observe(error, {childList: true, subtree: true, characterData: true});
    }

    new MutationObserver(() => rememberIdleLabel()).observe(button, {childList: true, subtree: true, characterData: true});
  }

  function initProjectVocabulary() {
    const suite = $('.suite-return-btn');
    if (suite) {
      suite.title = 'Return to Total Water Design Suite';
      suite.setAttribute('aria-label', 'Return to Total Water Design Suite');
    }
    const project = $('#projectMetaToggle');
    if (project) project.setAttribute('aria-label', 'Project information and revision');
    const save = $('#saveProjectBtn');
    if (save) save.title = 'Save current project / create next revision when applicable';
  }

  function advancedConfigButton(mode) {
    return document.querySelector(`.sidebar-nav [data-mode="${mode}"]`);
  }

  function ensureAdvancedRoPlacement() {
    const plant = advancedConfigButton('multistage');
    const ccro = advancedConfigButton('ccro');
    const batch = advancedConfigButton('batch_ro');
    if (!plant || (!ccro && !batch)) return;

    const group = plant.closest('.nav-group');
    if (!group) return;

    let heading = group.querySelector('[data-advanced-ro-heading]');
    if (!heading) {
      heading = document.createElement('span');
      heading.className = 'nav-group-title advanced-ro-config-title';
      heading.dataset.advancedRoHeading = '1';
      heading.textContent = 'ADVANCED RO CONFIGURATIONS';
    }

    const first = ccro || batch;
    if (first.parentElement !== group) group.appendChild(first);
    first.insertAdjacentElement('beforebegin', heading);

    if (ccro) {
      if (ccro.parentElement !== group) group.appendChild(ccro);
      heading.insertAdjacentElement('afterend', ccro);
      const detail = ccro.querySelector('.nav-detail');
      if (detail) detail.textContent = 'Continuous fresh-feed makeup · concentrating recirculating loop';
      ccro.title = ccro.disabled ? (ccro.title || 'Calculate Plant Design before opening CCRO') : 'Closed Circuit RO · continuous fresh-feed makeup into a concentrating recirculating loop';
    }

    if (batch) {
      if (batch.parentElement !== group) group.appendChild(batch);
      (ccro || heading).insertAdjacentElement('afterend', batch);
      const detail = batch.querySelector('.nav-detail');
      if (detail) detail.textContent = 'Full Batch RO · initially charged inventory · cyclic concentration';
      batch.title = batch.disabled ? (batch.title || 'Calculate Plant Design before opening Batch RO') : 'Full Batch RO · processes an initially charged inventory without continuous fresh-feed mixing';
    }
  }

  function normalizeGuidance(root = document) {
    root.querySelectorAll('.warning,.error,.error-bubble,.solve-hint').forEach((el) => {
      if (el.dataset.twdsSeverity) return;
      const classes = String(el.className || '');
      const text = el.textContent || '';
      let severity = 'information';
      if (/error-bubble|\berror\b/.test(classes)) severity = /service|system|network|internal error/i.test(text) ? 'critical' : 'calculation_error';
      else if (/warning/.test(classes)) severity = 'warning';
      else if (/solve-hint/.test(classes)) severity = 'review';
      el.dataset.twdsSeverity = severity;
      el.setAttribute('role', severity === 'critical' || severity === 'calculation_error' ? 'alert' : 'status');
    });
  }

  function normalizeResults() {
    const root = $('.results');
    if (!root) return;
    root.setAttribute('aria-label', 'RO calculation results');
    root.querySelectorAll('table').forEach((table) => {
      table.dataset.twdsResultsLevel ||= 'detailed-results';
      const parent = table.parentElement;
      if (parent && !/table-wrap|table-scroll/.test(parent.className || '')) parent.style.overflowX = 'auto';
    });
    root.querySelectorAll('.warning,.constraint,.error').forEach((el) => el.dataset.twdsResultsLevel = 'warnings-constraints');
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.dataset.twdsUiContract = '1.0';
    initTheme();
    initProjectVocabulary();
    initCalculationState();
    ensureAdvancedRoPlacement();
    normalizeGuidance();
    normalizeResults();

    const nav = $('.sidebar-nav');
    if (nav) new MutationObserver(() => ensureAdvancedRoPlacement()).observe(nav, {childList: true, subtree: true});
    const results = $('.results');
    if (results) new MutationObserver(() => { normalizeGuidance(results); normalizeResults(); }).observe(results, {childList: true, subtree: true});
    const fields = $('#fields');
    if (fields) new MutationObserver(() => { rememberIdleLabel(); normalizeGuidance(fields); }).observe(fields, {childList: true, subtree: true});
  });
})();
