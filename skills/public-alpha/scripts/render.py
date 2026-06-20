"""Writers for the three output-contract artifacts + a console funnel trace.

Strategy Spec (JSON), Strategy Card (Markdown), Backtest Report (JSON) all land in
results/. The card is a one-screen rendering a judge can skim. Nothing here computes
strategy logic — it only formats what strategy.py / backtest.py produced.
"""
import json
from pathlib import Path
from typing import Optional

from .util import RESULTS_DIR


def _write_json(obj: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))
    return path


def write_spec(spec: dict, out_dir: Optional[Path] = None) -> Path:
    out_dir = Path(out_dir) if out_dir else RESULTS_DIR
    return _write_json(spec, out_dir / "strategy_spec.json")


def write_report(report: dict, out_dir: Optional[Path] = None) -> Path:
    out_dir = Path(out_dir) if out_dir else RESULTS_DIR
    win = report.get("window", {})
    name = f"backtest_{win.get('start', 'start')}_{win.get('end', 'end')}.json"
    return _write_json(report, out_dir / name)


def write_card(spec: dict, report: Optional[dict] = None, out_dir: Optional[Path] = None) -> Path:
    out_dir = Path(out_dir) if out_dir else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "strategy_card.md"
    path.write_text(render_card(spec, report))
    return path


def render_card(spec: dict, report: Optional[dict] = None) -> str:
    s = spec.get("strategy", {})
    sig = spec.get("signals", {})
    calls = sig.get("calls", {})
    conf = sig.get("onchain_confirmation", {})
    reg = sig.get("regime", {})
    nar = sig.get("narrative", {})
    rules = spec.get("rules", {})
    ex = rules.get("exit", {})
    sz = rules.get("position_sizing", {})

    verdict = "✅ ENTRY" if spec.get("entry_signal") else "⛔ NO ENTRY"
    L = []
    L.append(f"# Strategy Card — {s.get('name', 'public-alpha')}")
    L.append("")
    L.append(f"**{verdict}**  ·  confidence **{spec.get('confidence')}**  ·  "
             f"{s.get('risk_profile')} / {s.get('horizon')} / lookback {s.get('lookback')}  ·  "
             f"chain `{s.get('universe', {}).get('chain')}`")
    L.append("")
    L.append(f"> {spec.get('thesis', '')}")
    L.append("")
    L.append("## The funnel")
    heating = nar.get("heating")
    L.append(f"1. **Narrative heating** — {'🔥 ' + str(nar.get('sector', 'sector heating')) if heating else 'flat'} "
             f"_(source: {nar.get('source', 'cmc')})_")
    L.append(f"2. **Calls** — {calls.get('n_calls', 0)} calls on `{calls.get('symbol')}` "
             f"from {', '.join(calls.get('sources', [])) or 'n/a'}")
    L.append(f"3. **Organic vs coordinated** — **{str(calls.get('classification', '?')).upper()}** "
             f"(organic score {calls.get('score')})")
    for r in calls.get("reasons", []):
        L.append(f"   - {r}")
    if conf.get("available") is False:
        L.append("4. **On-chain confirmation** — _not available (run with a CMC key)_")
    else:
        verdict = "✅ confirmed" if conf.get("confirmed") else "❌ not confirmed"
        notes = conf.get("notes") or []
        detail = "; ".join(notes[:3]) if notes else (
            f"buy/sell {conf.get('buy_sell_ratio')}, liquidity ${_int(conf.get('liquidity_usd'))}")
        L.append(f"4. **Confirmation** (on-chain for crypto / market activity otherwise) — {verdict} — {detail}")
    if reg.get("available") is False:
        L.append("5. **Regime gate** — _not available (run with a CMC key)_")
    else:
        L.append(f"5. **Regime gate** — **{reg.get('state')}** "
                 f"(F&G {reg.get('fear_greed')}, BTC dom {reg.get('btc_dominance')}%, altseason {reg.get('altseason')})")
    L.append("")
    L.append("## Rules")
    L.append("**Entry (all must hold):**")
    for r in rules.get("entry", []):
        L.append(f"- `{r}`")
    L.append(f"\n**Exit:** SL `{ex.get('stop_loss_pct')}%` · TP `{ex.get('take_profit_pct')}%` · "
             f"time-stop `{ex.get('time_stop')}` · invalidations: {', '.join(ex.get('invalidations', []))}")
    L.append(f"\n**Sizing:** base `{sz.get('base_pct')}%` (confidence-scaled), max `{sz.get('max_position_pct')}%`")
    L.append("")
    if report:
        m = report.get("metrics", {})
        g = report.get("gate_stats", {})
        L.append("## Backtest headline")
        L.append(f"- Return **{m.get('total_return_pct')}%** vs benchmark **{m.get('benchmark_return_pct')}%** "
                 f"(`{report.get('benchmark')}`) → excess **{m.get('excess_pct')}%**")
        L.append(f"- Max drawdown **{m.get('max_drawdown_pct')}%** · Sharpe **{m.get('sharpe')}** · "
                 f"win rate **{m.get('win_rate_pct')}%** · trades **{m.get('num_trades')}**")
        L.append(f"- Gate: across **{g.get('clusters_seen')}** call clusters ({g.get('calls_seen')} calls), "
                 f"**{g.get('filtered_coordinated_pct')}%** coordinated (filtered), "
                 f"**{g.get('organic_pct')}%** organic, **{g.get('mixed_pct')}%** mixed")
        hon = report.get("honesty", {})
        if hon:
            L.append(f"- _Honesty: backtested on {', '.join(hon.get('backtested_on_history', []))}; "
                     f"forward-validated: {', '.join(hon.get('forward_validated_or_proxied', []))}._")
    L.append("")
    L.append("_Research artifact — no live execution, no real money. Generated by the Public Alpha CMC Skill._")
    return "\n".join(L)


def _int(v) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def print_funnel_trace(spec: dict, report: Optional[dict] = None) -> None:
    """Console narration of a run — what the agent echoes during the demo."""
    print(render_card(spec, report))
