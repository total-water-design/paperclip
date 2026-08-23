/* Shared membrane catalog presentation for Total RO Design.
 * Loaded after app.js by the Total RO Design app branch during reconciliation.
 * Keeps RO and NF as separate menu sections while preserving legacy project IDs.
 */
(function () {
  const esc = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  function canonicalManufacturer(name) {
    const raw = String(name || '').trim();
    const key = raw.toLowerCase();
    if (['lg water solutions', 'lg nanoh2o', 'lg chem water solutions', 'nanoh2o'].includes(key)) return 'NanoH2O';
    if (['mann+hummel / trisep', 'trisep', 'trisep®'].includes(key)) return 'TRISEP';
    return raw;
  }

  function canonicalRecordId(recordId) {
    const parts = String(recordId || '').split('|');
    if (parts.length < 3) return String(recordId || '');
    parts[0] = canonicalManufacturer(parts[0]);
    return parts.join('|');
  }

  window.membraneManufacturerLabel = canonicalManufacturer;

  window.membraneOptions = function membraneOptionsByTechnology(selected) {
    const current = canonicalRecordId(selected);
    const all = Array.isArray(window.membranes) ? window.membranes : (typeof membranes !== 'undefined' ? membranes : []);
    const order = ['RO', 'NF'];
    const labels = {RO: 'Reverse Osmosis (RO)', NF: 'Nanofiltration (NF)'};
    const grouped = {};
    all.forEach((m) => {
      const technology = String(m.membrane_type || 'RO').toUpperCase();
      (grouped[technology] ??= []).push(m);
    });
    return order.filter((technology) => grouped[technology]?.length).map((technology) => {
      const options = grouped[technology]
        .slice()
        .sort((a, b) => `${canonicalManufacturer(a.manufacturer)} ${a.family || ''} ${a.model || ''}`.localeCompare(`${canonicalManufacturer(b.manufacturer)} ${b.family || ''} ${b.model || ''}`))
        .map((m) => {
          const id = canonicalRecordId(m.record_id);
          const disabled = (!m.calculation_enabled || m.design_selectable === false) ? ' disabled' : '';
          const chosen = (id === current) ? ' selected' : '';
          const suffix = disabled ? ' · catalog only' : '';
          return `<option value="${esc(m.record_id)}"${chosen}${disabled}>${esc(canonicalManufacturer(m.manufacturer))} · ${esc(m.model)}${suffix}</option>`;
        }).join('');
      return `<optgroup label="${labels[technology] || esc(technology)}">${options}</optgroup>`;
    }).join('');
  };

  if (typeof window.membraneSpecNoteHtml === 'function') {
    const baseSpecNote = window.membraneSpecNoteHtml;
    window.membraneSpecNoteHtml = function membraneSpecNoteWithArchive(mm, key) {
      const base = baseSpecNote(mm, key);
      if (!mm) return base;
      const extras = [];
      if (Number.isFinite(Number(mm.specific_flux_A_app_lmh_bar))) extras.push(`A ${Number(mm.specific_flux_A_app_lmh_bar).toFixed(4)} LMH/bar`);
      if (Number.isFinite(Number(mm.salt_permeability_B_lmh))) extras.push(`B ${Number(mm.salt_permeability_B_lmh).toFixed(4)} LMH`);
      if (mm.spec_archive_url) extras.push(`<a href="${esc(mm.spec_archive_url)}" target="_blank" rel="noopener">Manufacturer spec PDF</a>`);
      if (!extras.length) return base;
      return `${base}<div class="membrane-spec-transport">${extras.join(' · ')}</div>`;
    };
  }
})();
