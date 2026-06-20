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


def gather_calls(cfg, sources, since, symbol):
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
            n0 = len(cands)
            cands += CMCSource().calls_for(symbol, since)   # per-coin community posts + news
            print(f"  [cmc community+news] +{len(cands) - n0} calls for {symbol.upper()}")
        except Exception as e:
            print(f"  [cmc calls] unavailable: {type(e).__name__}: {e}")
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


def run(query, cfg, args):
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    since = datetime.now(timezone.utc) - timedelta(days=args.lookback)
    market = get_market(cfg)

    # resolve to a unified asset entity (crypto, or a tokenized stock across chains/issuers)
    entity = None
    if market is not None:
        try:
            entity = market.resolve(query)
        except Exception as e:
            print(f"  [resolve] {type(e).__name__}: {e}")
    if entity:
        underlying = entity["underlying"]
        aliases = {a.upper() for a in entity["aliases"]}
        listing = entity["listing"]
        market_symbol, display, chain = listing["symbol"], entity["display"], listing.get("chain") or "—"
        print(f"  resolved '{query}' → {display} [{entity['kind']}] · tradeable {market_symbol} on {chain} "
              f"(24h vol ${int(listing.get('volume_24h') or 0):,}) · call aliases {sorted(aliases)}")
    else:
        underlying, aliases = query.upper(), {query.upper()}
        market_symbol, display, chain, listing = query.upper(), query.upper(), "bsc", None

    print(f"\n— gathering calls for {display} (sources: {', '.join(sources)}; since {since:%Y-%m-%d}) —")
    candidates = gather_calls(cfg, sources, since, underlying)
    calls = normalize(candidates, cfg)
    groups = group_by_symbol(calls)                              # full set, for gate stats
    sym_calls = [c for c in calls if c.symbol.upper() in aliases]
    for c in sym_calls:                                          # unify aliases under one display ticker
        c.symbol = underlying
    print(f"  {len(calls)} calls across {len(groups)} symbols; {len(sym_calls)} matched {display}")

    if not sym_calls:
        top = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:15]
        print(f"\n  no calls for {display}. Symbols with calls: " +
              ", ".join(f"{k}({len(v)})" for k, v in top))
        return None

    # narrative heating (market-wide)
    narrative = {"heating": False, "source": "cmc_community_topics+categories", "available": False}
    if market is not None:
        try:
            narrative = market.narrative(underlying)
        except Exception as e:
            print(f"  [narrative] unavailable: {e}")

    # confirmation via the tradeable listing (on-chain for crypto, market volume otherwise)
    conf, conf_for_classifier = None, None
    if market is not None:
        try:
            conf = confirm(market.onchain(market_symbol), cfg)
            conf_for_classifier = conf
        except Exception as e:
            print(f"  [confirm] unavailable: {e}")

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
        judgment = json.loads(Path(args.judgment_file).read_text()).get(underlying)

    cls = classify(sym_calls, underlying, conf=conf_for_classifier, cfg=cfg, llm_judgment=judgment)

    asset = {"display": display, "kind": (entity or {}).get("kind", "crypto"),
             "market_listing": market_symbol, "chain": chain}
    spec = strategy.assemble_spec(
        symbol=underlying, cls=cls, calls=sym_calls, conf=conf, regime=regime,
        narrative=narrative, cfg=cfg, chain=chain, risk_profile=args.risk, lookback_days=args.lookback,
        thesis=_load_thesis(args, underlying), asset=asset,
    )

    report = None
    if args.backtest:
        report = _try_backtest(market_symbol, spec, cfg, market, args, groups)
        if report:
            spec["backtest_ref"] = f"results/backtest_{report['window']['start']}_{report['window']['end']}.json"
            render.write_report(report)

    render.write_spec(spec)
    render.write_card(spec, report)
    print(f"\n— wrote results/strategy_spec.json, results/strategy_card.md"
          + (", results/backtest_*.json" if report else "") + " —\n")
    render.print_funnel_trace(spec, report)
    return spec


def _try_backtest(symbol, spec, cfg, market, args, groups):
    try:
        from scripts.backtest import compute_gate_stats, run_backtest
        gate = compute_gate_stats(groups, cfg)
        return run_backtest(symbol, spec, cfg, market, gate_stats=gate)
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
