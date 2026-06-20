# PRD: Public Alpha — Track 2 CMC Strategy Skill

> **Project:** BNB Hack — AI Trading Agent Edition (CoinMarketCap × Trust Wallet × BNB Chain)
> **Author:** Solo builder, orchestrating Claude Code (non-developer)
> **Date:** 2026-06-13 · **Status:** Draft for build · **Lock:** 2026-06-21, 12:00 UTC (~8 days)
> **Track (locked):** **Track 2 — Strategy Skills** ($6k, 3 winners). Build a CMC Skill that turns
> market data into a **backtestable strategy spec**. No live execution, no real money, no live agent.
> **Special prize targeted:** **Best Use of CoinMarketCap Data & Signal** ($2k, stackable).
> **Companion docs:** `technical-spec.md` · `data-sourcing-spec.md` · `output-contract.md` ·
> `build-plan.md` · `config/default.yaml`.

---

## How the contest works (so the docs don't drift)
- **Pick ONE track** (we picked Track 2). A team may also win a panel-judged **special prize** on top.
- **Track 2 is panel-judged** on four criteria: technical execution, originality, real-world relevance, demo.
- **Deliverable:** a CMC Skill that ships a **backtestable strategy spec** — "quant research," not a live bot.
- **Submission requires:** a public repo (GitHub/GitLab/Bitbucket) + a demo video or setup instructions.
- **Using CMC Agent Hub data scores higher**; AI tooling / vibe-coding is explicitly fine.

## Problem
In crypto, attention moves before price — but most attention is noise. The naive trade ("buy what's
trending," "follow the influencer") loses money: by the time a call is loud it's often late, and a large
share of calls are coordinated promotion that pumps and dumps. Sites like paste.trade exist because the
**alpha is already public** — buried in podcasts, streams, and substacks — but it's unreadable at human
speed and indistinguishable from shilling without work.

The edge isn't "sentiment." Plenty of tools already score aggregate bullish/bearish mood and backtest it.
The edge is: **extract specific calls, separate the organic ones from the coordinated pumps, and only act
when on-chain flow confirms them** — then express that as a transparent, backtested strategy. Distinguishing
an organically growing thesis from a paid pump is, per practitioners, one of the most valuable skills in
crypto right now. No one has packaged that as a CMC Skill with a backtest. That gap is the project.

## The concept — "Public Alpha", a funnel
A CMC Skill that runs a five-stage funnel and emits a strategy spec:

1. **Narrative heating** — which sectors/narratives are gaining attention (CMC community trending topics +
   categories + per-category performance).
2. **Call extraction** — which specific tokens are being *called* in content (CMC news + community posts,
   plus our own extractor over public shows/substacks/KOLs), with stance and conviction. **← LLM-native.**
3. **Organic vs coordinated** — classify each call: a thesis growing naturally vs a coordinated burst
   (clustered timing, near-identical language, urgency, no substance). **← the headline novelty.**
4. **On-chain confirmation** — is money actually moving? (DEX buy/sell split, liquidity, holder growth.)
   Coordinated/unconfirmed calls get filtered out.
5. **Regime gate** — only take risk when Fear & Greed / dominance / altseason permit; size accordingly.

→ emit a **Strategy Spec (JSON)** + a human-readable **Strategy Card** + a **Backtest Report**. The whole
thing runs agent-driven (V0): you ask the Skill for a strategy and watch hype get filtered to a confirmed,
backtested spec. Full output shapes are in `output-contract.md`.

### Why this wins on the judged axes
- **Originality:** call-extraction + organic-vs-coordinated + on-chain confirmation as a Skill — not found elsewhere.
- **Real-world relevance:** everyone follows calls; the organic/coordinated filter is a real, sought-after edge.
- **Technical execution:** a genuine backtest, honest about what's provable (below).
- **Demo:** the funnel narrates itself — hype in, confirmed strategy out.
- **Best Use of CMC Data & Signal:** leans on community, content, on-chain, derivatives, and regime — the full stack.

## Goals & success metrics
| Goal | Metric | Target |
|------|--------|--------|
| The classifier earns its keep | % of calls filtered as coordinated/unconfirmed (reported in the backtest) | Measured & shown |
| Every strategy is transparent | Spec carries signals used, rules, thesis, confidence, and provenance | 100% |
| Demonstrable edge | Backtest vs buy-and-hold benchmark (risk-adjusted), honest about scope | Beats or clearly justified |
| Reusable artifact | Shipped as a CMC Skill (SKILL.md + scripts) that emits the spec | Shipped before lock |
| Data honesty | Backtest states which signals are historical vs forward-validated | Explicit |
| Sponsor credit | CMC data used across ≥4 families; optional Skills-Marketplace publish + x402 | Done / attempted |

**Non-goals (this submission):** no live trading/execution, no real money, no 24/7 bot, no drawdown exposure.

## Scope
**V0 — in scope (the submission):** the full funnel; CMC as the data spine + our own public-source call
extractor; the organic-vs-coordinated classifier; on-chain confirmation; regime gate; the backtest engine;
the three output artifacts; packaged as a CMC Skill; run agent-driven.

**V1 — enrichment (if time):** paste.trade adapter (best-effort), optional LunarCrush/Santiment for deeper
historical backtest, publish the Skill to the Skills Marketplace, wire one x402 data call.

**V2 — optional results dashboard:** a thin web view that renders the Skill's output (funnel, spec, equity
curve) for a stronger demo video. Strictly after V0/V1; reads the Skill's JSON, computes nothing new.

## Prize targets & fold-ins
Track 2 placement + **Best Use of CoinMarketCap Data & Signal**. Fold-ins that strengthen the special prize:
build on the official CMC skills (cmc-mcp, cmc-api-dex) rather than reinvent; publish our Skill to the
Skills Marketplace (discoverable via find_skill); optionally use x402 for a data call to show agent-native flow.

## Honest backtest plan (this protects the technical-execution score)
- **Backtestable on real history:** price/OHLCV, Fear & Greed, dominance, altseason, CMC indices, categories.
- **Live-only on CMC (forward-validated, or sourced externally):** community trending, post engagement, the call layer.
- **Plan:** build a **backtestable backbone first** — regime + on-chain/price confirmation + narrative
  rotation over real history — then stack the call layer, validated forward from the build window (or via
  LunarCrush/Santiment history in V1). The backtest report states exactly which is which. Judges reward this
  honesty over a suspiciously perfect curve.

## Version ladder
**V0 fully agentic Skill (submit this) → V1 enrichment → V2 optional dashboard.** Each layer is independently
shippable; if time runs out, the prior layer is a complete entry.

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Call layer hard to backtest | High | Med | Backtestable backbone first; forward-validate calls; honesty section |
| paste.trade unusable (no API) | High | Low | Own extractor is the real source; paste.trade is a pluggable best-effort adapter |
| Concept reads as "just sentiment" | Med | High | Lead with call-extraction + organic-vs-coordinated, not sentiment |
| Scope creep (live exec, dashboard) | Med | Med | Execution is out of scope; dashboard is optional V2 |
| Historical OHLCV access/quirks | Low (premium) | Med | Verify day 0; GeckoTerminal fallback |

## Open questions (close on day 0, cheap)
- Which public shows/substacks/KOLs to seed the extractor with, and how to pull them (YouTube transcripts, RSS, X)?
- Backtest window + benchmark (buy-and-hold BNB vs CMC100)?
- Final thresholds (call score, organic-vs-coordinated, confirmation, regime) — tune during build.
- Does the CMC DEX historical OHLCV cover the chosen BSC universe cleanly, or use GeckoTerminal?

## Timeline (summary; full breakdown in `build-plan.md`)
| Phase | Dates | Deliverable |
|-------|-------|-------------|
| V0.0 scaffold + data | Jun 13–14 | Skill skeleton, CMC data + own-extractor stub, day-0 questions closed |
| V0.1 funnel + classifier | Jun 15–16 | Call extraction + organic/coordinated + on-chain confirmation + regime |
| V0.2 backtest + spec | Jun 17–18 | Backtest engine, Strategy Spec/Card/Report output, tuning |
| V0.3 package + demo | Jun 19–20 | CMC Skill packaging, README, agentic demo recording |
| V0.4 submit | Jun 21 (pre-12:00 UTC) | Public repo + demo on DoraHacks; tag sponsors |
| V1 / V2 | as time allows | Enrichment; optional dashboard |
