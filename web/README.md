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
- **Context strip** — regime (Fear & Greed), heating narrative, trending topics, totals.
- **Market insights** — total market cap, 24h / DeFi volume, BTC & ETH dominance, and a **CEX vs DEX
  volume** split across the surfaced assets.
- **Hot assets** — most-called assets (with price + 24h %); click one to open its detail page.
- **Social-trades feed** — 3 views via the selector: `CALLS` (each call: author · asset+verdict ·
  stance · time · snippet · source link), `ASSETS` (a table with price / 24h / CEX vol / DEX vol),
  `GROUPED` (calls under each asset).
- **Trade Ideas** — the confirmed subset with a gate scoreboard (heating / organic / confirmed / regime).
- **Asset detail** (`/asset?symbol=X`) — price, % changes, **CEX vs DEX volume**, market cap; the
  classifier verdict + reasons + per-signal feature bars + on-chain confirmation; and the asset's full
  call feed with source links.

Verdict colors: green = organic, amber = mixed, red = coordinated.
