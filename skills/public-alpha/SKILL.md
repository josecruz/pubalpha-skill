---
name: public-alpha
description: |
  Turns crypto attention into a backtestable strategy spec. Extracts specific token CALLS from
  public content, classifies each cluster as organically growing vs a coordinated pump, confirms
  with on-chain flow, gates by market regime, and emits a Strategy Spec (JSON) + Strategy Card
  (Markdown) + Backtest Report (JSON). Quant research — no live execution, no real money.
  Use when the user wants a transparent, evidence-backed trading strategy from market + social +
  on-chain data, or wants to know whether a token's hype is organic or coordinated.
  Trigger: "build a strategy", "is this call organic or a pump", "public alpha", "backtest a
  narrative", "should I trust this call", "/public-alpha"
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - mcp__cmc-mcp__search_cryptos
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_crypto_latest_news
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__trending_crypto_narratives
  - mcp__cmc-mcp__get_crypto_metrics
---

# Public Alpha — CMC Strategy Skill

You filter crypto hype into a confirmed, backtested strategy spec. The funnel below does the work;
**your job is to run it and narrate it** — and the narration *is* the product. The single most
important thing you do is **announce what gets filtered and why** (the coordinated pumps, the
unconfirmed calls). That rejection is the whole point of the tool.

The LLM (you) does the language work — judging call substance/language and writing the thesis.
Everything quantitative (the deterministic features, on-chain confirmation, sizing, backtest) is
Python, so it's reproducible. CoinMarketCap is the data spine.

## Prerequisites
- `skills/public-alpha/.env` has `CMC_PRO_API_KEY` (paid tier). Optional `PASTE_TRADE_TOKEN`.
- `pip install -r requirements.txt` (pydantic v1, numpy, requests, PyYAML, beautifulsoup4).
- Without a CMC key the funnel still runs on the seed + paste.trade allowed surface; on-chain,
  regime, narrative and the backtest will report "not available".

## Inputs (from the user's request; fall back to config/default.yaml)
- `symbol` (e.g. CAKE) or a small `universe`; `risk_profile` (conservative|balanced|aggressive);
  `lookback` days; `horizon`.
- **Any CMC-listed coin works** — the searched coin's calls are pulled live from CMC community posts +
  news (`calls_for`), plus paste.trade's shows + the seed where they cover it. So you're not limited to
  a fixed list; `--symbol PEPE`, `--symbol SOL`, etc. all resolve.

## The funnel — run it, then narrate each stage IN ORDER

The whole funnel is one command. Run it, then walk the user through the Strategy Card it writes:

```bash
python3 skills/public-alpha/scripts/run.py --symbol CAKE --risk balanced --backtest
```

Then read `skills/public-alpha/results/strategy_card.md` and narrate, stage by stage:

| # | Stage | What it uses | What to say to the user |
|---|-------|--------------|-------------------------|
| 1 | **Narrative heating** | CMC categories + community trending | "Which sectors are heating, and why I'm hunting calls there." |
| 2 | **Call extraction** | paste.trade allowed surface + CMC content + seed | "How many calls on the token, from which sources/authors." |
| 3 | **Organic vs coordinated** ★ | `classifier.py` | **The money shot.** State the verdict AND the deciding `reasons` (clustered timing? copypasta? low-credibility authors? pure urgency?). **Announce what you FILTER and why.** |
| 4 | **Confirmation** (asset-aware) | CMC DEX pools (crypto) → DEX volume → market volume (any asset) | "Is money actually moving? On-chain liquidity/flow for crypto, market volume for other assets — confirmed or not." |
| 5 | **Regime gate** | CMC Fear & Greed + global metrics | "Is the macro backdrop risk-on? Size accordingly." |
| → | **Emit** | `strategy.py` + `backtest.py` + `render.py` | Summarize the spec verdict (ENTRY / NO ENTRY), the backtest headline (return vs benchmark, drawdown, win rate), the **% of calls filtered**, and the **honesty block**. |

The three artifacts land in `skills/public-alpha/results/`: `strategy_spec.json`, `strategy_card.md`,
`backtest_*.json`. Echo the card; offer the JSON.

## Optional enrichment (you, the LLM, doing the language work)
For a richer Stage 3, before the run you may judge the calls yourself instead of using the
deterministic fallback:
1. Read the token's calls (run with `--sources paste_trade,seed,cmc` and inspect, or read the seed).
2. Produce a JSON judgment per symbol and write it to a temp file:
   `{"CAKE": {"substance_score": 0.0-1.0, "urgency_flags": ["..."], "language_verdict": "varied|templated|identical", "rationale": "<=2 sentences"}}`
   Feed only short paraphrases (≤15 words) — never long verbatim quotes (copyright).
3. Write a one-paragraph `thesis` per symbol to another JSON file: `{"CAKE": "..."}`.
4. Re-run with `--judgment-file <path> --thesis-file <path>`. The Python fuses your judgment with the
   deterministic features; you then narrate the result.

## Replay (demo fallback)
`python3 skills/public-alpha/scripts/run.py --replay` narrates the cached run in `results/` without
any live calls — use this if live data is flaky during a demo.

## Narration rules (the legibility layer)
- Always say WHAT you filtered and WHY — the rejections sell the tool.
- End with the % of calls filtered as coordinated/unconfirmed, and the honesty block
  (what's backtested on real history vs forward-validated).
- Keep evidence paraphrased and short (copyright).
- Never present the spec's rules as opaque — they're inspectable strings a judge can read.

## How CoinMarketCap data is used
Community trending + categories (narrative heating) · Content/news (call extraction) · DEX on-chain
(confirmation) · Global metrics + Fear & Greed (regime) · OHLCV historical (backtest). Breadth is
deliberate — this is a full-stack use of CMC data.

## Output contract
The three artifacts follow `docs/PRDs/01/output-contract.md`. The optional dashboard and any reuse
consume exactly those files — do not improvise the schema.
