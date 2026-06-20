# Examples — golden run

Real funnel output demonstrating the contract (`docs/PRDs/01/output-contract.md`). Generated with a
live CMC key (`python3 skills/public-alpha/scripts/run.py --symbol <SYM> --backtest`).

### `cake/` — the full funnel on a BNB-ecosystem token (organic)
CAKE classifies **organic** (0.927) from 30 calls (paste.trade + CMC community/news + seed), narrative
heating from CMC categories, on-chain **confirmed** via CMC DEX volume ($4.1M), regime **risk_off**
(F&G 21) → honest **NO ENTRY**. 180-day daily backtest: **+0.44% vs −31% buy-and-hold BNB**
(**+31.6% excess**), Sharpe 1.49. Gate: across 64 real call clusters, **3.1% coordinated**.

### `pepe/` — search ANY coin (calls sourced live from CMC)
PEPE isn't covered by the paste.trade shows, so its **27 calls come entirely from CMC community posts +
news** — proof that any CMC-listed coin is searchable. Classifies **organic** (0.925, 22 distinct
authors); backtest **−8.5% vs −31% BNB** (timing kept it out of most of the drawdown).

### `moon/` — the wedge rejecting a coordinated pump (the headline)
$MOON classifies **coordinated** (0.238): 6 calls in 38 min (clustered), near-identical copypasta
(3-gram Jaccard 1.0), 100% low-follower accounts, pure urgency — **filtered**, with reasons. This is
the differentiator: a coordinated burst vs an organically-discussed thesis.

> The classifier scores conviction 0–1 and labels organic / mixed / coordinated. Coordination is
> judged **relative** to the cluster (a burst that *dominates*, like MOON's 6/6), so large, diverse,
> organically-discussed feeds (CAKE, PEPE, BTC) read organic even with a little repost noise. The
> regime gate shows NO ENTRY for all three because the live market was risk-off (F&G 21) — an honest
> demonstration of the gate. On-chain uses CMC aggregated DEX volume (the per-pool DEX endpoint is
> rate-limited on this tier; buy/sell split + holders aren't exposed by the CMC DEX API — stated in the card).
