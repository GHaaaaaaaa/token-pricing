import unittest
from decimal import Decimal

from token_pricing import (
    Plan,
    blended_cost,
    blended_cost_for_model,
    max_safe_quota,
    overage_break_even,
    profit_per_subscriber,
    validate_plan,
)
from token_pricing.catalog import MODEL_PRICING_2026


class TestBlendedCost(unittest.TestCase):
    def test_weighted_mix(self):
        # 4:1 mix => 80% input + 20% output
        self.assertEqual(blended_cost(1.0, 5.0, 4), Decimal("1.8"))

    def test_one_to_one(self):
        self.assertEqual(blended_cost(2.0, 10.0, 1), Decimal("6.0"))

    def test_budget_tier_is_about_40_cents(self):
        self.assertAlmostEqual(float(blended_cost_for_model("budget")), 0.40, 2)

    def test_all_catalog_tiers_finite(self):
        for tier in MODEL_PRICING_2026:
            self.assertGreater(float(blended_cost_for_model(tier)), 0)

    def test_negative_ratio_rejected(self):
        with self.assertRaises(ValueError):
            blended_cost(1, 2, -1)


class TestValidatePlan(unittest.TestCase):
    def test_safe_budget_plan(self):
        # $19, 10M included at ~$0.40/M blended => cost $4, ample margin.
        plan = Plan(price=19, included_tokens_m=10, overage_per_m=1.50)
        check = validate_plan(plan, blended_cost_per_m=0.40)
        self.assertEqual(check.status, "SAFE")
        self.assertGreater(check.included_margin_pct, 30)
        self.assertGreaterEqual(check.max_safe_included_m, 10)
        # overage $1.50 >= 1.6 * 0.40 = $0.64
        self.assertGreaterEqual(check.overage_margin_pct, 0)

    def test_unsafe_when_quota_exceeds_fee(self):
        # $19 plan promising 100M at flagship cost (~$9/M) cannot work.
        plan = Plan(price=19, included_tokens_m=100, overage_per_m=12.0)
        check = validate_plan(plan, blended_cost_per_m=9.0)
        self.assertEqual(check.status, "UNSAFE")
        self.assertLess(check.included_margin_pct, 0)
        self.assertTrue(
            any("margin" in w.lower() or "below" in w.lower()
                for w in check.warnings)
        )

    def test_unsafe_when_overage_below_cost(self):
        plan = Plan(price=19, included_tokens_m=1, overage_per_m=0.10)
        check = validate_plan(plan, blended_cost_per_m=1.00)
        self.assertEqual(check.status, "UNSAFE")
        self.assertTrue(
            any("below backend cost" in w.lower() for w in check.warnings)
        )

    def test_warning_for_thin_margin(self):
        # Cost chosen so margin is positive but under the 30% target.
        # Net fee ~ 19 * 0.971 = 18.449; include 17M @ $1/M => cost 17,
        # margin ~7.9% > 0 but < 30% => WARNING, overage 1.6*1=1.6 safe.
        plan = Plan(price=19, included_tokens_m=17, overage_per_m=2.0)
        check = validate_plan(plan, blended_cost_per_m=1.0)
        self.assertEqual(check.status, "WARNING")
        self.assertGreater(check.included_margin_pct, 0)

    def test_platform_fees_reduce_safe_quota(self):
        low_fee = max_safe_quota(19, 0.40, 0.029, 0.0)
        high_fee = max_safe_quota(19, 0.40, 0.029, 0.10)
        self.assertGreater(low_fee, high_fee)

    def test_overage_break_even_rule(self):
        self.assertEqual(float(overage_break_even(1.0)), 1.60)
        self.assertEqual(float(overage_break_even(0.40)), 0.64)

    def test_profit_per_subscriber(self):
        plan = Plan(price=19, included_tokens_m=10)
        # net 19*0.971 = 18.449 - cost 4 = 14.449
        profit = profit_per_subscriber(plan, 0.40, payment_fee_pct=0.029)
        self.assertAlmostEqual(float(profit), 14.449, places=2)

    def test_invalid_plan_rejected(self):
        with self.assertRaises(ValueError):
            Plan(price=-1)
        with self.assertRaises(ValueError):
            validate_plan(Plan(10), blended_cost_per_m=-1)

    def test_zero_overage_is_hard_stop_not_unsafe(self):
        # No overage configured: overage rule should not mark UNSAFE.
        plan = Plan(price=19, included_tokens_m=10, overage_per_m=0)
        check = validate_plan(plan, blended_cost_per_m=0.40)
        self.assertEqual(check.status, "SAFE")
        self.assertIsNone(check.overage_margin_pct)


class TestCLI(unittest.TestCase):
    def test_cli_validate_returns_zero_on_safe(self):
        from token_pricing.cli import main
        rc = main([
            "validate", "--tier", "budget",
            "--price", "19", "--included", "10", "--overage", "1.5",
        ])
        self.assertEqual(rc, 0)

    def test_cli_validate_returns_two_on_unsafe(self):
        from token_pricing.cli import main
        rc = main([
            "validate", "--tier", "flagship",
            "--price", "19", "--included", "100", "--overage", "1",
        ])
        self.assertEqual(rc, 2)

    def test_cli_tiers_runs(self):
        from token_pricing.cli import main
        self.assertEqual(main(["tiers"]), 0)


if __name__ == "__main__":
    unittest.main()
