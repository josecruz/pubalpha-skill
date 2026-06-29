# Public Alpha — web dashboard

The browser surface of the Public Alpha **social-signal scanner** — follow the trades other traders are
calling across social, filtered for coordinated noise and cross-referenced against CMC's own crowd. A
**hot-assets top bar**, a 5-mode **social-trades feed** (switchable: timeline / individual calls / asset
rows / grouped by asset / news), and a **Trade Ideas** panel — styled with
[SMUI](https://smui.statico.io) (a shadcn/ui terminal theme). It reads `public/scan.json` produced by the
Python scanner; it computes nothing itself.

Built with Next.js 16 + Tailwind v4 + shadcn/ui + the SMUI `spacemolt` theme. JetBrains Mono, zero
radius, Nord palette — per SMUI's design rules.

## Run

```bash
cd web
npm install          # once
npm run scan:dev     # runs the Python scan, copies scan.json here, then `next dev`
```

Open http://localhost:3000. Needs `CMC_PRO_API_KEY` in the repo `.env` (for regime + confirmation);
the call feed works regardless.

- `npm run scan` — re-run the scan + refresh `public/scan.json` (then reload the page).
- `npm run dev` — serve the existing `public/scan.json` without re-scanning.

## What it shows
- **Context strip** — regime (Fear & Greed + 14-day trend arrow), heating narrative, trending topics, totals.
- **Market insights** — total market cap, 24h / DeFi volume, BTC & ETH dominance, the **real Altcoin
  Season Index**, and a **CEX vs DEX volume** split across the surfaced assets.
- **CMC crowd vs calls** strip — corroborated / KOL-only / CMC-only counts; links to Market Intel.
- **Hot assets** — most-called assets (price + 24h %, plus a **CMC ✓** marker when CMC's crowd
  corroborates the call); click one to open its thesis page.
- **Social-trades feed** — 5 views via the selector: `TIMELINE` (compact chronological KOL timeline —
  stance dots on a time axis, avatar · handle · LONG/SHORT · asset · since-call %), `CALLS` (cards),
  `ASSETS` (table with price / 24h / CEX vol / DEX vol), `GROUPED` (calls per asset), `NEWS` (market-wide
  CMC headlines — source · time · asset chips deep-linking to the thesis).
- Real **asset logos** (CMC) on chips/feed/tables, **exchange logos** on venue tables, and **real KOL
  profile photos** (via unavatar — Twitch/X by show platform) with a **verified ✓** badge and a **platform
  icon** (Twitch / YouTube / X) per call; monogram fallback. Verbose labels trimmed to icons.
- **Trade Ideas** — the confirmed subset with a gate scoreboard (heating / organic / confirmed / regime).

### Streams browser (`/streams` · `/stream?id=` · `/speaker?handle=`)
A paste.trade-style browser across **all ~36 source shows** (podcasts, newsletters, and an aggregate X
feed). A **Shows** tab lists episodes (filter by show — grouped by medium — speaker, or ticker; sort
newest/most-calls) and a **Tweets** tab is the flat X/tweet call feed. A **stream page** has the streamer
header, an **embedded Twitch/YouTube player** (click a call's timestamp to seek), the calls list, and
"trades explained" cards (bucket / paste-pick tags, the quote, speaker, reasoning, price box, expandable
reasoning); **speaker/trader pages** show a trader's calls **across every show they appear on** + L/S +
verified + win-rate / total-PnL record. Every call links to its CMC `/asset` thesis. Reads
`public/paste.json` (from `paste_browse.py`, built from paste.trade's robots-allowed `/api/shows` surface).
Content is paste.trade's, shown **with attribution + links** to the show and source video.

### Setups (`/setups`)
The *decide / predict a move* surface — native re-implementations of CMC Skill Hub skills. Two ranked
tables: **spot breakout candidates** (20-day-high breakout + volume/ATR + **KOL social confirmation**) and
**perp breakout candidates** (funding / open interest on major venues + long/short bias). Breakouts sort to
the top; the rest are "building." Forward screens, not backtested. A teaser strip + a "Setups →" link sit on
the dashboard. (Mirrors `scan_spot_altcoin_breakout_with_social_confirmation`,
`screen_perp_breakout_candidates`, `altcoin_kol_sentiment`.)

### Market Intel (`/intel`)
*CMC's own crowd vs the KOL calls.* Three columns — **corroborated** (called AND trending on CMC),
**KOL-only** (called, CMC's crowd isn't watching = unconfirmed hype), **CMC-only** (trending on CMC,
nobody's calling = under-called watch list) — plus market movers (gainers / losers / most-visited),
**market-wide 24h liquidations** (long / short split), and a regime panel (altcoin-season index, Fear &
Greed 14-day trend, dominance).

### Asset thesis (`/asset?symbol=X`)
Logo, tags, listing age + **NEW** flag, provenance links; the **CMC-attention** line (which CMC lists it's
trending in + rank); a **price chart** (shadcn/Recharts) where each **KOL call lands as an avatar dot on
the line** (colored by stance, clustered, hover for the thesis) with a **range selector**
(1D/7D/1M/3M/1Y/ALL); price, % changes, **CEX vs DEX volume**, market cap; **price context** (ATH, % from
ATH, ROI ladder); **decision signals** (KOL sentiment gauge · spot breakout · perp funding/OI + a
**long/short lean** bar, funding-implied); **top spot venues** + **perp venues (CEX + DEX)** with
funding/OI; a **leverage & liquidations** card (perp funding + realized long/short flushes →
squeeze-vs-cascade read); the **CMC community** (top posts + news articles); the classifier verdict +
reasons + feature bars + on-chain confirmation; the asset's **mentions** as a compact **timeline**
(default) or paste.trade-style cards; and the call feed rendered **paste.trade-style** — each call a
LONG/SHORT thesis card with **entry price + % move since the call**.

Verdict colors: green = organic, amber = mixed, red = coordinated.
