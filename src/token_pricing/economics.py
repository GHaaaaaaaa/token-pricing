"""
Core token-pricing economics.

All money is USD and is calculated with Decimal to avoid float drift.
Prices are expressed per 1,000,000 tokens ("per 1M"), the unit every
major model provider uses.

This module is intentionally dependency-free and side-effect-free: it is
pure math over plain values so it is trivial to test and embed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


ONE_MILLION = Decimal("1000000")


def _d(value) -> Decimal:
    """Coerce int/float/str/Decimal to Decimal safely."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _q(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------
# Blended cost
# ----------------------------------------------------------------------

def blended_cost(input_per_m, output_per_m, io_ratio=4) -> Decimal:
    """
    Blended backend cost per 1M tokens for a given traffic mix.

    Args:
        input_per_m:  input price in USD per 1M tokens.
        output_per_m: output price in USD per 1M tokens.
        io_ratio:     input-to-output token ratio, e.g. 4 means a 4:1
                      mix (80% input, 20% output). Typical chat traffic
                      is ~4:1; summarisation is higher; generation-heavy
                      traffic is closer to 1:1.

    Returns:
        Blended cost in USD per 1M tokens.

    >>> float(blended_cost(1.0, 5.0, 4))
    1.8
    """
    ratio = _d(io_ratio)
    if ratio < 0:
        raise ValueError("io_ratio must be non-negative")
    total = ratio + 1
    return (_d(input_per_m) * ratio + _d(output_per_m)) / total


# ----------------------------------------------------------------------
# Plan definition
# ----------------------------------------------------------------------

@dataclass
class Plan:
    """
    A flat or hybrid (fixed fee + included quota + overage) plan.

    Attributes:
        price:             fixed monthly price in USD.
        included_tokens_m: millions of tokens included in the fee.
        overage_per_m:     price charged per 1M tokens over the quota.
                           0 means overage is disabled (hard stop).
    """

    price: float
    included_tokens_m: float = 0.0
    overage_per_m: float = 0.0

    def __post_init__(self):
        if _d(self.price) < 0:
            raise ValueError("plan price must be non-negative")
        if _d(self.included_tokens_m) < 0:
            raise ValueError("included_tokens_m must be non-negative")
        if _d(self.overage_per_m) < 0:
            raise ValueError("overage_per_m must be non-negative")


# ----------------------------------------------------------------------
# Standalone helpers
# ----------------------------------------------------------------------

def net_revenue(price, payment_fee_pct=0.0, platform_fee_pct=0.0) -> Decimal:
    """What is left of the sticker price after payment/platform fees."""
    fee_factor = Decimal("1") - _d(payment_fee_pct) - _d(platform_fee_pct)
    return _d(price) * fee_factor


def max_safe_quota(
    price,
    blended_cost_per_m,
    payment_fee_pct=0.0,
    platform_fee_pct=0.0,
    target_margin=0.30,
) -> Decimal:
    """
    Maximum millions of tokens that can be included while still leaving
    ``target_margin`` after fees. Returns millions of tokens (Decimal).

    A plan whose included quota exceeds this number erodes the margin
    buffer that is meant to absorb usage spikes and model price changes.
    """
    net = net_revenue(price, payment_fee_pct, platform_fee_pct)
    budget = net * (Decimal("1") - _d(target_margin))
    cost = _d(blended_cost_per_m)
    if cost <= 0:
        # Free backend (mocked/self-hosted) — no finite quota ceiling.
        return Decimal("Infinity")
    return budget / cost


def overage_break_even(blended_cost_per_m, markup=1.6) -> Decimal:
    """
    Minimum overage price per 1M tokens. Defaults to a 60% markup over
    cost (1.6x) so heavy overage users keep contributing margin instead
    of quietly costing more than they pay.
    """
    return _q(_d(blended_cost_per_m) * _d(markup), "0.01")


def profit_per_subscriber(
    plan: Plan,
    blended_cost_per_m,
    payment_fee_pct=0.0,
    platform_fee_pct=0.0,
) -> Decimal:
    """Net revenue minus the cost of the fully-consumed included quota."""
    net = net_revenue(plan.price, payment_fee_pct, platform_fee_pct)
    included_cost = _d(plan.included_tokens_m) * _d(blended_cost_per_m)
    return net - included_cost


# ----------------------------------------------------------------------
# Full validation
# ----------------------------------------------------------------------

@dataclass
class PlanCheck:
    status: str                      # "SAFE" | "WARNING" | "UNSAFE"
    blended_cost_per_m: float
    base_fee_usd: float
    net_base_fee_usd: float
    included_tokens_m: float
    included_cost_usd: float
    included_margin_pct: float
    overage_price_per_m: float
    overage_margin_pct: Optional[float]
    max_safe_included_m: float
    break_even_overage_price: float
    warnings: list

    def __str__(self):
        lines = [
            f"{self.status}",
            f"  blended cost:        ${self.blended_cost_per_m:.4f} / 1M tokens",
            f"  net base fee:        ${self.net_base_fee_usd:.4f}",
            f"  included cost:       ${self.included_cost_usd:.4f}",
            f"  included margin:     {self.included_margin_pct:.1f}%",
            f"  max safe quota:      {self.max_safe_included_m:.2f}M tokens",
            f"  overage price:       ${self.overage_price_per_m:.2f} / 1M",
        ]
        if self.overage_margin_pct is not None:
            lines.append(f"  overage margin:      {self.overage_margin_pct:.1f}%")
        lines.append(
            f"  break-even overage:  ${self.break_even_overage_price:.2f} / 1M"
        )
        if self.warnings:
            lines.append("  warnings:")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


def validate_plan(
    plan: Plan,
    blended_cost_per_m,
    payment_fee_pct=0.029,
    platform_fee_pct=0.0,
    target_margin=0.30,
    overage_markup=1.6,
) -> PlanCheck:
    """
    Validate that ``plan`` cannot lose money at ``blended_cost_per_m``.

    Rules:
      1. Included-quota cost must fit inside the fee (after fees) with
         at least ``target_margin`` left.
      2. If overage is enabled, its price must be >= ``overage_markup``
         times backend cost (default 1.6x).

    Status:
      SAFE    - both rules pass.
      WARNING - margin is positive but below target, or overage markup
                is thin.
      UNSAFE  - included quota alone costs more than the net fee, or
                overage is priced below cost (every token loses money).

    Args:
        plan: the Plan to check.
        blended_cost_per_m: measured blended backend cost per 1M tokens.
        payment_fee_pct: payment processor share (Stripe ~0.029 + fixed
                         fee; use a slightly higher conservative value).
        platform_fee_pct: merchant-of-record cut (Creem/Gumroad/Paddle
                         /Lemon Squeezy ~0.04-0.10); 0 for direct Stripe.
        target_margin: minimum margin wanted on the included allowance.
        overage_markup: minimum required overage price / cost ratio.
    """
    cost_m = _d(blended_cost_per_m)
    if cost_m < 0:
        raise ValueError("blended_cost_per_m must be non-negative")

    pay_pct = _d(payment_fee_pct)
    plat_pct = _d(platform_fee_pct)
    fee_factor = Decimal("1") - pay_pct - plat_pct
    if fee_factor <= 0:
        raise ValueError("payment + platform fees must be below 100%")

    base_fee = _d(plan.price)
    net = base_fee * fee_factor
    included_m = _d(plan.included_tokens_m)
    included_cost = included_m * cost_m

    if net > 0:
        included_margin = (net - included_cost) / net
    else:
        included_margin = Decimal("-1")

    safe_quota_m = max_safe_quota(
        plan.price, cost_m, pay_pct, plat_pct, target_margin
    )

    overage = _d(plan.overage_per_m)
    overage_enabled = overage > 0
    overage_margin = (
        float((overage - cost_m) / overage) if overage_enabled else None
    )
    break_even_overage = overage_break_even(cost_m, overage_markup)

    included_safe = included_cost <= net * (Decimal("1") - _d(target_margin))
    overage_safe = (not overage_enabled) or overage >= cost_m * _d(
        overage_markup
    )

    warnings = []
    if pay_pct + plat_pct > Decimal("0.10"):
        warnings.append("payment + platform fees exceed 10% of revenue")
    if overage_enabled and overage < cost_m:
        warnings.append(
            "overage price is BELOW backend cost - every overage token "
            "loses money"
        )
    elif overage_enabled and not overage_safe:
        warnings.append(
            f"overage price is below the {overage_markup:g}x cost rule "
            f"(${break_even_overage}/1M); heavy users erode margin"
        )
    if not included_safe and included_cost <= net:
        warnings.append(
            f"margin on the included quota is below "
            f"{float(_d(target_margin)) * 100:.0f}%; the plan is fragile "
            "to usage spikes or model price hikes"
        )

    if included_cost > net or (overage_enabled and overage < cost_m):
        status = "UNSAFE"
    elif included_safe and overage_safe:
        status = "SAFE"
    else:
        status = "WARNING"

    def f(d: Decimal) -> float:
        return float(_q(d))

    return PlanCheck(
        status=status,
        blended_cost_per_m=f(cost_m),
        base_fee_usd=f(base_fee),
        net_base_fee_usd=f(net),
        included_tokens_m=float(included_m),
        included_cost_usd=f(included_cost),
        included_margin_pct=float(_q(included_margin * 100, "0.1")),
        overage_price_per_m=float(overage),
        overage_margin_pct=(
            round(overage_margin * 100, 1) if overage_margin is not None
            else None
        ),
        max_safe_included_m=(
            f(safe_quota_m) if safe_quota_m.is_finite() else float("inf")
        ),
        break_even_overage_price=float(break_even_overage),
        warnings=warnings,
    )
