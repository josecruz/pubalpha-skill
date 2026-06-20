# Build Plan — Public Alpha (Track 2)

> Companion to `prd-public-alpha.md`, `technical-spec.md`, `output-contract.md`, `data-sourcing-spec.md`.
> **Today:** 2026-06-13 · **Lock:** 2026-06-21 12:00 UTC (~8 days) · **Track 2, panel-judged.**
>
> Ladder: **V0 fully agentic Skill (the submission) → V1 enrichment → V2 optional dashboard.**
> Each layer is independently shippable. Build the deterministic backbone before the call layer so the
> backtest stays credible no matter how time goes.

## How to drive with Claude Code
Point it at all five docs. Build to the schemas in `output-contract.md` — that's the contract. The LLM does
language work only (call extraction, organic/coordinated substance, thesis); everything quantitative is
deterministic code. "DoD" = Definition of Done.

---

# V0 — Fully Agentic Skill (the submission)

### V0.0 — Scaffold + data · Jun 13–14
- [ ] Day-0 verifications (`technical-spec.md §9`): CMC MCP field names; test public-content pull on 2–3 seed
      shows; confirm historical OHLCV reach for the BSC universe; confirm DEX on-chain fields populated.
- [ ] Scaffold `skills/public-alpha/` (`technical-spec.md §3`); implement `sources/base.py` protocols + types.
- [ ] `sources/cmc.py`: community trending, content (news+posts), categories, regime inputs, on-chain, OHLCV (real data).
- [ ] `config/default.yaml` loaded; `render.py` JSON/Markdown writers stubbed.

**DoD:** the Skill can pull live CMC data + a first batch of public-content call candidates, and write a stub spec.

### V0.1 — Funnel + the classifier · Jun 15–16
- [ ] `content_extractor.py`: YouTube transcripts / RSS / X → `CallCandidate`s on the seed sources.
- [ ] `calls.py`: normalize + resolve to CMC assets; stance + conviction + short paraphrased evidence.
- [ ] `classifier.py`: **organic vs coordinated** (timing, language, substance, author diversity, on-chain cross-check) — the novelty.
- [ ] `confirm.py`: on-chain confirmation (buy/sell split, liquidity, holders).
- [ ] `regime.py`: RegimeState from Fear&Greed + dominance + altseason.

**DoD:** for a token, the Skill produces calls, an organic/coordinated verdict with reasons, a confirmation verdict, and the regime.

### V0.2 — Backtest + spec output · Jun 17–18
- [ ] `strategy.py`: assemble the Strategy Spec (entry/exit/SL/TP/sizing/risk) from the funnel; LLM writes the thesis.
- [ ] `backtest.py`: replay rules over historical candles → Backtest Report incl. the mandatory `honesty` block; benchmark + fees/slippage.
- [ ] `render.py`: Strategy Card (Markdown) + JSON spec + report to `results/`; add `examples/`.
- [ ] Tune thresholds; record gate stats (% calls filtered coordinated/unconfirmed).

**DoD:** all three artifacts in `output-contract.md` are produced from real data and reproducible from the repo.

### V0.3 — Package as a CMC Skill + demo · Jun 19–20
- [ ] Write `SKILL.md` (inputs, the funnel, when to call each script, output format) so the agent runs it end-to-end.
- [ ] README: the edge (call-extraction + organic/coordinated + confirmation), how to run, how CMC data is used.
- [ ] Agentic demo recording: prompt → agent narrates the funnel (heating narrative → calls → organic/coordinated → on-chain → regime) → emits Card + Spec + Backtest.

**DoD:** a clean agent-driven demo end to end; repo reproducible; tests green.

### V0.4 — Submit · Jun 21 (before 12:00 UTC)
- [ ] Confirm exact submission fields on DoraHacks (public repo + demo link/video).
- [ ] Submit under Track 2; tag CoinMarketCap for **Best Use of CMC Data & Signal**.

**DoD:** submission accepted before the lock.

---

# V1 — Enrichment (if time)
- [ ] `paste_trade.py`: best-effort adapter (inspect their private endpoint at build time; off by default; caveated) — `technical-spec.md §7`.
- [ ] `social_ext.py`: LunarCrush / Santiment for **historical** social → lets the call layer be backtested properly (strengthens the backtest).
- [ ] Publish the Skill to the CMC Skills Marketplace (discoverable via find_skill) — direct "Best Use of CMC" signal.
- [ ] Wire one x402 data call to show agent-native flow.

# V2 — Optional results dashboard (only after V0/V1)
- [ ] Thin **web** view that loads `results/*.json` and renders: the funnel (hype → filtered → confirmed),
      the Strategy Card, and the backtest equity curve + metrics. Reads the Skill's output; computes nothing new.
- [ ] (Alternative: a terminal view via OpenTUI if a CLI aesthetic is preferred — but web renders the equity-curve charts better, and the Skill is Python while OpenTUI is TS.)

**DoD (V2):** a 60–90s screen capture of the dashboard for the demo video. If unfinished, cut it — V0 stands alone.

---

## Critical-path notes
- Build the **deterministic backbone** (regime + confirmation + narrative rotation, all backtestable) before the call layer.
- The **classifier is the differentiator** — give it real care; it's what makes this not "just sentiment."
- The **`honesty` block** in the backtest is non-negotiable; it's what makes the panel trust the number.
- Don't build live execution or the dashboard until the Skill + backtest are done. V0 is the submission.
