"""
Unit tests for src/data_generation/incremental/business_logic.py --
the shared demand/cancellation formulas used by the incremental generator.
No Snowflake, no fixtures beyond pure function calls.
"""
# Validates the core pricing and demand formulas used by the data generator.

import random

from business_logic import (
    base_popularity,
    cancellation_multiplier,
    price_elasticity_factor,
    rating_factor,
    sample_lead_time_days,
)

# Checks that popularity remains stable for identical inputs and varies across IDs.
class TestBasePopularity:
    def test_is_deterministic_for_same_seed_and_id(self):
        result1 = base_popularity("EXP1001", seed=42)
        result2 = base_popularity("EXP1001", seed=42)
        assert result1 == result2

    def test_different_ids_produce_different_values(self):
        values = {base_popularity(f"EXP{i}", seed=42) for i in range(20)}
        assert len(values) > 1, "20 different experience_ids all produced identical popularity"

    def test_is_always_positive(self):
        for i in range(50):
            assert base_popularity(f"EXP{i}", seed=42) > 0

# Ensures price changes affect demand elasticity in the expected direction.
class TestPriceElasticityFactor:
    def test_higher_price_than_base_reduces_factor(self):
        base = price_elasticity_factor(price=100, base_price=100)
        higher = price_elasticity_factor(price=200, base_price=100)
        assert higher < base

    def test_lower_price_than_base_increases_factor(self):
        base = price_elasticity_factor(price=100, base_price=100)
        lower = price_elasticity_factor(price=50, base_price=100)
        assert lower > base

    def test_floor_at_point_three(self):
        result = price_elasticity_factor(price=10000, base_price=10)
        assert result == 0.3

    def test_zero_base_price_returns_neutral_factor(self):
        assert price_elasticity_factor(price=50, base_price=0) == 1.0

# Verifies that rating quality changes demand multiplier at the defined thresholds.
class TestRatingFactor:
    def test_high_rating_boosts_demand(self):
        assert rating_factor(4.5) == 1.15
        assert rating_factor(5.0) == 1.15

    def test_low_rating_penalizes_demand(self):
        assert rating_factor(3.9) == 0.85
        assert rating_factor(1.0) == 0.85

    def test_mid_rating_is_neutral(self):
        assert rating_factor(4.0) == 1.0
        assert rating_factor(4.4) == 1.0

    def test_boundary_at_four_point_five(self):
        assert rating_factor(4.5) == 1.15
        assert rating_factor(4.49) == 1.0

# Confirms that cancellation risk increases or decreases based on booking conditions.
class TestCancellationMultiplier:
    def _baseline(self, **overrides):
        defaults = dict(
            lead_time_days=10, discount_pct=0.0, channel="WEB",
            category="Show",
            prior_cancellations=0,
        )
        defaults.update(overrides)
        return cancellation_multiplier(**defaults)

    def test_long_lead_time_increases_risk(self):
        baseline = self._baseline()
        long_lead = self._baseline(lead_time_days=90)
        assert long_lead > baseline

    def test_short_lead_time_decreases_risk(self):
        baseline = self._baseline()
        short_lead = self._baseline(lead_time_days=1)
        assert short_lead < baseline

    def test_large_discount_increases_risk(self):
        baseline = self._baseline()
        discounted = self._baseline(discount_pct=0.25)
        assert discounted > baseline

    def test_partner_channel_increases_risk(self):
        baseline = self._baseline()
        partner = self._baseline(channel="PARTNER")
        assert partner > baseline

    def test_high_cancel_category_increases_risk(self):
        baseline = self._baseline()
        adventure = self._baseline(category="Adventure")
        assert adventure > baseline

    def test_low_cancel_category_decreases_risk(self):
        baseline = self._baseline()
        museum = self._baseline(category="Museum")
        assert museum < baseline

    def test_prior_cancellations_compound(self):
        one_prior = self._baseline(prior_cancellations=1)
        two_prior = self._baseline(prior_cancellations=2)
        assert two_prior > one_prior

# Validates that lead-time sampling stays within supported booking windows.
class TestSampleLeadTimeDays:
    def test_always_within_valid_range(self):
        rng = random.Random(42)
        for _ in range(200):
            lead_time = sample_lead_time_days(rng)
            assert 1 <= lead_time <= 120

    def test_produces_variety_across_buckets(self):
        rng = random.Random(42)
        values = [sample_lead_time_days(rng) for _ in range(500)]
        assert min(values) <= 7
        assert any(v > 60 for v in values)