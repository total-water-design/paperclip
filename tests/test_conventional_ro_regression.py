"""Release-regression coverage for the authoritative conventional RO engine.

These tests exercise Total RO Design's existing calculation entry points directly.
They are intentionally independent from CCRO/Batch RO specialist engines and do not
assert one historical pressure value; they assert physical/contract invariants so
legitimate model calibration can evolve without silently breaking the RO workflow.
"""
from __future__ import annotations

import copy
import math

import pytest

import calculations


MEMBRANE = "DuPont FilmTec|SW30HRLE-400|A / standard"


def base_case(*, tds=2000.0, temp=25.0, stages=1):
    data = {
        "flow_unit": "m3/h",
        "pressure_unit": "bar",
        "water_mode": "tds",
        "feed_tds": tds,
        "analysis_tds": tds,
        "temperature_c": temp,
        "feed_ph": 7.8,
        "feed_flow": 100.0,
        "stage_count": stages,
        "membrane_coupling": True,
        "solve_basis": "recovery",
        "target_recovery": 35.0 if stages == 1 else 60.0,
        "membrane_pressure_1": 20.0 if tds < 10000 else 65.0,
        "suction_pressure": 2.0,
        "permeate_pressure": 0.0,
        "permeate_pressure_1": 0.0,
        "membrane_1": MEMBRANE,
        "vessels_1": 12,
        "elements_per_vessel_1": 7,
        "fouling_factor": 0.90,
        "salt_passage_factor": 1.0,
        "pump_eff": 0.85,
        "motor_eff": 0.97,
        "vfd_eff": 0.97,
        "pretreatment_discharge_pressure": 6.0,
        "pretreatment_recovery": 0.85,
        "pretreatment_pump_eff": 0.82,
        "pretreatment_motor_eff": 0.95,
        "pretreatment_vfd_eff": 0.97,
    }
    if stages >= 2:
        data.update({
            "membrane_2": MEMBRANE,
            "vessels_2": 6,
            "elements_per_vessel_2": 7,
            "permeate_pressure_2": 0.0,
            "interstage_equipment_2": "none",
            "interstage_boost_2": 0.0,
        })
    if stages >= 3:
        data.update({
            "membrane_3": MEMBRANE,
            "vessels_3": 3,
            "elements_per_vessel_3": 7,
            "permeate_pressure_3": 0.0,
            "interstage_equipment_3": "none",
            "interstage_boost_3": 0.0,
        })
    if stages >= 4:
        data.update({
            "membrane_4": MEMBRANE,
            "vessels_4": 2,
            "elements_per_vessel_4": 7,
            "permeate_pressure_4": 0.0,
            "interstage_equipment_4": "none",
            "interstage_boost_4": 0.0,
        })
    return data


def assert_physical(result, *, expected_stages=None):
    assert isinstance(result, dict)
    qf = float(result["feed_flow"])
    qp = float(result["product_flow"])
    assert math.isfinite(qf) and math.isfinite(qp)
    assert qf > 0 and 0 < qp < qf
    recovery = float(result["recovery"])
    assert 0 < recovery < 1
    assert abs(qp / qf - recovery) < 5e-3
    assert float(result["membrane_pressure_1"]) > float(result.get("permeate_pressure_1", 0.0) or 0.0)
    assert float(result["ro_sec"]) > 0
    assert float(result["total_sec"]) >= float(result["ro_sec"])
    if expected_stages is not None:
        assert int(result.get("stage_count", expected_stages)) == expected_stages
        for i in range(1, expected_stages + 1):
            assert float(result[f"stage{i}_permeate_flow"]) >= 0
            assert float(result[f"stage{i}_feed_tds_ppm"]) >= 0


def test_single_stage_brackish_recovery_solve():
    result = calculations.multistage(base_case(tds=2000, stages=1))
    assert_physical(result, expected_stages=1)
    assert abs(result["recovery"] - 0.35) < 5e-3


def test_single_stage_seawater_recovery_solve():
    case = base_case(tds=35000, stages=1)
    case["target_recovery"] = 40.0
    result = calculations.multistage(case)
    assert_physical(result, expected_stages=1)
    assert abs(result["recovery"] - 0.40) < 5e-3


def test_membrane_elements_converge_on_true_residuals():
    stage = calculations.membrane_stage(
        100.0, 65.0, MEMBRANE, 12, 7, 35000.0
    )

    for element in stage["element_results"]:
        flow_tolerance = max(
            calculations.ELEMENT_FLOW_ABS_TOL_M3H,
            calculations.ELEMENT_FLOW_REL_TOL * max(1.0, element["feed_flow_m3h"]),
        )
        tds_tolerance = (
            calculations.ELEMENT_TDS_REL_TOL
            * max(1.0, element["feed_tds_ppm"])
        )
        assert abs(element["convergence_flow_residual_m3h"]) < flow_tolerance
        assert abs(element["convergence_tds_residual_mg_l"]) < tds_tolerance


def test_damped_element_does_not_treat_relaxation_as_convergence_proof():
    stage = calculations.membrane_stage(
        1.0, 60.0, MEMBRANE, 1, 1, 60000.0
    )
    element = stage["element_results"][0]

    assert element["convergence_relaxation_history"] == [0.45, 0.225, 0.12]
    assert element["convergence_iterations"] > 90
    assert abs(element["convergence_flow_residual_m3h"]) < calculations.ELEMENT_FLOW_ABS_TOL_M3H
    assert abs(element["convergence_tds_residual_mg_l"]) < (
        calculations.ELEMENT_TDS_REL_TOL * element["feed_tds_ppm"]
    )


def test_two_stage_conventional_ro():
    result = calculations.multistage(base_case(tds=3000, stages=2))
    assert_physical(result, expected_stages=2)
    assert result["stage2_feed_tds_ppm"] >= result["stage1_feed_tds_ppm"]


@pytest.mark.parametrize("stages", [3, 4])
def test_three_and_four_stage_conventional_ro(stages):
    case = base_case(tds=2500, stages=stages)
    case["target_recovery"] = 70.0
    result = calculations.multistage(case)
    assert_physical(result, expected_stages=stages)


def test_tridirectional_pressure_product_recovery_paths():
    pressure = base_case(tds=2000, stages=1)
    pressure.update({"solve_basis": "pressure", "membrane_pressure_1": 18.0})
    r_pressure = calculations.multistage(pressure)
    assert_physical(r_pressure, expected_stages=1)
    assert r_pressure["solve_basis"] == "pressure"

    product = copy.deepcopy(pressure)
    product.update({"solve_basis": "product", "target_product_flow": float(r_pressure["product_flow"])})
    r_product = calculations.multistage(product)
    assert_physical(r_product, expected_stages=1)
    assert r_product["solve_basis"] == "product"
    assert abs(float(r_product["product_flow"]) - float(r_pressure["product_flow"])) < 0.1

    recovery = copy.deepcopy(pressure)
    recovery.update({"solve_basis": "recovery", "target_recovery": 100.0 * float(r_pressure["recovery"])})
    r_recovery = calculations.multistage(recovery)
    assert_physical(r_recovery, expected_stages=1)
    assert r_recovery["solve_basis"] == "recovery"
    assert abs(float(r_recovery["recovery"]) - float(r_pressure["recovery"])) < 5e-3


def test_full_ion_chemistry_case():
    case = base_case(tds=5000, stages=1)
    case.update({
        "water_mode": "full",
        "ion_sodium": 1350,
        "ion_calcium": 120,
        "ion_magnesium": 80,
        "ion_potassium": 20,
        "ion_chloride": 2050,
        "ion_sulfate": 900,
        "ion_bicarbonate": 250,
        "ion_nitrate": 20,
        "ion_boron": 2,
        "ion_silica": 40,
        "ion_ammonium": 0,
        "ion_strontium": 0,
        "ion_barium": 0,
        "ion_fluoride": 1,
        "ion_bromide": 0,
        "ion_phosphate": 0,
    })
    result = calculations.multistage(case)
    assert_physical(result, expected_stages=1)
    assert result.get("stage1_permeate_composition_mg_l")
    assert result.get("stage1_concentrate_composition_mg_l")


def test_hybrid_membrane_recipe_case():
    case = base_case(tds=2000, stages=1)
    case["membrane_recipe_1"] = [MEMBRANE] * 7
    case["membrane_design_mode_1"] = "hybrid"
    result = calculations.multistage(case)
    assert_physical(result, expected_stages=1)
    assert len(result.get("stage1_membrane_recipe") or []) == 7


@pytest.mark.parametrize("temp", [10.0, 40.0])
def test_temperature_envelope_conventional_ro(temp):
    result = calculations.multistage(base_case(tds=3000, temp=temp, stages=1))
    assert_physical(result, expected_stages=1)
