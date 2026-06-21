"""Public Alpha — terminal scanner UI (Textual).

Reads results/scan.json (produced by scan.py) and lets you navigate the call universe:
a SIGNALS feed (every asset being called, ranked by volume, with the organic/coordinated
verdict) and a TRADE IDEAS view (the confirmed, ready-to-act subset). Enter opens a detail
pane with the social evidence (who said what, when) + the funnel verdict.

    python3 skills/public-alpha/scripts/scan_tui.py      # reads existing scan.json
    python3 skills/public-alpha/scripts/scan_tui.py --scan   # re-scan first
"""
import json
import subprocess
import sys
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane

ROOT = Path(__file__).resolve().parent.parent          # skills/public-alpha/
SCAN_JSON = ROOT / "results" / "scan.json"
SCAN_PY = ROOT / "scripts" / "scan.py"

VERDICT_STYLE = {"organic": "bold green", "mixed": "yellow", "coordinated": "bold red"}


def _verdict(text: str) -> Text:
    return Text(text, style=VERDICT_STYLE.get(text, "white"))


def _stance(mix: dict) -> Text:
    t = Text()
    t.append(f"{mix.get('bullish', 0)}▲", style="green")
    t.append(" ")
    t.append(f"{mix.get('bearish', 0)}▼", style="red")
    return t


def _check(ok: bool) -> Text:
    return Text("✓", style="green") if ok else Text("✗", style="red")


def _esc(s) -> str:
    """Escape Textual markup brackets in dynamic text."""
    return str(s).replace("[", r"\[")


def _usd(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    a = abs(n)
    if a >= 1e12:
        return f"${n / 1e12:.2f}T"
    if a >= 1e9:
        return f"${n / 1e9:.2f}B"
    if a >= 1e6:
        return f"${n / 1e6:.1f}M"
    if a >= 1e3:
        return f"${n / 1e3:.1f}K"
    return f"${n:.2f}"


def _funding(n) -> str:
    try:
        return f"{'+' if n >= 0 else ''}{float(n) * 100:.4f}%"
    except (TypeError, ValueError):
        return "—"


def _pct_c(n) -> str:
    """Signed percent with green/up red/down Rich markup."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    return f"[{'green' if n >= 0 else 'red'}]{'+' if n >= 0 else ''}{n:.1f}%[/]"


def _load() -> dict:
    if not SCAN_JSON.exists():
        return {}
    return json.loads(SCAN_JSON.read_text())


class DetailScreen(Screen):
    BINDINGS = [("escape,enter,q", "app.pop_screen", "Back")]

    def __init__(self, item: dict, scan: dict):
        super().__init__()
        self.item = item
        self.scan = scan

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield VerticalScroll(Static(self._build_markup(), id="detail", markup=True))
        yield Footer()

    def _build_markup(self) -> str:
        it, scan = self.item, self.scan
        reg, nar = scan.get("regime", {}), scan.get("narrative", {})
        # trade ideas carry only a subset; the full signal has perp/liquidations/community
        full = {s["symbol"]: s for s in scan.get("signals", [])}.get(it.get("symbol"), {})
        cls = it.get("classification", "?")
        cls_style = VERDICT_STYLE.get(cls, "white")
        L = []
        head = f"  [bold white]{_esc(it['symbol'])}[/]   [{cls_style}]{cls}[/]   [dim]organic score {it.get('score')}[/]"
        if "confidence" in it:
            head += f"   [bold cyan]· confidence {it['confidence']}[/]"
        L += [head, ""]

        # market — price near the top (mirrors the site's asset header)
        mkt = full.get("market") or it.get("market") or {}
        perf = full.get("performance") or it.get("performance") or {}
        if mkt:
            L.append("[bold underline]  Market[/]")
            L.append(f"   [bold]{_usd(mkt.get('price'))}[/]   [dim]24h[/] {_pct_c(mkt.get('percent_change_24h'))}   "
                     f"[dim]7d[/] {_pct_c(mkt.get('percent_change_7d'))}   [dim]mcap[/] {_usd(mkt.get('market_cap'))}   "
                     f"[dim]24h vol[/] {_usd(mkt.get('volume_24h'))}")
            if perf.get("ath"):
                L.append(f"   [dim]ATH[/] {_usd(perf.get('ath'))}   [dim]from ATH[/] {_pct_c(perf.get('pct_from_ath'))}")
            L.append("")

        L.append("[bold underline]  Why[/]")
        L += [f"   • {_esc(r)}" for r in it.get("reasons", [])]
        L.append("")

        oc = it.get("onchain")
        if oc:
            ok = oc.get("confirmed")
            L.append("[bold underline]  Confirmation[/]")
            L.append(f"   [{'green' if ok else 'red'}]{'confirmed' if ok else 'NOT confirmed'}[/]")
            L += [f"   [dim]• {_esc(n)}[/]" for n in oc.get("notes", [])[:4]]
            L.append("")

        # KOL sentiment lean (mirrors the site's sentiment bar)
        sent = full.get("sentiment") or it.get("sentiment") or {}
        if sent.get("n_kols"):
            lbl = sent.get("label", "neutral")
            sty = {"bullish": "green", "bearish": "red"}.get(lbl, "yellow")
            L.append("[bold underline]  KOL sentiment[/]")
            L.append(f"   [{sty}]{_esc(lbl)} lean[/] [dim]· {sent.get('n_kols')} KOLs · "
                     f"{sent.get('bull')} bull / {sent.get('bear')} bear[/]")
            L.append("")

        # breakout (spot) — mirrors the site's breakout card
        bo = full.get("breakout") or it.get("breakout") or {}
        if bo and bo.get("strength") is not None:
            status = "[green]● BREAKOUT[/]" if bo.get("is_breakout") else "[dim]building[/]"
            conf = "  [green]✓ social-confirmed[/]" if bo.get("social_confirmed") else ""
            L.append("[bold underline]  Breakout (spot)[/]")
            L.append(f"   {status}{conf}   [dim]vs 20d-high[/] {_pct_c(bo.get('pct_above_20d_high'))}   "
                     f"[dim]vol×[/] {bo.get('vol_mult')}   [dim]strength[/] {bo.get('strength')}")
            L.append("")

        L.append("[bold underline]  Social evidence — the calls[/]")
        for c in it.get("top_calls", []):
            stance = c.get("stance") or "?"
            sc = {"bullish": "green", "bearish": "red"}.get(stance, "yellow")
            eng = c.get("engagement", {}) or {}
            foll = eng.get("followers") or eng.get("likes")
            engtxt = f"{int(foll)} eng" if foll else ""
            L.append(f"   [bold]{_esc(c.get('author', '?')[:18]):<18}[/] [{sc}]{stance:<8}[/] "
                     f"[dim]{str(c.get('ts', ''))[:10]} {engtxt:>10}[/]  {_esc((c.get('summary') or '')[:70])}")
        L.append("")

        # top spot venues (mirrors the site's venues table)
        venues = full.get("venues") or it.get("venues") or []
        if venues:
            L.append("[bold underline]  Top venues[/]")
            for v in venues[:5]:
                L.append(f"   [bold]{_esc((v.get('exchange') or '?')[:16]):<16}[/] "
                         f"[dim]{_esc((v.get('pair') or '')[:14]):<14}[/]  {_usd(v.get('volume_24h'))}")
            L.append("")

        # leverage & liquidations (perp funding/OI + realized liquidations + the fused read)
        perp = it.get("perp") or full.get("perp") or {}
        liq = it.get("liquidations") or full.get("liquidations") or {}
        lr = it.get("leverage_read") or full.get("leverage_read") or {}
        if perp or liq or lr:
            L.append("[bold underline]  Leverage & liquidations[/]")
            if perp:
                L.append(f"   [dim]funding[/] {_funding(perp.get('funding_rate'))}   "
                         f"[dim]OI[/] {_usd(perp.get('open_interest'))}   "
                         f"[dim]perp vol[/] {_usd(perp.get('perp_volume_24h'))}"
                         + (f"   [dim]· {_esc(perp.get('bias'))}[/]" if perp.get('bias') else ""))
            if liq:
                L.append(f"   [dim]liq 24h[/] {_usd(liq.get('total'))}   "
                         f"[green]long {_usd(liq.get('long'))}[/]  [red]short {_usd(liq.get('short'))}[/]")
            if lr.get("label"):
                lr_style = ("green" if "squeeze" in lr["label"]
                            else "red" if ("cascade" in lr["label"] or "flush" in lr["label"]) else "yellow")
                note = f" — {lr['note']}" if lr.get("note") else ""
                L.append(f"   [{lr_style}]{_esc(lr['label'])}[/][dim]{_esc(note)}[/]")
            L.append("")

        # CMC community pulse (top posts + articles)
        com = it.get("community") or full.get("community") or {}
        posts, arts = com.get("posts") or [], com.get("articles") or []
        if posts or arts:
            L.append(f"[bold underline]  CMC community[/]  [dim]{com.get('n_posts', 0)} posts · "
                     f"{com.get('engagement', 0)} eng · {len(arts)} articles[/]")
            for p in posts[:3]:
                L.append(f"   [bold]{_esc((p.get('author') or '?')[:18]):<18}[/] "
                         f"[dim]{int(p.get('likes', 0))} likes[/]  {_esc((p.get('text') or '')[:62])}")
            for a in arts[:2]:
                L.append(f"   [dim]· {_esc((a.get('title') or '')[:72])}[/]")
            L.append("")

        L.append("[bold underline]  Market context[/]")
        L.append(f"   [dim]regime {reg.get('state')} (F&G {reg.get('fear_greed')}, "
                 f"BTC dom {reg.get('btc_dominance')}%)[/]")
        topics = ", ".join(nar.get("trending_topics", [])[:4])
        L.append(f"   [dim]heating: {_esc(nar.get('sector') if nar.get('heating') else 'flat')}  ·  "
                 f"topics: {_esc(topics)}[/]")
        L.append("\n   [dim]\\[escape] back[/]")
        return "\n".join(L)


class ScannerApp(App):
    CSS = """
    #context { height: auto; padding: 0 1; background: $panel; color: $text; }
    DataTable { height: 1fr; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "rescan", "Rescan"),
        ("1", "tab('signals')", "Signals"),
        ("2", "tab('ideas')", "Trade Ideas"),
        ("3", "tab('news')", "News"),
    ]
    TITLE = "Public Alpha — Scanner"

    def __init__(self, scan: dict):
        super().__init__()
        self.scan = scan
        self.by_key: dict = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="context")
        with TabbedContent(initial="signals"):
            with TabPane("Signals", id="signals"):
                yield DataTable(id="signals_t", cursor_type="row", zebra_stripes=True)
            with TabPane("Trade Ideas", id="ideas"):
                yield DataTable(id="ideas_t", cursor_type="row", zebra_stripes=True)
            with TabPane("News", id="news"):
                yield DataTable(id="news_t", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._populate()
        # show the cached snapshot instantly, then refresh in the background so
        # entering the TUI always lands you on current data without a startup lag.
        self._start_refresh(on_launch=True)

    def _populate(self) -> None:
        scan = self.scan
        meta, reg, nar = scan.get("meta", {}), scan.get("regime", {}), scan.get("narrative", {})
        gs = scan.get("gate_stats", {})
        state = reg.get("state", "?")
        state_style = "bold red" if state == "risk_off" else "bold green"
        heating = nar.get("sector") if nar.get("heating") else "flat"
        liq = scan.get("liquidations") or {}
        liq_txt = ""
        if liq.get("total_24h"):
            lp = liq.get("long_pct")
            split = f" ({round(lp * 100)}%L/{round((1 - lp) * 100)}%S)" if lp is not None else ""
            liq_txt = f"    [dim]liq 24h[/] [bold]{_usd(liq['total_24h'])}[/][dim]{split}[/]"
        ctx = (f"[dim]regime[/] [{state_style}]{state}[/] [dim](F&G {reg.get('fear_greed')})[/]"
               f"    [dim]heating[/] [bold magenta]{_esc(heating)}[/]"
               f"{liq_txt}"
               f"    [dim]{meta.get('total_calls')} calls · {meta.get('classified')} assets · "
               f"{gs.get('organic_pct')}% organic / {gs.get('filtered_coordinated_pct')}% coordinated"
               f"    · scanned {scan.get('generated_at', '')[:16]}[/]")
        self.query_one("#context", Static).update(ctx)

        sig = self.query_one("#signals_t", DataTable)
        sig.clear(columns=True)
        sig.add_columns("Asset", "Calls", "Verdict", "Score", "Authors", "Stance", "Top call")
        for s in scan.get("signals", []):
            top = (s.get("top_calls") or [{}])[0]
            tc = f"{top.get('author', '')[:14]}: {(top.get('summary') or '')[:42]}"
            key = sig.add_row(
                Text(s["symbol"], style="bold"), str(s["n_calls"]), _verdict(s["classification"]),
                f"{s['score']:.2f}", str(s["distinct_authors"]), _stance(s.get("stance_mix", {})), tc,
            )
            self.by_key[key.value] = s

        ide = self.query_one("#ideas_t", DataTable)
        ide.clear(columns=True)
        ide.add_columns("Asset", "Confidence", "Heating", "Organic", "Confirmed", "Regime", "Top evidence")
        for i in scan.get("trade_ideas", []):
            top = (i.get("top_calls") or [{}])[0]
            key = ide.add_row(
                Text(i["symbol"], style="bold"),
                Text(f"{i.get('confidence')}", style="bold cyan" if i.get("entry_ready") else "cyan"),
                _check(i.get("narrative_heating")), _check(i.get("score", 0) >= 0.6),
                _check(i.get("confirmed")),
                Text(i.get("regime_state", "?"), style="green" if i.get("regime_state") in ("risk_on", "neutral") else "red"),
                f"{top.get('author', '')[:14]}: {(top.get('summary') or '')[:40]}",
            )
            self.by_key[key.value] = i

        # News — market-wide CMC feed across all listed assets (mirrors the site's News tab)
        nw = self.query_one("#news_t", DataTable)
        nw.clear(columns=True)
        nw.add_columns("Time", "Source", "Assets", "Headline")
        for it in scan.get("news", [])[:60]:
            nw.add_row(str(it.get("ts", ""))[:10], (it.get("source") or "")[:14],
                       " ".join(it.get("symbols", [])[:3])[:14], (it.get("title") or "")[:84])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        item = self.by_key.get(event.row_key.value)
        if item:
            self.push_screen(DetailScreen(item, self.scan))

    def action_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_rescan(self) -> None:
        self._start_refresh(on_launch=False)

    def _start_refresh(self, on_launch: bool) -> None:
        if getattr(self, "_refreshing", False):
            return  # a scan is already in flight; don't stack subprocesses
        self._refreshing = True
        self.notify("Refreshing live data…" if on_launch else "Rescanning…", timeout=2)
        self.run_worker(self._refresh_worker, thread=True, exclusive=True)

    def _refresh_worker(self) -> None:
        try:
            subprocess.run([sys.executable, str(SCAN_PY)], check=True, capture_output=True)
            scan = _load()
            self.call_from_thread(self._apply_refresh, scan)
        except subprocess.CalledProcessError as e:
            self.call_from_thread(self.notify, f"Scan failed: {e}", severity="error")
        finally:
            self._refreshing = False

    def _apply_refresh(self, scan: dict) -> None:
        self.scan = scan
        self.by_key.clear()
        self._populate()
        self.notify("Updated to live data.")


def main():
    if "--scan" in sys.argv or not SCAN_JSON.exists():
        print("Scanning…", file=sys.stderr)
        subprocess.run([sys.executable, str(SCAN_PY)], check=True)
    scan = _load()
    if not scan:
        print("No scan.json. Run: python3 skills/public-alpha/scripts/scan.py", file=sys.stderr)
        sys.exit(1)
    ScannerApp(scan).run()


if __name__ == "__main__":
    main()
