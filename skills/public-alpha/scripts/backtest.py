"""Deterministic backtest — the honest backbone.

We can only backtest what has real history: price/OHLCV. The call layer, the
organic-vs-coordinated classification, regime and on-chain confirmation are
live/forward-validated signals, NOT replayed as history — so the backtested entry
is an explicit, disclosed momentum *proxy* for "a confirmed organic entry fired",
and the `honesty` block says exactly that. Exits/sizing/fees come from the spec.

numpy only (no pandas). Output matches output-contract.md §3.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import numpy as np

from .classifier import classify


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ema(x: np.ndarray, span: int) -> np.ndarray:
    a = 2.0 / (span + 1.0)
    out = np.empty_like(x, dtype=float)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def _to_arrays(candles: List[dict]):
    ts, o, h, l, c = [], [], [], [], []
    for cd in candles:
        t = cd["ts"]
        if isinstance(t, datetime):
            t = t.timestamp()
        elif isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        ts.append(float(t))
        o.append(float(cd["open"])); h.append(float(cd["high"]))
        l.append(float(cd["low"])); c.append(float(cd["close"]))
    order = np.argsort(ts)
    A = lambda v: np.array(v, dtype=float)[order]
    return A(ts), A(o), A(h), A(l), A(c)


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# gate stats (computed from the live run's call clusters — a real number)
# ---------------------------------------------------------------------------

def compute_gate_stats(groups: dict, cfg: dict, min_calls: int = 3) -> dict:
    """The classifier's verdict breakdown across this run's call clusters — a real number.

    Only clusters with >= min_calls are classified (fewer than that has no timing/language
    signal). This is the wedge's headline stat: what share of attention is coordinated.
    """
    clusters = {s: cs for s, cs in groups.items() if len(cs) >= min_calls}
    seen = sum(len(cs) for cs in clusters.values())
    n = len(clusters) or 1
    counts = {"organic": 0, "coordinated": 0, "mixed": 0}
    for sym, cs in clusters.items():
        counts[classify(cs, sym, conf=None, cfg=cfg).classification] += 1
    return {
        "calls_seen": seen,
        "clusters_seen": len(clusters),
        "min_calls_per_cluster": min_calls,
        "organic_pct": round(100 * counts["organic"] / n, 1),
        "filtered_coordinated_pct": round(100 * counts["coordinated"] / n, 1),
        "mixed_pct": round(100 * counts["mixed"] / n, 1),
        "organic_candidates": counts["organic"],
    }


# ---------------------------------------------------------------------------
# the backtest
# ---------------------------------------------------------------------------

def run_backtest(symbol, spec, cfg, market=None, candles=None, benchmark_candles=None,
                 gate_stats: Optional[dict] = None) -> dict:
    bt = cfg.get("backtest", {})
    interval = bt.get("interval", "1h")
    window_days = bt.get("window_days", 30)
    fee = bt.get("fee_pct", 0.25) / 100.0
    slip = bt.get("slippage_pct", 0.3) / 100.0
    benchmark_asset = str(bt.get("benchmark", "buy_and_hold_bnb")).replace("buy_and_hold_", "").upper()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=window_days)
    if candles is None:
        if market is None:
            raise RuntimeError("no candles and no market source for OHLCV")
        candles = market.ohlcv(symbol, interval, start, end)
    if not candles or len(candles) < 60:
        raise RuntimeError(f"insufficient candles for {symbol} ({0 if not candles else len(candles)})")

    ts, o, h, l, c = _to_arrays(candles)
    n = len(c)

    rp = spec.get("rules", {}).get("exit", {})
    sl_pct = rp.get("stop_loss_pct", -8) / 100.0
    tp_pct = rp.get("take_profit_pct", 25) / 100.0
    time_stop_h = _hours(rp.get("time_stop", "72h"))
    excfg = cfg.get("exhaustion", {})
    max_runup = excfg.get("max_runup_pct", 50) / 100.0
    bar_hours = max(1.0, float(np.median(np.diff(ts))) / 3600.0) if n > 1 else 24.0
    runup_lb = max(1, round(excfg.get("lookback_hours", 24) / bar_hours))   # candle count, interval-aware

    ema_f, ema_s = _ema(c, 12), _ema(c, 48)
    warmup = min(48, n // 3)

    eq = 1.0
    curve, trades = [], []
    pos = None
    for i in range(n):
        if pos is None:
            curve.append({"ts": _iso(ts[i]), "equity": round(float(eq), 6)})
            cross_up = ema_f[i] > ema_s[i] and ema_f[i - 1] <= ema_s[i - 1] if i > 0 else False
            runup = (c[i] / c[max(0, i - runup_lb)] - 1) if i >= runup_lb else 0.0
            if i >= warmup and cross_up and runup < max_runup:
                entry_eff = c[i] * (1 + slip)
                eq *= (1 - fee)
                pos = {"entry_i": i, "entry_eff": entry_eff, "entry_ts": ts[i], "eq0": eq, "last": c[i]}
        else:
            sl_price = pos["entry_eff"] * (1 + sl_pct)
            tp_price = pos["entry_eff"] * (1 + tp_pct)
            hours = (ts[i] - pos["entry_ts"]) / 3600.0
            reason, xprice = None, c[i]
            if l[i] <= sl_price:
                reason, xprice = "stop_loss", sl_price
            elif h[i] >= tp_price:
                reason, xprice = "take_profit", tp_price
            elif hours >= time_stop_h:
                reason, xprice = "time_stop", c[i]
            mark = xprice if reason else c[i]
            eq *= mark / pos["last"]
            pos["last"] = mark
            curve.append({"ts": _iso(ts[i]), "equity": round(float(eq), 6)})
            if reason:
                eq *= (1 - fee - slip)                       # exit cost
                exit_eff = xprice * (1 - slip)
                net = (exit_eff * (1 - fee)) / pos["entry_eff"] - 1
                trades.append({
                    "symbol": symbol, "entry_ts": _iso(pos["entry_ts"]), "exit_ts": _iso(ts[i]),
                    "entry_price": round(float(pos["entry_eff"]), 6), "exit_price": round(float(xprice), 6),
                    "pnl_pct": round(float(net) * 100, 2), "exit_reason": reason, "hold_hours": round(float(hours), 1),
                })
                pos = None

    metrics = _metrics(curve, trades, ts)
    bench_ret = _benchmark_return(market, benchmark_candles, benchmark_asset, interval, start, end)
    metrics["benchmark_return_pct"] = bench_ret
    metrics["excess_pct"] = (round(metrics["total_return_pct"] - bench_ret, 2)
                             if bench_ret is not None else None)

    report = {
        "symbol": symbol,
        "window": {"start": _iso(ts[0])[:10], "end": _iso(ts[-1])[:10], "interval": interval},
        "benchmark": f"buy_and_hold_{benchmark_asset}",
        "metrics": metrics,
        "gate_stats": gate_stats or {},
        "equity_curve": curve,
        "trade_log": trades,
        "honesty": {
            "backtested_on_history": ["price/ohlcv"],
            "forward_validated_or_proxied": [
                "call extraction", "organic-vs-coordinated classification",
                "on-chain confirmation", "regime gate",
            ],
            "entry_proxy": "EMA(12/48) momentum cross + not-exhausted, standing in for a confirmed organic entry "
                           "(the call layer has no per-hour history to replay)",
            "assumptions": {"fee_pct": fee * 100, "slippage_pct": slip * 100,
                            "allocation": "fully allocated per trade (timing test); live sizing uses base_pct"},
        },
    }
    return report


def _hours(time_stop) -> float:
    s = str(time_stop).lower().strip()
    if s.endswith("h"):
        return float(s[:-1])
    if s.endswith("d"):
        return float(s[:-1]) * 24
    try:
        return float(s)
    except ValueError:
        return 72.0


def _metrics(curve, trades, ts) -> dict:
    eqs = np.array([p["equity"] for p in curve], dtype=float)
    total_return = (eqs[-1] - 1) * 100 if len(eqs) else 0.0
    peak = np.maximum.accumulate(eqs)
    dd = (eqs / peak - 1.0)
    max_dd = dd.min() * 100 if len(dd) else 0.0
    rets = np.diff(eqs) / eqs[:-1] if len(eqs) > 1 else np.array([0.0])
    ppy = 24 * 365  # hourly
    sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(ppy)) if np.std(rets) > 1e-12 else 0.0
    downside = rets[rets < 0]
    sortino = float(np.mean(rets) / np.std(downside) * np.sqrt(ppy)) if len(downside) and np.std(downside) > 1e-12 else 0.0
    wins = [t for t in trades if t["pnl_pct"] > 0]
    gross_p = sum(t["pnl_pct"] for t in wins)
    gross_l = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0))
    return {
        "total_return_pct": round(float(total_return), 2),
        "max_drawdown_pct": round(float(max_dd), 2),
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
        "num_trades": len(trades),
        "avg_hold_hours": round(float(np.mean([t["hold_hours"] for t in trades])), 1) if trades else 0.0,
        "profit_factor": round(float(gross_p / gross_l), 2) if gross_l > 1e-9 else (round(float(gross_p), 2) if gross_p else 0.0),
    }


def _benchmark_return(market, benchmark_candles, asset, interval, start, end):
    candles = benchmark_candles
    if candles is None and market is not None:
        try:
            candles = market.ohlcv(asset, interval, start, end)
        except Exception:
            return None
    if not candles or len(candles) < 2:
        return None
    _, _, _, _, c = _to_arrays(candles)
    return round(float(c[-1] / c[0] - 1) * 100, 2)
