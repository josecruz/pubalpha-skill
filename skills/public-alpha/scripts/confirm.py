"""On-chain confirmation — the deterministic gate after the classifier.

Takes raw on-chain metrics (from a MarketSource, e.g. CMC DEX) and asks: is money
actually moving into this token, or is it a thin/distributing trap? Confirmed only
if liquidity is deep enough, buys outpace sells, holders are growing, and ownership
isn't dangerously concentrated. Every check is reported so the agent can narrate it.
"""
from typing import Optional

from .models import OnchainConfirmation


def _ratio(buy: float, sell: float) -> float:
    if sell > 0:
        return buy / sell
    return 99.0 if buy > 0 else 0.0


def confirm(metrics: Optional[dict], cfg: dict) -> OnchainConfirmation:
    """Apply the confirmation thresholds from config to raw on-chain metrics."""
    ccfg = (cfg or {}).get("confirmation", {})
    min_liq = ccfg.get("min_liquidity_usd", 25000)
    min_ratio = ccfg.get("min_buy_sell_ratio", 1.1)
    require_growth = ccfg.get("require_holder_growth", True)
    max_top10 = ccfg.get("max_top10_holder_pct", 70)

    m = metrics or {}
    liq = float(m.get("liquidity_usd", 0.0) or 0.0)
    buy = float(m.get("buy_volume_24h", 0.0) or 0.0)
    sell = float(m.get("sell_volume_24h", 0.0) or 0.0)
    growth = float(m.get("holder_growth_pct", 0.0) or 0.0)
    top10 = float(m.get("top10_holder_pct", 100.0) if m.get("top10_holder_pct") is not None else 100.0)
    runup = float(m.get("price_runup_pct", 0.0) or 0.0)
    ratio = _ratio(buy, sell)

    checks = {
        "liquidity": liq >= min_liq,
        "buy_sell": ratio >= min_ratio,
        "holder_growth": (growth > 0) if require_growth else True,
        "concentration": top10 <= max_top10,
    }
    notes = []
    if checks["liquidity"]:
        notes.append(f"liquidity ${int(liq):,} ≥ ${int(min_liq):,}")
    else:
        notes.append(f"liquidity ${int(liq):,} below floor ${int(min_liq):,}")
    notes.append(f"buy/sell {round(ratio, 2)} {'≥' if checks['buy_sell'] else '<'} {min_ratio}")
    notes.append(f"holders {'+' if growth >= 0 else ''}{growth}%" + ("" if checks["holder_growth"] else " (not growing)"))
    notes.append(f"top-10 hold {top10}% {'≤' if checks['concentration'] else '>'} {max_top10}%")

    if not metrics:
        notes.append("no on-chain data available — treated as unconfirmed")

    return OnchainConfirmation(
        confirmed=bool(metrics) and all(checks.values()),
        buy_sell_ratio=round(ratio, 2),
        liquidity_usd=liq,
        holder_growth_pct=growth,
        top10_holder_pct=top10,
        price_runup_pct=runup,
        notes=notes,
    )
