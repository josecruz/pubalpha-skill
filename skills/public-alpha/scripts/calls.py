"""Normalize raw CallCandidates into resolved, scored Call objects.

If a candidate already carries stance/conviction (seed set, or the agent's LLM
extraction over CMC content), we trust it; otherwise we derive a lightweight
keyword-based fallback so the pipeline still runs headless. Evidence summaries
are truncated to a short paraphrase (copyright).
"""
from collections import defaultdict
from typing import Dict, List

from .models import Call, CallCandidate

_BULLISH = {
    "buy", "long", "bullish", "undervalued", "accumulate", "moon", "100x", "10x",
    "1000x", "breakout", "send", "ape", "gem", "pump", "bull", "higher", "tighter",
    "cashflow", "revenue",
}
_BEARISH = {
    "sell", "short", "bearish", "overvalued", "dump", "rug", "avoid", "exit",
    "lower", "bear", "down", "crash",
}
# longer-form / more accountable sources carry more weight than anonymous X posts
_SOURCE_WEIGHT = {
    "podcast": 1.0, "show": 0.95, "substack": 0.9, "cmc_news": 0.9,
    "alexandria": 0.9, "cmc_community": 0.7, "paste_trade": 0.75, "x": 0.6,
}


def _source_weight(source: str) -> float:
    s = source.lower()
    for key, w in _SOURCE_WEIGHT.items():
        if key in s:
            return w
    return 0.7


def _derive_stance(text: str) -> str:
    toks = set(_tokenize(text))
    if toks & _BULLISH and not (toks & _BEARISH):
        return "bullish"
    if toks & _BEARISH and not (toks & _BULLISH):
        return "bearish"
    if toks & _BULLISH:
        return "bullish"
    return "neutral"


def _derive_conviction(text: str, engagement: dict) -> float:
    toks = _tokenize(text)
    strong = sum(1 for t in toks if t in {"100x", "1000x", "must", "huge", "guaranteed"})
    base = 0.5 + 0.1 * strong
    return _clamp(base)


def _tokenize(text: str) -> List[str]:
    return [t.strip("$#!.,'\"").lower() for t in text.split()]


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalize(candidates: List[CallCandidate], cfg: dict) -> List[Call]:
    """CallCandidate[] -> Call[]: resolve symbol, set stance/conviction, paraphrase, weight, filter."""
    calls_cfg = (cfg or {}).get("calls", {})
    min_conviction = calls_cfg.get("min_conviction", 0.4)
    max_words = calls_cfg.get("evidence_max_words", 15)

    out: List[Call] = []
    for c in candidates:
        if not c.symbol:
            continue  # unresolved symbol — a live extractor/agent would resolve via CMC search
        symbol = c.symbol.strip().lstrip("$").upper()
        stance = c.stance or _derive_stance(c.raw_text)
        conviction = c.conviction if c.conviction is not None else _derive_conviction(c.raw_text, c.engagement)
        if conviction < min_conviction:
            continue
        weight = _clamp(0.6 * conviction + 0.4 * _source_weight(c.source))
        out.append(
            Call(
                symbol=symbol,
                stance=stance,
                conviction=round(conviction, 3),
                summary=_paraphrase(c.raw_text, max_words),
                author=c.author,
                source=c.source,
                ts=c.ts,
                weight=round(weight, 3),
                url=c.url,
                engagement=c.engagement,
            )
        )
    return out


def _paraphrase(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def group_by_symbol(calls: List[Call]) -> Dict[str, List[Call]]:
    by: Dict[str, List[Call]] = defaultdict(list)
    for c in calls:
        by[c.symbol].append(c)
    return dict(by)
