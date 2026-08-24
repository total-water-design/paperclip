# Shared WaterStream v0.5 → v0.6 Migration Contract

**From:** `twds.water-stream` version `0.5.0`  
**To:** `twds.water-stream` version `0.6.0`

v0.6 is a deliberate breaking revision made before the WaterStream ↔ Shared Water Chemistry production adapter is implemented. The migration is intentionally explicit; it does not guess chemistry semantics.

## 1. Why the schema changed

Two v0.5 ambiguities prevented a safe production chemistry adapter.

### Aqueous flow circularity

v0.5 exposed `flow_m3_s` only through a valid ChemistryCertificate (`solution_mass_kg_s / density_kg_m3`). Mixing intentionally invalidates the certificate, yet the current Shared Chemistry `WaterState` accepts analytical composition in mg/L. This created a circular first-solve dependency: chemistry was needed to obtain the volume basis required to construct the chemistry input.

v0.6 resolves this by making `aqueous_volume_flow_m3_s` authoritative pure-aqueous hydraulic state, required before chemistry.

### TOTH meaning

v0.5 transported `toth_eq_s` as a general proton-condition/TOTH quantity but did not define it tightly enough to assert that it was the total-alkalinity convention expected by Shared Chemistry.

v0.6 defines `toth_eq_s` explicitly as **total alkalinity equivalents/s on the Shared Water Chemistry TA convention**, positive for positive acid-neutralizing capacity.

## 2. Migration API

Use:

```python
migrate_v05_payload(
    payload,
    aqueous_volume_flow_m3_s=None,
    confirm_toth_is_total_alkalinity=False,
)
```

Do not version-bump a serialized dictionary manually.

## 3. Aqueous volume flow migration

For an AQUEOUS v0.5 payload, v0.6 requires an authoritative aqueous flow.

Preferred path:

- supply `aqueous_volume_flow_m3_s` explicitly from the owning process/hydraulic model.

Compatibility path:

- if the v0.5 payload contains a usable ChemistryCertificate, migration may recover the historical volume as `solution_mass_kg_s / density_kg_m3`.

The certificate is used only as a migration source for the old volume representation. It is not preserved as a v0.6 certificate.

If neither explicit flow nor a usable legacy certificate exists, migration fails closed.

## 4. Nonzero TOTH migration

A nonzero v0.5 `toth_eq_s` is not silently reinterpreted as v0.6 total alkalinity.

Migration requires:

```python
confirm_toth_is_total_alkalinity=True
```

This flag is a source-data assertion by the migration owner. Set it only after confirming that the v0.5 producer's TOTH quantity used the same analytical total-alkalinity reference/sign convention required by Shared Chemistry.

If the source meaning cannot be established, do not migrate the nonzero TOTH value as v0.6 TA. Reconstruct the stream from authoritative source analysis/process state instead.

A zero v0.5 TOTH can migrate without this semantic assertion because no nonzero proton inventory is being reinterpreted.

## 5. ChemistryCertificate behavior

Every v0.5 ChemistryCertificate is invalidated during migration.

Reasons:

- WaterStream schema version changes;
- `state_hash` changes because aqueous flow becomes authoritative/hash-participating;
- TOTH semantics are narrowed;
- v0.6 certificates have v0.6 schema identity.

After migration, Shared Chemistry must issue a new v0.6 certificate for the migrated state if derived chemistry is required.

## 6. Preserved data

Migration preserves, subject to v0.6 validation:

- stream ID;
- temperature;
- pressure;
- authoritative component mol/s totals;
- H2O inventory;
- TOTH numerical value when semantic confirmation rules are satisfied;
- phase and phase inventory;
- chemistry policy;
- tracked quantities/extensions;
- provenance;
- diagnostics plus a migration warning;
- unknown/future top-level fields.

pH remains forbidden as independent transport state.

## 7. Numerical behavior

Migration does not intentionally round values.

- explicit aqueous flow is stored as the supplied Python binary64 value;
- flow recovered from a legacy certificate uses normal binary64 division;
- component and TOTH values remain binary64 transport values;
- canonical serialization remains deterministic.

## 8. Application migration guidance

Existing v0.5 consumers should not be made v0.6-compatible by merely adding a default flow or assuming old TOTH is TA.

For each producer:

1. identify the authoritative process/hydraulic source for aqueous volume flow;
2. confirm the TOTH/alkalinity convention at the source;
3. populate v0.6 through the normal constructor or controlled migration helper;
4. expect the old ChemistryCertificate to be absent;
5. recertify through Shared Chemistry when derived equilibrium data is needed.

## 9. Backward-compatibility statement

v0.6 is **schema-incompatible by design** with a raw v0.5 WaterStream payload. Compatibility is provided by a controlled migration function, not permissive deserialization.

This prevents legacy payloads from appearing valid while silently carrying the wrong hydraulic or alkalinity basis into Shared Chemistry.
