"""Regenerate the scanner TUI screenshots (docs/img/tui-*.svg) via Textual's Pilot.

    python3 skills/public-alpha/scripts/shoot_tui.py   # reads existing results/scan.json

Drives the app headlessly and exports each state to SVG:
  tui-signals.svg      — the Signals feed (default tab)
  tui-trade-ideas.svg  — the Trade Ideas tab (key 2)
  tui-news.svg         — the market-wide News tab (key 3)
  tui-detail.svg       — the detail pane (Enter on the first signal row), showing the
                         leverage & liquidations + CMC community sections
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_tui import DetailScreen, ScannerApp, _load  # noqa: E402

OUT = Path(__file__).resolve().parents[3] / "docs" / "img"

COLS = 140          # ~1726px wide, matching the original SVGs (≈12.3 px/col)
TAB_ROWS = 40       # the table tabs — ~1026px tall like the originals
DETAIL_ROWS = 68    # taller so the detail fits leverage & liquidations + community


def _pick_detail(scan: dict) -> dict:
    """A signal rich enough to showcase the detail pane (leverage + community + venues)."""
    sigs = {s["symbol"]: s for s in scan.get("signals", [])}
    btc = sigs.get("BTC")
    if btc and btc.get("leverage_read") and btc.get("community"):
        return btc
    for s in scan.get("signals", []):
        if s.get("leverage_read") and (s.get("community") or {}).get("posts") and s.get("venues"):
            return s
    return scan["signals"][0]


async def _shot(app: ScannerApp, name: str) -> None:
    app.save_screenshot(filename=name, path=str(OUT))
    print("shot", name)


async def capture_tabs(scan: dict) -> None:
    app = ScannerApp(scan)
    async with app.run_test(size=(COLS, TAB_ROWS)) as pilot:
        await pilot.pause()
        await _shot(app, "tui-signals.svg")
        await pilot.press("2"); await pilot.pause()
        await _shot(app, "tui-trade-ideas.svg")
        await pilot.press("3"); await pilot.pause()
        await _shot(app, "tui-news.svg")


async def capture_detail(scan: dict) -> None:
    app = ScannerApp(scan)
    item = _pick_detail(scan)
    async with app.run_test(size=(COLS, DETAIL_ROWS)) as pilot:
        await pilot.pause()
        app.push_screen(DetailScreen(item, scan))   # same screen Enter opens on a signal row
        await pilot.pause()
        await _shot(app, "tui-detail.svg")


async def main() -> None:
    scan = _load()
    if not scan:
        print("No results/scan.json — run scan.py first", file=sys.stderr)
        sys.exit(1)
    await capture_tabs(scan)
    await capture_detail(scan)
    print("done ->", OUT)


if __name__ == "__main__":
    asyncio.run(main())
