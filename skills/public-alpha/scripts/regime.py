"""Regime gate — only take risk when the macro backdrop permits.

Maps raw market inputs (Fear & Greed, BTC dominance, altcoin-season index) to a
risk_on / neutral / risk_off state. Thresholds come from config; dominance and
altseason refine the call but Fear & Greed is the primary lever (per the spec).
"""
from .models import RegimeState


def get_state(inputs: dict, cfg: dict) -> RegimeState:
    rcfg = (cfg or {}).get("regime", {})
    risk_off_below = rcfg.get("fear_greed_risk_off_below", 25)
    risk_on_above = rcfg.get("fear_greed_risk_on_above", 55)

    m = inputs or {}
    fg = int(m.get("fear_greed", 50))
    dom = float(m.get("btc_dominance", 50.0))
    alt = int(m.get("altseason", 50))

    if fg < risk_off_below:
        state = "risk_off"
    elif fg >= risk_on_above:
        state = "risk_on"
    else:
        state = "neutral"

    notes = [
        f"Fear & Greed {fg} ({_fg_label(fg)})",
        f"BTC dominance {dom}%",
        f"altcoin-season index {alt}",
    ]
    return RegimeState(state=state, fear_greed=fg, btc_dominance=dom, altseason=alt, notes=notes)


def _fg_label(fg: int) -> str:
    if fg < 25:
        return "extreme fear"
    if fg < 45:
        return "fear"
    if fg < 55:
        return "neutral"
    if fg < 75:
        return "greed"
    return "extreme greed"
