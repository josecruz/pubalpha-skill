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
    """Gate on whatever on-chain signals are available, honestly.

    We evaluate a check only when its input is present; absent inputs are noted, not
    failed (CMC's DEX API doesn't expose holders, and pool liquidity/buy-sell can be
    unavailable on some tiers). Confirmation requires a real activity signal (pool
    liquidity OR aggregated DEX volume above the floor) and that no *evaluated* check fails.
    """
    ccfg = (cfg or {}).get("confirmation", {})
    min_liq = ccfg.get("min_liquidity_usd", 25000)
    min_ratio = ccfg.get("min_buy_sell_ratio", 1.1)
    max_top10 = ccfg.get("max_top10_holder_pct", 70)

    if not metrics:
        return OnchainConfirmation(confirmed=False, buy_sell_ratio=0.0, liquidity_usd=0.0,
                                   holder_growth_pct=0.0, top10_holder_pct=0.0, price_runup_pct=0.0,
                                   notes=["no on-chain data available — treated as unconfirmed"])
    m = metrics
    runup = float(m.get("price_runup_pct", 0.0) or 0.0)
    checks, notes = [], []           # checks: list of (name, passed); activity flag tracked separately
    activity_ok = False

    liq = m.get("liquidity_usd")
    dex_vol = m.get("dex_volume_24h")
    if liq is not None:
        ok = liq >= min_liq; checks.append(ok); activity_ok = activity_ok or ok
        notes.append(f"pool liquidity ${int(liq):,} {'≥' if ok else '<'} ${int(min_liq):,}")
    elif dex_vol:
        ok = dex_vol >= min_liq; checks.append(ok); activity_ok = activity_ok or ok
        notes.append(f"24h on-chain DEX volume ${int(dex_vol):,} {'≥' if ok else '<'} ${int(min_liq):,}")
    else:
        notes.append("no liquidity/DEX-volume data")

    buy, sell = m.get("buy_volume_24h"), m.get("sell_volume_24h")
    ratio = 0.0
    if buy is not None and sell is not None:
        ratio = _ratio(float(buy), float(sell))
        ok = ratio >= min_ratio; checks.append(ok)
        notes.append(f"buy/sell {round(ratio, 2)} {'≥' if ok else '<'} {min_ratio}")
    else:
        notes.append("buy/sell split not exposed by CMC DEX")

    growth = m.get("holder_growth_pct")
    if growth is not None:
        ok = float(growth) > 0; checks.append(ok)
        notes.append(f"holders {'+' if float(growth) >= 0 else ''}{growth}%" + ("" if ok else " (not growing)"))
    else:
        notes.append("holder data not exposed by CMC DEX")

    top10 = m.get("top10_holder_pct")
    if top10 is not None:
        ok = float(top10) <= max_top10; checks.append(ok)
        notes.append(f"top-10 hold {top10}% {'≤' if ok else '>'} {max_top10}%")

    if m.get("onchain_source") == "cmc_aggregated_dex_volume":
        notes.append("source: CMC aggregated on-chain DEX volume (pool-level split unavailable on tier)")

    confirmed = activity_ok and all(checks)
    return OnchainConfirmation(
        confirmed=confirmed,
        buy_sell_ratio=round(ratio, 2),
        liquidity_usd=float(liq if liq is not None else (dex_vol or 0.0)),
        holder_growth_pct=float(growth) if growth is not None else 0.0,
        top10_holder_pct=float(top10) if top10 is not None else 0.0,
        price_runup_pct=runup,
        notes=notes,
    )
