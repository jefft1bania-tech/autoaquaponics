"""Tests for growth factor functions in evaluate.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from evaluate import (
    sgr_base,
    temperature_factor,
    dissolved_oxygen_factor,
    density_factor,
    water_quality_factor,
    turnover_factor,
)


# ---------------------------------------------------------------------------
# sgr_base
# ---------------------------------------------------------------------------

class TestSgrBase:
    def test_fingerling_weight(self):
        assert sgr_base(7.0) == 5.0

    def test_decreases_with_weight(self):
        """SGR should decrease monotonically as fish get larger."""
        weights = [5, 15, 50, 100, 200, 300, 400, 500, 700]
        sgrs = [sgr_base(w) for w in weights]
        for i in range(len(sgrs) - 1):
            assert sgrs[i] >= sgrs[i + 1], (
                f"SGR should decrease: sgr({weights[i]})={sgrs[i]} "
                f">= sgr({weights[i+1]})={sgrs[i+1]}"
            )

    def test_always_positive(self):
        for w in [1, 10, 50, 100, 200, 400, 600, 1000]:
            assert sgr_base(w) > 0

    def test_boundary_at_10g(self):
        assert sgr_base(9) == 5.0
        assert sgr_base(10) == 4.2

    def test_large_fish(self):
        assert sgr_base(700) == 0.5


# ---------------------------------------------------------------------------
# temperature_factor
# ---------------------------------------------------------------------------

class TestTemperatureFactor:
    def test_optimal_range(self):
        """26-30°C should return 1.0."""
        assert temperature_factor(26) == 1.0
        assert temperature_factor(28) == 1.0
        assert temperature_factor(30) == 1.0

    def test_below_minimum_viable(self):
        assert temperature_factor(17) == 0.0
        assert temperature_factor(0) == 0.0

    def test_above_maximum_viable(self):
        assert temperature_factor(35) == 0.0
        assert temperature_factor(40) == 0.0

    def test_suboptimal_cold(self):
        val = temperature_factor(20)
        assert 0.0 < val < 1.0

    def test_suboptimal_hot(self):
        val = temperature_factor(31)
        assert 0.0 < val < 1.0

    def test_output_range(self):
        for temp in range(0, 50):
            val = temperature_factor(temp)
            assert 0.0 <= val <= 1.0, f"temperature_factor({temp}) = {val}"

    def test_minimum_boundary(self):
        assert temperature_factor(18) == 0.15

    def test_monotonic_cold_to_optimal(self):
        temps = [18, 20, 22, 24, 26]
        vals = [temperature_factor(t) for t in temps]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1]

    def test_monotonic_optimal_to_hot(self):
        temps = [30, 31, 32, 33, 34]
        vals = [temperature_factor(t) for t in temps]
        for i in range(len(vals) - 1):
            assert vals[i] >= vals[i + 1]


# ---------------------------------------------------------------------------
# dissolved_oxygen_factor
# ---------------------------------------------------------------------------

class TestDissolvedOxygenFactor:
    def test_optimal(self):
        assert dissolved_oxygen_factor(7.0) == 1.0
        assert dissolved_oxygen_factor(10.0) == 1.0

    def test_critical_low(self):
        val = dissolved_oxygen_factor(1.5)
        assert val == 0.10

    def test_monotonically_increasing(self):
        levels = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        vals = [dissolved_oxygen_factor(do) for do in levels]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1]

    def test_output_range(self):
        for do in [x * 0.5 for x in range(0, 20)]:
            val = dissolved_oxygen_factor(do)
            assert 0.0 <= val <= 1.0


# ---------------------------------------------------------------------------
# density_factor
# ---------------------------------------------------------------------------

class TestDensityFactor:
    def test_low_density_optimal(self):
        assert density_factor(3) == 1.0

    def test_high_density_stressed(self):
        val = density_factor(60)
        assert val == 0.20

    def test_extreme_density(self):
        assert density_factor(100) == 0.20

    def test_monotonically_decreasing(self):
        densities = [1, 10, 20, 30, 50, 70]
        vals = [density_factor(d) for d in densities]
        for i in range(len(vals) - 1):
            assert vals[i] >= vals[i + 1]


# ---------------------------------------------------------------------------
# water_quality_factor
# ---------------------------------------------------------------------------

class TestWaterQualityFactor:
    def test_zero_tan_production(self):
        assert water_quality_factor(0, 100) == 1.0

    def test_excellent_ratio(self):
        assert water_quality_factor(10, 50) == 1.0  # ratio = 5.0

    def test_toxic_ratio(self):
        val = water_quality_factor(100, 10)  # ratio = 0.1
        assert val == 0.05

    def test_marginal_ratio(self):
        val = water_quality_factor(10, 10)  # ratio = 1.0
        assert 0.5 < val < 0.9

    def test_monotonic_with_increasing_capacity(self):
        tans = [5, 10, 15, 25, 50, 100]
        vals = [water_quality_factor(10, t) for t in tans]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1]


# ---------------------------------------------------------------------------
# turnover_factor
# ---------------------------------------------------------------------------

class TestTurnoverFactor:
    def test_optimal_range(self):
        assert turnover_factor(3.0) == 1.0
        assert turnover_factor(4.0) == 1.0

    def test_very_low_flow(self):
        assert turnover_factor(0.1) == 0.40

    def test_excessive_flow(self):
        assert turnover_factor(5.0) == 0.95

    def test_output_range(self):
        for t in [x * 0.5 for x in range(0, 20)]:
            val = turnover_factor(t)
            assert 0.0 <= val <= 1.0
