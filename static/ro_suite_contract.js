(() => {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const THEME_KEY = 'twds-theme';
  const VALID_THEMES = new Set(['system', 'light', 'dark']);
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

  function initCalculationState() {
    let live = $('#twdsRoCalculationLive');
    if (!live) {
      live = document.createElement('div');
      live.id = 'twdsRoCalculationLive';
      live.setAttribute('aria-live', 'polite');
      live.setAttribute('aria-atomic', 'true');
      live.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)';
      document.body.appendChild(live);
    }
    const button = $('#calculateBtn');
    if (button) button.setAttribute('aria-describedby', live.id);
    document.addEventListener('twds:ro-calculation-state', (event) => {
      const detail = event.detail || {};
      live.textContent = detail.message || detail.state || '';
    });
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

  let advancedPlacementScheduled = false;

  function ensureAdvancedRoPlacement() {
    const plant = advancedConfigButton('multistage');
    const ccro = advancedConfigButton('ccro');
    const batch = advancedConfigButton('batch_ro');
    if (!plant || (!ccro && !batch)) return false;

    const group = plant.closest('.nav-group');
    if (!group) return false;

    let changed = false;
    let heading = group.querySelector('[data-advanced-ro-heading]');
    if (!heading) {
      heading = document.createElement('span');
      heading.className = 'nav-group-title advanced-ro-config-title';
      heading.dataset.advancedRoHeading = '1';
      heading.textContent = 'ADVANCED RO CONFIGURATIONS';
    }

    const first = ccro || batch;
    if (heading.parentElement !== group || heading.nextElementSibling !== first) {
      group.insertBefore(heading, first);
      changed = true;
    }

    if (ccro) {
      if (heading.nextElementSibling !== ccro) {
        group.insertBefore(ccro, heading.nextSibling);
        changed = true;
      }
      const detail = ccro.querySelector('.nav-detail');
      const detailText = 'Continuous fresh-feed makeup · concentrating recirculating loop';
      if (detail && detail.textContent !== detailText) detail.textContent = detailText;
      const title = ccro.disabled
        ? (ccro.title || 'Calculate Plant Design before opening CCRO')
        : 'Closed Circuit RO · continuous fresh-feed makeup into a concentrating recirculating loop';
      if (ccro.title !== title) ccro.title = title;
    }

    if (batch) {
      const anchor = ccro || heading;
      if (anchor.nextElementSibling !== batch) {
        group.insertBefore(batch, anchor.nextSibling);
        changed = true;
      }
      const detail = batch.querySelector('.nav-detail');
      const detailText = 'Full Batch RO · initially charged inventory · cyclic concentration';
      if (detail && detail.textContent !== detailText) detail.textContent = detailText;
      const title = batch.disabled
        ? (batch.title || 'Calculate Plant Design before opening Batch RO')
        : 'Full Batch RO · processes an initially charged inventory without continuous fresh-feed mixing';
      if (batch.title !== title) batch.title = title;
    }

    return changed;
  }

  function scheduleAdvancedRoPlacement() {
    if (advancedPlacementScheduled) return;
    advancedPlacementScheduled = true;
    queueMicrotask(() => {
      advancedPlacementScheduled = false;
      ensureAdvancedRoPlacement();
    });
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
    if (nav) new MutationObserver(scheduleAdvancedRoPlacement).observe(nav, {childList: true, subtree: true});
    const results = $('.results');
    if (results) new MutationObserver(() => { normalizeGuidance(results); normalizeResults(); }).observe(results, {childList: true, subtree: true});
    const fields = $('#fields');
    if (fields) new MutationObserver(() => normalizeGuidance(fields)).observe(fields, {childList: true, subtree: true});
  });
})();
