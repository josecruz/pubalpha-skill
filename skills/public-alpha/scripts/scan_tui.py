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
        cls = it.get("classification", "?")
        cls_style = VERDICT_STYLE.get(cls, "white")
        L = []
        head = f"  [bold white]{_esc(it['symbol'])}[/]   [{cls_style}]{cls}[/]   [dim]organic score {it.get('score')}[/]"
        if "confidence" in it:
            head += f"   [bold cyan]· confidence {it['confidence']}[/]"
        L += [head, ""]

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
        yield Footer()

    def on_mount(self) -> None:
        self._populate()

    def _populate(self) -> None:
        scan = self.scan
        meta, reg, nar = scan.get("meta", {}), scan.get("regime", {}), scan.get("narrative", {})
        gs = scan.get("gate_stats", {})
        state = reg.get("state", "?")
        state_style = "bold red" if state == "risk_off" else "bold green"
        heating = nar.get("sector") if nar.get("heating") else "flat"
        ctx = (f"[dim]regime[/] [{state_style}]{state}[/] [dim](F&G {reg.get('fear_greed')})[/]"
               f"    [dim]heating[/] [bold magenta]{_esc(heating)}[/]"
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        item = self.by_key.get(event.row_key.value)
        if item:
            self.push_screen(DetailScreen(item, self.scan))

    def action_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_rescan(self) -> None:
        self.notify("Rescanning…", timeout=2)
        try:
            subprocess.run([sys.executable, str(SCAN_PY)], check=True, capture_output=True)
            self.scan = _load()
            self.by_key.clear()
            self._populate()
            self.notify("Scan refreshed.")
        except subprocess.CalledProcessError as e:
            self.notify(f"Scan failed: {e}", severity="error")


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
