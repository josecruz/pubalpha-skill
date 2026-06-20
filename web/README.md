# Public Alpha — web dashboard

A browser dashboard for the Public Alpha scanner: a **hot-assets top bar**, a **social-trades feed**
(switchable: individual calls / asset rows / grouped by asset), and a **Trade Ideas** panel — styled
with [SMUI](https://smui.statico.io) (a shadcn/ui terminal theme). It reads `public/scan.json`
produced by the Python scanner; it computes nothing itself.

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
- **Social-trades feed** — 3 views via the selector: `CALLS` (author · asset+verdict · stance · time ·
  snippet · source), `ASSETS` (table with price / 24h / CEX vol / DEX vol), `GROUPED` (calls per asset).
- **Trade Ideas** — the confirmed subset with a gate scoreboard (heating / organic / confirmed / regime).

### Market Intel (`/intel`)
*CMC's own crowd vs the KOL calls.* Three columns — **corroborated** (called AND trending on CMC),
**KOL-only** (called, CMC's crowd isn't watching = unconfirmed hype), **CMC-only** (trending on CMC,
nobody's calling = under-called watch list) — plus market movers (gainers / losers / most-visited) and a
regime panel (altcoin-season index, Fear & Greed 14-day trend, dominance).

### Asset thesis (`/asset?symbol=X`)
Logo, tags, listing age + **NEW** flag, provenance links; the **CMC-attention** line (which CMC lists it's
trending in + rank); price, % changes, **CEX vs DEX volume**, market cap; **price context** (ATH, % from
ATH, ROI ladder); **top venues**; the classifier verdict + reasons + feature bars + on-chain confirmation;
and the asset's full call feed with source links.

Verdict colors: green = organic, amber = mixed, red = coordinated.
