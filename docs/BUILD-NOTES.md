# Build Notes — Public Alpha

Living engineering log: what's built, the key decisions, and what's pending. Kept current at each checkpoint.

## Status vs the checkpoint ladder
| CP | What | State |
|----|------|-------|
| C0 | Scaffold + protocols + config | ✅ done; CMC client live-validated |
| C1 | The wedge: classifier + confirm + regime + calls + seed | ✅ done, tested (`tests/test_wedge.py`) |
| C2 | Strategy Spec + Card output (`strategy.py`, `render.py`, `run.py`) | ✅ done, runs on real data |
| C3 | numpy backtest + honesty block + **golden run** | ✅ done; live golden run in `examples/` |
| C4 | SKILL.md + README + dashboard + demo + submit | 🟡 SKILL.md + README + dashboard done; **demo video + DoraHacks submit pending** |

**Live golden run** (`examples/cake` + `examples/moon`) produced with a CMC key: classifier, calls
(paste.trade + CMC + seed), on-chain confirmation (CMC aggregated DEX volume), regime gate, and a
180-day daily backtest (+31.6% excess vs buy-and-hold BNB). The optional `dashboard/index.html`
renders it. Remaining: record the demo video and submit on DoraHacks (after making the repo public).

## Data sources & the access decision
- **CMC (`scripts/sources/cmc.py`)** — the spine. Exercises community trending + categories (heating),
  content/news (calls), DEX token pools (on-chain), Fear&Greed + global metrics (regime), and
  `/v2/cryptocurrency/ohlcv/historical` (backtest — BNB/CAKE/TWT are listed, so no DEX-OHLCV needed).
  Defensive parsing (tolerant of field drift). Holder data isn't exposed by the DEX API, so
  `confirm.py` doesn't gate on it.
- **paste.trade (`scripts/sources/paste_trade.py`)** — real KOL calls (~4,500 across ~36 shows: podcasts,
  newsletters, and an aggregate Tweets/X feed), with traders **cross-referenced across shows**.
  **Access boundary (important):** their `robots.txt` declares the public surface explicitly —
  `Allow: /api/shows` (the show index *and* each show's trades/sources), `Allow: /api/prices /api/og/
  /api/avatars/` — while `Disallow`ing the gated bulk corpus API (`/api/trades`, `/api/feed`,
  `/api/sources`, `/api/leaderboard`, `/api/users`, `/api/asset`, `/api/news`, `/api/search`, …). We
  discover shows from the allowed `/api/shows` index and read ONLY `/api/shows/<slug>`; `_assert_allowed()`
  hard-blocks every `Disallow`ed prefix so the adapter can never reach the gated corpus, even by bug. We
  never circumvent the read-gate. Content signals honored (`ai-train=no` — we don't train). Theses are
  paraphrased short downstream (copyright). If the index/surface changes, the adapter falls back to the two
  seed shows (or `[]`) and the funnel keeps running on CMC + seed.
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
1. Record the agent-driven demo (the funnel narrating itself; the $MOON rejection is the money shot).
   Script + checklist in `docs/DEMO-AND-SUBMISSION.md`.
2. Make the repo **public**; submit on DoraHacks (Track 2, tag CoinMarketCap).
3. (Optional) connect the CMC MCP for live demo narration.

Done since last: CMC client live-validated, golden run committed, dashboard built.
