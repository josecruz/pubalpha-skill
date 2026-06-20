# Examples — golden run

Real funnel output demonstrating the contract (`docs/PRDs/01/output-contract.md`). Generated live with a
CMC key (`python3 skills/public-alpha/scripts/run.py --symbol <query> --backtest`). Public Alpha resolves a
query (ticker **or** company name) to a unified asset — crypto, or one of CMC's 400+ tokenized stocks across
chains — then unifies its calls (paste.trade ticker + CMC posts) and runs the full funnel.

### `tsla/` — a tokenized stock (all-asset support)
"Tesla" / "TSLA" resolves to **Tesla tokenized stock (xStock), TSLAX on Ethereum** ($11.8M 24h vol). 46 calls
(paste.trade "TSLA" + CMC posts) unify under one entity → **organic** (0.946), confirmed on DEX volume,
180-day backtest **−6.3% vs −31% buy-and-hold BNB (+24.8% excess)**. Searching a stock name works because
the resolver bridges the underlying ticker to the tradeable tokenized listing.

### `cake/` — a BNB-ecosystem crypto (full on-chain funnel)
CAKE → **organic** (0.927), 30 calls, on-chain **confirmed** via CMC DEX volume ($4.1M), regime risk_off →
NO ENTRY. Backtest **+0.44% vs −31% BNB (+31.6% excess)**. Gate: 64 clusters, 3.1% coordinated.

### `pepe/` — search any coin (calls sourced live from CMC)
PEPE isn't covered by the paste.trade shows, so its 27 calls come entirely from CMC community posts + news.
**Organic** (0.925); backtest −8.5% vs −31% BNB.

### `moon/` — the wedge rejecting a coordinated pump (the headline)
$MOON → **coordinated** (0.238): 6 calls in 38 min (clustered), copypasta (3-gram Jaccard 1.0), low-follower
accounts, pure urgency — **filtered**, with reasons.

> The classifier is asset-agnostic (it judges any asset's call pattern). Confirmation is asset-aware —
> on-chain DEX flow for crypto, market volume for tokenized stocks/others, honest "no data (pluggable)" when
> CMC doesn't track it. The regime gate shows NO ENTRY for the real assets because the live crypto market was
> risk-off (F&G 21) on the run date — an honest demo of the gate. The dashboard (`/dashboard/?run=tsla|cake|pepe|moon`)
> renders any of these.
