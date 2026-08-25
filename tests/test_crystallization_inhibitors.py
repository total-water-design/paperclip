import pytest

from total_zld_design.crystallization_inhibitors import (
    InhibitorDescriptor,
    antiscalant_family_guidance,
    evaluate_inhibitor_effect,
    langmuir_surface_coverage,
)


def test_zero_concentration_is_neutral():
    effect = evaluate_inhibitor_effect(InhibitorDescriptor("phosphonate", 0.0, 0.1, 4.0, 3.0, 2.0, 1.0, 1.0))
    assert effect.surface_coverage_fraction == 0.0
    assert effect.growth_rate_multiplier == 1.0
    assert effect.nucleation_rate_multiplier == 1.0
    assert effect.metastable_zone_multiplier == 1.0
    assert effect.induction_time_multiplier == 1.0


def test_langmuir_coverage_is_bounded_and_increases_with_concentration():
    low = langmuir_surface_coverage(1.0, 0.1)
    high = langmuir_surface_coverage(10.0, 0.1)
    assert 0.0 < low < high < 1.0


def test_adsorbing_inhibitor_suppresses_growth_and_nucleation():
    effect = evaluate_inhibitor_effect(InhibitorDescriptor(
        "polycarboxylate", 5.0, adsorption_constant_l_mg=0.2,
        growth_blocking_strength=2.0, nucleation_blocking_strength=1.5,
        metastable_zone_strength=0.4,
    ))
    assert effect.growth_rate_multiplier < 1.0
    assert effect.nucleation_rate_multiplier < 1.0
    assert effect.induction_time_multiplier > 1.0
    assert effect.metastable_zone_multiplier > 1.0


def test_stronger_growth_blocking_reduces_growth_multiplier():
    weak = evaluate_inhibitor_effect(InhibitorDescriptor("x", 4.0, 0.2, growth_blocking_strength=0.5))
    strong = evaluate_inhibitor_effect(InhibitorDescriptor("x", 4.0, 0.2, growth_blocking_strength=3.0))
    assert strong.growth_rate_multiplier < weak.growth_rate_multiplier


def test_family_guidance_does_not_claim_universal_coefficients():
    guidance = antiscalant_family_guidance()
    assert "phosphonate" in guidance
    assert "polycarboxylate" in guidance
    assert "coefficients" not in guidance["phosphonate"]
    assert "pilot calibration" in guidance["proprietary_blend"]["zld_note"]
