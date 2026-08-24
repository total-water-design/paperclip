(() => {
  'use strict';

  const status = document.getElementById('mfa-copy-status');

  async function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const area = document.createElement('textarea');
    area.value = value;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand('copy');
    document.body.removeChild(area);
    if (!copied) throw new Error('copy unavailable');
  }

  document.querySelectorAll('[data-copy-value]').forEach((button) => {
    button.addEventListener('click', async () => {
      const value = button.getAttribute('data-copy-value') || '';
      const label = button.getAttribute('data-copy-label') || 'value';
      try {
        await copyText(value);
        if (status) status.textContent = `${label.charAt(0).toUpperCase() + label.slice(1)} copied.`;
      } catch (_error) {
        if (status) status.textContent = `Copy unavailable. Select and copy the ${label} manually.`;
      }
    });
  });
})();
