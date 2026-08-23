#!/usr/bin/env python3
"""Structural validation for the shared Total Water Design Suite membrane catalog."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from membrane_db import MEMBRANES, META, _identity, get_membrane, grouped_membranes


def fail(message):
    raise SystemExit(f"MEMBRANE CATALOG VALIDATION FAILED: {message}")


def main():
    identities = [_identity(row) for row in MEMBRANES]
    if len(identities) != len(set(identities)):
        fail("duplicate canonical membrane identities remain after loader deduplication")

    stale_names = {"LG Water Solutions", "LG NanoH2O", "LG Chem Water Solutions", "MANN+HUMMEL / TriSep"}
    effective_stale = sorted({row.get("manufacturer") for row in MEMBRANES if row.get("manufacturer") in stale_names})
    if effective_stale:
        fail(f"non-canonical manufacturer names remain: {effective_stale}")

    trisep = [row for row in MEMBRANES if row.get("manufacturer") == "TRISEP"]
    ready = [row for row in trisep if row.get("calculation_enabled", True)]
    if len(ready) < 39:
        fail(f"expected at least 39 calculation-ready TRISEP element records, found {len(ready)}")
    for row in ready:
        for key in ("area_m2", "flow_m3d", "rejection_pct", "pressure_psi", "tds_ppm", "recovery_pct", "specific_flux_A_app_lmh_bar", "salt_permeability_B_lmh"):
            if row.get(key) in (None, ""):
                fail(f"{row['record_id']} missing calculation field {key}")

    # UPR and DS TS40 are intentionally catalog-only because their supplied sheets
    # do not provide a complete nominal permeate-flow transport test point.
    for row in trisep:
        if row.get("model", "").startswith("UPR ") or row.get("model") == "DS TS40 8038-65":
            if row.get("calculation_enabled", True):
                fail(f"{row['record_id']} must remain catalog-only until a complete test point is verified")

    groups = grouped_membranes(suite_app="total-ro-design")
    if "RO" not in groups or "NF" not in groups:
        fail("Total RO Design catalog must expose separate RO and NF groups")

    # Legacy NanoH2O project identifiers must still resolve after canonical rename.
    sample = next((row for row in MEMBRANES if row.get("manufacturer") == "NanoH2O" and row.get("calculation_enabled", True)), None)
    if sample:
        legacy = sample["record_id"].replace("NanoH2O|", "LG Water Solutions|", 1)
        if get_membrane(legacy)["record_id"] != sample["record_id"]:
            fail("legacy LG Water Solutions project ID did not resolve to NanoH2O")

    metadata = META.get("metadata", {})
    print(f"effective={len(MEMBRANES)}")
    print(f"duplicates_removed={metadata.get('duplicates_removed')}")
    print(f"calculation_ready={metadata.get('calculation_ready_count')}")
    print(f"trisep_total={len(trisep)} trisep_ready={len(ready)}")
    print(f"ro={len(groups['RO'])} nf={len(groups['NF'])}")
    print("MEMBRANE CATALOG VALIDATION PASSED")


if __name__ == "__main__":
    main()
