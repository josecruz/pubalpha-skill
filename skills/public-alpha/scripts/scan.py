"""Public Alpha scanner — classify the whole call universe into one scan.json for the TUI.

Where run.py analyzes ONE asset, scan.py sweeps every asset people are calling (seed +
paste.trade shows), classifies each cluster organic/mixed/coordinated, ranks them by how
much they're being called (the social-signal feed), then on-chain-confirms the top organic
names into a ranked TRADE IDEAS list. Market context (regime + heating narratives) is fetched
once. Output: results/scan.json — the TUI just reads + navigates it.

    python3 skills/public-alpha/scripts/scan.py
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.backtest import compute_gate_stats              # noqa: E402
from scripts.calls import group_by_symbol, normalize         # noqa: E402
from scripts.classifier import classify                      # noqa: E402
from scripts.confirm import confirm                          # noqa: E402
from scripts.regime import get_state                         # noqa: E402
from scripts.sources.paste_trade import PasteTradeSource     # noqa: E402
from scripts.sources.seed import SeedSource                  # noqa: E402
from scripts.util import RESULTS_DIR, get_key, load_config   # noqa: E402


def _market(cfg):
    if not get_key("CMC_PRO_API_KEY"):
        return None
    try:
        from scripts.sources.cmc import CMCSource
        return CMCSource()
    except Exception as e:
        print(f"[cmc] unavailable: {e}", file=sys.stderr)
        return None


def _call_dict(c) -> dict:
    return {
        "author": c.author, "source": c.source, "stance": c.stance,
        "conviction": c.conviction, "summary": c.summary, "weight": c.weight,
        "ts": c.ts.isoformat(), "engagement": c.engagement, "url": c.url,
    }


def _stance_mix(calls) -> dict:
    m = Counter(c.stance for c in calls)
    return {"bullish": m.get("bullish", 0), "bearish": m.get("bearish", 0), "neutral": m.get("neutral", 0)}


def _regime_dict(r):
    if r is None:
        return {"available": False, "state": "unknown"}
    return {"available": True, "state": r.state, "fear_greed": r.fear_greed,
            "btc_dominance": r.btc_dominance, "altseason": r.altseason, "notes": r.notes}


def _conf_dict(c):
    if c is None:
        return None
    return {"confirmed": c.confirmed, "buy_sell_ratio": c.buy_sell_ratio,
            "liquidity_usd": c.liquidity_usd, "notes": c.notes}


def scan(cfg, args) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=args.lookback)
    cands = SeedSource().fetch(since)
    try:
        cands += PasteTradeSource().fetch(since)
    except Exception as e:
        print(f"[paste_trade] {e}", file=sys.stderr)
    calls = normalize(cands, cfg)
    groups = group_by_symbol(calls)

    market = _market(cfg)
    regime = narrative = None
    if market is not None:
        try:
            regime = get_state(market.regime_inputs(), cfg)
        except Exception as e:
            print(f"[regime] {e}", file=sys.stderr)
        try:
            narrative = market.narrative()
        except Exception as e:
            print(f"[narrative] {e}", file=sys.stderr)
    narrative = narrative or {"heating": False, "available": False, "trending_topics": [], "top_categories": []}

    # social-signal feed: classify every cluster with >= min_calls
    signals = []
    for sym, cs in groups.items():
        if len(cs) < args.min_calls:
            continue
        res = classify(cs, sym, conf=None, cfg=cfg)
        top = sorted(cs, key=lambda c: c.weight, reverse=True)[:6]
        signals.append({
            "symbol": sym, "n_calls": len(cs),
            "classification": res.classification, "score": res.score, "reasons": res.reasons,
            "distinct_authors": len({c.author for c in cs}),
            "sources": sorted({c.source.split(":")[0] for c in cs}),
            "stance_mix": _stance_mix(cs),
            "latest_ts": max(c.ts for c in cs).isoformat(),
            "top_calls": [_call_dict(c) for c in top],
        })
    signals.sort(key=lambda s: (s["n_calls"], s["score"]), reverse=True)   # most-called first

    # trade ideas: on-chain confirm the top organic names (bounded), gate by regime
    ideas = []
    regime_ok = regime is not None and regime.state in ("risk_on", "neutral")
    heating = bool(narrative.get("heating"))
    organic = [s for s in signals if s["classification"] == "organic"]
    for s in organic[:args.confirm_top]:
        conf = None
        if market is not None:
            try:
                conf = confirm(market.onchain(s["symbol"]), cfg)
            except Exception as e:
                print(f"[onchain {s['symbol']}] {e}", file=sys.stderr)
        confirmed = bool(conf and conf.confirmed)
        confidence = round(s["score"] * (1.0 if confirmed else 0.5) * (1.0 if regime_ok else 0.5), 2)
        ideas.append({
            "symbol": s["symbol"], "n_calls": s["n_calls"], "score": s["score"],
            "classification": s["classification"],
            "distinct_authors": s["distinct_authors"], "reasons": s["reasons"][:3],
            "onchain": _conf_dict(conf), "confirmed": confirmed,
            "narrative_heating": heating, "regime_state": (regime.state if regime else "unknown"),
            "entry_ready": heating and confirmed and regime_ok,
            "confidence": confidence, "top_calls": s["top_calls"][:3],
        })
    ideas.sort(key=lambda i: (i["entry_ready"], i["confidence"]), reverse=True)

    # flat social-trades feed: every call on a classified asset, recent-first (for the web dashboard)
    sig_by_sym = {s["symbol"]: s for s in signals}
    feed = []
    for c in calls:
        s = sig_by_sym.get(c.symbol)
        if not s:
            continue
        feed.append({
            "symbol": c.symbol, "classification": s["classification"], "score": s["score"],
            "author": c.author, "source": c.source.split(":")[0], "stance": c.stance,
            "conviction": c.conviction, "summary": c.summary, "ts": c.ts.isoformat(),
            "engagement": c.engagement, "url": c.url,
        })
    feed.sort(key=lambda f: f["ts"], reverse=True)
    feed = feed[:300]

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "meta": {"total_calls": len(calls), "unique_symbols": len(groups),
                 "classified": len(signals), "trade_ideas": len(ideas), "lookback_days": args.lookback},
        "regime": _regime_dict(regime),
        "narrative": narrative,
        "gate_stats": compute_gate_stats(groups, cfg),
        "signals": signals,
        "trade_ideas": ideas,
        "feed": feed,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "scan.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"scanned {len(calls)} calls · {len(signals)} assets classified · {len(ideas)} trade ideas "
          f"→ {RESULTS_DIR / 'scan.json'}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Public Alpha scanner")
    ap.add_argument("--lookback", type=int, default=180)
    ap.add_argument("--min-calls", type=int, default=2, dest="min_calls")
    ap.add_argument("--confirm-top", type=int, default=15, dest="confirm_top",
                    help="how many top organic names to on-chain-confirm into trade ideas")
    scan(load_config(), ap.parse_args())


if __name__ == "__main__":
    main()
