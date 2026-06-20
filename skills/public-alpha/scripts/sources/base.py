"""Source protocols — the pluggable interface.

This is how CMC, paste.trade, the seed set, and (later) live extractors all slot
in behind the same shape. The funnel only ever talks to these protocols, so a
swapped call feed never touches the classifier/strategy/backtest code.
"""
from datetime import datetime
from typing import List, Protocol, runtime_checkable

from ..models import CallCandidate


@runtime_checkable
class CallSource(Protocol):
    """Emits raw call candidates over a time window."""

    name: str

    def fetch(self, since: datetime) -> List[CallCandidate]:
        ...


@runtime_checkable
class MarketSource(Protocol):
    """Quotes, OHLCV, on-chain, and regime inputs (CMC is the default impl)."""

    name: str

    def quotes(self, symbols: List[str]) -> dict:
        ...

    def ohlcv(self, symbol: str, interval: str, start: datetime, end: datetime) -> List[dict]:
        """List of candles: {ts, open, high, low, close, volume}."""
        ...

    def onchain(self, symbol: str) -> dict:
        """Raw on-chain metrics for the token. confirm.py applies the gate logic.
        Keys: liquidity_usd, buy_volume_24h, sell_volume_24h, holder_growth_pct,
        top10_holder_pct, price_runup_pct.
        """
        ...

    def regime_inputs(self) -> dict:
        """Raw regime inputs. regime.py applies thresholds.
        Keys: fear_greed, btc_dominance, altseason.
        """
        ...


@runtime_checkable
class AttentionSource(Protocol):
    """Narrative-heating inputs."""

    name: str

    def trending(self) -> List[dict]:
        ...

    def categories(self) -> List[dict]:
        ...
