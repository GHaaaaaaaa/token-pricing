# Publishing & launch checklist — token-pricing

Internal guide. Everything below is free and takes ~30 minutes the first time.

## 1. Create the GitHub repo

1. github.com → **New repository**
2. Name: `token-pricing` · Description: `Token economics for AI products — blended cost, profitable-plan validation (SAFE/UNSAFE), max safe quota. Zero deps.`
3. Public · Add license is NOT needed (LICENSE already included) · do **not** add a README (one already exists)
4. Push the contents of this folder (the folder that contains `pyproject.toml`).

```bash
cd token-pricing
git init -b main
git add .
git commit -m "feat: token economics core — blended cost, plan validation, CLI"
git remote add origin https://github.com/tingstudio/token-pricing.git
git push -u origin main
```

5. Repo → **Settings → General → Topics**, add:
   `llm, pricing, ai, saas, usage-based-billing, metered-billing, openai, anthropic, stripe, token, llm-cost, fintech, cli, pypi`
6. Repo → About gear → set Homepage to `https://tokenkit.tingstudioai.com/calculator`.

## 2. Publish to PyPI (recommended: trusted publisher, no token to manage)

First release only:

1. Create the project slot: log into <https://pypi.org> → **Your projects → Publish a new project** isn't needed; instead go to **Publishing** (or the project's Publishing settings after a first OIDC publish). The clean first-time flow:
   - PyPI → Account settings → **Publishing** → Add a new pending publisher:
     - PyPI Project Name: `token-pricing`
     - Owner: `tingstudio` · Repository name: `token-pricing`
     - Workflow name: `release.yml` · Environment name: `pypi`
2. In GitHub: **Settings → Environments → New environment → `pypi`** (leave no protectors, or restrict to yourself).
3. Create `.github/workflows/release.yml` (see snippet below), push, then cut a release:
   - GitHub → **Releases → Draft a new release** → tag `v0.1.0` → title `0.1.0` → Publish.
   - The workflow builds and uploads to PyPI automatically via OIDC.

```yaml
name: release
on:
  release:
    types: [published]
jobs:
  pypi:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python -m pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

(Alternative manual route: `python -m build && twine upload dist/*` with an API token — works but trusted publishing is safer.)

After release, verify: `pip install token-pricing` in a fresh environment.

## 3. Submit to discovery lists (the part that actually drives installs)

Open one pull request / issue per list. Keep the description factual; these curators
reject marketing tone.

### awesome lists (GitHub PRs)

- **awesome-stripe** — add under a "Libraries / Billing tools" heading.
- **awesome-llm-apps** / **awesome-llmops** — under cost / pricing / billing.
- **awesome-python** — under a suitable "Financial" or "Hardware-of-business" list if scoped.
- **awesome-indie** / **awesome-saas** — pricing/billing category if present.

PR description template:

> Adds `token-pricing` — a zero-dependency Python library for AI SaaS token economics: blended input/output token cost, a `validate_plan()` guard rail returning SAFE/WARNING/UNSAFE with max safe included quota and overage break-even price, Decimal money math, plus a CLI whose exit code is usable in CI. MIT, tested on 3.8–3.12. PyPI: https://pypi.org/project/token-pricing/

### package directories (web forms, ~2 min each, long-tail SEO)

- PyPI (primary) · libraries.io auto-detects from PyPI
- Snyk Advisor · Openbase · Awesome PyPI mirrors
- Toolify / Futurepedia-style AI tool directories → submit the **calculator URL**
  (https://tokenkit.tingstudioai.com/calculator), category "Developer / Pricing"
- AlternativeTo / SaaSHub → "free alternative to spreadsheet pricing math", link repo + calculator
- Reddit (ONLY from an aged, warmed-up personal account, comment-first for weeks):
  r/Python "Share your project" monthly megathread; r/SaaS and r/SideProject
  discussion threads where someone is actively asking about AI pricing — answer
  the question and link the calculator, not the repo.

## 4. Launch posts (post PyPI is live and CI badge is green)

### Hacker News (Show HN)

Title: `Show HN: token-pricing – check that your AI SaaS plan can't lose money (Python)`
Body:

> I kept seeing AI wrappers price "$19/mo includes 10M tokens" without doing the cost math, and then quietly lose money on their heaviest users. This is a small zero-dependency library that computes blended input/output token cost, validates a plan as SAFE/WARNING/UNSAFE after payment and platform fees, returns the max quota you can safely include, and prices overage at >= 1.6x cost. Money math is Decimal; the CLI exits non-zero on UNSAFE so you can fail a deploy on a bad price change. MIT, no business model for the library itself. Free browser version for non-coders: https://tokenkit.tingstudioai.com/calculator — feedback welcome especially on the fee defaults.

### X / LinkedIn (build-in-public framing, not an ad)

> I shipped a tiny open-source library because too many AI wrappers price "$19 = 10M tokens" and lose money on power users without realising.

`pip install token-pricing` → blended cost, SAFE/UNSAFE verdict, max safe quota, overage break-even. Zero deps, Decimal math, CLI fails CI on a money-losing plan.

Free no-install version + how it works ↓
[calculator link]

### Dev.to / own blog (SEO long-tail)

Title: `Pricing AI tokens without losing money: the math behind a $19 plan`
Structure: the three ways plans lose money → the formulas (same as README "How the numbers are derived") → show the library → show the calculator. Reuse the existing token-billing article and cross-link.

## 5. Funnel wiring (already done in code, verify after launch)

- Repo README top + bottom → calculator and Kit.
- PyPI project links → Homepage (Kit), Free Calculator, Repository.
- Calculator page CTA → Kit checkout.
- After first real users: add a USAGE note / examples from their questions,
  and ask 2–3 who got value for a GitHub star or a one-line quote.

## Versioning

Bump `version` in `pyproject.toml` and `__init__.py` together, then cut a new
GitHub Release tag (`v0.1.1`, …) — the workflow publishes automatically.
