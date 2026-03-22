"""Tests for constraint validation in evaluate.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from evaluate import validate_constraints


class TestValidateConstraints:
    def test_baseline_passes(self, baseline_params):
        passes, issues = validate_constraints(baseline_params)
        assert passes is True
        assert issues == []

    def test_oversized_length(self, baseline_params):
        baseline_params["structure_length_mm"] = 8000
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("length" in i.lower() for i in issues)

    def test_oversized_width(self, baseline_params):
        baseline_params["structure_width_mm"] = 4000
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("width" in i.lower() for i in issues)

    def test_tank_too_large_for_structure(self, baseline_params):
        baseline_params["fish_tank_dia_mm"] = 3600  # > width - 200
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("tank diameter" in i.lower() for i in issues)

    def test_gravity_cascade_fails(self, baseline_params):
        # Make tank rim lower than biofilter top
        baseline_params["fish_tank_stand_h_mm"] = 100
        baseline_params["fish_tank_h_mm"] = 200
        baseline_params["bio_stand_h_mm"] = 500
        baseline_params["bio_h_mm"] = 880
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("gravity" in i.lower() for i in issues)

    def test_pump_head_too_high(self, baseline_params):
        baseline_params["fish_tank_stand_h_mm"] = 2500
        baseline_params["fish_tank_h_mm"] = 1000
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("pump" in i.lower() or "tdh" in i.lower() for i in issues)

    def test_lethal_density(self, baseline_params):
        baseline_params["stocking_count"] = 500
        baseline_params["tank_volume_l"] = 100
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("density" in i.lower() for i in issues)

    def test_no_biofilter(self, baseline_params):
        baseline_params["bio_barrel_count"] = 0
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("biofilter" in i.lower() for i in issues)

    def test_pump_flow_too_low(self, baseline_params):
        baseline_params["pump_flow_lpm"] = 2
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("pump flow" in i.lower() for i in issues)

    def test_air_pump_too_low(self, baseline_params):
        baseline_params["air_pump_flow_lpm"] = 2
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert any("air pump" in i.lower() for i in issues)

    def test_multiple_failures(self, baseline_params):
        baseline_params["bio_barrel_count"] = 0
        baseline_params["pump_flow_lpm"] = 1
        baseline_params["air_pump_flow_lpm"] = 1
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
        assert len(issues) >= 3

    def test_boundary_length_within_tolerance(self, baseline_params):
        # 10mm tolerance is allowed
        baseline_params["structure_length_mm"] = 7630
        passes, issues = validate_constraints(baseline_params)
        assert passes is True

    def test_boundary_length_exceeds_tolerance(self, baseline_params):
        baseline_params["structure_length_mm"] = 7631
        passes, issues = validate_constraints(baseline_params)
        assert passes is False
