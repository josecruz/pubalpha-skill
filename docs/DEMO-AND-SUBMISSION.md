# Demo & Submission — runbook

Everything to record the demo and submit on DoraHacks. Pre-staged so the final hour is just
recording + clicking submit. (Judging is async/after-lock — the **repo + video are all the judges see**.)

---

## 1. The demo (60–120s, agent-driven)

**Setup:** terminal with Claude Code in this repo; CMC key in `.env`; a clean run already produced
(so `results/` exists for `--replay` fallback). Record with macOS **Cmd-Shift-5**.

**The prompt to type (the opening beat):**
> "Using the Public Alpha skill, build me a backtested swing strategy for CAKE on BNB Chain, balanced
> risk, 30-day lookback — walk me through the funnel as you go: which narratives are heating, the
> calls you found, which are organic vs coordinated, whether on-chain confirms, the regime, then emit
> the spec, card, and backtest."

**The beats (let the agent narrate from SKILL.md):**
1. **Heating** (~10s) — "CMC categories/community say <sector> is heating."
2. **Calls** (~15s) — "N calls on CAKE from paste.trade (All-In/ThreadGuy) + CMC content + seed."
3. **Organic vs coordinated** (~25s) ★ **the money shot** — show a coordinated cluster getting
   **FILTERED** (e.g. $MOON: 6 calls in 38 min, copypasta Jaccard 1.0, low-follower accounts, pure
   urgency) next to CAKE surviving as **organic** (spread over days, distinct authors, real theses).
4. **On-chain** (~12s) — "buys outpace sells, liquidity deep → confirmed" (or not).
5. **Regime** (~10s) — "Fear & Greed / dominance → risk-on."
6. **Emit** (~20s) — the 3 artifacts; the backtest headline (return vs benchmark, drawdown, win rate);
   the **% of calls filtered**; the **honesty block**.
7. **Close** (~8s) — "It reads the same public alpha you do, throws out the pumps, and only acts when
   the chain agrees."

**Fallback if live data is flaky on record day:** `python3 skills/public-alpha/scripts/run.py --replay`
— narrates the cached golden run identically, no live calls. Record this version too as insurance.

**Recording tips:** one take is fine; keep it well under any size limit; put the prompt + the three
output filenames on screen (judges skim). Don't over-produce — a clean terminal walk beats a montage.
Host unlisted on YouTube/Loom; test the link in an incognito window.

---

## 2. Make the repo public (before submitting)
The repo is currently **private** (`github.com/josecruz/cmc-hackathon`). DoraHacks needs a **public**
repo. In GitHub: Settings → General → Danger Zone → Change visibility → Public. Then confirm it opens
in an incognito window. Double-check no secrets: `.env` is gitignored; `results/` is gitignored.

---

## 3. DoraHacks submission checklist
Pre-stage all of this by ~T-3h; the form fill is ~15 min. **Aim to submit by T-2h (≈10:00 UTC Jun 21).**

- [ ] **Public repo URL:** `https://github.com/josecruz/cmc-hackathon` (verify public in incognito)
- [ ] **Demo video link** (YouTube unlisted / Loom; tested in incognito)
- [ ] **Track:** Track 2 — Strategy Skills
- [ ] **Sponsor tags:** **CoinMarketCap** (Best Use of CMC Data) — and Trust Wallet / BNB Chain if the
      form allows (the spec is BNB-ecosystem + forward-compatible with the Trust Wallet Agent Kit).
- [ ] **Cover image:** a screenshot of the funnel / Strategy Card (reuse a demo frame).
- [ ] **Title + one-liner + description** (ready to paste below).
- [ ] Submit → screenshot the confirmation → re-open the public submission page in incognito to verify
      the repo + video links resolve for an outsider.

### Ready-to-paste copy

**Title:** Public Alpha — a CoinMarketCap Strategy Skill

**One-liner:** A CMC Skill that filters crypto hype into a backtestable strategy spec — it extracts
specific token calls, separates organically-growing theses from coordinated pumps, confirms with
on-chain flow, gates by regime, and emits a transparent, backtested spec.

**Description:**
> Public Alpha is a CoinMarketCap Skill (SKILL.md + Python) that runs a five-stage funnel: narrative
> heating → call extraction → **organic-vs-coordinated classification** → on-chain confirmation →
> regime gate → a backtestable Strategy Spec + Strategy Card + Backtest Report.
>
> The edge isn't sentiment scoring — it's the wedge most tools skip: telling an organically growing
> thesis apart from a coordinated pump, then only acting when on-chain flow confirms it. The classifier
> fuses deterministic signals (timing clustering, copypasta detection, author credibility, an on-chain
> pump cross-check) with an LLM substance judgment, and outputs human-readable reasons for every verdict.
>
> CoinMarketCap data is used across the stack: community trending + categories (heating), content/news
> (calls), DEX on-chain (confirmation), global metrics + Fear & Greed (regime), and OHLCV (backtest).
> Real KOL calls come from paste.trade's public show surface; CMC content and a curated seed round out
> the call layer.
>
> The backtest is honest by design: only price/OHLCV is replayed on history; the call layer, regime and
> on-chain confirmation are forward-validated, and every report carries a mandatory honesty block.
> No live execution, no real money — this is quant research that emits a transparent, inspectable spec.
>
> Repo: github.com/josecruz/cmc-hackathon · Built on the official CMC skills pattern (cmc-mcp,
> cmc-api-dex, cmc-api-market). MIT.

**On-chain proof note (if the form asks):** No live execution — this is a research/strategy-spec Skill;
CMC DEX on-chain data is used for *signal confirmation*, not for placing trades.
