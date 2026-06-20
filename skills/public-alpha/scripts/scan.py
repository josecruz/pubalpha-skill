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
from scripts.decide import kol_sentiment, perp_breakout, spot_breakout  # noqa: E402
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


def _regime_dict(r, altseason_index=None, fear_greed_trend=None):
    base = {"available": False, "state": "unknown"} if r is None else {
        "available": True, "state": r.state, "fear_greed": r.fear_greed,
        "btc_dominance": r.btc_dominance, "altseason": r.altseason, "notes": r.notes}
    if altseason_index:
        base["altseason_index"] = altseason_index        # real CMC index (replaces the proxy)
    if fear_greed_trend:
        base["fear_greed_trend"] = fear_greed_trend
    return base


def _attention_overlap(attention: dict, called: set) -> dict:
    """Cross-ref the called symbols against CMC's own attention lists.
    Returns the raw movers + overlap sets: corroborated / kol_only / cmc_only,
    and a per-symbol map {SYM: {sources[], rank}} for stamping each signal."""
    per_symbol: dict = {}
    for listname in ("most_visited", "gainers", "losers", "community"):
        for x in attention.get(listname, []):
            sym = x.get("symbol")
            if not sym:
                continue
            a = per_symbol.setdefault(sym, {"sources": [], "name": x.get("name"),
                                            "rank": x.get("rank"), "percent_change_24h": x.get("percent_change_24h")})
            if listname not in a["sources"]:
                a["sources"].append(listname)
            if x.get("rank") and (a["rank"] is None or x["rank"] < a["rank"]):
                a["rank"] = x["rank"]
            if a["percent_change_24h"] is None and x.get("percent_change_24h") is not None:
                a["percent_change_24h"] = x["percent_change_24h"]
    cmc_syms = set(per_symbol)
    cmc_only = [{"symbol": s, **per_symbol[s]} for s in sorted(cmc_syms - called,
                key=lambda s: per_symbol[s]["rank"] or 9999)][:24]
    return {
        "per_symbol": per_symbol,
        "corroborated": sorted(called & cmc_syms),
        "kol_only": sorted(called - cmc_syms),
        "cmc_only": cmc_only,
    }


def _since_call(series, call_ts_iso, current_price):
    """Entry = the daily close on/just-before the call date; return = move to current price.
    Powers the paste.trade-style 'since call' P&L on each social signal."""
    if not series or current_price is None:
        return (None, None)
    day = (call_ts_iso or "")[:10]
    entry = None
    for c in series:                       # series is sorted oldest -> newest
        if (c.get("ts") or "")[:10] <= day:
            entry = c.get("close")
        else:
            break
    if entry is None:
        entry = series[0].get("close")
    if not entry:
        return (None, None)
    return (round(entry, 6), round((current_price - entry) / entry * 100, 2))


def _identity(info):
    """Pass through CMC metadata + derive age_days + is_new (brand-new token = pump risk)."""
    if not info:
        return None
    out = dict(info)
    out["age_days"], out["is_new"] = None, False
    da = info.get("date_added")
    if da:
        try:
            d = datetime.fromisoformat(str(da).replace("Z", "+00:00"))
            out["age_days"] = (datetime.now(timezone.utc) - d).days
            out["is_new"] = out["age_days"] < 30
        except ValueError:
            pass
    return out


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
    altseason_index, fg_trend = {}, {}
    if market is not None:
        try:
            regime = get_state(market.regime_inputs(), cfg)
        except Exception as e:
            print(f"[regime] {e}", file=sys.stderr)
        try:
            narrative = market.narrative()
        except Exception as e:
            print(f"[narrative] {e}", file=sys.stderr)
        try:
            altseason_index = market.altcoin_season()       # real CMC index (replaces 100-BTC_dom proxy)
        except Exception as e:
            print(f"[altcoin_season] {e}", file=sys.stderr)
        try:
            fg_trend = market.fear_greed_trend()
        except Exception as e:
            print(f"[fear_greed_trend] {e}", file=sys.stderr)
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
            "features": res.features,
            "distinct_authors": len({c.author for c in cs}),
            "sources": sorted({c.source.split(":")[0] for c in cs}),
            "stance_mix": _stance_mix(cs),
            "sentiment": kol_sentiment(cs, res.classification),   # KOL sentiment skill (free, all signals)
            "latest_ts": max(c.ts for c in cs).isoformat(),
            "top_calls": [_call_dict(c) for c in top],
        })
    signals.sort(key=lambda s: (s["n_calls"], s["score"]), reverse=True)   # most-called first

    # per-asset market block (price, %changes, CEX/DEX volume split, market cap)
    if market is not None and signals:
        try:
            mkt = market.market_block([s["symbol"] for s in signals])
            for s in signals:
                s["market"] = mkt.get(s["symbol"])
        except Exception as e:
            print(f"[market_block] {e}", file=sys.stderr)

    # CMC attention cross-ref + identity + price context (enrichment over the classified set)
    cmc_attention = {}
    if market is not None and signals:
        sym_to_id = {s["symbol"]: (s.get("market") or {}).get("id")
                     for s in signals if (s.get("market") or {}).get("id")}
        try:
            raw = market.cmc_attention()
            ov = _attention_overlap(raw, {s["symbol"] for s in signals})
            for s in signals:                                # stamp each signal: does CMC's crowd agree?
                a = ov["per_symbol"].get(s["symbol"])
                s["attention"] = {"on_cmc": bool(a), "sources": a["sources"] if a else [],
                                  "rank": a["rank"] if a else None}
            cmc_attention = {k: raw.get(k, []) for k in ("most_visited", "gainers", "losers", "community")}
            cmc_attention["overlap"] = {k: ov[k] for k in ("corroborated", "kol_only", "cmc_only")}
            print(f"  attention: {len(ov['corroborated'])} corroborated · "
                  f"{len(ov['kol_only'])} KOL-only · {len(ov['cmc_only'])} CMC-only")
        except Exception as e:
            print(f"[cmc_attention] {e}", file=sys.stderr)
        try:
            ident = market.info(sym_to_id)
            for s in signals:
                s["identity"] = _identity(ident.get(s["symbol"]))
        except Exception as e:
            print(f"[info] {e}", file=sys.stderr)
        try:
            perf = market.price_performance(sym_to_id)
            for s in signals:
                s["performance"] = perf.get(s["symbol"])
        except Exception as e:
            print(f"[price_performance] {e}", file=sys.stderr)

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

    # top venues (real CEX/DEX breakdown) for the trade-idea + top signals only (bounds per-asset calls)
    if market is not None:
        want = {i["symbol"] for i in ideas} | {s["symbol"] for s in signals[:12]}
        for s in signals:
            if s["symbol"] in want:
                cid = (s.get("market") or {}).get("id")
                s["venues"] = market.market_pairs(cid) if cid else []

    # price series (daily OHLCV) for charts + per-call "since call" P&L (paste.trade-style)
    series_by_sym = {}
    price_by_sym = {s["symbol"]: (s.get("market") or {}).get("price") for s in signals}
    if market is not None:
        want_series = {i["symbol"] for i in ideas} | {s["symbol"] for s in signals[:20]}
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=min(args.lookback, 180))
        for s in signals:
            if s["symbol"] not in want_series:
                continue
            try:
                candles = market.ohlcv(s["symbol"], "daily", start, end)
                ser = sorted(({"ts": c["ts"], "close": c["close"]}
                              for c in candles if c.get("close") is not None), key=lambda x: x["ts"])
            except Exception as e:
                print(f"[ohlcv {s['symbol']}] {e}", file=sys.stderr)
                ser = []
            if ser:
                series_by_sym[s["symbol"]] = ser
                s["price_series"] = ser
            price = price_by_sym.get(s["symbol"])
            for tc in s["top_calls"]:                       # annotate the signal's own calls
                tc["entry_price"], tc["since_call_pct"] = _since_call(ser, tc.get("ts"), price)
            # decision skills: breakout (spot) + perp (derivatives funding/OI) — crypto only
            if (s.get("market") or {}).get("kind") != "tokenized_stock":
                s["breakout"] = spot_breakout(candles)
                try:
                    s["perp"] = perp_breakout(market.derivatives(s["symbol"]), s.get("breakout"))
                except Exception as e:
                    print(f"[derivatives {s['symbol']}] {e}", file=sys.stderr)
        print(f"  price series for {len(series_by_sym)} assets")

    # decision setups (forward screens — NOT backtested) — ranked candidates, breakouts on top.
    spot_setups, perp_setups = [], []
    for s in signals:
        bo, sent, perp = s.get("breakout"), s.get("sentiment") or {}, s.get("perp")
        if bo:                                              # any crypto with a price series → rank as a candidate
            confirmed = sent.get("label") == "bullish" and s["classification"] != "coordinated"
            bo["social_confirmed"] = confirmed
            spot_setups.append({
                "symbol": s["symbol"], "classification": s["classification"], "n_calls": s["n_calls"],
                "is_breakout": bool(bo.get("is_breakout")),
                "pct_above_20d_high": bo.get("pct_above_20d_high"), "vol_mult": bo.get("vol_mult"),
                "atr_pct": bo.get("atr_pct"), "mom_7d": bo.get("mom_7d"), "strength": bo.get("strength"),
                "sentiment_label": sent.get("label"), "sentiment_score": sent.get("score"),
                "social_confirmed": confirmed,
            })
        if perp and (perp.get("is_breakout") or (perp.get("open_interest") or 0) > 1e7):  # drop illiquid perps
            perp_setups.append({
                "symbol": s["symbol"], "venue": perp.get("venue"), "funding_rate": perp.get("funding_rate"),
                "open_interest": perp.get("open_interest"), "perp_volume_24h": perp.get("perp_volume_24h"),
                "is_breakout": bool(perp.get("is_breakout")), "bias": perp.get("bias"), "score": perp.get("score"),
            })
    # breakouts first, then social-confirmed, then strength; perp: breakouts, then score, then funding stretch
    spot_setups.sort(key=lambda x: (x["is_breakout"], x["social_confirmed"], x["strength"] or 0), reverse=True)
    perp_setups.sort(key=lambda x: (x["is_breakout"], x["score"] or 0, abs(x["funding_rate"] or 0)), reverse=True)
    spot_setups, perp_setups = spot_setups[:15], perp_setups[:15]
    setups = {"spot": spot_setups, "perp": perp_setups,
              "disclaimer": "Forward screens — ranked breakout candidates with live volume, funding, OI and "
                            "social-confirmation signals. Not backtested entries; perp OI/funding are "
                            "point-in-time snapshots."}
    print(f"  setups: {len(spot_setups)} spot candidates "
          f"({sum(x['is_breakout'] for x in spot_setups)} breaking out, "
          f"{sum(x['social_confirmed'] for x in spot_setups)} social-confirmed) · {len(perp_setups)} perp")

    # flat social-trades feed: every call on a classified asset, recent-first (for the web dashboard)
    sig_by_sym = {s["symbol"]: s for s in signals}
    feed = []
    for c in calls:
        s = sig_by_sym.get(c.symbol)
        if not s:
            continue
        entry, since = _since_call(series_by_sym.get(c.symbol), c.ts.isoformat(), price_by_sym.get(c.symbol))
        feed.append({
            "symbol": c.symbol, "classification": s["classification"], "score": s["score"],
            "author": c.author, "source": c.source.split(":")[0], "stance": c.stance,
            "conviction": c.conviction, "summary": c.summary, "ts": c.ts.isoformat(),
            "engagement": c.engagement, "url": c.url,
            "entry_price": entry, "since_call_pct": since,
        })
    feed.sort(key=lambda f: f["ts"], reverse=True)
    feed = feed[:300]

    # market insights (global volumes/dominance + the CEX/DEX split across surfaced assets)
    gate = compute_gate_stats(groups, cfg)
    gi = {}
    if market is not None:
        try:
            gi = market.global_insights()
        except Exception as e:
            print(f"[global_insights] {e}", file=sys.stderr)
    num = lambda x: float(x) if isinstance(x, (int, float)) else 0.0
    insights = {
        **gi,
        "surfaced_cex_volume_24h": round(sum(num((s.get("market") or {}).get("cex_volume_24h")) for s in signals)),
        "surfaced_dex_volume_24h": round(sum(num((s.get("market") or {}).get("dex_volume_24h")) for s in signals)),
        "verdict_split": {"organic_pct": gate["organic_pct"],
                          "coordinated_pct": gate["filtered_coordinated_pct"], "mixed_pct": gate["mixed_pct"]},
    }

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "meta": {"total_calls": len(calls), "unique_symbols": len(groups),
                 "classified": len(signals), "trade_ideas": len(ideas), "lookback_days": args.lookback},
        "regime": _regime_dict(regime, altseason_index, fg_trend),
        "narrative": narrative,
        "gate_stats": gate,
        "market_insights": insights,
        "cmc_attention": cmc_attention,
        "setups": setups,
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
