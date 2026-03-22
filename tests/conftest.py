"""Shared fixtures for autoaquaponics tests."""

import pytest


@pytest.fixture
def baseline_params():
    """A baseline parameter set representing a reasonable default design."""
    return {
        "ambient_temp_c": 23.0,
        "greenhouse_boost_c": 4.0,
        "insulation_boost_c": 0.0,
        "dark_tank_boost_c": 1.0,
        "air_pump_flow_lpm": 60,
        "tank_volume_l": 500,
        "stocking_count": 28,
        "pump_flow_lpm": 66.5,
        "bio_barrel_count": 3,
        "bio_barrel_volume_l": 208.2,
        "bio_fill_ratio": 0.60,
        "bio_media_surface_m2_per_m3": 500,
        "bio_nitrification_rate": 0.5,
        "structure_length_mm": 7620,
        "structure_width_mm": 3657.6,
        "fish_tank_dia_mm": 1117.6,
        "fish_tank_stand_h_mm": 450,
        "fish_tank_h_mm": 762,
        "bio_stand_h_mm": 170,
        "bio_h_mm": 880,
        "sump_inlet_z_mm": 200,
    }
