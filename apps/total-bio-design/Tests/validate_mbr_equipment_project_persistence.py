from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/'Source'/'web'/'app.js').read_text(encoding='utf-8')

for token in (
    'let mbrEquipmentConfig={};',
    'mbrEquipmentConfig:{...mbrEquipmentConfig}',
    'getMbrEquipmentConfig()',
    'setMbrEquipmentConfig(next)',
    'p.mbrEquipmentConfig',
    'saved.mbrEquipmentConfig'
):
    assert token in APP, token
print('Total Bio Design MBR equipment project persistence contract: PASS')
