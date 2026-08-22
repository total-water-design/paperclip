import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'data' / 'swro_membranes.json'


def _load():
    data = json.loads(DB_PATH.read_text(encoding='utf-8'))
    rows = data['membranes']
    for row in rows:
        variant = row.get('test_variant', 'A / standard')
        row['record_id'] = f"{row['manufacturer']}|{row['model']}|{variant}"
    return data, rows


META, MEMBRANES = _load()
BY_ID = {r['record_id']: r for r in MEMBRANES}

# Compatibility aliases for project files created before LG's current corporate
# naming was normalized in the expanded membrane catalog.
_ID_ALIASES = {}
for r in MEMBRANES:
    if r.get('manufacturer') == 'LG Water Solutions':
        old = f"LG NanoH2O|{r['model']}|{r.get('test_variant','A / standard')}"
        _ID_ALIASES[old] = r['record_id']


def _public_row(r):
    numeric = ('area_m2','area_ft2','flow_m3d','flow_gpd','rejection_pct','boron_rejection_pct',
               'pressure_psi','tds_ppm','recovery_pct','specific_flux_A_app_lmh_bar',
               'test_flux_lmh','salt_passage_pct','max_operating_pressure_bar','diameter_in','spacer_mil',
               'water_permeability_A_lmh_bar','nf_b_mono_mono_lmh','nf_b_mixed_lmh','nf_b_divalent_divalent_lmh','max_dp_per_vessel_bar')
    out = {
        'record_id': r['record_id'],
        'manufacturer': r['manufacturer'],
        'model': r['model'],
        'family': r.get('family'),
        'application': r.get('application'),
        'membrane_type': r.get('membrane_type','RO'),
        'test_variant': r.get('test_variant'),
        'source': r.get('source'),
        'catalog_status': r.get('catalog_status'),
        'verification_status': r.get('verification_status'),
        'calculation_enabled': bool(r.get('calculation_enabled', True)),
        'calculation_disabled_reason': r.get('calculation_disabled_reason'),
        'feed_spacer_text': r.get('feed_spacer_text'),
        'test_solute': r.get('test_solute'),
        'data_basis': r.get('data_basis'),
        'nf_transport_model': r.get('nf_transport_model'),
        'nf_rejection_benchmarks': r.get('nf_rejection_benchmarks'),
        'nf_selectivity_note': r.get('nf_selectivity_note'),
        'pressure_drop_note': r.get('pressure_drop_note'),
        'prelaunch': bool(r.get('prelaunch', False)),
    }
    for k in numeric:
        out[k] = r.get(k)
    return out


def list_membranes():
    return [_public_row(r) for r in MEMBRANES]


def get_membrane(record_id):
    record_id = _ID_ALIASES.get(record_id, record_id)
    try:
        row = BY_ID[record_id]
    except KeyError:
        raise ValueError(f'Unknown membrane selection: {record_id}')
    if not row.get('calculation_enabled', True):
        reason = row.get('calculation_disabled_reason') or 'This catalog entry is not calculation-ready.'
        raise ValueError(f"Selected membrane {row.get('manufacturer')} {row.get('model')} is catalog-only: {reason}")
    return row
