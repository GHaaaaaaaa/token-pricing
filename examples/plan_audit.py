"""
Audit a small plan catalog against your measured backend costs.

Run:  python examples/plan_audit.py
"""

from token_pricing import (
    MODEL_PRICING_2026,
    Plan,
    blended_cost_for_model,
    validate_plan,
)

# Plans you are considering. (included quota is in MILLIONS of tokens.)
plans = [
    ("Starter", Plan(9, 3, 2.00)),
    ("Pro",     Plan(19, 10, 1.50)),
    ("Scale",   Plan(49, 40, 1.20)),
]

# Which backend route each plan is allowed to use.
route = "budget"          # budget | smart | premium | flagship
platform_fee_pct = 0.05   # selling via a merchant-of-record (5%)

blended = blended_cost_for_model(route)
print(f"Route: {MODEL_PRICING_2026[route]['label']}  "
      f"blended ${float(blended):.4f}/1M\n")

for name, plan in plans:
    check = validate_plan(
        plan,
        blended_cost_per_m=blended,
        platform_fee_pct=platform_fee_pct,
    )
    print(f"{name:8s} ${plan.price:<4} {plan.included_tokens_m:>4}M incl  "
          f"-> {check.status:7} "
          f"margin {check.included_margin_pct:6.1f}%  "
          f"max-safe {check.max_safe_included_m:6.2f}M")
    for w in check.warnings:
        print(f"         ! {w}")
