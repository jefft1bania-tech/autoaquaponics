"""Tests for the end-to-end score_design function."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from evaluate import score_design, GROW_OUT_DAYS, FINGERLING_WEIGHT_G, MORTALITY_RATE


class TestScoreDesign:
    def test_baseline_weight_range(self, baseline_params):
        result = score_design(baseline_params)
        # Baseline should produce roughly 280-350g
        assert 200 < result["predicted_weight_g"] < 500

    def test_result_has_expected_keys(self, baseline_params):
        result = score_design(baseline_params)
        expected_keys = {
            "predicted_weight_g",
            "total_harvest_kg",
            "surviving_fish",
            "final_density_kg_m3",
            "effective_temp_c",
            "effective_do_mg_l",
            "biofilter_capacity_g_day",
            "turnovers_per_hour",
            "constraints_pass",
            "constraint_issues",
            "daily_log",
        }
        assert set(result.keys()) == expected_keys

    def test_surviving_fish_count(self, baseline_params):
        result = score_design(baseline_params)
        expected = int(baseline_params["stocking_count"] * (1 - MORTALITY_RATE))
        assert result["surviving_fish"] == expected

    def test_weight_always_increases(self, baseline_params):
        """Fish should gain weight every day under normal conditions."""
        result = score_design(baseline_params, verbose=True)
        log = result["daily_log"]
        assert len(log) > 0
        for i in range(len(log) - 1):
            assert log[i + 1]["weight_g"] > log[i]["weight_g"]

    def test_constraints_propagate(self, baseline_params):
        result = score_design(baseline_params)
        assert result["constraints_pass"] is True
        assert result["constraint_issues"] == []

    def test_failed_constraints_propagate(self, baseline_params):
        baseline_params["bio_barrel_count"] = 0
        result = score_design(baseline_params)
        assert result["constraints_pass"] is False
        assert len(result["constraint_issues"]) > 0

    def test_optimal_temp_produces_more_weight(self, baseline_params):
        """Higher effective temp (within optimal range) should help growth."""
        cold_params = dict(baseline_params, ambient_temp_c=18.0, greenhouse_boost_c=0.0,
                           insulation_boost_c=0.0, dark_tank_boost_c=0.0)
        warm_params = dict(baseline_params, ambient_temp_c=24.0, greenhouse_boost_c=4.0)
        cold_result = score_design(cold_params)
        warm_result = score_design(warm_params)
        assert warm_result["predicted_weight_g"] > cold_result["predicted_weight_g"]

    def test_no_fish(self):
        params = {"stocking_count": 0, "tank_volume_l": 500}
        result = score_design(params)
        assert result["surviving_fish"] == 0

    def test_verbose_log_populated(self, baseline_params):
        result = score_design(baseline_params, verbose=True)
        assert len(result["daily_log"]) > 0
        assert result["daily_log"][0]["day"] == 0

    def test_non_verbose_log_empty(self, baseline_params):
        result = score_design(baseline_params, verbose=False)
        assert result["daily_log"] == []
