# public-alpha (CMC Skill)

A CoinMarketCap Skill that follows the trades other traders are calling across social and turns them
into a backtestable strategy spec: scan calls (paste.trade KOLs + CMC community/news) → classify
**organic vs coordinated** → cross-reference CMC's crowd + confirm on-chain → gate by regime → emit
Spec + Card + Backtest.

- **Run it:** `python3 scripts/run.py --symbol CAKE --backtest`
- **The agent's runbook:** [`SKILL.md`](SKILL.md)
- **Wedge self-test:** `python3 tests/test_wedge.py`
- **Full project README + the edge, data-access notes, and CMC-data matrix:** [`../../README.md`](../../README.md)
- **Output schemas:** [`../../docs/PRDs/01/output-contract.md`](../../docs/PRDs/01/output-contract.md)

Install into an agent's skills dir and configure the CMC MCP / `CMC_PRO_API_KEY`. MIT licensed.
