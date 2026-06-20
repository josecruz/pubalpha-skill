# Output Contract — Public Alpha Skill

> The Skill produces three artifacts every run. This is the load-bearing interface: the V2 dashboard,
> the demo, and any reuse all consume these. Companion to `prd-public-alpha.md` and `technical-spec.md`.

The Skill takes inputs — `universe` (BSC assets or a set), `risk_profile` (conservative/balanced/aggressive),
`horizon`, `lookback` — and emits: (1) a **Strategy Spec (JSON)**, (2) a **Strategy Card (Markdown)**,
(3) a **Backtest Report (JSON + chart data)**.

## 1. Strategy Spec (JSON) — the Track 2 "backtestable spec"
```jsonc
{
  "strategy": {
    "name": "ai-narrative-organic-momentum",
    "version": "1.0",
    "generated_at": "2026-06-19T12:00:00Z",
    "universe": { "chain": "bsc", "assets": ["BNB", "CAKE", "TWT"] },
    "risk_profile": "balanced", "horizon": "swing/days", "lookback": "30d"
  },
  "signals": {
    "narrative": { "sector": "AI agents", "heating": true,
                   "source": "cmc_community_topics+categories" },
    "calls": {                                   // the novelty layer
      "score": 0.72,                             // 0..1 conviction
      "classification": "organic",               // organic | coordinated | mixed
      "sources": ["cmc_news", "cmc_community", "podcast:forward-guidance", "x:<kol>"],
      "evidence": [
        { "source": "podcast:forward-guidance", "ts": "2026-06-17T...",
          "stance": "bullish", "summary": "<=15-word paraphrase", "weight": 0.4 }
      ]
    },
    "onchain_confirmation": { "confirmed": true, "buy_sell_ratio": 1.8,
                              "liquidity_usd": 250000, "holder_growth_pct": 6.5 },
    "regime": { "state": "risk_on", "fear_greed": 62, "btc_dominance": 54.1, "altseason": 38 }
  },
  "rules": {
    "entry": [
      "narrative.heating == true",
      "calls.score > 0.6 AND calls.classification == 'organic'",
      "onchain_confirmation.confirmed == true",
      "regime.state in ['risk_on','neutral']",
      "not exhausted (price runup < max_runup_pct over lookback)"
    ],
    "exit": {
      "stop_loss_pct": -8, "take_profit_pct": 25, "time_stop": "72h",
      "invalidations": ["calls.classification -> coordinated",
                        "onchain distribution (buy_sell_ratio < 0.8)",
                        "attention fades AND price breaks entry"]
    },
    "position_sizing": { "base_pct": 3, "confidence_scaled": true, "max_position_pct": 10 },
    "risk_limits": { "max_total_exposure_pct": 50, "max_drawdown_guard_pct": 20 }
  },
  "thesis": "Human-readable rationale written by the LLM.",
  "confidence": 0.68,
  "backtest_ref": "results/backtest_2026-05-20_2026-06-19.json"
}
```
Rules are expressed as explicit, inspectable conditions (strings the backtester parses, or a small typed
rule object) — never opaque model output. A judge can read exactly why a trade fires and what kills it.

## 2. Strategy Card (Markdown) — what a judge skims
A one-screen rendering of the spec: name + thesis; the funnel evidence (heating narrative → calls found →
organic vs coordinated with the deciding signals → on-chain verdict → regime); the entry/exit/sizing rules;
and the backtest headline (return vs benchmark, max drawdown, win rate, % calls filtered).

## 3. Backtest Report (JSON + chart data)
```jsonc
{
  "window": { "start": "2026-05-20", "end": "2026-06-19", "interval": "1h" },
  "benchmark": "buy_and_hold_BNB",
  "metrics": {
    "total_return_pct": 14.2, "benchmark_return_pct": 5.1, "excess_pct": 9.1,
    "max_drawdown_pct": -11.3, "sharpe": 1.4, "sortino": 1.9,
    "win_rate_pct": 58, "num_trades": 24, "avg_hold_hours": 31, "profit_factor": 1.7
  },
  "gate_stats": { "calls_seen": 140, "filtered_coordinated_pct": 38,
                  "filtered_unconfirmed_pct": 22, "entries_taken": 24 },
  "equity_curve": [ { "ts": "...", "equity": 1.0 }, { "ts": "...", "equity": 1.03 } ],
  "trade_log": [ { "symbol": "...", "entry_ts": "...", "exit_ts": "...",
                   "pnl_pct": 0.0, "exit_reason": "take_profit" } ],
  "honesty": {
    "backtested_on_history": ["price/ohlcv", "fear_greed", "dominance", "altseason", "categories"],
    "forward_validated_or_proxied": ["call extraction", "community trending", "post engagement"],
    "assumptions": { "fee_pct": 0.25, "slippage_pct": 0.3 }
  }
}
```
The `honesty` block is mandatory — it is what makes the backtest credible to the panel.

## Notes
- All three artifacts are written to `results/` and echoed by the agent in the demo.
- Copyright: `evidence[].summary` must be a short paraphrase (never long verbatim quotes from content).
- The V2 dashboard (if built) loads exactly these files and renders them — no recomputation.
