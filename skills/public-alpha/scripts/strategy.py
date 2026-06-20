"""Assemble the Strategy Spec (output-contract.md §1) from the funnel outputs.

Rules are explicit, inspectable strings (and a typed mirror the backtester reads) —
never opaque model output. The thesis is written by the agent (LLM) at runtime and
passed in; a deterministic fallback keeps the Skill runnable headless.
"""
from datetime import datetime, timezone
from typing import List, Optional

from .models import Call, CallClassification, OnchainConfirmation, RegimeState

SPEC_VERSION = "1.0"


def _confidence(cls: CallClassification, conf: Optional[OnchainConfirmation], regime: Optional[RegimeState]) -> float:
    c = cls.score
    c *= 1.0 if (conf and conf.confirmed) else 0.55
    if regime is not None:
        c *= 1.0 if regime.state in ("risk_on", "neutral") else 0.45
    return round(max(0.0, min(1.0, c)), 2)


def _entry_rules(cfg: dict) -> List[str]:
    ccfg = cfg.get("classifier", {})
    excfg = cfg.get("exhaustion", {})
    return [
        "narrative.heating == true",
        f"calls.score >= {ccfg.get('organic_threshold', 0.6)} AND calls.classification == 'organic'",
        "onchain_confirmation.confirmed == true",
        "regime.state in ['risk_on','neutral']",
        f"not_exhausted (price_runup_pct < {excfg.get('max_runup_pct', 50)} over {excfg.get('lookback_hours', 24)}h)",
    ]


def _evidence(calls: List[Call], limit: int = 4) -> List[dict]:
    top = sorted(calls, key=lambda c: c.weight, reverse=True)[:limit]
    return [
        {"source": c.source, "ts": c.ts.isoformat(), "stance": c.stance,
         "summary": c.summary, "weight": c.weight}
        for c in top
    ]


def fallback_thesis(symbol: str, cls: CallClassification, conf: Optional[OnchainConfirmation],
                    regime: Optional[RegimeState]) -> str:
    bits = [f"{symbol}: calls classified {cls.classification} (organic score {cls.score})."]
    if cls.reasons:
        bits.append("Drivers: " + "; ".join(cls.reasons[:2]) + ".")
    if conf is not None:
        if conf.buy_sell_ratio and conf.buy_sell_ratio > 0:
            detail = f"buy/sell {conf.buy_sell_ratio}, liquidity ${int(conf.liquidity_usd):,}"
        else:
            detail = conf.notes[0] if conf.notes else f"liquidity ${int(conf.liquidity_usd):,}"
        bits.append("On-chain " + ("confirmed" if conf.confirmed else "NOT confirmed") + f" ({detail}).")
    if regime is not None:
        bits.append(f"Regime {regime.state} (F&G {regime.fear_greed}).")
    return " ".join(bits)


def assemble_spec(
    symbol: str,
    cls: CallClassification,
    calls: List[Call],
    conf: Optional[OnchainConfirmation],
    regime: Optional[RegimeState],
    narrative: dict,
    cfg: dict,
    chain: str = "bsc",
    universe: Optional[List[str]] = None,
    risk_profile: str = "balanced",
    horizon: Optional[str] = None,
    lookback_days: Optional[int] = None,
    thesis: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> dict:
    skill_cfg = cfg.get("skill", {})
    profiles = skill_cfg.get("risk_profiles", {})
    rp = profiles.get(risk_profile, profiles.get("balanced", {}))
    risk_limits = cfg.get("risk_limits", {})
    horizon = horizon or skill_cfg.get("default_horizon", "swing/days")
    lookback_days = lookback_days or skill_cfg.get("default_lookback_days", 30)
    universe = universe or [symbol]
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sources = sorted({c.source for c in calls})

    spec = {
        "strategy": {
            "name": f"public-alpha-{cls.classification}-{symbol.lower()}",
            "version": SPEC_VERSION,
            "generated_at": generated_at,
            "universe": {"chain": chain, "assets": universe},
            "risk_profile": risk_profile,
            "horizon": horizon,
            "lookback": f"{lookback_days}d",
        },
        "signals": {
            "narrative": narrative or {"heating": False, "source": "cmc_community_topics+categories"},
            "calls": {
                "symbol": symbol,
                "score": cls.score,
                "classification": cls.classification,
                "reasons": cls.reasons,
                "sources": sources,
                "n_calls": len(calls),
                "evidence": _evidence(calls),
            },
            "onchain_confirmation": (
                {"confirmed": conf.confirmed, "buy_sell_ratio": conf.buy_sell_ratio,
                 "liquidity_usd": conf.liquidity_usd, "holder_growth_pct": conf.holder_growth_pct,
                 "top10_holder_pct": conf.top10_holder_pct, "notes": conf.notes}
                if conf is not None else {"confirmed": False, "available": False}
            ),
            "regime": (
                {"state": regime.state, "fear_greed": regime.fear_greed,
                 "btc_dominance": regime.btc_dominance, "altseason": regime.altseason}
                if regime is not None else {"state": "unknown", "available": False}
            ),
        },
        "rules": {
            "entry": _entry_rules(cfg),
            "exit": {
                "stop_loss_pct": rp.get("stop_loss_pct", -8),
                "take_profit_pct": rp.get("take_profit_pct", 25),
                "time_stop": "72h",
                "invalidations": [
                    "calls.classification -> coordinated",
                    "onchain distribution (buy_sell_ratio < 0.8)",
                    "attention fades AND price breaks entry",
                ],
            },
            "position_sizing": {
                "base_pct": rp.get("base_pct", 3),
                "confidence_scaled": True,
                "max_position_pct": rp.get("max_position_pct", 10),
            },
            "risk_limits": {
                "max_total_exposure_pct": risk_limits.get("max_total_exposure_pct", 50),
                "max_drawdown_guard_pct": risk_limits.get("max_drawdown_guard_pct", 20),
            },
        },
        "thesis": thesis or fallback_thesis(symbol, cls, conf, regime),
        "confidence": _confidence(cls, conf, regime),
        "entry_signal": _entry_fires(cls, conf, regime, narrative, cfg),
        "backtest_ref": None,
    }
    return spec


def _entry_fires(cls, conf, regime, narrative, cfg) -> bool:
    """Whether the entry conditions are all met right now (the live verdict)."""
    organic_threshold = cfg.get("classifier", {}).get("organic_threshold", 0.6)
    checks = [
        bool(narrative and narrative.get("heating")),
        cls.classification == "organic" and cls.score >= organic_threshold,
        conf is not None and conf.confirmed,
        regime is not None and regime.state in ("risk_on", "neutral"),
    ]
    return all(checks)
