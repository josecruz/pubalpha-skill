"""Organic-vs-coordinated classifier — THE wedge.

Given the calls for one symbol over a window, decide whether the pattern looks
like a thesis growing organically or a coordinated burst (a pump). Deterministic
features do the measurable work; a structured substance/language judgment (normally
produced by the agent/LLM and passed in, with a deterministic fallback so this runs
headless) covers what only language understanding can. The output carries
human-readable `reasons` — that's the demo gold and the originality proof.

Nothing here hits the network. Feed it Call objects; it returns a CallClassification.
"""
from datetime import datetime, timezone
from itertools import combinations
from typing import List, Optional, Tuple

from .models import Call, CallClassification, OnchainConfirmation

# Phrases that signal hype/urgency rather than substance. Used by the deterministic
# fallback judgment (the agent's LLM judgment supersedes this when supplied).
_URGENCY_PHRASES = [
    "100x", "1000x", "10x", "don't miss", "dont miss", "last chance", "ape",
    "moon", "pump", "next gem", "gem", "don't fade", "dont fade", "fomo",
    "before it", "too late", "guaranteed", "easy money", "🚀",
]

# Fusion weights (renormalized over whatever features are available).
_WEIGHTS = {
    "timing_clustering": 0.28,
    "language_similarity": 0.28,
    "author_concentration": 0.18,
    "onchain_pump": 0.12,
    "low_substance": 0.14,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _epoch(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ---------------------------------------------------------------------------
# Deterministic features (pure, testable, no network)
# ---------------------------------------------------------------------------

def timing_clustering(calls: List[Call], window_min: int) -> Tuple[float, dict]:
    """1.0 = many calls jammed into one window (coordinated); 0.0 = spread out (organic).

    Uses the largest count of calls inside any rolling window of `window_min`.
    """
    n = len(calls)
    if n < 2:
        return 0.0, {"max_in_window": n, "total": n, "window_min": window_min}
    ts = sorted(_epoch(c.ts) for c in calls)
    win = window_min * 60
    max_in, j = 1, 0
    for i in range(n):
        while ts[i] - ts[j] > win:
            j += 1
        max_in = max(max_in, i - j + 1)
    score = (max_in - 1) / (n - 1)
    return _clamp(score), {"max_in_window": max_in, "total": n, "window_min": window_min}


def _char_ngrams(text: str, n: int = 3) -> set:
    t = "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace())
    t = " ".join(t.split())
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def language_similarity(calls: List[Call]) -> Tuple[float, dict]:
    """1.0 = near-identical phrasing across *different* authors (copypasta); 0.0 = varied.

    Char-3gram Jaccard over cross-author pairs (cheap, no sklearn). We take the mean of
    the top third of pairs so a copypasta ring dominates without one coincidence skewing it.
    """
    if len(calls) < 2:
        return 0.0, {"max_pair": 0.0, "cross_author_pairs": 0}
    grams = [(_char_ngrams(c.summary), c.author) for c in calls]
    cross, allp = [], []
    for (ga, aa), (gb, ab) in combinations(grams, 2):
        s = _jaccard(ga, gb)
        allp.append(s)
        if aa != ab:
            cross.append(s)
    pool = sorted(cross or allp, reverse=True)
    k = max(1, len(pool) // 3)
    score = sum(pool[:k]) / k
    return _clamp(score), {"max_pair": round(max(pool), 3), "cross_author_pairs": len(cross)}


def author_diversity(calls: List[Call], cfg: dict) -> Tuple[float, dict]:
    """1.0 = few / low-credibility authors repeating (coordinated); 0.0 = many distinct, established."""
    authors = [c.author for c in calls]
    distinct, total = len(set(authors)), len(calls)
    min_distinct = cfg.get("min_distinct_authors_for_organic", 3)
    few = _clamp((min_distinct - distinct) / min_distinct) if min_distinct else 0.0
    repetition = 1 - distinct / total if total else 0.0
    foll = [c.engagement.get("followers") for c in calls if c.engagement.get("followers") is not None]
    lowcred = (sum(1 for f in foll if f < 5000) / len(foll)) if foll else 0.0
    score = _clamp(0.4 * few + 0.3 * repetition + 0.3 * lowcred)
    return score, {
        "distinct_authors": distinct, "total": total,
        "low_credibility_share": round(lowcred, 2), "min_distinct": min_distinct,
    }


def onchain_crosscheck(conf: Optional[OnchainConfirmation], cfg: dict) -> Tuple[float, dict]:
    """1.0 = price spiking on thin liquidity (classic pump tell). 0.0 / unavailable = neutral."""
    if conf is None:
        return 0.0, {"available": False}
    if conf.liquidity_usd <= 0:                          # no liquidity/volume data -> can't assess a pump (missing != thin)
        return 0.0, {"available": True, "price_runup_pct": conf.price_runup_pct,
                     "liquidity_usd": 0.0, "thin_liquidity": 0.0, "no_data": True}
    min_liq = cfg.get("confirmation", {}).get("min_liquidity_usd", 25000)
    max_runup = cfg.get("exhaustion", {}).get("max_runup_pct", 50)
    runup_signal = _clamp(conf.price_runup_pct / max_runup) if max_runup else 0.0
    thin = _clamp(1 - conf.liquidity_usd / (min_liq * 4)) if min_liq else 0.0
    score = _clamp(runup_signal * thin)
    return score, {
        "available": True, "price_runup_pct": conf.price_runup_pct,
        "liquidity_usd": conf.liquidity_usd, "thin_liquidity": round(thin, 2),
    }


# ---------------------------------------------------------------------------
# Substance/language judgment (LLM at runtime; deterministic fallback here)
# ---------------------------------------------------------------------------

def fallback_substance(calls: List[Call]) -> dict:
    """Deterministic stand-in for the agent's LLM judgment, so the classifier runs headless."""
    texts = [c.summary.lower() for c in calls]
    hits, per_call = set(), 0
    for t in texts:
        n = 0
        for p in _URGENCY_PHRASES:
            if p in t:
                hits.add(p)
                n += 1
        per_call += n
    density = per_call / max(1, len(texts))
    substance = _clamp(1.0 - density / 3.0)   # ~3 urgency markers/call -> ~0 substance
    return {
        "substance_score": round(substance, 2),
        "urgency_flags": sorted(hits)[:6],
        "language_verdict": None,             # filled from the language feature
        "rationale": "deterministic fallback (no LLM judgment supplied)",
    }


# ---------------------------------------------------------------------------
# Fusion -> verdict
# ---------------------------------------------------------------------------

def classify(
    calls: List[Call],
    symbol: str,
    conf: Optional[OnchainConfirmation] = None,
    cfg: Optional[dict] = None,
    llm_judgment: Optional[dict] = None,
) -> CallClassification:
    """Fuse features + substance judgment into {organic|coordinated|mixed} + score + reasons."""
    cfg = cfg or {}
    ccfg = cfg.get("classifier", {})
    cluster_min = ccfg.get("coordinated_cluster_minutes", 120)
    lang_flag = ccfg.get("language_similarity_flag", 0.85)
    min_distinct = ccfg.get("min_distinct_authors_for_organic", 3)
    organic_threshold = ccfg.get("organic_threshold", 0.6)

    timing, t_meta = timing_clustering(calls, cluster_min)
    lang, l_meta = language_similarity(calls)
    author, a_meta = author_diversity(calls, ccfg)
    onchain, o_meta = onchain_crosscheck(conf, cfg)

    judgment = dict(llm_judgment) if llm_judgment else fallback_substance(calls)
    substance = float(judgment.get("substance_score", 0.5))
    if not judgment.get("language_verdict"):
        judgment["language_verdict"] = (
            "identical" if lang >= lang_flag else "templated" if lang >= 0.5 else "varied"
        )

    features = {
        "timing_clustering": timing,
        "language_similarity": lang,
        "author_concentration": author,
        "onchain_pump": onchain,
        "low_substance": _clamp(1.0 - substance),
    }
    active = {k: w for k, w in _WEIGHTS.items() if not (k == "onchain_pump" and not o_meta.get("available"))}
    coordinated_signal = sum(features[k] * w for k, w in active.items()) / sum(active.values())
    organic_score = _clamp(1.0 - coordinated_signal)

    # hard flags — any one caps the verdict away from "organic"
    flags = []
    if timing >= 0.5 and len(calls) >= 3:   # RELATIVE: cluster dominated by one burst (not a few posts in a big feed)
        flags.append("timing")
    if lang >= lang_flag:
        flags.append("language")
    if a_meta["distinct_authors"] < min_distinct:
        flags.append("authors")

    if organic_score >= organic_threshold and not flags:
        classification = "organic"
    elif len(flags) >= 2 or coordinated_signal >= 0.6:
        classification = "coordinated"
    else:
        classification = "mixed"

    reasons = _build_reasons(
        classification, t_meta, l_meta, a_meta, o_meta, judgment, flags, lang, lang_flag
    )

    return CallClassification(
        classification=classification,
        score=round(organic_score, 3),
        reasons=reasons,
        features={k: round(v, 3) for k, v in features.items()},
        llm=judgment,
    )


def _build_reasons(classification, t_meta, l_meta, a_meta, o_meta, judgment, flags, lang, lang_flag) -> list:
    reasons = []
    # timing
    if "timing" in flags:
        reasons.append(
            f"{t_meta['max_in_window']} of {t_meta['total']} calls within "
            f"{t_meta['window_min']} min → clustered"
        )
    elif t_meta["total"] >= 2:
        reasons.append(f"calls spread out (max {t_meta['max_in_window']} in {t_meta['window_min']} min) → organic timing")
    # language
    if lang >= lang_flag:
        reasons.append(f"near-identical phrasing across authors (3-gram Jaccard {l_meta['max_pair']}) → copypasta")
    elif l_meta.get("cross_author_pairs"):
        reasons.append(f"varied phrasing across authors (max similarity {l_meta['max_pair']})")
    # authors
    if "authors" in flags:
        reasons.append(f"only {a_meta['distinct_authors']} distinct authors; organic needs ≥{a_meta['min_distinct']}")
    else:
        msg = f"{a_meta['distinct_authors']} distinct authors"
        if a_meta["low_credibility_share"] >= 0.6:
            msg += f", {int(a_meta['low_credibility_share'] * 100)}% low-follower accounts"
        reasons.append(msg)
    # on-chain
    if o_meta.get("available") and o_meta.get("thin_liquidity", 0) >= 0.5 and o_meta.get("price_runup_pct", 0) > 0:
        reasons.append(
            f"price +{o_meta['price_runup_pct']}% on ${int(o_meta['liquidity_usd']):,} liquidity → pump tell"
        )
    # substance (LLM)
    sub = judgment.get("substance_score", 0.5)
    if sub <= 0.4:
        flags_txt = ", ".join(judgment.get("urgency_flags", [])[:4]) or "urgency-heavy"
        reasons.append(f"LLM: low substance — {flags_txt}; little thesis")
    elif sub >= 0.6:
        reasons.append(f"LLM: substantive thesis (substance {sub})")
    return reasons
