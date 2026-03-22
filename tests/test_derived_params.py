"""Tests for derived parameter calculations in evaluate.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from evaluate import (
    compute_effective_temp,
    compute_do,
    compute_biofilter_capacity,
    compute_turnovers,
)


class TestComputeEffectiveTemp:
    def test_baseline(self, baseline_params):
        temp = compute_effective_temp(baseline_params)
        # 23 + 4 + 0 + 1 = 28
        assert temp == 28.0

    def test_defaults_without_params(self):
        temp = compute_effective_temp({})
        # defaults: 23 + 4 + 0 + 1 = 28
        assert temp == 28.0

    def test_insulation_adds(self):
        params = {"insulation_boost_c": 3.0}
        temp = compute_effective_temp(params)
        assert temp == 23.0 + 4.0 + 3.0 + 1.0

    def test_custom_ambient(self):
        params = {"ambient_temp_c": 30.0}
        temp = compute_effective_temp(params)
        assert temp == 30.0 + 4.0 + 0.0 + 1.0


class TestComputeDo:
    def test_baseline_reasonable(self, baseline_params):
        do = compute_do(baseline_params)
        # Should be in a physiologically plausible range
        assert 1.0 <= do <= 7.5

    def test_high_aeration_near_saturation(self):
        params = {
            "air_pump_flow_lpm": 200,
            "tank_volume_l": 500,
            "stocking_count": 5,
        }
        do = compute_do(params)
        assert do >= 5.0

    def test_low_aeration_drops_do(self):
        params = {
            "air_pump_flow_lpm": 5,
            "tank_volume_l": 1000,
            "stocking_count": 50,
        }
        do = compute_do(params)
        assert do < 5.0

    def test_never_exceeds_saturation(self):
        params = {
            "air_pump_flow_lpm": 1000,
            "tank_volume_l": 100,
            "stocking_count": 1,
        }
        do = compute_do(params)
        assert do <= 7.5

    def test_never_below_minimum(self):
        params = {
            "air_pump_flow_lpm": 1,
            "tank_volume_l": 10000,
            "stocking_count": 200,
        }
        do = compute_do(params)
        assert do >= 1.0


class TestComputeBiofilterCapacity:
    def test_baseline(self, baseline_params):
        cap = compute_biofilter_capacity(baseline_params)
        # 3 barrels * 208.2L * 0.6 fill / 1000 * 500 m2/m3 * 0.5 g/m2/day
        expected = 3 * 208.2 * 0.60 / 1000 * 500 * 0.5
        assert abs(cap - expected) < 0.01

    def test_zero_barrels(self):
        params = {"bio_barrel_count": 0}
        assert compute_biofilter_capacity(params) == 0.0

    def test_scales_with_barrel_count(self):
        p1 = {"bio_barrel_count": 1}
        p2 = {"bio_barrel_count": 3}
        assert abs(compute_biofilter_capacity(p2) - 3 * compute_biofilter_capacity(p1)) < 0.01


class TestComputeTurnovers:
    def test_baseline(self, baseline_params):
        t = compute_turnovers(baseline_params)
        expected = (66.5 * 60) / 500
        assert abs(t - expected) < 0.01

    def test_defaults(self):
        t = compute_turnovers({})
        expected = (66.5 * 60) / 500
        assert abs(t - expected) < 0.01

    def test_high_flow_small_tank(self):
        t = compute_turnovers({"pump_flow_lpm": 200, "tank_volume_l": 100})
        assert t == (200 * 60) / 100
