"""
Command-line interface for ai-token-pricing.

Examples
--------
Blended cost at a 4:1 mix::

    python -m token_pricing blended --input 0.20 --output 1.20 --ratio 4

Validate a $19 plan with 10M included tokens and $1.50 overage::

    python -m token_pricing validate --price 19 --included 10 \
        --overage 1.50 --tier budget

Max safe quota for a plan::

    python -m token_pricing max-quota --price 19 --tier smart

List reference pricing tiers::

    python -m token_pricing tiers
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .catalog import MODEL_PRICING_2026, PRICING_AS_OF, blended_cost_for_model
from .economics import Plan, blended_cost, max_safe_quota, validate_plan


def _resolve_cost(args):
    if args.tier:
        return blended_cost_for_model(args.tier, args.ratio)
    if args.input is None or args.output is None:
        raise SystemExit(
            "provide --tier, or both --input and --output per-1M prices"
        )
    return blended_cost(args.input, args.output, args.ratio)


def cmd_blended(args):
    cost = _resolve_cost(args)
    print(f"Blended cost: ${float(cost):.4f} per 1M tokens")


def cmd_validate(args):
    cost = _resolve_cost(args)
    plan = Plan(
        price=args.price,
        included_tokens_m=args.included,
        overage_per_m=args.overage,
    )
    check = validate_plan(
        plan,
        cost,
        payment_fee_pct=args.payment_fee / 100.0,
        platform_fee_pct=args.platform_fee / 100.0,
        target_margin=args.margin / 100.0,
    )
    print(check)
    return 0 if check.status != "UNSAFE" else 2


def cmd_max_quota(args):
    cost = _resolve_cost(args)
    m = max_safe_quota(
        args.price,
        cost,
        payment_fee_pct=args.payment_fee / 100.0,
        platform_fee_pct=args.platform_fee / 100.0,
        target_margin=args.margin / 100.0,
    )
    print(
        f"Max safe included quota for ${args.price}/mo: "
        f"{float(m):.2f}M tokens (blended ${float(cost):.4f}/1M)"
    )


def cmd_tiers(args):
    print(f"Reference tiers (USD per 1M tokens, as of {PRICING_AS_OF})")
    for key, e in MODEL_PRICING_2026.items():
        b = float(blended_cost_for_model(key))
        print(
            f"  {key:16s} in ${e['input_per_m']:>5.2f}  "
            f"out ${e['output_per_m']:>6.2f}  blended ${b:>6.4f}"
        )
    print("\nVerify against your provider invoice before publishing prices.")


def build_parser():
    p = argparse.ArgumentParser(
        prog="ai-token-pricing",
        description="Token economics for AI products: blended cost, "
        "profitable-plan validation, max safe quota.",
    )
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    def add_cost_args(sp):
        sp.add_argument("--tier", choices=sorted(MODEL_PRICING_2026),
                        help="reference routing tier")
        sp.add_argument("--input", type=float,
                        help="input price USD per 1M tokens")
        sp.add_argument("--output", type=float,
                        help="output price USD per 1M tokens")
        sp.add_argument("--ratio", type=float, default=4.0,
                        help="input:output token ratio (default 4)")

    def add_fee_args(sp):
        sp.add_argument("--payment-fee", type=float, default=2.9,
                        help="payment fee %% (default 2.9)")
        sp.add_argument("--platform-fee", type=float, default=0.0,
                        help="platform/MoR fee %% (default 0)")
        sp.add_argument("--margin", type=float, default=30.0,
                        help="target margin %% (default 30)")

    sp = sub.add_parser("blended", help="compute blended cost per 1M")
    add_cost_args(sp)
    sp.set_defaults(func=cmd_blended)

    sp = sub.add_parser("validate", help="validate a plan (SAFE/UNSAFE)")
    add_cost_args(sp)
    sp.add_argument("--price", type=float, required=True,
                    help="monthly plan price USD")
    sp.add_argument("--included", type=float, default=0.0,
                    help="included millions of tokens")
    sp.add_argument("--overage", type=float, default=0.0,
                    help="overage price USD per 1M (0 = disabled)")
    add_fee_args(sp)
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("max-quota", help="max safe included quota")
    add_cost_args(sp)
    sp.add_argument("--price", type=float, required=True)
    add_fee_args(sp)
    sp.set_defaults(func=cmd_max_quota)

    sp = sub.add_parser("tiers", help="list reference pricing tiers")
    sp.set_defaults(func=cmd_tiers)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())