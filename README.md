# token-pricing

**Token economics for AI products.** Compute your real blended token cost, validate that a subscription plan is profitable (`SAFE` / `WARNING` / `UNSAFE`), find the maximum quota you can safely include, and price overage so heavy users never erase your margin.

- 🟢 **Zero dependencies** — pure Python, `Decimal` money math, safe to vendor anywhere.
- 🧮 **Blended cost** from separate input/output prices and your real input:output ratio.
- 🛡️ **`validate_plan()`** — the "never lose money" guard rail, accounting for payment **and** platform fees.
- 📈 **Max safe included quota** + **overage break-even price** in one call.
- 💻 **CLI** for quick checks without writing code.
- 🌐 Prefer a UI? Use the **free calculator**: <https://tokenkit.tingstudioai.com/calculator>

```bash
pip install token-pricing
```

```python
from token_pricing import Plan, blended_cost, validate_plan

# Your measured traffic mix: $0.20/1M input, $1.20/1M output, 4:1 ratio
blended = blended_cost(input_per_m=0.20, output_per_m=1.20, io_ratio=4)
# -> Decimal('0.40')  per 1M tokens

plan = Plan(price=19, included_tokens_m=10, overage_per_m=1.50)
check = validate_plan(plan, blended_cost_per_m=blended)

print(check.status)            # SAFE
print(check.max_safe_included_m)  # 32.29  (millions of tokens)
print(check.included_margin_pct)  # 78.3
```

## Why this exists

A flat "10M tokens included" plan looks profitable until you do the math:

- The **blended** token cost depends on your input:output ratio — output is commonly 5–6× the input price, so guessing one "cost per token" is usually wrong.
- **Overage priced below cost** means your heaviest users are the ones who lose you the most money.
- **Payment fees (~2.9%) plus a merchant-of-record cut (Creem/Gumroad/Paddle/Lemon Squeezy, ~4–10%)** come off the top before a single token is paid for.
- One customer silently routing every request to your flagship model can wipe a day of margin.

`token-pricing` encodes the boring, easy-to-get-wrong arithmetic so you can publish prices with a margin buffer instead of a hope.

## Install

```bash
pip install token-pricing
```

Python 3.8+. No third-party dependencies.

## Library API

### `blended_cost(input_per_m, output_per_m, io_ratio=4) -> Decimal`

Blended backend cost per 1M tokens for a traffic mix. `io_ratio=4` means 4 input tokens per 1 output token (80/20) — typical chat. Use a higher ratio for summarisation/cache-heavy traffic, closer to `1` for generation-heavy traffic.

```python
blended_cost(1.0, 5.0, 4)   # Decimal('1.8')  -> $1.80 per 1M
```

### `Plan(price, included_tokens_m, overage_per_m)`

A hybrid plan: fixed monthly fee, included quota (in **millions** of tokens), and an overage price per 1M. Set `overage_per_m=0` for a hard-stop plan with no overage.

### `validate_plan(plan, blended_cost_per_m, ...) -> PlanCheck`

| Parameter | Default | Meaning |
| --- | --- | --- |
| `payment_fee_pct` | `0.029` | Payment processor share. |
| `platform_fee_pct` | `0.0` | Merchant-of-record cut (`0.04`–`0.10` for Creem/Gumroad/Paddle/Lemon Squeezy; `0` for direct Stripe). |
| `target_margin` | `0.30` | Minimum margin to keep on the included allowance. |
| `overage_markup` | `1.6` | Required overage price / cost ratio. |

Returns a `PlanCheck` with:

- `status` — `"SAFE"`, `"WARNING"`, or `"UNSAFE"`.
- `net_base_fee_usd`, `included_cost_usd`, `included_margin_pct`.
- `max_safe_included_m` — most tokens you can include while keeping `target_margin`.
- `overage_margin_pct`, `break_even_overage_price`.
- `warnings` — human-readable reasons.

```python
from token_pricing import Plan, blended_cost_for_model, validate_plan

# Flagship routing makes a "$19 with 100M tokens" plan obviously dangerous:
plan = Plan(price=19, included_tokens_m=100, overage_per_m=1.0)
check = validate_plan(plan, blended_cost_for_model("flagship"))
print(check.status)          # UNSAFE
print(check.warnings[0])     # overage price is BELOW backend cost ...
```

### `max_safe_quota(price, blended_cost_per_m, ...) -> Decimal`

Maximum millions of tokens includable at the target margin.

### `overage_break_even(blended_cost_per_m, markup=1.6) -> Decimal`

Minimum overage price per 1M (default 1.6× cost).

### Reference pricing tiers

`MODEL_PRICING_2026` provides dated reference routing tiers (USD per 1M, **as of 2026-08**) for quick sanity checks — `budget`, `smart`, `premium`, `flagship`, `deepseek-flash`. **Always replace these with the prices on your own provider invoice** before publishing anything.

```python
from token_pricing import MODEL_PRICING_2026, blended_cost_for_model
blended_cost_for_model("budget")   # ~0.40 per 1M at 4:1
```

## CLI

```bash
# reference tiers
token-pricing tiers

# blended cost
token-pricing blended --input 0.20 --output 1.20 --ratio 4

# validate a plan (exit code 0 = SAFE/WARNING, 2 = UNSAFE — usable in CI)
token-pricing validate --tier budget  --price 19 --included 10 --overage 1.50
token-pricing validate --tier premium --price 19 --included 5  --overage 6 \
    --platform-fee 5

# maximum safe quota
token-pricing max-quota --price 19 --tier smart --platform-fee 5
```

Example output:

```text
SAFE
  blended cost:        $0.4000 / 1M tokens
  net base fee:        $18.4490
  included cost:       $4.0000
  included margin:     78.3%
  max safe quota:      32.29M tokens
  overage price:       $1.50 / 1M
  overage margin:      73.3%
  break-even overage:  $0.64 / 1M
```

Because the `validate` command exits non-zero on `UNSAFE`, you can fail a build or a deploy if a planned price change would make a plan lose money.

## How the numbers are derived

- **Blended cost** = `(ratio · input_price + output_price) / (ratio + 1)`.
- **Net fee** = `price · (1 − payment_fee − platform_fee)`.
- **Included cost** = `included_tokens_m · blended_cost`.
- **Included margin** = `(net fee − included cost) / net fee`.
- **Max safe quota** = `net fee · (1 − target_margin) / blended_cost` (millions of tokens).
- **Break-even overage** = `1.6 · blended_cost`.

All arithmetic uses `decimal.Decimal` with `ROUND_HALF_UP`; there is no float drift in money values.

## Free calculator

Don't want to install anything? The same logic runs in your browser at **<https://tokenkit.tingstudioai.com/calculator>** — paste model costs and a plan price and get the verdict with a live profit curve. No account, no data leaves the browser.

## Need the rest of the billing stack?

This library is the **pricing guard rail only** — the math that stops a plan losing money. If you also need the production billing engine around it (Stripe Metered Billing integration with idempotent MeterEvents, retries, circuit breaker, fallback queue, webhook verification, weighted model quotas, hard USD caps, rate limiting, anomaly throttling, and a JSON-lines audit log), that ships as the paid **[AI SaaS Token Billing Kit](https://tokenkit.tingstudioai.com/)**. The open-source package stays free and MIT-licensed forever.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE). Independent project; not affiliated with Stripe, OpenAI, Anthropic, DeepSeek, or Google. All trademarks belong to their respective owners. Reference prices are estimates for planning only.
