"""Offline check of the decision skills (decide.py). Deterministic, no network.

Run: python3 skills/public-alpha/tests/test_decide.py
Expects:
  - spot_breakout flags an upside breakout when today closes above the prior 20d high on volume.
  - spot_breakout returns is_breakout=False for a declining series.
  - kol_sentiment is bullish for an organic bullish cluster, and is DOWN-weighted when coordinated.
  - perp_breakout marks a long bias on a breakout into negative funding (short-squeeze fuel).
"""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # skills/public-alpha/
sys.path.insert(0, ROOT)

from scripts.decide import kol_sentiment, perp_breakout, spot_breakout   # noqa: E402


def _series(closes, vol=100.0):
    return [{"ts": f"2026-01-{i + 1:02d}", "open": c, "high": c, "low": c, "close": c, "volume": vol}
            for i, c in enumerate(closes)]


def _call(stance, conviction=0.5, author="kol"):
    return SimpleNamespace(stance=stance, conviction=conviction, author=author)


def main() -> int:
    ok = True

    # 1. breakout: 25 flat days at 100, then a close at 110 on 3x volume
    candles = _series([100.0] * 25)
    candles[-1] = {**candles[-1], "close": 110.0, "high": 110.0, "volume": 300.0}
    bo = spot_breakout(candles)
    print("breakout(up)  :", {k: bo.get(k) for k in ("is_breakout", "pct_above_20d_high", "vol_mult", "strength")})
    ok &= bo.get("is_breakout") is True and (bo.get("vol_mult") or 0) >= 2.5

    # 2. no breakout: declining series
    bod = spot_breakout(_series([100.0 - i for i in range(25)]))
    print("breakout(down):", {k: bod.get(k) for k in ("is_breakout", "strength")})
    ok &= bod.get("is_breakout") is False

    # 3. KOL sentiment: same bullish cluster, organic vs coordinated (down-weighted)
    bulls = [_call("bullish", 0.7, f"a{i}") for i in range(4)] + [_call("bearish", 0.5, "b")]
    org, coord = kol_sentiment(bulls, "organic"), kol_sentiment(bulls, "coordinated")
    print("sentiment     : organic", org["label"], org["score"], "| coordinated", coord["label"], coord["score"])
    ok &= org["label"] == "bullish" and org["score"] > coord["score"]

    # 4. perp: breakout + negative funding => long (short-squeeze fuel)
    perp = perp_breakout(
        {"funding_rate": -0.0008, "open_interest": 1e9, "perp_volume_24h": 5e9, "venue": "Binance", "venues": []},
        {"is_breakout": True, "strength": 0.6})
    print("perp          :", perp["bias"], perp["score"])
    ok &= "long" in perp["bias"] and perp["score"] > 0.5

    print("\n" + ("OK: decision skills behave as expected." if ok else "FAIL: a decision-skill check did not hold."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
