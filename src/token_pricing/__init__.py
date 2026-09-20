"""
token-pricing
=============

Token economics for AI products: blended token cost, profitable plan
validation (SAFE / WARNING / UNSAFE), max safe included quota, and
overage break-even pricing.

Zero third-party dependencies. Money math uses Decimal throughout.

    from token_pricing import blended_cost, validate_plan, Plan

Quick start
-----------
    >>> blended = blended_cost(input_per_m=0.20, output_per_m=1.20, io_ratio=4)
    >>> plan = Plan(price=19, included_tokens_m=10, overage_per_m=1.50)
    >>> result = validate_plan(plan, blended_cost_per_m=blended)
    >>> result.status
    'SAFE'

The free browser version lives at
https://tokenkit.tingstudioai.com/calculator
"""

from .economics import (
    Plan,
    PlanCheck,
    blended_cost,
    validate_plan,
    max_safe_quota,
    overage_break_even,
    profit_per_subscriber,
)
from .catalog import MODEL_PRICING_2026, blended_cost_for_model

__version__ = "0.1.1"

__all__ = [
    "Plan",
    "PlanCheck",
    "blended_cost",
    "validate_plan",
    "max_safe_quota",
    "overage_break_even",
    "profit_per_subscriber",
    "MODEL_PRICING_2026",
    "blended_cost_for_model",
    "__version__",
]
