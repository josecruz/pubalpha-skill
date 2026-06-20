# Examples — golden run

Real funnel output demonstrating the contract (`docs/PRDs/01/output-contract.md`). Generated with a
live CMC key (`python3 skills/public-alpha/scripts/run.py --symbol <SYM> --backtest`).

### `cake/` — the full funnel (organic, confirmed, backtested)
`strategy_spec.json` · `strategy_card.md` · `backtest_*.json`. CAKE's calls classify **organic**
(0.965), narrative heating from CMC categories, on-chain **confirmed** via CMC aggregated DEX volume
($3.7M), regime gate **risk_off** (Fear & Greed 20) → the Skill honestly returns **NO ENTRY** (it
won't size into a fear market). The 180-day daily backtest returns **+0.44% vs −31% buy-and-hold BNB**
(**+31.6% excess**) by staying out of the downtrend — Sharpe 1.49. Gate stats: across 72 real call
clusters, **9.7% coordinated**, 68% organic, 22% mixed.

### `moon/` — the wedge rejecting a coordinated pump (the headline)
`strategy_spec.json` · `strategy_card.md`. $MOON classifies **coordinated** (0.238): 6 calls in 38 min
(clustered), near-identical copypasta (3-gram Jaccard 1.0), 100% low-follower accounts, pure urgency
("100x", "ape", "don't miss") — **filtered out**, with human-readable reasons. This is the
differentiator: telling a coordinated burst apart from an organic thesis.

> Note on the regime gate: both show NO ENTRY because the live market was risk-off (F&G 20) on the run
> date — an honest demonstration of the gate doing its job. The classifier + backtest are independent
> of it. On-chain uses CMC aggregated DEX volume because the per-pool DEX endpoint is rate-limited on
> this tier; buy/sell split and holders aren't exposed by the CMC DEX API (stated transparently in the card).
