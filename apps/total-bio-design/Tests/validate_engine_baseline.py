from pathlib import Path
import hashlib

WEB = Path(__file__).resolve().parents[1] / "Source" / "web"
EXPECTED = {
    "engine.js": "6aa6c39b652b169dfbec527e2b92506d3b06c004e746b2909d0ec47f05502c4a",
    "process_network.js": "3d2af62445902dca151b88aca7770efec1b9d474b29e4892326b2742f1e07b47",
    "compliance_advisor.js": "495372885d43f0ee61d13742f1c5ec0a4cc9c66c64c41c6eefd1e1a4a59f883b",
    "model.json": "153897b2f9261712f48abfcbf310105af4af391c331f142ab5e48a4fe3721d40",
    "unit_catalog.js": "bcbaf4c6194ae82afb58158bbe2b18cacd7a0ab6819eda84cf213b772c139477",
}

for name, expected in EXPECTED.items():
    actual = hashlib.sha256((WEB / name).read_bytes()).hexdigest()
    assert actual == expected, f"{name}: recovered production baseline changed ({actual} != {expected})"

print("Bio engineering/source baseline hashes: PASS")
