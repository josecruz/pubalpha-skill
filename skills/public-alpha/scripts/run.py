"""Public Alpha funnel CLI — drives the whole pipeline for one symbol.

    python3 skills/public-alpha/scripts/run.py --symbol CAKE
    python3 skills/public-alpha/scripts/run.py --symbol BTC --sources paste_trade
    python3 skills/public-alpha/scripts/run.py --replay        # narrate the cached run

Call layer = seed + paste.trade (allowed surface) + CMC content (if a key is set).
Regime / on-chain / narrative come from CMC when CMC_PRO_API_KEY is present; otherwise
those stages are marked unavailable and the spec says so. The agent (LLM) may inject a
richer substance judgment via --judgment-file; without it the deterministic fallback runs.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # skills/public-alpha/

from scripts import render, strategy                              # noqa: E402
from scripts.calls import group_by_symbol, normalize             # noqa: E402
from scripts.classifier import classify                          # noqa: E402
from scripts.confirm import confirm                              # noqa: E402
from scripts.regime import get_state                             # noqa: E402
from scripts.sources.paste_trade import PasteTradeSource         # noqa: E402
from scripts.sources.seed import SeedSource                      # noqa: E402
from scripts.util import RESULTS_DIR, get_key, load_config       # noqa: E402


def gather_calls(cfg, sources, since):
    cands = []
    if "seed" in sources:
        cands += SeedSource().fetch(since)
    if "paste_trade" in sources:
        try:
            n0 = len(cands)
            cands += PasteTradeSource().fetch(since)
            print(f"  [paste_trade] +{len(cands) - n0} calls from allowed shows (all-in, threadguy)")
        except Exception as e:
            print(f"  [paste_trade] unavailable: {type(e).__name__}: {e}")
    if "cmc" in sources:
        try:
            from scripts.sources.cmc import CMCSource
            cands += CMCSource().fetch(since)
        except Exception as e:
            print(f"  [cmc content] unavailable: {type(e).__name__}: {e}")
    return cands


def get_market(cfg):
    """Return a CMC-backed MarketSource, or None if no key / not wired."""
    if not get_key("CMC_PRO_API_KEY"):
        return None
    try:
        from scripts.sources.cmc import CMCSource
        return CMCSource()
    except Exception as e:
        print(f"  [cmc market] unavailable: {type(e).__name__}: {e}")
        return None


def run(symbol, cfg, args):
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    since = datetime.now(timezone.utc) - timedelta(days=args.lookback)

    print(f"\n— gathering calls (sources: {', '.join(sources)}; since {since:%Y-%m-%d}) —")
    candidates = gather_calls(cfg, sources, since)
    calls = normalize(candidates, cfg)
    groups = group_by_symbol(calls)
    print(f"  normalized {len(calls)} calls across {len(groups)} symbols")

    symbol = symbol.upper()
    sym_calls = groups.get(symbol, [])
    if not sym_calls:
        top = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:15]
        print(f"\n  no calls for {symbol}. Symbols with calls: " +
              ", ".join(f"{k}({len(v)})" for k, v in top))
        return None

    market = get_market(cfg)

    # narrative heating
    narrative = {"heating": False, "source": "cmc_community_topics+categories", "available": False}
    if market is not None:
        try:
            narrative = market.narrative(symbol)
        except Exception as e:
            print(f"  [narrative] unavailable: {e}")

    # on-chain confirmation (None when no market data -> card shows "not available")
    conf, conf_for_classifier = None, None
    if market is not None:
        try:
            conf = confirm(market.onchain(symbol), cfg)
            conf_for_classifier = conf
        except Exception as e:
            print(f"  [onchain] unavailable: {e}")

    # regime
    regime = None
    if market is not None:
        try:
            regime = get_state(market.regime_inputs(), cfg)
        except Exception as e:
            print(f"  [regime] unavailable: {e}")

    # optional agent-supplied substance judgment
    judgment = None
    if args.judgment_file and Path(args.judgment_file).exists():
        judgment = json.loads(Path(args.judgment_file).read_text()).get(symbol)

    cls = classify(sym_calls, symbol, conf=conf_for_classifier, cfg=cfg, llm_judgment=judgment)

    spec = strategy.assemble_spec(
        symbol=symbol, cls=cls, calls=sym_calls, conf=conf, regime=regime,
        narrative=narrative, cfg=cfg, risk_profile=args.risk, lookback_days=args.lookback,
        thesis=_load_thesis(args, symbol),
    )

    report = None
    if args.backtest:
        report = _try_backtest(symbol, spec, cfg, market, args)
        if report:
            spec["backtest_ref"] = f"results/backtest_{report['window']['start']}_{report['window']['end']}.json"
            render.write_report(report)

    render.write_spec(spec)
    render.write_card(spec, report)
    print(f"\n— wrote results/strategy_spec.json, results/strategy_card.md"
          + (", results/backtest_*.json" if report else "") + " —\n")
    render.print_funnel_trace(spec, report)
    return spec


def _try_backtest(symbol, spec, cfg, market, args):
    try:
        from scripts.backtest import run_backtest
        return run_backtest(symbol, spec, cfg, market)
    except ImportError:
        print("  [backtest] engine not built yet — skipping")
    except Exception as e:
        print(f"  [backtest] failed: {type(e).__name__}: {e}")
    return None


def _load_thesis(args, symbol):
    if args.thesis_file and Path(args.thesis_file).exists():
        return json.loads(Path(args.thesis_file).read_text()).get(symbol)
    return None


def replay():
    spec_path = RESULTS_DIR / "strategy_spec.json"
    if not spec_path.exists():
        print("No cached run in results/. Run without --replay first.")
        return
    spec = json.loads(spec_path.read_text())
    report = None
    ref = spec.get("backtest_ref")
    if ref and (RESULTS_DIR.parent / ref).exists():
        report = json.loads((RESULTS_DIR.parent / ref).read_text())
    else:
        reports = sorted(RESULTS_DIR.glob("backtest_*.json"))
        if reports:
            report = json.loads(reports[-1].read_text())
    render.print_funnel_trace(spec, report)


def main():
    ap = argparse.ArgumentParser(description="Public Alpha funnel")
    ap.add_argument("--symbol", default="CAKE")
    ap.add_argument("--risk", default="balanced", choices=["conservative", "balanced", "aggressive"])
    ap.add_argument("--lookback", type=int, default=180)
    ap.add_argument("--sources", default="seed,paste_trade,cmc")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--judgment-file", default=None, help="JSON {symbol: {substance_score,...}} from the agent")
    ap.add_argument("--thesis-file", default=None, help="JSON {symbol: thesis} from the agent")
    ap.add_argument("--replay", action="store_true", help="narrate the cached run in results/")
    args = ap.parse_args()

    if args.replay:
        replay()
        return

    cfg = load_config()
    run(args.symbol, cfg, args)


if __name__ == "__main__":
    main()
