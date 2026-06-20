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
- **Hot assets** — most-called assets; click one to filter the feed.
- **Social-trades feed** — 3 views via the selector: `CALLS` (each call: author · asset+verdict ·
  stance · time · snippet · source), `ASSETS` (a table), `GROUPED` (calls under each asset).
- **Trade Ideas** — the confirmed subset with a gate scoreboard (heating / organic / confirmed / regime).

Verdict colors: green = organic, amber = mixed, red = coordinated.
