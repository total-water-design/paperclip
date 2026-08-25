from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'Source'/'web'
html=(WEB/'index.html').read_text(encoding='utf-8')
ui=(WEB/'mbr_equipment_ui.js').read_text(encoding='utf-8')
calc=(WEB/'mbr_equipment_sizing.js').read_text(encoding='utf-8')
css=(WEB/'mbr_equipment_sizing.css').read_text(encoding='utf-8')
combined='\n'.join((html,ui,calc,css))

for asset in ('mbr_equipment_sizing.css','mbr_equipment_sizing.js','mbr_equipment_ui.js'):
    assert asset in html, asset
for token in (
    'MBR Equipment & Mechanical Design','Equipment & Mechanical Design',
    'Installed membrane area','Normal net flux','Biological air','Membrane air',
    'Warnings & constraints','Fine-screen planning range','Backwash tank working volume',
    'Internal recycle','Maintenance clean solution','Recovery clean solution'
):
    assert token in combined, token
for source_guard in (
    'Historical literature planning basis',
    'verify current membrane supplier limits',
    'not a vendor guarantee',
    'current project/vendor data before design release'
):
    assert source_guard.lower() in combined.lower(), source_guard
assert 'Simon Judd' in combined
assert 'The MBR Book' in combined
assert "screenHF:[0.8,1.5]" in calc
assert "screenFS:[2,3]" in calc
assert "typicalMunicipalNetFluxLMH:25" in calc
assert "alphaMlssExponent:0.083" in calc
assert "theta:1.024" in calc
assert "fineBubbleCleanOtePerM:0.05" in calc
assert '1.42*sludgeVssKgD' in calc
assert '4.33*nitrifiedNkgD' in calc
assert '2.83*denitrifiedNkgD' in calc
assert 'N+1 train during peak/cleaning' in calc
assert "getActiveUnit(){" in (WEB/'app.js').read_text(encoding='utf-8')
assert 'mbrEquipmentInline' in ui
assert 'mbrEquipmentUnitBtn' in ui
assert "['mbr','anmbr']" in ui
assert "#nav button.active,#nav .nav-item.active" in ui
assert 'Membrane Bioreactor' in ui
assert "document.querySelector('.bio-workspace-nav')" not in ui
# The inline implementation may defensively remove a stale legacy dialog node,
# but it must not create or display a modal equipment workspace.
assert "document.createElement('dialog')" not in ui
assert 'showModal' not in ui
assert 'mbr-equipment-inline' in css
assert 'mbr-equipment-dialog' not in css
assert 'mbr-eq-input-details' in css
assert '@media(max-width:560px)' in css
print('Total Bio Design MBR equipment UI/source contract validation: PASS')
