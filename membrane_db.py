import copy
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "swro_membranes.json"
EXTENSION_DIR = ROOT / "data" / "membranes"
SPEC_ARCHIVE_DIR = ROOT / "static" / "membrane_specs"

GPD_TO_M3D = 0.003785411784
FT2_TO_M2 = 0.09290304

_MANUFACTURER_ALIASES = {
    "lg water solutions": "NanoH2O",
    "lg nanoh2o": "NanoH2O",
    "lg chem water solutions": "NanoH2O",
    "nanoh2o": "NanoH2O",
    "mann+hummel / trisep": "TRISEP",
    "mann+hummel / trisep®": "TRISEP",
    "trisep": "TRISEP",
    "trisep®": "TRISEP",
}


def canonical_manufacturer(name):
    raw = str(name or "").strip()
    return _MANUFACTURER_ALIASES.get(raw.casefold(), raw)


def _record_id(manufacturer, model, variant):
    return f"{manufacturer}|{model}|{variant or 'A / standard'}"


def _normal_text(value):
    s = unicodedata.normalize("NFKC", str(value or ""))
    s = s.replace("®", "").replace("™", "")
    return re.sub(r"\s+", " ", s).strip().casefold()


def _identity(row):
    return (
        _normal_text(canonical_manufacturer(row.get("manufacturer"))),
        _normal_text(row.get("model")),
        _normal_text(row.get("test_variant", "A / standard")),
        _normal_text(row.get("membrane_type", "RO")),
    )


def _derive_common_fields(row):
    out = copy.deepcopy(row)
    if out.get("area_ft2") is not None and out.get("area_m2") is None:
        out["area_m2"] = round(float(out["area_ft2"]) * FT2_TO_M2, 6)
    if out.get("flow_gpd") is not None and out.get("flow_m3d") is None:
        out["flow_m3d"] = round(float(out["flow_gpd"]) * GPD_TO_M3D, 6)
    if out.get("flow_m3d") is not None and out.get("area_m2") not in (None, 0):
        flux = float(out["flow_m3d"]) * 1000.0 / 24.0 / float(out["area_m2"])
        out.setdefault("test_flux_lmh", round(flux, 6))
        out.setdefault("test_flux_gfd", round(flux * 0.589024, 6))
    if out.get("rejection_pct") is not None:
        out.setdefault("salt_passage_pct", round(100.0 - float(out["rejection_pct"]), 6))
        if out.get("tds_ppm") is not None:
            out.setdefault(
                "permeate_tds_est_ppm",
                round(float(out["tds_ppm"]) * (1.0 - float(out["rejection_pct"]) / 100.0), 6),
            )
    if not out.get("suite_apps"):
        membrane_type = str(out.get("membrane_type", "RO")).upper()
        if membrane_type in {"RO", "NF"}:
            out["suite_apps"] = ["total-ro-design"]
        elif membrane_type in {"UF", "MF"}:
            out["suite_apps"] = ["total-pretreatment-design"]
        elif membrane_type == "MBR":
            out["suite_apps"] = ["total-bio-design"]
        else:
            out["suite_apps"] = []
    return out


def _load_extension_rows():
    rows = []
    if not EXTENSION_DIR.exists():
        return rows
    for path in sorted(EXTENSION_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        defaults = payload.get("defaults") or {}
        profiles = payload.get("profiles") or {}
        for raw in payload.get("membranes") or []:
            profile_name = raw.get("profile")
            profile = profiles.get(profile_name, {}) if profile_name else {}
            row = {}
            row.update(defaults)
            row.update(profile)
            row.update({k: v for k, v in raw.items() if k != "profile"})
            row["_catalog_source_file"] = str(path.relative_to(ROOT))
            rows.append(_derive_common_fields(row))
    return rows


def _quality_score(row):
    verification = str(row.get("verification_status", "")).casefold()
    catalog = str(row.get("catalog_status", "")).casefold()
    complete = sum(
        row.get(k) not in (None, "")
        for k in ("area_ft2", "flow_gpd", "rejection_pct", "pressure_psi", "tds_ppm", "recovery_pct")
    )
    return (
        int(row.get("source_priority") or 0),
        50 if row.get("calculation_enabled", True) else 0,
        30 if "official" in verification else 20 if "verified" in verification else 0,
        15 if "current" in catalog else -10 if "legacy" in catalog else 0,
        complete,
        1 if row.get("spec_document_id") else 0,
    )


def _load():
    base = json.loads(DB_PATH.read_text(encoding="utf-8"))
    base_rows = [_derive_common_fields(r) for r in base.get("membranes", [])]
    extension_rows = _load_extension_rows()
    candidates = base_rows + extension_rows

    selected = {}
    source_ids = {}
    duplicate_audit = []

    for original in candidates:
        row = copy.deepcopy(original)
        source_manufacturer = str(row.get("manufacturer") or "").strip()
        variant = row.get("test_variant", "A / standard")
        old_id = _record_id(source_manufacturer, row.get("model"), variant)

        row["manufacturer"] = canonical_manufacturer(source_manufacturer)
        row["manufacturer_alias"] = source_manufacturer if source_manufacturer != row["manufacturer"] else None
        row["record_id"] = _record_id(row["manufacturer"], row.get("model"), variant)
        key = _identity(row)

        existing = selected.get(key)
        if existing is None or _quality_score(row) > _quality_score(existing):
            if existing is not None:
                duplicate_audit.append({
                    "identity": key,
                    "kept_source": row.get("_catalog_source_file") or row.get("source"),
                    "discarded_record_id": existing.get("record_id"),
                    "reason": "higher verification/source quality score",
                })
            selected[key] = row
        else:
            duplicate_audit.append({
                "identity": key,
                "kept_source": existing.get("_catalog_source_file") or existing.get("source"),
                "discarded_record_id": row.get("record_id"),
                "reason": "lower verification/source quality score",
            })
        source_ids.setdefault(key, set()).update({old_id, row["record_id"]})

    rows = sorted(
        selected.values(),
        key=lambda r: (
            str(r.get("membrane_type", "RO")),
            str(r.get("manufacturer", "")),
            str(r.get("family", "")),
            str(r.get("model", "")),
            str(r.get("test_variant", "")),
        ),
    )
    by_id = {r["record_id"]: r for r in rows}
    aliases = {}
    for key, ids in source_ids.items():
        winner = selected[key]["record_id"]
        for rid in ids:
            if rid != winner:
                aliases[rid] = winner

    # Preserve every legacy LG manufacturer prefix already used by historical
    # Total RO Design project files while presenting the current NanoH2O name.
    for row in rows:
        if row.get("manufacturer") != "NanoH2O":
            continue
        variant = row.get("test_variant", "A / standard")
        for legacy_name in ("LG Water Solutions", "LG NanoH2O", "LG Chem Water Solutions"):
            aliases[_record_id(legacy_name, row.get("model"), variant)] = row["record_id"]

    metadata = dict(base.get("metadata") or {})
    metadata.update({
        "architecture": "Total Water Design Suite shared membrane catalog",
        "base_catalog_count": len(base_rows),
        "extension_catalog_count": len(extension_rows),
        "effective_catalog_count": len(rows),
        "duplicates_removed": len(candidates) - len(rows),
        "calculation_ready_count": sum(bool(r.get("calculation_enabled", True)) for r in rows),
        "manufacturer_canonicalization": {
            "LG Water Solutions": "NanoH2O",
            "LG NanoH2O": "NanoH2O",
            "LG Chem Water Solutions": "NanoH2O",
            "MANN+HUMMEL / TriSep": "TRISEP",
        },
        "technology_groups": sorted({str(r.get("membrane_type", "RO")).upper() for r in rows}),
    })
    meta = dict(base)
    meta["metadata"] = metadata
    meta["membranes"] = rows
    return meta, rows, by_id, aliases, duplicate_audit


META, MEMBRANES, BY_ID, _ID_ALIASES, DUPLICATE_AUDIT = _load()


def _spec_archive_path(row):
    document_id = row.get("spec_document_id")
    if not document_id:
        return None
    rel = Path("membrane_specs") / str(document_id) / "current.pdf"
    if (ROOT / "static" / rel).exists():
        return f"/static/{rel.as_posix()}"
    return None


def _public_row(r):
    numeric = (
        "area_m2", "area_ft2", "flow_m3d", "flow_gpd", "rejection_pct", "min_rejection_pct",
        "boron_rejection_pct", "pressure_psi", "tds_ppm", "recovery_pct",
        "specific_flux_A_app_lmh_bar", "water_permeability_A_lmh_bar",
        "salt_permeability_B_lmh", "test_flux_lmh", "test_flux_gfd", "salt_passage_pct",
        "max_operating_pressure_bar", "max_operating_temperature_c", "diameter_in", "spacer_mil",
        "nf_b_mono_mono_lmh", "nf_b_mixed_lmh", "nf_b_divalent_divalent_lmh",
        "max_dp_per_element_bar", "max_dp_per_vessel_bar", "max_sdi15", "max_turbidity_ntu",
        "typical_nacl_rejection_pct", "permeate_tds_est_ppm",
    )
    out = {
        "record_id": r["record_id"],
        "manufacturer": r["manufacturer"],
        "manufacturer_alias": r.get("manufacturer_alias"),
        "brand_owner": r.get("brand_owner"),
        "model": r["model"],
        "part_number": r.get("part_number"),
        "family": r.get("family"),
        "application": r.get("application"),
        "application_tags": r.get("application_tags") or [],
        "suite_apps": r.get("suite_apps") or [],
        "membrane_type": str(r.get("membrane_type", "RO")).upper(),
        "membrane_chemistry": r.get("membrane_chemistry"),
        "test_variant": r.get("test_variant"),
        "source": r.get("source"),
        "spec_document_id": r.get("spec_document_id"),
        "spec_uploaded_sha256": r.get("spec_uploaded_sha256"),
        "spec_archive_url": _spec_archive_path(r),
        "catalog_status": r.get("catalog_status"),
        "verification_status": r.get("verification_status"),
        "calculation_enabled": bool(r.get("calculation_enabled", True)),
        "design_selectable": bool(r.get("design_selectable", True)),
        "calculation_disabled_reason": r.get("calculation_disabled_reason"),
        "feed_spacer_text": r.get("feed_spacer_text"),
        "test_solute": r.get("test_solute"),
        "data_basis": r.get("data_basis"),
        "nf_transport_model": r.get("nf_transport_model"),
        "nf_rejection_benchmarks": r.get("nf_rejection_benchmarks"),
        "nf_selectivity_note": r.get("nf_selectivity_note"),
        "pressure_drop_note": r.get("pressure_drop_note"),
        "cleaning_ph_range": r.get("cleaning_ph_range"),
        "chlorine_tolerance": r.get("chlorine_tolerance"),
        "outer_wrap": r.get("outer_wrap"),
        "prelaunch": bool(r.get("prelaunch", False)),
    }
    for k in numeric:
        out[k] = r.get(k)
    return out


def _matches(row, membrane_type=None, suite_app=None, application=None, manufacturer=None, calculation_ready=None):
    if membrane_type and str(row.get("membrane_type", "RO")).upper() != str(membrane_type).upper():
        return False
    if suite_app and str(suite_app) not in (row.get("suite_apps") or []):
        return False
    if manufacturer and _normal_text(row.get("manufacturer")) != _normal_text(canonical_manufacturer(manufacturer)):
        return False
    if calculation_ready is not None and bool(row.get("calculation_enabled", True)) != bool(calculation_ready):
        return False
    if application:
        needle = _normal_text(application)
        haystack = " ".join([str(row.get("application") or "")] + [str(x) for x in row.get("application_tags") or []])
        if needle not in _normal_text(haystack):
            return False
    return True


def list_membranes(membrane_type=None, suite_app=None, application=None, manufacturer=None, calculation_ready=None):
    return [
        _public_row(r)
        for r in MEMBRANES
        if _matches(r, membrane_type, suite_app, application, manufacturer, calculation_ready)
    ]


def grouped_membranes(**filters):
    grouped = {}
    for row in list_membranes(**filters):
        grouped.setdefault(row["membrane_type"], []).append(row)
    return grouped


def catalog_audit():
    return {
        "metadata": META.get("metadata", {}),
        "duplicates": copy.deepcopy(DUPLICATE_AUDIT),
        "aliases": dict(_ID_ALIASES),
    }


def get_membrane(record_id):
    record_id = _ID_ALIASES.get(record_id, record_id)
    try:
        row = BY_ID[record_id]
    except KeyError:
        raise ValueError(f"Unknown membrane selection: {record_id}")
    if not row.get("calculation_enabled", True):
        reason = row.get("calculation_disabled_reason") or "This catalog entry is not calculation-ready."
        raise ValueError(
            f"Selected membrane {row.get('manufacturer')} {row.get('model')} is catalog-only: {reason}"
        )
    return row
