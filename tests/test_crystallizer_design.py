import pytest

from total_zld_design.crystallizer_design import (
    CrystallizerSelectionInput,
    ideal_msmpr_residence_time_h,
    recommend_crystallizer_types,
    size_ideal_msmpr,
)


def test_l43_target_sets_residence_time_from_growth_rate():
    tau = ideal_msmpr_residence_time_h(0.80, 0.10, "L43")
    assert tau == pytest.approx(2.0)


def test_working_volume_follows_tau_equals_v_over_q():
    result = size_ideal_msmpr(
        slurry_throughput_m3_h=50.0,
        target_mean_size_mm=0.80,
        growth_rate_mm_h=0.10,
        suspension_density_kg_m3=120.0,
        mean_size_basis="L43",
        volume_margin_fraction=0.20,
    )
    assert result.residence_time_h == pytest.approx(2.0)
    assert result.working_volume_m3 == pytest.approx(100.0)
    assert result.design_volume_m3 == pytest.approx(120.0)
    assert result.crystal_inventory_kg == pytest.approx(12000.0)
    assert result.nominal_solids_withdrawal_kg_h == pytest.approx(6000.0)


def test_l10_l21_l32_l43_relations_are_consistent():
    sizes = {
        basis: ideal_msmpr_residence_time_h(target, 0.2, basis)
        for basis, target in (("L10", 0.2), ("L21", 0.4), ("L32", 0.6), ("L43", 0.8))
    }
    assert len(set(round(v, 12) for v in sizes.values())) == 1


def test_high_scaling_zld_evaporation_prefers_forced_circulation_screen():
    ranking = recommend_crystallizer_types(CrystallizerSelectionInput(
        evaporation_required=True,
        scaling_fouling_risk="high",
        viscosity_risk="high",
        solids_loading_risk="high",
        large_crystal_priority="low",
        narrow_csd_priority="low",
        fines_control_priority="low",
    ))
    assert ranking[0].crystallizer_type == "Forced-circulation evaporative crystallizer"


def test_large_crystal_narrow_csd_case_rewards_classified_growth_options():
    ranking = recommend_crystallizer_types(CrystallizerSelectionInput(
        evaporation_required=False,
        scaling_fouling_risk="low",
        viscosity_risk="low",
        solids_loading_risk="medium",
        large_crystal_priority="high",
        narrow_csd_priority="high",
        fines_control_priority="high",
    ))
    assert ranking[0].crystallizer_type in {
        "Oslo / classified growth crystallizer",
        "Draft-tube-baffle (DTB) crystallizer",
    }


def test_selection_returns_ranked_advisory_list():
    ranking = recommend_crystallizer_types(CrystallizerSelectionInput())
    assert [r.rank for r in ranking] == [1, 2, 3, 4]
    assert all(r.strengths and r.cautions for r in ranking)
