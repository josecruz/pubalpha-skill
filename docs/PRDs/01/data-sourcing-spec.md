# Data & Sourcing Spec — Public Alpha Skill

> Where every signal in the funnel comes from, what's historical vs live, and the backtest-data plan.
> Premium CMC tier assumed (full catalog + history). Companion to `technical-spec.md`.

## 1. Access paths (CMC)
- **REST Pro API** (`https://pro-api.coinmarketcap.com`, header `X-CMC_PRO_API_KEY`) — the deterministic
  data path (quotes, OHLCV, global metrics, content, community, categories). Default for the engine.
- **DEX REST API** (`/dex/*`, `/v4/dex/*`) — on-chain confirmation (liquidity, holders, buy/sell, OHLCV, security). BSC supported.
- **MCP** (`https://mcp.coinmarketcap.com/mcp`) — used inside Claude Code for exploration + the LLM's data access.
- **x402** — optional pay-per-call (V1 / special-prize signal).
Build on the official skills: `cmc-mcp` (data), `cmc-api-dex` (on-chain), `cmc-api-market` (global/F&G/community).

## 2. Funnel signal → source
| Funnel stage | Signal | Source |
|---|---|---|
| Narrative heating | sector/topic attention | CMC Community Trending Topics + Cryptocurrency categories + per-category price-performance |
| Call extraction | per-token calls (news/posts) | CMC Content (`/v1/content/latest` news+Alexandria; `/v1/content/posts/*`, engagement-tagged) |
| Call extraction | per-token calls (shows/KOLs) | **Own extractor**: YouTube transcripts of tracked shows, substack RSS, X posts |
| Call extraction | enrichment (V1) | paste.trade adapter (best-effort); LunarCrush / Santiment (historical social) |
| Organic vs coordinated | timing/language/substance/author features | computed over the above + LLM substance judgment |
| On-chain confirmation | buy/sell split, liquidity, holders | CMC DEX (`/v4/dex/spot-pairs`, `/dex/holders/*`, aux: 24h buys/sells, liquidity, security) |
| Regime gate | Fear&Greed, dominance, altseason | CMC Global Metrics + indices (CMC100/20) |
| Backtest | historical candles | CMC DEX OHLCV historical / Cryptocurrency `ohlcv/historical` (fallback: GeckoTerminal 1yr) |

## 3. Historical vs live (the backtest reality)
- **Has real history (backtest backbone):** quotes/OHLCV, Fear & Greed, BTC/ETH dominance, altcoin season,
  CMC indices, categories, price-performance. ~14 years available on premium.
- **Live-only (forward-validate or source externally):** CMC Community trending (top-5), post engagement,
  and the call layer generally. CMC Content news is paginated + dated, so a partial per-token news timeline
  can be reconstructed for backtest.
- **Plan:** backtest the deterministic backbone (regime + on-chain/price confirmation + narrative rotation)
  on real history; stack the call layer forward-validated from the build window, or use LunarCrush/Santiment
  history in V1. The Backtest Report `honesty` block states which is which.

## 4. Own content extractor (the real paste.trade-style source)
Seed with a handful of public shows/substacks/KOLs (e.g., the ones paste.trade tracks + crypto KOLs). Pull:
- **YouTube** transcripts (e.g., youtube-transcript-api) for podcasts/streams,
- **Substack/RSS** for written calls,
- **X** posts for KOL calls (within API limits).
Run the LLM to extract `CallCandidate`s (token, stance, conviction, short paraphrased evidence, timestamp).
This is robust and self-owned. Keep evidence paraphrased/short (copyright).

## 5. Rate / cost
Premium tier is generous, but still cache and tier: regime/global every few minutes; content + community per
run; on-chain per candidate; OHLCV history fetched once and cached for backtests. Keep the universe focused
(BNB-ecosystem + recognizable BSC assets) to control calls and keep the demo legible.

## 6. Forward-compat (not built now)
- **Track 1 (live):** the strategy spec could later drive a live agent via Trust Wallet Agent Kit; universe
  would collapse to the fixed 149 BEP-20 tokens and the logic shift to staying deployed — a different policy,
  same signals. Out of scope.
- **Solana / other chains:** CMC + the extractor cover other chains; repointing is a config + adapter-param
  change. The strategy spec is chain-agnostic. BNB stays the focus.
