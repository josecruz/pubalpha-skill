"""paste.trade CallSource — allowed public surface only.

paste.trade (by Rohun Vora) extracts specific trade "calls" from public shows.
Its robots.txt + a server-side read-gate keep the bulk corpus API
(/api/trades, /api/feed, …) private and block AI crawlers — we do NOT touch those.

But the operator explicitly designates the two curated shows and *the trades that
belong to them* as the public surface, and the per-show data lives under the
robots-ALLOWED `/api/shows/<id>` prefix. Content signals: search=yes, ai-train=no
(we don't train), ai-input unspecified. So this adapter reads ONLY
`/api/shows/{all-in,threadguy}` and parses the trades those shows publish. Theses
are paraphrased short downstream (copyright / the operator's reserved rights).

If the endpoint shape changes or the network fails, fetch() returns [] and the
funnel falls back to CMC content + the seed set.
"""
import json
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests

from ..models import CallCandidate
from ..util import RESULTS_DIR, get_key

# The operator's public surface is exactly these two curated shows. We hard-allow
# only them so the adapter can never wander onto gated/other paths.
ALLOWED_SHOWS = ("all-in", "threadguy")
_BASE = "https://app.paste.trade/api/shows"
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
_CACHE_TTL = 900  # 15 min — be gentle on their server during a run


class PasteTradeSource:
    name = "paste_trade"

    def __init__(self, shows=ALLOWED_SHOWS, use_cache: bool = True, timeout: int = 30):
        self.shows = [s for s in shows if s in ALLOWED_SHOWS]
        self.use_cache = use_cache
        self.timeout = timeout
        self.token = get_key("PASTE_TRADE_TOKEN")  # optional sanctioned access; unused for gated paths

    def fetch(self, since: Optional[datetime] = None) -> List[CallCandidate]:
        out: List[CallCandidate] = []
        for show in self.shows:
            try:
                payload = self._get_show(show)
            except Exception as e:  # network/shape failure -> degrade gracefully
                print(f"  [paste_trade] {show}: skipped ({type(e).__name__}: {e})")
                continue
            out.extend(self._parse(show, payload, since))
        # promote: if a speaker is verified on ANY trade, treat them as verified everywhere
        verified = {c.author for c in out if c.verified}
        for c in out:
            if c.author in verified:
                c.verified = True
        return out

    def browse(self) -> dict:
        """Structured browse data for the paste.trade pages (verbatim content kept, with attribution
        in the UI). Returns {shows[], speakers{}, episodes[]} from the allowed shows only."""
        episodes, speaker_stats, show_meta = [], {}, {}
        for show in self.shows:
            try:
                payload = self._get_show(show)
            except Exception as e:
                print(f"  [paste_trade browse] {show}: skipped ({type(e).__name__}: {e})")
                continue
            counts = show_meta.setdefault(show, {"platform": None, "n_trades": 0, "speakers": {}})
            for src in payload.get("sources", []):
                s = src.get("source", {})
                pub = _parse_ts(s.get("published_at"))
                counts["platform"] = counts["platform"] or s.get("platform")
                trades = []
                for tr in src.get("trades", []):
                    tk = (tr.get("display_ticker") or tr.get("ticker") or "").strip().upper()
                    if not tk:
                        continue
                    ad = _parse_ts(tr.get("author_date"))
                    vsec = int((ad - pub).total_seconds()) if (ad and pub) else None
                    if vsec is not None and vsec < 0:
                        vsec = None
                    sp = tr.get("speaker_handle") or tr.get("author_handle") or show
                    trades.append({
                        "id": tr.get("id"), "ticker": tk, "direction": tr.get("direction"),
                        "bucket": tr.get("bucket"), "staked": bool(tr.get("staked")),
                        "speaker": sp, "speaker_name": tr.get("speaker_name"),
                        "speaker_verified": bool(tr.get("speaker_verified")),
                        "platform": s.get("platform"), "instrument": tr.get("instrument"),
                        "video_seconds": vsec, "author_date": tr.get("author_date"),
                        "entry_price": tr.get("author_price"), "posted_price": tr.get("posted_price"),
                        "peak_pct": tr.get("peak_pct"), "market_cap_fmt": tr.get("market_cap_fmt"),
                        "logo_url": tr.get("logo_url"),
                        "headline_quote": tr.get("headline_quote"), "thesis": tr.get("thesis"),
                        "trade_summary": tr.get("trade_summary"), "ticker_context": tr.get("ticker_context"),
                        "edge_note": tr.get("edge_note"), "caveat": tr.get("caveat"),
                        "horizon": tr.get("horizon"), "target": tr.get("target"),
                        "catalyst": tr.get("catalyst"), "facts": tr.get("facts") or [],
                        "chain_steps": tr.get("chain_steps_card") or [],
                        "source_url": tr.get("source_url") or s.get("url"),
                    })
                    st = speaker_stats.setdefault(sp, {
                        "handle": sp, "name": tr.get("speaker_name"), "verified": False,
                        "platform": s.get("platform"), "n_calls": 0, "long": 0, "short": 0,
                        "shows": set(), "episodes": set()})
                    st["n_calls"] += 1
                    st["long"] += tr.get("direction") == "long"
                    st["short"] += tr.get("direction") == "short"
                    st["verified"] = st["verified"] or bool(tr.get("speaker_verified"))
                    st["name"] = st["name"] or tr.get("speaker_name")
                    st["shows"].add(show)
                    st["episodes"].add(s.get("id"))
                    counts["speakers"][sp] = counts["speakers"].get(sp, 0) + 1
                counts["n_trades"] += len(trades)
                trades.sort(key=lambda t: t["video_seconds"] if t["video_seconds"] is not None else 10 ** 9)
                episodes.append({
                    "id": s.get("id"), "show": show, "title": s.get("title"), "url": s.get("url"),
                    "platform": s.get("platform"), "published_at": s.get("published_at"),
                    "thumbnail": (s.get("source_images") or [None])[0],
                    "n_positions": sum(t["bucket"] == "Position" for t in trades),
                    "n_ideas": sum(t["bucket"] == "Idea" for t in trades),
                    "trades": trades,
                })

        shows = []
        for show, m in show_meta.items():
            streamer = max(m["speakers"], key=m["speakers"].get) if m["speakers"] else show
            shows.append({"slug": show, "platform": m["platform"], "streamer": streamer,
                          "streamer_name": (speaker_stats.get(streamer) or {}).get("name"),
                          "n_episodes": sum(1 for e in episodes if e["show"] == show),
                          "n_trades": m["n_trades"], "speakers": sorted(m["speakers"])})
        speakers = {h: {**st, "shows": sorted(st["shows"]),
                        "n_episodes": len(st["episodes"]), "episodes": sorted(st["episodes"])}
                    for h, st in speaker_stats.items()}
        episodes.sort(key=lambda e: e["published_at"] or "", reverse=True)
        return {"shows": shows, "speakers": speakers, "episodes": episodes}

    # --- internals -------------------------------------------------------

    def _get_show(self, show: str) -> dict:
        cache = RESULTS_DIR / f"paste_cache_{show}.json"
        if self.use_cache and cache.exists() and (time.time() - cache.stat().st_mtime) < _CACHE_TTL:
            return json.loads(cache.read_text())
        headers = dict(_UA)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.get(f"{_BASE}/{show}", headers=headers, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if self.use_cache:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
        return data

    def _parse(self, show: str, payload: dict, since: Optional[datetime]) -> List[CallCandidate]:
        out: List[CallCandidate] = []
        for src in payload.get("sources", []):
            source = src.get("source", {})
            platform = source.get("platform")        # show platform: twitch | youtube | x | ...
            for tr in src.get("trades", []):
                ticker = (tr.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                ts = _parse_ts(tr.get("author_date") or source.get("published_at"))
                if ts is None:
                    continue
                if since is not None and ts < _aware(since):
                    continue
                out.append(
                    CallCandidate(
                        symbol=ticker,
                        raw_text=tr.get("thesis") or f"{tr.get('direction', 'long')} {ticker}",
                        author=tr.get("author_handle") or source.get("author_id") or show,
                        source=f"paste_trade:{show}",
                        ts=ts,
                        engagement=_engagement(source),
                        url=tr.get("source_url") or source.get("url"),
                        stance=_stance(tr.get("direction")),
                        conviction=None,  # calls.py derives; paste.trade has no conviction field
                        platform=platform,
                        verified=bool(tr.get("speaker_verified")),
                        source_id=source.get("id"),
                    )
                )
        return out


def _stance(direction: Optional[str]) -> str:
    d = (direction or "").lower()
    if d in ("long", "buy", "bull"):
        return "bullish"
    if d in ("short", "sell", "bear"):
        return "bearish"
    return "neutral"


def _engagement(source: dict) -> dict:
    e = {}
    for k_src, k_dst in (("engagement_views", "views"), ("engagement_likes", "likes"),
                         ("engagement_retweets", "retweets")):
        if source.get(k_src) is not None:
            e[k_dst] = source[k_src]
    return e


def _parse_ts(s) -> Optional[datetime]:
    if not s:
        return None
    txt = str(s).replace("Z", "+00:00")
    dt = None
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        try:
            dt = datetime.strptime(str(s), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # always tz-aware


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
