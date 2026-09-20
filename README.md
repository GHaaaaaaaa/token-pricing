# ai-token-pricing

**Token economics for AI products.** Compute your real blended token cost, validate that a subscription plan is profitable (`SAFE` / `WARNING` / `UNSAFE`), find the maximum quota you can safely include, and price overage so heavy users never erase your margin.

- **Zero dependencies** — pure Python, `Decimal` money math, safe to vendor anywhere.
- **Blended cost** from separate input/output prices and your real input:output ratio.
- **`validate_plan()`** — the "never lose money" guard rail, accounting for payment **and** platform fees.
- **Max safe included quota** + **overage break-even price** in one call.
- **CLI** for quick checks without writing code.
- Prefer a UI? Use the **free calculator**: <https://tokenkit.tingstudioai.com/calculator>

## Install

`pip install ai-token-pricing`

Python 3.8+. No third-party dependencies.

## Library API

### `blended_cost(input_per_m, output_per_m, io_ratio=4) -> Decimal`

Blended backend cost per 1M tokens for a traffic mix.

### `Plan(price, included_tokens_m, overage_per_m)`

A hybrid plan: fixed monthly fee, included quota (in millions of tokens), and an overage price per 1M.

### `validate_plan(plan, blended_cost_per_m, ...) -> PlanCheck`

| Parameter | Default | Meaning |
| --- | --- | --- |
| `payment_fee_pct` | `0.029` | Payment processor share. |
| `platform_fee_pct` | `0.0` | Merchant-of-record cut. |
| `target_margin` | `0.30` | Minimum margin. |
| `overage_markup` | `1.6` | Required overage price / cost ratio. |

Returns `status` (SAFE / WARNING / UNSAFE), `max_safe_included_m`, `overage_margin_pct`, `break_even_overage_price`, `warnings`.

## CLI

`ai-token-pricing tiers`
`ai-token-pricing blended --input 0.20 --output 1.20 --ratio 4`
`ai-token-pricing validate --tier budget --price 19 --included 10 --overage 1.50`
`ai-token-pricing max-quota --price 19 --tier smart --platform-fee 5`

The `validate` command exits non-zero on UNSAFE, so you can fail a deploy on a bad price change.

## Free calculator

<https://tokenkit.tingstudioai.com/calculator>

## Need the rest of the billing stack?

The production billing engine (Stripe Metered Billing, idempotent MeterEvents, retries, circuit breaker, fallback queue, webhook verification, weighted quotas, hard USD caps, rate limiting, anomaly throttling, audit log) ships as the paid [AI SaaS Token Billing Kit](https://tokenkit.tingstudioai.com/).

## License

MIT — see [LICENSE](LICENSE). Independent project; not affiliated with Stripe, OpenAI, Anthropic, DeepSeek, or Google.
