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
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
  - mcp__cmc-mcp__search_crypto_info
---

# Public Alpha — CMC Strategy Skill

You filter crypto hype into a confirmed, backtested strategy spec. The funnel below does the work;
**your job is to run it and narrate it** — and the narration *is* the product. The single most
important thing you do is **announce what gets filtered and why** (the coordinated pumps, the
unconfirmed calls). That rejection is the whole point of the tool.

The LLM (you) does the language work — judging call substance/language and writing the thesis.
Everything quantitative (the deterministic features, on-chain confirmation, sizing, backtest) is
Python, so it's reproducible. CoinMarketCap is the data spine.

## Two ways to use it
- **Scanner (navigable TUI) — the fast way in.** `./skills/public-alpha/scan` sweeps the whole call
  universe and opens a terminal UI: a **Signals** feed (every asset being called, ranked by volume,
  with the organic/coordinated verdict color-coded) and a **Trade Ideas** view (the confirmed,
  ready-to-act subset with a gate scoreboard). The top bar carries the regime + **market-wide 24h
  liquidations**. ↑↓ navigate · Enter = detail (the calls + reasons + confirmation + **leverage &
  liquidations** + **CMC community** pulse) · 1/2 tabs · r rescan · q quit. Under the hood: `scan.py` → `results/scan.json` →
  `scan_tui.py` (Textual). Use this to spot what's bubbling up.
- **Deep dive (single asset).** The funnel below, for one asset, emits the Spec + Card + Backtest.

## Prerequisites
- `skills/public-alpha/.env` has `CMC_PRO_API_KEY` (paid tier). Optional `PASTE_TRADE_TOKEN`.
- `pip install -r requirements.txt` (pydantic v1, numpy, requests, PyYAML, beautifulsoup4).
- Without a CMC key the funnel still runs on the seed + paste.trade allowed surface; on-chain,
  regime, narrative and the backtest will report "not available".

## Inputs (from the user's request; fall back to config/default.yaml)
- `symbol` (e.g. CAKE) or a small `universe`; `risk_profile` (conservative|balanced|aggressive);
  `lookback` days; `horizon`.
- **Any asset works** — pass a ticker OR a company name. `resolve()` maps it to a unified entity: a
  crypto, or one of CMC's 400+ **tokenized stocks across chains** (xStock `<T>X`, Ondo `<T>on`, bStocks
  `<T>B` on Ethereum/Solana/BNB). It then unifies the calls under every alias (the underlying ticker from
  paste.trade + CMC community posts/news) and uses the highest-volume tradeable listing for confirmation +
  backtest. So `--symbol TSLA`, `--symbol micron`, `--symbol PEPE`, `--symbol SOL` all resolve.

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
Community trending + categories (narrative heating) · Content/news + per-coin community posts (call
extraction) · DEX on-chain pools + aggregated DEX volume (confirmation) · Global metrics + Fear & Greed
+ **real Altcoin Season Index** (regime) · OHLCV historical (backtest + breakout) · **derivatives perp
funding / open interest** (perp breakout screen) · **liquidations** (market-wide + per-asset long/short,
via CMC's liquidations dashboard) · **community pulse** (top posts + news articles per asset, for display).
Per-asset liquidations are fused with perp funding into a **leverage read** (`decide.leverage_read` —
short-squeeze vs long-cascade). Breadth is deliberate — a full-stack use of CMC data.

**Attention cross-reference (the scanner's edge).** The scanner also asks *does CMC's own crowd
corroborate the KOL calls?* — cross-referencing every called symbol against CMC `trending/most-visited`,
`trending/gainers-losers`, and `community/trending/token`. Calls that are **corroborated** (also trending
on CMC) are the strongest; **KOL-only** = unconfirmed hype; **CMC-only** = trending but nobody's calling
(under-called, a watch list). Each asset is further enriched with `cryptocurrency/info` (logo, tags, age
+ "NEW" flag, provenance links), `price-performance-stats` (ATH, % from ATH, ROI ladder), and
`market-pairs` (top spot venues). These feed the web dashboard's **Market Intel** page + per-asset thesis.

For the agent's narration path you may also reach for MCP `get_crypto_technical_analysis` (RSI/MACD/SMA),
`get_global_crypto_derivatives_metrics` (leverage/funding/ETF flows), and `search_crypto_info` (semantic
search over whitepapers/docs) — exploratory color on top of the deterministic REST spine.

## Decision skills (CMC Skill Hub)
Beyond the funnel, the scanner runs three **decision skills** that mirror CMC Skill Hub marketplace
pipelines — re-implemented natively over the data above (deterministic; see `scripts/decide.py`). They
power the web **Setups** page + the per-asset thesis, and are **forward screens, not backtested entries**:

| Skill Hub pipeline | native equivalent | what it surfaces |
|---|---|---|
| `altcoin_kol_sentiment` | `decide.kol_sentiment` | net KOL sentiment (bull−bear, conviction-weighted, **down-weighted when coordinated**) |
| `scan_spot_altcoin_breakout_with_social_confirmation` | `decide.spot_breakout` | 20-day-high (Donchian) breakout + volume/ATR + **organic social confirmation** |
| `screen_perp_breakout_candidates` | `decide.perp_breakout` + `cmc.derivatives` | perp funding / open interest (major venues) + breakout → long/short bias |

**Adapter — calling the real Skill Hub.** If the marketplace MCP is connected, the agent can call the live
skills instead of (or to cross-check) the native ones:
```json
{ "mcpServers": { "cmc-skills": { "url": "https://<skill-hub-mcp-endpoint>",
  "headers": { "X-CMC-MCP-API-KEY": "your-api-key" } } } }
```
Protocol: `find_skill(query="screen_perp_breakout_candidates")` → read `skill_description` + `input_schema`
→ `execute_skill(unique_name, params)` with params built from the schema (pass a JSON object, never a
JSON-encoded string; e.g. `{universe:["BTC","ETH"], venue:"Binance", timeframe:"4h"}`). If a required param
is missing, **ask — do not fabricate**; on failure, give the reason + 1–2 alternative skills, **don't
silently retry**. The Skill Hub is **not required** — the native `decide.py` skills run regardless.

## paste.trade browser (streams · streamers · calls)
The calls come from paste.trade shows; you can browse the source the same way the web does.
`scripts/paste_browse.py` builds `results/paste.json` (the operator's allowed public surface — the
`threadguy`/`all-in` shows — with a CMC-derived, collision-guarded since-call % where the ticker resolves)
and exposes a CLI so **you have the same streamer/stream/call info as the web**:

```bash
python3 skills/public-alpha/scripts/paste_browse.py            # (re)build results/paste.json
python3 skills/public-alpha/scripts/paste_browse.py --shows    # threadguy (twitch) · all-in (youtube)
python3 skills/public-alpha/scripts/paste_browse.py --list [--show threadguy]   # episodes
python3 skills/public-alpha/scripts/paste_browse.py --stream <id>   # an episode's calls (ts · ticker · dir · entry · since%)
python3 skills/public-alpha/scripts/paste_browse.py --speakers      # top speakers (calls · L/S · verified)
python3 skills/public-alpha/scripts/paste_browse.py --speaker <handle>   # one speaker's calls
```

Use it to answer "what did ThreadGuy call on the latest stream", "show chamath's calls", or to trace a
feed mention back to its stream. The web mirrors this at `/streams`, `/stream?id=`, `/speaker?handle=`.
Content is paste.trade's and **always shown with attribution + a link back to the show + source video**.

## Output contract
The three artifacts follow `docs/PRDs/01/output-contract.md`. The optional dashboard and any reuse
consume exactly those files — do not improvise the schema.
