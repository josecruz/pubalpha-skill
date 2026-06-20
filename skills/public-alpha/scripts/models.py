"""Contract types passed around the funnel.

pydantic v1 (the installed line — 1.10.x). The big composite artifacts
(Strategy Spec, Backtest Report) are assembled as plain dicts in strategy.py /
backtest.py to match output-contract.md exactly; these models are the
intermediate funnel objects that benefit from validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CallCandidate(BaseModel):
    """A raw call, pre-resolution. Emitted by any CallSource."""

    symbol: Optional[str] = None       # may be unresolved; calls.py resolves to a CMC asset
    raw_text: str                      # the statement (kept short / paraphrased downstream)
    author: str                        # KOL / show / outlet
    source: str                        # "cmc_news" | "cmc_community" | "paste_trade:all-in" | "seed:<id>"
    ts: datetime
    engagement: dict = Field(default_factory=dict)   # likes/comments/views/followers where available
    url: Optional[str] = None
    # Optional, pre-extracted: sources that already did extraction (the seed set, or the
    # agent's LLM extraction over CMC content) may fill these; otherwise calls.py derives them.
    stance: Optional[str] = None       # bullish | bearish | neutral
    conviction: Optional[float] = None # 0..1


class Call(BaseModel):
    """A resolved, scored call (output of calls.py)."""

    symbol: str
    stance: str                        # bullish | bearish | neutral
    conviction: float                  # 0..1
    summary: str                       # <=15-word paraphrase (copyright)
    author: str
    source: str
    ts: datetime
    weight: float = 1.0
    url: Optional[str] = None
    engagement: dict = Field(default_factory=dict)   # carried through for the classifier (followers, likes)


class CallClassification(BaseModel):
    """Verdict from the organic-vs-coordinated classifier (the wedge)."""

    classification: str                # organic | coordinated | mixed
    score: float                       # 0..1 conviction THIS is organic (higher = more organic)
    reasons: list = Field(default_factory=list)      # human-readable drivers — the demo gold
    features: dict = Field(default_factory=dict)     # raw deterministic feature values
    llm: dict = Field(default_factory=dict)          # the structured LLM substance judgment


class OnchainConfirmation(BaseModel):
    """On-chain confirmation verdict (confirm.py), from CMC DEX data."""

    confirmed: bool
    buy_sell_ratio: float
    liquidity_usd: float
    holder_growth_pct: float
    top10_holder_pct: float
    price_runup_pct: float = 0.0       # over the exhaustion lookback; feeds the classifier cross-check
    notes: list = Field(default_factory=list)


class RegimeState(BaseModel):
    """Market regime gate (regime.py)."""

    state: str                         # risk_on | neutral | risk_off
    fear_greed: int
    btc_dominance: float
    altseason: int
    notes: list = Field(default_factory=list)
