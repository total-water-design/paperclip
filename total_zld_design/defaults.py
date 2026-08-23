"""Workbook-derived default inputs for the v0.1 engineering preview."""

from copy import deepcopy

_THERMAL_DEFAULTS = {
    "feed_flow_m3_h": 250.0,
    "feed_temperature_c": 35.0,
    "feed_tds_mg_l": 120000.0,
    "feed_ph": 7.2,
    "species_mg_l": {
        "Na": 38000.0,
        "Cl": 62000.0,
        "Ca": 2200.0,
        "Mg": 3100.0,
        "SO4": 9800.0,
        "K": 1400.0,
        "HCO3": 180.0,
        "Sr": 25.0,
        "Ba": 0.3,
        "SiO2": 15.0,
    },
    "bc_concentrate_tds_mg_l": 250000.0,
    "vffe_concentrate_tds_mg_l": 280000.0,
    "nacl_saturation_mg_l": 264000.0,
    "target_overall_recovery": 0.95,
    "bc": {
        "compressor_approach_dt_c": 3.0,
        "latent_heat_kj_kg": 2260.0,
        "compressor_isentropic_efficiency": 0.72,
        "seed_to_feed_recirculation_ratio": 12.0,
        "seed_crystal_mass_fraction": 0.02,
        "recirculation_head_m": 30.0,
        "pump_efficiency": 0.75,
    },
    "vffe": {
        "effects": 4,
        "tube_od_m": 0.038,
        "tubes_per_effect": 400,
        "film_thermal_conductivity_w_m_k": 0.60,
        "ncg_fan_configuration": "Series (2 fans)",
        "ncg_flow_m3_h": 500.0,
        "single_fan_static_pressure_kpa": 1.2,
        "fans_in_series": 2,
        "live_steam_temperature_c": 70.0,
        "live_steam_latent_heat_kj_kg": 2085.0,
    },
    "fcc": {
        "magma_density_kg_m3": 300.0,
        "residence_time_h": 3.0,
        "growth_coefficient_m_s": 3.0e-7,
        "growth_exponent": 1.5,
        "nucleation_coefficient": 1.0e10,
        "nucleation_supersaturation_exponent": 2.0,
        "nucleation_magma_exponent": 1.0,
        "evaporation_fraction": 0.35,
    },
    "screening": {
        "caso4_solubility_limit_mg_l_as_caso4": 2100.0,
        "vffe_electric_kw": 150.0,
        "fcc_electric_kw": 120.0,
        "fcc_live_steam_t_h": 2.0,
        "bc_cooling_water_m3_h": 50.0,
        "vffe_cooling_water_m3_h": 80.0,
        "fcc_cooling_water_m3_h": 30.0,
        "bc_capex_usd_per_m3_h_distillate": 180000.0,
        "vffe_capex_usd_per_m3_h_distillate": 140000.0,
        "fcc_capex_usd_per_t_h_salt": 950000.0,
        "bop_fraction": 0.30,
    },
}

_FO_DEFAULTS = {
    "model_basis": "FO workbook saved-case chemistry lookup",
    "water_permeability_lmh_bar": 3.0,
    "salt_permeability_lmh": 0.35,
    "structural_parameter_um": 450.0,
    "draw_diffusivity_m2_s": 1.47e-9,
    "feed_channel_hydraulic_diameter_mm": 0.8,
    "feed_crossflow_velocity_m_s": 0.2,
    "kinematic_viscosity_m2_s": 1.0e-6,
    "sherwood_coefficient": 0.2,
    "sherwood_re_exponent": 0.57,
    "sherwood_sc_exponent": 0.4,
    "membrane_area_m2": 5000.0,
    "feed_flow_m3_h": 100.0,
    "draw_flow_m3_h": 100.0,
    "draw_solute": "NaCl",
    "draw_inlet_molality": 2.0,
    "draw_molar_mass_g_mol": 58.4428,
    "draw_solute_already_in_feed_mol_kg": 0.474837379003438,
    "stages": 10,
    "bisection_refinements": 17,
}


def thermal_defaults():
    return deepcopy(_THERMAL_DEFAULTS)


def fo_defaults():
    return deepcopy(_FO_DEFAULTS)
