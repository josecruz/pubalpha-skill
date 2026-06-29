"""paste.trade CallSource — the operator's robots-allowed public surface.

paste.trade (by Rohun Vora) extracts specific trade "calls" from public shows,
podcasts, newsletters and tweets. Its robots.txt declares exactly what is public:

    Allow:    /api/shows   (the show index AND each show's trades/sources)
              /api/prices  /api/og/  /api/avatars/
    Disallow: /api/trades /api/feed /api/sources /api/leaderboard /api/users
              /api/asset /api/context /api/discover /api/news /api/search /api/stats

So the *shows* (every show in `/api/shows`, plus the trades that belong to them)
are the designated public surface, while the bulk corpus API is gated. This adapter
reads ONLY the allowed `/api/shows` prefix — `_assert_allowed()` hard-blocks every
Disallowed path so the adapter can never wander onto the gated corpus, even by bug.

We honor the content signals (`search=yes, ai-train=no`): we do NOT train on this
content; we surface it for search/browse with attribution and a link back to the
show + source moment. Theses are paraphrased short downstream (the operator reserves
those rights). If the index or an endpoint fails, fetch()/browse() degrade to the
two seed shows or [] so the funnel keeps running offline.
"""
import json
import posixpath
import re
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests

from ..models import CallCandidate
from ..util import RESULTS_DIR, get_key

_HOST = "https://app.paste.trade"
_INDEX_PATH = "/api/shows"
# If the index is unreachable we fall back to these two always-public shows.
SEED_SHOWS = ("all-in", "threadguy")
# robots.txt-allowed API prefixes. We only ever build URLs under these.
_ALLOWED_PREFIXES = ("/api/shows", "/api/prices", "/api/og/", "/api/avatars/")
# robots.txt-Disallowed (gated corpus). Belt-and-suspenders: never request these.
_BLOCKED_PREFIXES = (
    "/api/trades", "/api/feed", "/api/sources", "/api/leaderboard", "/api/users",
    "/api/asset", "/api/context", "/api/discover", "/api/news", "/api/search", "/api/stats",
)
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
_CACHE_TTL = 900  # 15 min — be gentle on their server during a run


_SLUG_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")


def _assert_allowed(path: str) -> None:
    """Guard every request against the robots.txt rules. Refuses anything that is
    Disallowed or that isn't explicitly under an Allowed prefix. Normalizes first so a
    traversal like `/api/shows/../trades` (which requests/urllib3 would collapse to the
    gated `/api/trades`) cannot slip past a naive prefix check."""
    low = path.lower()
    if ".." in path or "//" in path or "%2e" in low or "%2f" in low:
        raise PermissionError(f"unsafe paste.trade path (traversal/encoding): {path}")
    norm = posixpath.normpath(path)
    if any(norm.startswith(b) for b in _BLOCKED_PREFIXES):
        raise PermissionError(f"paste.trade path is robots-Disallowed (gated corpus): {path}")
    if not any(norm.startswith(a) for a in _ALLOWED_PREFIXES):
        raise PermissionError(f"paste.trade path not in robots-allowed surface: {path}")


class PasteTradeSource:
    name = "paste_trade"

    def __init__(self, shows=None, use_cache: bool = True, timeout: int = 30):
        # shows=None -> discover every show in the allowed index (with seed fallback).
        # An explicit list pins the adapter to those slugs (used by tests / targeted runs).
        self._shows = list(shows) if shows is not None else None
        self.use_cache = use_cache
        self.timeout = timeout
        self.token = get_key("PASTE_TRADE_TOKEN")  # optional sanctioned access; not required
        self._index = None  # cached list of show index items

    # --- discovery -------------------------------------------------------

    def index(self) -> List[dict]:
        """The `/api/shows` index: one item per show with metadata
        (id, name, description, channel_url, avatar_url, medium, source_count, trade_count)."""
        if self._index is not None:
            return self._index
        try:
            data = self._get_json(_INDEX_PATH, "paste_cache_index.json")
            items = data.get("items", []) if isinstance(data, dict) else []
            # only keep well-formed slugs — never let a crafted id reach the URL path
            self._index = [it for it in items if it.get("id") and _SLUG_RE.fullmatch(it["id"])]
        except Exception as e:
            print(f"  [paste_trade] index unavailable ({type(e).__name__}: {e}); using seed shows")
            self._index = [{"id": s} for s in SEED_SHOWS]
        return self._index

    def slugs(self) -> List[str]:
        if self._shows is not None:
            return self._shows
        # Only shows that actually have trades are worth fetching.
        return [it["id"] for it in self.index() if (it.get("trade_count") or 0) > 0] or list(SEED_SHOWS)

    # --- call funnel (CallCandidate) ------------------------------------

    def fetch(self, since: Optional[datetime] = None) -> List[CallCandidate]:
        out: List[CallCandidate] = []
        for show in self.slugs():
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

    # --- browser data (streams / speakers / calls) ----------------------

    def browse(self) -> dict:
        """Structured browse data for the paste.trade pages (verbatim content kept, with
        attribution in the UI). Returns {shows[], speakers{}, episodes[], tweets[]} across
        every show in the allowed index. Episodic shows (podcast/newsletter/video) become
        `episodes`; tweet-medium feeds become a flat `tweets` list (one row per call)."""
        index = {it["id"]: it for it in self.index()}
        episodes, tweets, speaker_stats, show_meta = [], [], {}, {}

        for show in self.slugs():
            try:
                payload = self._get_show(show)
            except Exception as e:
                print(f"  [paste_trade browse] {show}: skipped ({type(e).__name__}: {e})")
                continue

            meta = payload.get("show") or index.get(show) or {}
            medium = meta.get("medium")
            is_feed = medium == "tweet"
            counts = show_meta.setdefault(show, {
                "name": meta.get("name") or show, "platform": None, "medium": medium,
                "avatar_url": meta.get("avatar_url"), "channel_url": meta.get("channel_url"),
                "is_feed": is_feed, "n_trades": 0, "n_episodes": 0, "speakers": {}})
            pnl_by_handle = {sp.get("handle"): sp for sp in (payload.get("speakers") or []) if sp.get("handle")}

            for src in payload.get("sources", []):
                s = src.get("source", {})
                if not isinstance(s, dict):
                    continue
                pub = _parse_ts(s.get("published_at"))
                counts["platform"] = counts["platform"] or s.get("platform")
                trades = []
                for tr in src.get("trades", []):
                    if not isinstance(tr, dict):
                        continue
                    tk = (tr.get("display_ticker") or tr.get("ticker") or "").strip().upper()
                    if not tk:
                        continue
                    seg_sec, seg_url = _seg(tr)
                    if seg_sec is not None:
                        vsec = seg_sec
                    else:
                        ad = _parse_ts(tr.get("author_date"))
                        vsec = int((ad - pub).total_seconds()) if (ad and pub) else None
                    if vsec is not None and vsec < 0:
                        vsec = None
                    sp = tr.get("speaker_handle") or tr.get("author_handle") or show
                    row = {
                        "id": tr.get("id"), "ticker": tk, "direction": tr.get("direction"),
                        "bucket": tr.get("bucket"), "staked": bool(tr.get("staked")),
                        "speaker": sp, "speaker_name": tr.get("speaker_name") or tr.get("author_handle"),
                        "speaker_verified": bool(tr.get("speaker_verified")),
                        "platform": s.get("platform"), "instrument": tr.get("instrument"),
                        "video_seconds": vsec, "video_url": seg_url, "author_date": tr.get("author_date"),
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
                    }
                    if is_feed:
                        # flat feed row — keep it lean (no episode context, link is the post itself)
                        tweets.append({
                            "id": row["id"], "show": show, "ticker": tk, "direction": row["direction"],
                            "speaker": sp, "speaker_name": row["speaker_name"],
                            "speaker_verified": row["speaker_verified"], "platform": s.get("platform"),
                            "published_at": s.get("published_at"), "logo_url": row["logo_url"],
                            "entry_price": row["entry_price"], "peak_pct": row["peak_pct"],
                            "headline_quote": row["headline_quote"], "thesis": row["thesis"],
                            "source_url": row["source_url"],
                        })
                    else:
                        trades.append(row)
                    # feed sources are single tweets, not episodes — don't count them as episodes
                    self._tally(speaker_stats, sp, show, None if is_feed else s.get("id"), tr,
                                s.get("platform"), pnl_by_handle.get(sp))
                    counts["speakers"][sp] = counts["speakers"].get(sp, 0) + 1
                    counts["n_trades"] += 1

                if not is_feed and trades:
                    trades.sort(key=lambda t: t["video_seconds"] if t["video_seconds"] is not None else 10 ** 9)
                    episodes.append({
                        "id": s.get("id"), "show": show, "title": s.get("title"), "url": s.get("url"),
                        "platform": s.get("platform"), "published_at": s.get("published_at"),
                        "thumbnail": (s.get("source_images") or [None])[0],
                        "n_positions": sum(t["bucket"] == "Position" for t in trades),
                        "n_ideas": sum(t["bucket"] == "Idea" for t in trades),
                        "trades": trades,
                    })
                    counts["n_episodes"] += 1

        shows = []
        for show, m in show_meta.items():
            streamer = _primary_host(m["speakers"], speaker_stats)
            shows.append({
                "slug": show, "name": m["name"], "platform": m["platform"], "medium": m["medium"],
                "avatar_url": m["avatar_url"], "channel_url": m["channel_url"], "is_feed": m["is_feed"],
                "streamer": streamer, "streamer_name": (speaker_stats.get(streamer) or {}).get("name"),
                "n_episodes": m["n_episodes"], "n_trades": m["n_trades"],
                "n_speakers": len(m["speakers"]), "speakers": sorted(m["speakers"])})
        speakers = {h: _finalize_speaker(st) for h, st in speaker_stats.items()}
        episodes.sort(key=lambda e: e["published_at"] or "", reverse=True)
        tweets.sort(key=lambda t: t["published_at"] or "", reverse=True)
        shows.sort(key=lambda s: -s["n_trades"])
        return {"shows": shows, "speakers": speakers, "episodes": episodes, "tweets": tweets}

    @staticmethod
    def _tally(stats, handle, show, episode_id, tr, platform, pnl):
        """Accumulate a speaker across every show they appear in (the cross-reference)."""
        st = stats.setdefault(handle, {
            "handle": handle, "name": None, "avatar_url": None, "role": None, "verified": False,
            "platform": platform, "n_calls": 0, "long": 0, "short": 0,
            "shows": set(), "episodes": set(),
            "_tc": 0, "_pnl_sum": 0.0, "_pnl_n": 0, "_wins": 0.0, "_wins_n": 0,
            "best": None, "worst": None})
        st["n_calls"] += 1
        st["long"] += tr.get("direction") == "long"
        st["short"] += tr.get("direction") == "short"
        st["verified"] = st["verified"] or bool(tr.get("speaker_verified"))
        st["name"] = st["name"] or tr.get("speaker_name")
        st["shows"].add(show)
        if episode_id:
            st["episodes"].add(episode_id)
        if pnl:  # per-show stats from the show payload's speakers[]; merge once per show
            key = f"_merged::{show}"
            if key not in st:
                st[key] = True
                st["avatar_url"] = st["avatar_url"] or pnl.get("avatar_url")
                st["role"] = st["role"] or pnl.get("role")
                n = pnl.get("trade_count") or 0
                tp = pnl.get("total_pnl")
                wr = pnl.get("win_rate")
                st["_tc"] += n
                # keep each ratio's numerator and denominator paired so a show that reports
                # trade_count but null pnl/win_rate can't dilute avg_pnl/win_rate
                if isinstance(tp, (int, float)):
                    st["_pnl_sum"] += tp
                    st["_pnl_n"] += n
                if isinstance(wr, (int, float)) and n:
                    st["_wins"] += wr * n
                    st["_wins_n"] += n
                for slot, better in (("best", lambda a, b: a > b), ("worst", lambda a, b: a < b)):
                    cand = pnl.get(slot)
                    if cand and isinstance(cand.get("pnl_pct"), (int, float)):
                        cur = st[slot]
                        if cur is None or better(cand["pnl_pct"], cur.get("pnl_pct", 0)):
                            st[slot] = cand

    # --- internals -------------------------------------------------------

    def _get_show(self, show: str) -> dict:
        if not _SLUG_RE.fullmatch(show or ""):
            raise PermissionError(f"unsafe show slug: {show!r}")
        return self._get_json(f"/api/shows/{show}", f"paste_cache_{_safe(show)}.json")

    def _get_json(self, path: str, cache_name: str) -> dict:
        _assert_allowed(path)
        cache = RESULTS_DIR / cache_name
        if self.use_cache and cache.exists() and (time.time() - cache.stat().st_mtime) < _CACHE_TTL:
            return json.loads(cache.read_text())
        headers = dict(_UA)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.get(f"{_HOST}{path}", headers=headers, timeout=self.timeout)
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
            if not isinstance(source, dict):
                continue
            platform = source.get("platform")        # show platform: twitch | youtube | x | ...
            for tr in src.get("trades", []):
                if not isinstance(tr, dict):
                    continue
                # match browse()'s display_ticker so the funnel and the UI key the same symbol
                ticker = (tr.get("display_ticker") or tr.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                ts = _parse_ts(tr.get("author_date") or source.get("published_at"))
                if ts is None:
                    continue
                if since is not None and ts < _aware(since):
                    continue
                seg_sec, seg_url = _seg(tr)
                out.append(
                    CallCandidate(
                        symbol=ticker,
                        raw_text=tr.get("thesis") or f"{tr.get('direction', 'long')} {ticker}",
                        author=tr.get("speaker_handle") or tr.get("author_handle") or source.get("author_id") or show,
                        source=f"paste_trade:{show}",
                        ts=ts,
                        engagement=_engagement(source),
                        url=seg_url or tr.get("source_url") or source.get("url"),
                        stance=_stance(tr.get("direction")),
                        conviction=None,  # calls.py derives; paste.trade has no conviction field
                        platform=platform,
                        verified=bool(tr.get("speaker_verified")),
                        source_id=source.get("id"),
                        video_seconds=seg_sec,
                    )
                )
        return out


def _finalize_speaker(st: dict) -> dict:
    n_pnl, n_win = st["_pnl_n"], st["_wins_n"]
    out = {
        "handle": st["handle"], "name": st["name"], "avatar_url": st["avatar_url"], "role": st["role"],
        "verified": st["verified"], "platform": st["platform"],
        "n_calls": st["n_calls"], "long": st["long"], "short": st["short"],
        "shows": sorted(st["shows"]), "n_episodes": len(st["episodes"]), "episodes": sorted(st["episodes"]),
        "trade_count": st["_tc"] or None,
        "total_pnl": round(st["_pnl_sum"], 2) if n_pnl else None,
        "avg_pnl": round(st["_pnl_sum"] / n_pnl, 2) if n_pnl else None,
        "win_rate": round(st["_wins"] / n_win, 3) if n_win else None,
        "best": st["best"], "worst": st["worst"],
    }
    return out


def _primary_host(speaker_counts: dict, stats: dict) -> str:
    """The show's host = the role=host speaker with the most calls, else the most-frequent speaker."""
    if not speaker_counts:
        return ""
    hosts = [h for h in speaker_counts if (stats.get(h) or {}).get("role") == "host"]
    pool = hosts or list(speaker_counts)
    return max(pool, key=lambda h: speaker_counts.get(h, 0))


def _safe(slug: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", slug)


def _seg(tr: dict):
    """First derivation segment → (video_seconds, deep_source_url). The segment's source_url carries the
    authoritative in-stream moment as `?t=<seconds>s` (author_date − published_at is 0 for YouTube shows)."""
    deriv = tr.get("derivation")
    segs = (deriv.get("segments") if isinstance(deriv, dict) else None) or []
    if not segs or not isinstance(segs[0], dict):
        return None, None
    url = segs[0].get("source_url")
    sec = None
    if url:
        m = re.search(r"[?&]t=(\d+)", url)
        if m:
            sec = int(m.group(1))
    if sec is None:
        parts = (segs[0].get("timestamp") or "").strip("[] ").split(":")
        try:
            nums = [int(p) for p in parts]
            sec = nums[0] * 60 + nums[1] if len(nums) == 2 else nums[0] * 3600 + nums[1] * 60 + nums[2] if len(nums) == 3 else None
        except (ValueError, IndexError):
            sec = None
    return sec, url


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
