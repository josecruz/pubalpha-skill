# Build Notes — Public Alpha

Living engineering log: what's built, the key decisions, and what's pending. Kept current at each checkpoint.

## Status vs the checkpoint ladder
| CP | What | State |
|----|------|-------|
| C0 | Scaffold + protocols + config | ✅ done (live MCP/data verification pending CMC key) |
| C1 | The wedge: classifier + confirm + regime + calls + seed | ✅ done, tested offline (`tests/test_wedge.py`) |
| C2 | Strategy Spec + Card output (`strategy.py`, `render.py`, `run.py`) | ✅ done, runs on real paste.trade data |
| C3 | numpy backtest + honesty block (`backtest.py`) | ✅ engine done & tested (synthetic); **golden run pending live OHLCV** |
| C4 | SKILL.md + README + demo + submit | 🟡 SKILL.md + README done; demo + DoraHacks submit pending |

**Runs today without a key:** the classifier, the full funnel on seed + paste.trade allowed surface,
spec + card output, the backtest engine (synthetic). **Needs the CMC key:** on-chain confirmation,
regime gate, narrative heating, CMC content calls, and the real backtest/golden run.

## Data sources & the access decision
- **CMC (`scripts/sources/cmc.py`)** — the spine. Exercises community trending + categories (heating),
  content/news (calls), DEX token pools (on-chain), Fear&Greed + global metrics (regime), and
  `/v2/cryptocurrency/ohlcv/historical` (backtest — BNB/CAKE/TWT are listed, so no DEX-OHLCV needed).
  Defensive parsing (tolerant of field drift). Holder data isn't exposed by the DEX API, so
  `confirm.py` doesn't gate on it.
- **paste.trade (`scripts/sources/paste_trade.py`)** — real KOL calls (787 across all-in + threadguy).
  **Access boundary (important):** their `robots.txt` + a server-side read-gate keep the bulk corpus
  API (`/api/trades`, `/api/feed`) private and block AI crawlers (`ai-train=no`). But the operator
  *explicitly designates the two curated shows and the trades belonging to them as the public surface*,
  and that data is served under the robots-**allowed** `/api/shows/{all-in,threadguy}` prefix. We read
  ONLY that prefix; we never touch the gated bulk API or circumvent the read-gate. Content signals
  honored (we don't train). Theses are paraphrased short downstream (copyright). If the surface changes,
  the adapter returns `[]` and the funnel falls back to CMC + seed.
- **Seed (`scripts/sources/seed.py` + `fixtures/calls_seed.json`)** — curated, paraphrased, real-shaped
  calls: one organic cluster (CAKE) + one coordinated cluster ($MOON) so the wedge is demonstrable and
  deterministic offline.
- **Stubbed (V1):** `content_extractor.py` (YouTube/RSS/X — libs not installed), `social_ext.py`.

## Key technical decisions
- **pydantic v1** (installed line) — v1 syntax in `models.py`. **numpy** backtest (no pandas).
  **beautifulsoup4** available if HTML parsing is ever needed.
- **The classifier is the wedge.** Deterministic features (timing clustering, char-3gram language
  similarity, author diversity/credibility, on-chain pump cross-check) + a structured substance/language
  judgment. The judgment is normally produced by the agent (the LLM) and injected via `--judgment-file`;
  a deterministic urgency-keyword fallback keeps it runnable headless. Output carries human-readable
  `reasons` — the demo gold.
- **Honest backtest.** Only price/OHLCV is replayed on history; the entry is a disclosed EMA-momentum
  *proxy* for "a confirmed organic entry". Call layer, classification, regime and on-chain confirmation
  are live/forward-validated, stated in the mandatory `honesty` block. `gate_stats` reports the real
  filter rate from the run's call clusters.
- **The agent is the runtime.** `SKILL.md` orchestrates the Python helpers + CMC MCP and narrates the
  funnel; `run.py` is the deterministic engine.

## Verification
- `python3 skills/public-alpha/tests/test_wedge.py` — offline classifier check (CAKE organic, $MOON coordinated).
- `python3 skills/public-alpha/scripts/run.py --symbol CAKE` — full funnel (offline-capable).
- With a CMC key: on-chain/regime/narrative/backtest light up; produce + commit the golden run to `examples/`.

## Pending
1. CMC key → validate `cmc.py` live, fix any field-name drift, produce the **golden run** → commit to `examples/`.
2. Record the agent-driven demo (the funnel narrating itself; the $MOON rejection is the money shot).
3. Make the repo public; submit on DoraHacks (Track 2, tag CoinMarketCap).
4. Optional: the static dashboard (`dashboard/index.html`) over `results/*.json`.
