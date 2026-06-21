"""Decision skills — native re-implementations of CMC Skill Hub pipelines.

Pure functions (no I/O) so they're deterministic + unit-testable. Each mirrors a
CoinMarketCap Skill Hub marketplace skill, computed over data we already pull:
- kol_sentiment   ~ altcoin_kol_sentiment            (our KOL/social layer + classifier)
- spot_breakout   ~ scan_spot_altcoin_breakout_with_social_confirmation  (CMC OHLCV)
- perp_breakout   ~ screen_perp_breakout_candidates  (CMC derivatives funding/OI + breakout)

These are FORWARD screens (live signals to help spot a move), NOT backtested entries —
scan.py labels them as such and the dashboard repeats the disclaimer.
"""
from typing import List, Optional

_STANCE = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}
_VERDICT_W = {"organic": 1.0, "mixed": 0.5, "coordinated": 0.25}   # coordinated hype counts less


def kol_sentiment(calls, classification: str = "mixed") -> dict:
    """Net KOL sentiment: bullish−bearish weighted by conviction, then scaled down by the
    organic/coordinated verdict (a coordinated bullish cluster counts far less than an organic one)."""
    if not calls:
        return {"label": "neutral", "score": 0.0, "n_kols": 0, "bull": 0, "bear": 0, "neutral": 0, "top_kols": []}
    num = den = 0.0
    bull = bear = neu = 0
    for c in calls:
        s = _STANCE.get(getattr(c, "stance", None) or "neutral", 0.0)
        conv = getattr(c, "conviction", None)
        w = conv if isinstance(conv, (int, float)) and conv > 0 else 0.5
        num += s * w
        den += w
        bull += s > 0
        bear += s < 0
        neu += s == 0
    raw = (num / den) if den else 0.0
    score = round(raw * _VERDICT_W.get(classification, 0.5), 3)
    label = "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "neutral")
    top = sorted(calls, key=lambda c: (getattr(c, "conviction", None) or 0), reverse=True)[:3]
    top_kols = [{"author": getattr(c, "author", "?"), "stance": getattr(c, "stance", None),
                 "conviction": getattr(c, "conviction", None)} for c in top]
    return {"label": label, "score": score,
            "n_kols": len({getattr(c, "author", "?") for c in calls}),
            "bull": int(bull), "bear": int(bear), "neutral": int(neu), "top_kols": top_kols}


def spot_breakout(candles, lookback: int = 20) -> dict:
    """Donchian-style breakout from daily OHLCV. candles: [{high,low,close,volume,ts}] oldest→newest."""
    rows = [c for c in (candles or []) if c.get("close") is not None]
    if len(rows) < lookback + 2:
        return {}
    closes = [c["close"] for c in rows]
    highs = [c.get("high") or c["close"] for c in rows]
    vols = [c.get("volume") or 0 for c in rows]
    close = closes[-1]
    prior_high = max(highs[-(lookback + 1):-1])           # highest high of the prior `lookback` days (excl. today)
    is_breakout = close >= prior_high
    pct_above = round((close - prior_high) / prior_high * 100, 2) if prior_high else None
    avg_vol = sum(vols[-(lookback + 1):-1]) / lookback
    vol_mult = round(vols[-1] / avg_vol, 2) if avg_vol else None
    atr = _atr(rows, 14)
    atr_pct = round(atr / close * 100, 2) if (atr and close) else None
    mom7 = round((close - closes[-8]) / closes[-8] * 100, 2) if len(closes) >= 8 else None
    mom30 = round((close - closes[-31]) / closes[-31] * 100, 2) if len(closes) >= 31 else None
    strength = 0.0
    if is_breakout:
        strength += 0.4
    if vol_mult and vol_mult > 1.2:
        strength += min(0.3, (vol_mult - 1.2) * 0.3)
    if mom7 and mom7 > 0:
        strength += min(0.3, mom7 / 100)
    return {"is_breakout": is_breakout, "pct_above_20d_high": pct_above, "vol_mult": vol_mult,
            "atr_pct": atr_pct, "mom_7d": mom7, "mom_30d": mom30, "strength": round(min(1.0, strength), 2)}


def perp_breakout(derivs: dict, breakout: dict) -> dict:
    """Combine perp funding/OI (CMC derivatives) with the spot breakout into a perp setup.
    Bias logic: a breakout into crowded shorts (negative funding) = short-squeeze fuel (long)."""
    if not derivs:
        return {}
    fr = derivs.get("funding_rate")
    is_bo = bool(breakout and breakout.get("is_breakout"))
    bias = "neutral"
    if is_bo:
        bias = "long (short-squeeze fuel)" if (fr is not None and fr < 0) else "long"
    elif fr is not None and fr < -0.0005:
        bias = "long (crowded shorts)"
    elif fr is not None and fr > 0.0005:
        bias = "short (crowded longs)"
    score = 0.0
    if is_bo:
        score += 0.5
    if breakout:
        score += min(0.3, (breakout.get("strength") or 0) * 0.3)
    if fr is not None and abs(fr) > 0.0003:                # stretched funding = fuel either way
        score += 0.2
    return {"funding_rate": fr, "open_interest": derivs.get("open_interest"),
            "perp_volume_24h": derivs.get("perp_volume_24h"), "venue": derivs.get("venue"),
            "long_share": derivs.get("long_share"), "n_venues": derivs.get("n_venues"),
            "venues": derivs.get("venues") or [],
            "is_breakout": is_bo, "bias": bias, "score": round(min(1.0, score), 2)}


def leverage_read(perp: dict, liq: dict) -> dict:
    """Fuse perp positioning (CMC derivatives funding / long_share) with realized liquidations
    (CMC liquidation table) into a one-line leverage-stress read for the thesis page.
    short squeeze = shorts getting liquidated (into crowded shorts ⇒ upside fuel);
    long flush/cascade = longs getting liquidated (while crowded long ⇒ downside risk).
    Returns {label, note, long_pct, total} or {} when there's no liquidation data."""
    total = (liq or {}).get("total")
    if not isinstance(total, (int, float)) or total <= 0:
        return {}
    long_pct = liq.get("long_pct")                       # share of liquidations that were longs
    fr = (perp or {}).get("funding_rate")
    long_share = (perp or {}).get("long_share")          # share of perp volume where funding > 0
    label, note = "balanced", "longs and shorts liquidating evenly"
    if long_pct is not None:
        if long_pct >= 0.62:
            label, note = "long flush", "longs being liquidated"
            if (long_share is not None and long_share > 0.6) or (fr is not None and fr > 0.0003):
                label, note = "cascade risk", "longs liquidating while leverage is crowded long"
        elif long_pct <= 0.38:
            label, note = "short squeeze", "shorts being liquidated"
            if (long_share is not None and long_share < 0.4) or (fr is not None and fr < -0.0003):
                label, note = "squeeze fuel", "shorts liquidating while leverage is crowded short"
    return {"label": label, "note": note, "long_pct": long_pct, "total": float(total)}


def _atr(rows, n: int = 14) -> Optional[float]:
    if len(rows) < n + 1:
        return None
    trs = []
    for i in range(1, len(rows)):
        h = rows[i].get("high") or rows[i]["close"]
        l = rows[i].get("low") or rows[i]["close"]
        pc = rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    last = trs[-n:]
    return sum(last) / len(last) if last else None
