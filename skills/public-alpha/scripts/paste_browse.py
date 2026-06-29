"""paste.trade browser data + CLI — the same streams/speakers/calls the web pages show.

Default (no args): (re)build results/paste.json from the operator's allowed public surface
(PasteTradeSource.browse) + a CMC-derived since-call % where the ticker resolves (collision-guarded).

Query commands (so the agent/CLI has the same info as the web — read results/paste.json, build if missing):
    python3 skills/public-alpha/scripts/paste_browse.py                 # (re)build paste.json
    python3 skills/public-alpha/scripts/paste_browse.py --shows         # list all shows
    python3 skills/public-alpha/scripts/paste_browse.py --list [--show <slug>]      # list episodes
    python3 skills/public-alpha/scripts/paste_browse.py --tweets        # the flat tweet/X call feed
    python3 skills/public-alpha/scripts/paste_browse.py --stream <id>   # an episode's calls
    python3 skills/public-alpha/scripts/paste_browse.py --speakers      # top speakers/traders
    python3 skills/public-alpha/scripts/paste_browse.py --speaker <handle>          # a speaker's calls
Content is from paste.trade (every show in its robots-allowed /api/shows surface) and credited.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sources.paste_trade import PasteTradeSource   # noqa: E402
from scripts.util import RESULTS_DIR, get_key               # noqa: E402

PASTE_JSON = RESULTS_DIR / "paste.json"


def _cmc():
    if not get_key("CMC_PRO_API_KEY"):
        return None
    try:
        from scripts.sources.cmc import CMCSource
        return CMCSource()
    except Exception as e:
        print(f"[cmc] unavailable: {e}", file=sys.stderr)
        return None


def build() -> dict:
    """Pull the allowed surface (every show in /api/shows), enrich with collision-guarded
    since-call %, write paste.json."""
    data = PasteTradeSource().browse()
    eps, tweets = data["episodes"], data.get("tweets", [])
    print(f"  {len(data['shows'])} shows · {len(eps)} episodes · {len(tweets)} tweets · {len(data['speakers'])} speakers")
    # every priceable call across episodic trades + the tweet feed shares one CMC lookup
    rows = [t for e in eps for t in e["trades"]] + tweets
    market = _cmc()
    if market is not None and rows:
        try:
            mkt = market.market_block(sorted({t["ticker"] for t in rows}))
        except Exception as e:
            print(f"[market_block] {e}", file=sys.stderr)
            mkt = {}
        n = 0
        for t in rows:
            m, entry = mkt.get(t["ticker"]), t.get("entry_price")
            if not (m and m.get("price") and entry):
                continue
            if not (0.25 <= m["price"] / entry <= 4.0):   # guard stock↔crypto ticker collisions
                continue
            t["cmc_symbol"], t["cmc_price"] = t["ticker"], m["price"]
            t["since_call_pct"] = round((m["price"] - entry) / entry * 100, 2)
            n += 1
        print(f"  since-call % attached for {n} calls (CMC-priceable, collision-guarded)")
    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **data}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PASTE_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"-> {PASTE_JSON}")
    return out


def _load() -> dict:
    return json.loads(PASTE_JSON.read_text()) if PASTE_JSON.exists() else build()


def _pct(v):
    return f"{v:+.1f}%" if isinstance(v, (int, float)) else "—"


def _mmss(s):
    return f"{s // 60}:{s % 60:02d}" if isinstance(s, int) and s >= 0 else "—"


def main():
    ap = argparse.ArgumentParser(description="paste.trade browser data + CLI")
    ap.add_argument("--shows", action="store_true")
    ap.add_argument("--list", action="store_true", help="list episodes")
    ap.add_argument("--show", metavar="SLUG", help="filter --list to a show slug")
    ap.add_argument("--tweets", action="store_true", help="list the flat tweet/X call feed")
    ap.add_argument("--stream", metavar="ID", help="show an episode's calls")
    ap.add_argument("--speakers", action="store_true", help="list top speakers/traders")
    ap.add_argument("--speaker", metavar="HANDLE", help="a speaker's calls")
    a = ap.parse_args()

    if not any([a.shows, a.list, a.tweets, a.stream, a.speakers, a.speaker]):
        build()
        return

    d = _load()
    if a.shows:
        for s in d["shows"]:
            tag = "feed" if s.get("is_feed") else (s.get("medium") or s.get("platform") or "")
            print(f"{s['slug']:18} {tag:10} @{(s['streamer'] or ''):16} {s['n_episodes']:3} eps · {s['n_trades']:4} calls  {(s.get('name') or '')[:32]}")
    if a.tweets:
        for t in d.get("tweets", [])[:40]:
            print(f"{(t['published_at'] or '')[:10]}  @{(t['speaker'] or '')[:16]:16} {t['ticker']:6} {(t['direction'] or '').upper():5} "
                  f"{_pct(t.get('since_call_pct')):>8}  {(t.get('headline_quote') or t.get('thesis') or '')[:60]}")
    if a.list:
        for e in d["episodes"]:
            if a.show and e["show"] != a.show:
                continue
            print(f"{e['id']:12} {e['show']:9} {(e['published_at'] or '')[:10]}  {len(e['trades']):2} calls  {(e['title'] or '')[:64]}")
    if a.stream:
        e = next((x for x in d["episodes"] if x["id"] == a.stream), None)
        if not e:
            print(f"no episode {a.stream}"); return
        print(f"{e['title']}\n@{e['trades'][0]['speaker'] if e['trades'] else '?'} · {e['platform']} · {(e['published_at'] or '')[:10]} · {e['url']}")
        for t in e["trades"]:
            print(f"  {_mmss(t.get('video_seconds')):>7}  {t['ticker']:6} {(t['direction'] or '').upper():5} {t.get('bucket') or '':8} "
                  f"@{t['entry_price']!s:<10} {_pct(t.get('since_call_pct')):>8}  {(t.get('headline_quote') or t.get('thesis') or '')[:70]}")
    if a.speakers:
        for s in sorted(d["speakers"].values(), key=lambda x: -x["n_calls"])[:25]:
            v = " ✓" if s["verified"] else ""
            print(f"@{s['handle']:16}{v:2} {s['n_calls']:4} calls  {s['long']}L/{s['short']}S  {','.join(s['shows'])}")
    if a.speaker:
        s = d["speakers"].get(a.speaker)
        if not s:
            print(f"no speaker {a.speaker}"); return
        wr = f" · {s['win_rate']*100:.0f}% win" if s.get("win_rate") is not None else ""
        pnl = f" · {s['total_pnl']:+.0f}% total" if s.get("total_pnl") is not None else ""
        print(f"@{s['handle']} {'(verified)' if s['verified'] else ''} · {s['n_calls']} calls · {s['long']}L/{s['short']}S · {s['n_episodes']} eps{wr}{pnl} · {','.join(s['shows'])}")
        for e in d["episodes"]:
            for t in e["trades"]:
                if t["speaker"] == a.speaker:
                    print(f"  {(e['published_at'] or '')[:10]}  {t['ticker']:6} {(t['direction'] or '').upper():5} {_pct(t.get('since_call_pct')):>8}  {(t.get('headline_quote') or '')[:64]}  [{e['id']}]")
        for t in d.get("tweets", []):
            if t["speaker"] == a.speaker:
                print(f"  {(t['published_at'] or '')[:10]}  {t['ticker']:6} {(t['direction'] or '').upper():5} {_pct(t.get('since_call_pct')):>8}  {(t.get('headline_quote') or '')[:64]}  [tweet]")


if __name__ == "__main__":
    main()
