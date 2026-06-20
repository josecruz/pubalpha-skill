# Examples

Sample artifacts demonstrating the output contract (`docs/PRDs/01/output-contract.md`).

- `strategy_spec.sample.json` / `strategy_card.sample.md` — a real run of the funnel on **CAKE**
  in **offline mode** (seed + paste.trade allowed surface; no CMC key). The classifier, call layer,
  spec assembly and card rendering are all live here; on-chain confirmation, the regime gate and the
  backtest show **"not available"** because those require a CMC key.

The **golden run** — the same artifacts *with* live on-chain confirmation, regime gate, and a real
30-day backtest (return vs benchmark, drawdown, win rate, the honesty block) — is produced with a
CMC key set and committed here at C3. To reproduce:

```bash
cp .env.example .env   # add CMC_PRO_API_KEY
python3 skills/public-alpha/scripts/run.py --symbol CAKE --backtest
```
