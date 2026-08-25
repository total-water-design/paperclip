from __future__ import annotations

import pytest

import shared_waterstream as sw

PINNED_SHARED_WATERSTREAM_COMMIT = "e43bd4e1f86f657528e83dc9e185970443d30f4b"
EXPECTED_SCHEMA_VERSION = "0.6.0"
MW = sw.H2O_MOLAR_MASS_G_MOL


def aqueous(
    stream_id: str,
    *,
    flow_m3_s: float = 1.0,
    water_kg_s: float = 1000.0,
    sodium_mol_s: float = 1.0,
    chloride_mol_s: float = 1.0,
    tic_mol_s: float = 0.0,
    toth_eq_s: float = 0.0,
    temperature_c: float = 25.0,
    pressure_bar: float = 2.0,
) -> sw.WaterStream:
    components = {
        "h2o": water_kg_s * 1000.0 / MW,
        "sodium": sodium_mol_s,
        "chloride": chloride_mol_s,
    }
    if tic_mol_s:
        components["total_inorganic_carbon"] = tic_mol_s
    return sw.WaterStream(
        stream_id,
        temperature_c,
        pressure_bar,
        sw.FrozenDict(components),
        toth_eq_s,
        aqueous_volume_flow_m3_s=flow_m3_s,
    )


def test_package_root_is_pinned_shared_waterstream_v06_contract():
    assert sw.SCHEMA_VERSION == EXPECTED_SCHEMA_VERSION


def test_water_balance_mixer_conserves_authoritative_extensives_and_ledger():
    a = aqueous(
        "A",
        flow_m3_s=0.4,
        water_kg_s=400.0,
        sodium_mol_s=0.4,
        chloride_mol_s=0.4,
        tic_mol_s=0.04,
        toth_eq_s=0.004,
        temperature_c=20.0,
    )
    b = aqueous(
        "B",
        flow_m3_s=0.6,
        water_kg_s=600.0,
        sodium_mol_s=0.6,
        chloride_mol_s=0.6,
        tic_mol_s=0.06,
        toth_eq_s=0.006,
        temperature_c=30.0,
    )

    mixed = sw.mix_water_streams([a, b], stream_id="MIX")
    ledger = sw.MassLedger.from_streams("wb-mix", "water-balance-mixer", [a, b], [mixed])
    ledger.assert_closed()

    assert mixed.flow_m3_s == pytest.approx(1.0)
    assert mixed.solvent_water_kg_s_from_components == pytest.approx(1000.0)
    assert mixed.component_totals_mol_s["sodium"] == pytest.approx(1.0)
    assert mixed.component_totals_mol_s["chloride"] == pytest.approx(1.0)
    assert mixed.component_totals_mol_s["total_inorganic_carbon"] == pytest.approx(0.10)
    assert mixed.toth_eq_s == pytest.approx(0.010)
    assert mixed.temperature_c == pytest.approx(26.0)


def test_water_balance_split_conserves_flow_components_toth_and_ledger():
    parent = aqueous(
        "PARENT",
        flow_m3_s=1.0,
        water_kg_s=1000.0,
        sodium_mol_s=2.0,
        chloride_mol_s=2.0,
        tic_mol_s=0.2,
        toth_eq_s=0.02,
    )
    daughters = sw.split_water_stream(
        parent,
        {"product": 0.73, "recycle": 0.27},
        composition_preserving=True,
    )
    rows = list(daughters.values())
    sw.MassLedger.from_streams("wb-split", "water-balance-splitter", [parent], rows).assert_closed()

    assert sum(s.flow_m3_s for s in rows) == pytest.approx(parent.flow_m3_s)
    assert sum(s.solvent_water_kg_s_from_components for s in rows) == pytest.approx(
        parent.solvent_water_kg_s_from_components
    )
    assert sum(s.component_totals_mol_s["sodium"] for s in rows) == pytest.approx(
        parent.component_totals_mol_s["sodium"]
    )
    assert sum(s.component_totals_mol_s["total_inorganic_carbon"] for s in rows) == pytest.approx(
        parent.component_totals_mol_s["total_inorganic_carbon"]
    )
    assert sum(s.toth_eq_s for s in rows) == pytest.approx(parent.toth_eq_s)


def test_selective_split_with_nonzero_toth_fails_closed_for_owner_physics():
    parent = aqueous(
        "SELECTIVE",
        flow_m3_s=1.0,
        water_kg_s=1000.0,
        sodium_mol_s=1.0,
        chloride_mol_s=1.0,
        tic_mol_s=1.0,
        toth_eq_s=1.0,
    )
    fractions = {
        "light": {
            "h2o": 0.9,
            "sodium": 0.5,
            "chloride": 0.5,
            "total_inorganic_carbon": 0.1,
        },
        "heavy": {
            "h2o": 0.1,
            "sodium": 0.5,
            "chloride": 0.5,
            "total_inorganic_carbon": 0.9,
        },
    }

    with pytest.raises(sw.SelectiveSplitError):
        sw.split_water_stream(parent, fractions, composition_preserving=False)


def test_solid_flow_is_not_fabricated_as_volumetric_flow():
    components = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
    solid = sw.WaterStream(
        "SOLID",
        60.0,
        1.2,
        sw.FrozenDict(components),
        0.0,
        sw.StreamPhase.SOLID,
        (
            sw.PhaseInventoryItem(
                sw.StreamPhase.SOLID,
                "calcite",
                sw.FrozenDict(components),
            ),
        ),
    )

    with pytest.raises(sw.NonVolumetricFlowError):
        _ = solid.flow_m3_s


def test_mixed_phase_temperature_requires_owner_thermal_input():
    liquid = aqueous("LIQUID")
    components = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
    solid = sw.WaterStream(
        "SOLID",
        90.0,
        2.0,
        sw.FrozenDict(components),
        0.0,
        sw.StreamPhase.SOLID,
        (
            sw.PhaseInventoryItem(
                sw.StreamPhase.SOLID,
                "calcite",
                sw.FrozenDict(components),
            ),
        ),
    )

    with pytest.raises(sw.MixedPhaseThermalError):
        sw.mix_water_streams([liquid, solid], stream_id="INVALID-MIX")
