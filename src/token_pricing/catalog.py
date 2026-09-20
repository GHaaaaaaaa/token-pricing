"""
Reference model-pricing catalog and routing-tier presets.

IMPORTANT
---------
Vendor list prices change frequently and differ by region, contract,
cache handling and tier. The numbers below are REFERENCE routing tiers
used for quick sanity checks, dated August 2026, in USD per 1M tokens.
Always replace them with the prices on your own provider invoice before
publishing plan prices. This file is intentionally not a scraper.
"""

from __future__ import annotations

from .economics import blended_cost

# Reference routing tiers (USD per 1M tokens). Keyed by a descriptive
# routing tier rather than a SKU so they survive provider renames.
#   (input_price, output_price, typical_blended_at_4to1, notes)
MODEL_PRICING_2026 = {
    "budget": {
        "input_per_m": 0.20,
        "output_per_m": 1.20,
        "label": "Budget route (Flash/Lite tier)",
        "notes": "Cheapest fast tier; good default for high-volume chat.",
    },
    "smart": {
        "input_per_m": 0.60,
        "output_per_m": 2.60,
        "label": "Smart router (mixed cheap/mid)",
        "notes": "Intelligent routing across cheap and mid models.",
    },
    "premium": {
        "input_per_m": 2.00,
        "output_per_m": 10.00,
        "label": "Premium route (Sonnet-tier)",
        "notes": "Mid-tier flagship quality.",
    },
    "flagship": {
        "input_per_m": 5.00,
        "output_per_m": 25.00,
        "label": "Flagship route (Opus-tier)",
        "notes": "Top quality; quota weight ~22x the budget route.",
    },
    "deepseek-flash": {
        "input_per_m": 0.44,
        "output_per_m": 1.32,
        "label": "DeepSeek V4-Flash tier",
        "notes": "Low-cost alternative route; heavy prompt-cache discount.",
    },
}

PRICING_AS_OF = "2026-08"


def blended_cost_for_model(tier: str, io_ratio=4):
    """
    Blended cost per 1M tokens for a named reference tier.

    >>> c = blended_cost_for_model("budget")
    >>> round(float(c), 2)
    0.4
    """
    try:
        entry = MODEL_PRICING_2026[tier]
    except KeyError:
        raise KeyError(
            f"unknown tier {tier!r}; choose from "
            f"{sorted(MODEL_PRICING_2026)}"
        )
    return blended_cost(
        entry["input_per_m"], entry["output_per_m"], io_ratio
    )
