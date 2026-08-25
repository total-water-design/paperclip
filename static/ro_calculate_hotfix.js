(() => {
  'use strict';

  // Urgent Total RO calculation-control hotfix.
  // Keep #calculateBtn as the only authoritative normal workspace calculation action.
  const canonicalButton = () => document.querySelector('#calculateBtn');
  const canonicalLabel = () => canonicalButton()?.querySelector('.calc-btn-label');

  function normalWorkspaceLabel(requested) {
    try {
      if (typeof mode !== 'undefined') {
        if (mode === 'water') return 'Calculate water chemistry';
        if (mode === 'multistage') return 'Calculate Plant Design';
      }
    } catch (_) {}
    return requested || 'Calculate';
  }

  if (typeof setPrimaryLabel === 'function') {
    setPrimaryLabel = function totalRoSetPrimaryLabel(text) {
      const button = canonicalButton();
      if (!button) return;
      const label = normalWorkspaceLabel(text);
      button.innerHTML = `<span class="calc-btn-label">${escapeHtml(label)}</span><span class="calc-btn-spinner" aria-hidden="true"></span><span class="button-arrow">→</span>`;
    };
  }

  function normalizeMultiPassControl(root = document) {
    const button = root.querySelector?.('[data-mp-calculate]') || document.querySelector('[data-mp-calculate]');
    if (!button) return;

    button.classList.remove('primary');
    button.classList.add('ghost', 'mp-calculate-secondary');
    button.id ||= 'multiPassCalculateBtn';
    const label = button.querySelector('.calc-btn-label');
    const desired = 'Calculate multi-pass flowsheet';
    // MutationObserver watches child-list changes under #fields. Never write the
    // same text back unconditionally or the observer will recursively retrigger.
    if (label && label.textContent !== desired) label.textContent = desired;

    const hidden = button.disabled;
    if (button.hidden !== hidden) button.hidden = hidden;
    const ariaHidden = hidden ? 'true' : 'false';
    if (button.getAttribute('aria-hidden') !== ariaHidden) button.setAttribute('aria-hidden', ariaHidden);
  }

  function clearCanonicalBusyState() {
    const button = canonicalButton();
    if (!button) return;
    button.dataset.twdsBusy = '0';
    button.removeAttribute('data-twds-calculate-state');
    button.setAttribute('aria-busy', 'false');
    button.disabled = false;
  }

  function refreshWorkflowGatesAfterWaterQuality() {
    try {
      if (typeof updateWorkflowGates === 'function') updateWorkflowGates();
    } catch (_) {}
  }

  function normalizeCanonicalLabel() {
    const button = canonicalButton();
    const label = canonicalLabel();
    if (!button || !label || button.getAttribute('aria-busy') === 'true') return;
    const requested = label.textContent.trim();
    const desired = normalWorkspaceLabel(requested);
    if (requested !== desired) label.textContent = desired;
  }

  function preserveCanonicalLabelAfterBusyCleanup() {
    if (typeof setCalculating !== 'function' || setCalculating.__totalRoCanonicalLabelHotfix) return;
    const legacySetCalculating = setCalculating;
    const wrapped = function totalRoSetCalculatingWithCanonicalLabel(active, ...args) {
      const result = legacySetCalculating.call(this, active, ...args);
      if (!active) normalizeCanonicalLabel();
      return result;
    };
    wrapped.__totalRoCanonicalLabelHotfix = true;
    setCalculating = wrapped;
  }

  function resetStaleCancellationBeforeNormalSubmit() {
    try {
      if (!document.body.classList.contains('calculating')) {
        calculationCancelRequested = false;
        activeCalculationController = null;
      }
    } catch (_) {}
  }

  function renderWaterChemistryResult() {
    try {
      if (typeof lastChemistryResult === 'undefined' || !lastChemistryResult) return;
      const host = document.querySelector('#results');
      if (!host || typeof chemistryResultsHtml !== 'function') return;
      host.innerHTML = chemistryResultsHtml(lastChemistryResult);
      const balance = document.querySelector('#balanceWaterBtn');
      if (balance && typeof balanceActiveWater === 'function') {
        balance.addEventListener('click', balanceActiveWater, { once: true });
      }
    } catch (_) {}
  }

  function preserveWaterQualityWorkspaceAfterCalculation() {
    if (typeof calc !== 'function' || calc.__totalRoWaterWorkspaceHotfix) return;
    const legacyCalc = calc;
    const wrapped = async function totalRoCalculateWithWorkspaceOwnership(...args) {
      let startedInWater = false;
      try { startedInWater = typeof mode !== 'undefined' && mode === 'water'; } catch (_) {}
      if (!startedInWater || typeof changeMode !== 'function') return legacyCalc.apply(this, args);

      const legacyChangeMode = changeMode;
      changeMode = function totalRoWaterQualityNavigationGuard(target, ...rest) {
        if (target === 'multistage') return;
        return legacyChangeMode.call(this, target, ...rest);
      };
      try {
        const result = await legacyCalc.apply(this, args);
        renderWaterChemistryResult();
        clearCanonicalBusyState();
        refreshWorkflowGatesAfterWaterQuality();
        normalizeCanonicalLabel();
        return result;
      } finally {
        changeMode = legacyChangeMode;
      }
    };
    wrapped.__totalRoWaterWorkspaceHotfix = true;
    calc = wrapped;
  }

  function init() {
    const form = document.querySelector('#calcForm');
    if (form) form.addEventListener('submit', resetStaleCancellationBeforeNormalSubmit, true);

    preserveWaterQualityWorkspaceAfterCalculation();
    preserveCanonicalLabelAfterBusyCleanup();
    normalizeMultiPassControl();
    normalizeCanonicalLabel();

    const fields = document.querySelector('#fields');
    if (fields) {
      new MutationObserver(() => {
        normalizeMultiPassControl(fields);
        queueMicrotask(normalizeCanonicalLabel);
      }).observe(fields, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled'] });
    }

    const button = canonicalButton();
    if (button) {
      // The application temporarily changes the label while a calculation is
      // busy. Text mutations occur while aria-busy=true, so normalization must
      // also run when busy state clears; otherwise a transient label such as
      // "Validating…" can remain after the calculation has completed.
      new MutationObserver(() => queueMicrotask(normalizeCanonicalLabel))
        .observe(button, {
          childList: true,
          subtree: true,
          characterData: true,
          attributes: true,
          attributeFilter: ['aria-busy', 'disabled'],
        });
    }

    document.addEventListener('click', (event) => {
      if (event.target.closest('[data-mode],#conventionalSolutionBtn')) {
        setTimeout(() => {
          normalizeMultiPassControl();
          normalizeCanonicalLabel();
        }, 0);
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
