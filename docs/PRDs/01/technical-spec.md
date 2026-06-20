# Technical Spec — Public Alpha Skill

> The build doc for Claude Code. Companion to `prd-public-alpha.md`, `output-contract.md` (the output
> schemas), `data-sourcing-spec.md` (where data comes from), `build-plan.md` (sequence).
> **Language:** Python 3.11+ · **Deliverable:** a CMC Skill (SKILL.md + scripts) that emits a backtestable strategy spec.

---

## 1. What a CMC Skill is (so we build the right artifact)
A CMC Skill is the same construct as an LLM skill: a folder containing a `SKILL.md` (markdown instructions
telling the agent when/how to use the tools) plus supporting scripts. CMC's official repo
(github.com/openCMC/skills-for-ai-agents-by-CoinMarketCap, MIT) ships cmc-mcp, market-report, crypto-research,
cmc-api-dex, etc. — we build on those, not from scratch. Installation = copy the folder into the agent's
skills dir + configure the CMC MCP. So our deliverable is a skill folder; the agent (Claude/Claude Code)
executes it.

## 2. Architecture in one paragraph
A funnel run by the SKILL.md and backed by Python helpers: **attention** (heating narratives) → **calls**
(extracted from content, per token, with stance/conviction) → **classifier** (organic vs coordinated) →
**on-chain confirmation** (is money moving?) → **regime gate** → **strategy spec** → **backtest**. Data
sources sit behind a pluggable interface so the call feed is swappable (CMC content + our own public-source
extractor now; paste.trade / LunarCrush / Santiment later). The LLM does the language work (extracting and
classifying calls, writing the thesis); everything quantitative (confirmation, sizing, backtest) is
deterministic code. Output: the three artifacts in `output-contract.md`.

## 3. Skill folder structure (the deliverable)
```
skills/public-alpha/
├── SKILL.md                 # the LLM skill: inputs, the funnel, when to call each script, output format
├── scripts/
│   ├── sources/
│   │   ├── base.py          # AttentionSource / CallSource / MarketSource protocols
│   │   ├── cmc.py           # CMC: community trending, content (news+posts), categories, on-chain, regime
│   │   ├── content_extractor.py  # OUR extractor: YouTube transcripts / RSS / X -> raw call candidates
│   │   ├── paste_trade.py   # best-effort adapter (V1) — see §7
│   │   └── social_ext.py    # LunarCrush / Santiment adapter (V1, optional, historical)
│   ├── calls.py             # normalize call candidates -> Call objects (stance, conviction, evidence)
│   ├── classifier.py        # organic vs coordinated (THE novelty) — §5
│   ├── confirm.py           # on-chain confirmation (DEX buy/sell, liquidity, holders)
│   ├── regime.py            # RegimeState from Fear&Greed + dominance + altseason
│   ├── strategy.py          # assemble the Strategy Spec (rules/sizing/risk) from the funnel
│   ├── backtest.py          # deterministic backtest over historical candles -> Backtest Report
│   └── render.py            # Strategy Card (Markdown) + JSON writers
├── examples/                # sample Strategy Spec JSON + Strategy Card + Backtest Report
├── config/ -> ../../config/default.yaml
└── README.md
```

## 4. Source interface (pluggable — this is how paste.trade/others slot in)
```python
# scripts/sources/base.py
from typing import Protocol
from datetime import datetime

class CallCandidate(BaseModel):
    symbol: str | None        # may be unresolved; calls.py resolves to a CMC asset
    raw_text: str             # the statement (kept short / paraphrased downstream)
    author: str               # KOL / show / outlet
    source: str               # "cmc_news" | "cmc_community" | "podcast:<slug>" | "x:<handle>" | "paste_trade"
    ts: datetime
    engagement: dict          # likes/comments/views where available

class CallSource(Protocol):
    name: str
    def fetch(self, since: datetime) -> list[CallCandidate]: ...

class MarketSource(Protocol):       # quotes, OHLCV, on-chain, regime inputs (CMC)
    def quotes(self, symbols): ...
    def ohlcv(self, symbol, interval, start, end): ...
    def onchain(self, symbol): ...
    def regime(self): ...
```
Default sources: `cmc.py` (CallSource via content/community + MarketSource via everything else) and
`content_extractor.py` (CallSource over public shows/substacks/X). V1 adds `paste_trade.py` and `social_ext.py`
behind the same `CallSource` protocol. Config toggles which are active.

## 5. The organic-vs-coordinated classifier (the headline novelty)
Given the calls for a symbol over a window, classify the pattern. Signals (deterministic features + an LLM judgment):
- **Timing clustering** — many calls in a tight window (coordinated) vs spread over days (organic).
- **Language similarity** — near-identical phrasing / copypasta across authors (coordinated) vs varied, substantive (organic).
- **Substance** — thesis depth vs pure urgency ("don't miss", "1000x") — LLM scores this.
- **Author diversity & independence** — many low-history accounts at once (coordinated) vs reputable/varied (organic).
- **Cross-check vs on-chain** — price already spiking with thin liquidity (likely pump) feeds the score.
Output: `classification ∈ {organic, coordinated, mixed}` + a `score`. The strategy only enters on `organic`
(+ confirmation); `coordinated` is filtered (and is logged as a gate stat, and is itself a tradable *fade*
signal we can note). Keep features in code; use the LLM for substance/language judgment with a structured prompt.

## 6. Confirmation, regime, strategy, backtest
- **confirm.py** — pull DEX buy/sell volume split, liquidity, holder growth for the called token; `confirmed`
  if volume rising + liquidity ≥ floor + buy/sell healthy + holders not concentrated. Deterministic.
- **regime.py** — `RegimeState` from Fear&Greed + BTC dominance + altseason (thresholds in config).
- **strategy.py** — assemble the Strategy Spec (`output-contract.md §1`): entry conditions from the funnel,
  exits/SL/TP/time-stop/invalidations, sizing scaled by confidence and capped, risk limits. LLM writes `thesis`.
- **backtest.py** — replay the spec's rules over historical candles; produce the Backtest Report
  (`output-contract.md §3`) incl. the mandatory `honesty` block. Benchmark = buy-and-hold. Apply fee+slippage.

## 7. paste.trade adapter (honest)
No public API; the app loads data from a private backend. `paste_trade.py` is **best-effort enrichment**, not
a dependency: at build time, inspect the network call the app makes and, if a JSON endpoint is found, read it
behind the `CallSource` interface — clearly flagged as undocumented/fragile/possibly-ToS-bound, and off by
default. The robust path is `content_extractor.py` over the same public shows paste.trade tracks. If paste.trade
ships its waitlisted API, it drops into the same interface.

## 8. Key decisions
- **D1 — LLM only where language matters** (call extraction, organic/coordinated substance, thesis). Everything
  quantitative is deterministic. Keeps it credible and reproducible.
- **D2 — Lead with the classifier, not "sentiment."** The organic-vs-coordinated filter + on-chain confirmation is the wedge.
- **D3 — CMC is the spine.** Default sources are CMC; external feeds are optional enrichment. Protects the "CMC Skill" framing + special prize.
- **D4 — Honest backtest.** Backtestable backbone first; call layer forward-validated; `honesty` block always present.
- **D5 — Output is the contract.** Build to `output-contract.md`; the demo and any V2 dashboard just consume it.

## 9. Day-0 verifications
1. Connect CMC MCP in Claude Code; confirm field names for community/content/regime/on-chain/OHLCV.
2. Pick + test the public-content pull for the extractor (YouTube transcript lib, substack RSS, X) on 2–3 seed shows.
3. Confirm historical OHLCV reach for the BSC universe (CMC DEX OHLCV vs GeckoTerminal).
4. Confirm the CMC DEX on-chain fields used by confirm.py are populated for BSC tokens.
