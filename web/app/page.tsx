"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";

// ---- types (mirror results/scan.json) ----
type Verdict = "organic" | "mixed" | "coordinated";
interface Call {
  symbol: string; classification?: Verdict; score?: number; author: string;
  source: string; stance: string | null; conviction: number | null; summary: string;
  ts: string; engagement: Record<string, number>; url: string | null;
}
interface Signal {
  symbol: string; n_calls: number; classification: Verdict; score: number; reasons: string[];
  distinct_authors: number; sources: string[];
  stance_mix: { bullish: number; bearish: number; neutral: number };
  latest_ts: string; top_calls: Call[];
}
interface Idea {
  symbol: string; score: number; classification: Verdict; confidence: number;
  confirmed: boolean; narrative_heating: boolean; regime_state: string; entry_ready: boolean;
  reasons: string[]; onchain: { confirmed: boolean; notes: string[] } | null; top_calls: Call[];
}
interface Scan {
  generated_at: string;
  meta: { total_calls: number; unique_symbols: number; classified: number; trade_ideas: number };
  regime: { available: boolean; state: string; fear_greed?: number; btc_dominance?: number };
  narrative: { heating: boolean; sector?: string; trending_topics?: string[]; available?: boolean };
  gate_stats: { clusters_seen: number; organic_pct: number; filtered_coordinated_pct: number; mixed_pct: number };
  signals: Signal[]; trade_ideas: Idea[]; feed: Call[];
}

// ---- color helpers (SMUI / Nord palette) ----
const VC: Record<string, string> = { organic: "92 28% 65%", mixed: "40 71% 73%", coordinated: "355 52% 64%" };
const SC: Record<string, string> = { bullish: "92 28% 65%", bearish: "355 52% 64%", neutral: "213 14% 65%" };
const hsl = (t: string, a?: number) => (a ? `hsl(${t} / ${a})` : `hsl(${t})`);
const vc = (v?: string) => VC[v ?? "mixed"] ?? "213 14% 65%";
const sc = (s?: string | null) => SC[s ?? "neutral"] ?? "213 14% 65%";

function ago(iso?: string): string {
  if (!iso) return "";
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 3600) return `${Math.max(1, Math.round(d / 60))}m`;
  if (d < 86400) return `${Math.round(d / 3600)}h`;
  return `${Math.round(d / 86400)}d`;
}

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);

function Tag({ v }: { v: string }) {
  return (
    <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border"
      style={{ color: hsl(vc(v)), borderColor: hsl(vc(v), 0.35) }}>{v}</span>
  );
}

function Dot({ t }: { t: string }) {
  return <span className="inline-block w-[6px] h-[6px] rounded-full align-middle" style={{ background: hsl(t) }} />;
}

// ---- main ----
export default function Page() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<"calls" | "assets" | "grouped">("calls");
  const [picked, setPicked] = useState<string | null>(null);

  useEffect(() => {
    fetch("/scan.json")
      .then((r) => { if (!r.ok) throw new Error(`scan.json ${r.status}`); return r.json(); })
      .then(setScan)
      .catch((e) => setErr(String(e)));
  }, []);

  const feed = useMemo(
    () => (scan?.feed ?? []).filter((c) => !picked || c.symbol === picked),
    [scan, picked]
  );
  const grouped = useMemo(() => {
    const by: Record<string, Call[]> = {};
    for (const c of feed) (by[c.symbol] ??= []).push(c);
    const sigBy = Object.fromEntries((scan?.signals ?? []).map((s) => [s.symbol, s]));
    return Object.entries(by)
      .map(([sym, calls]) => ({ sym, calls, sig: sigBy[sym] as Signal | undefined }))
      .sort((a, b) => b.calls.length - a.calls.length);
  }, [feed, scan]);

  if (err) return <Shell><div className="text-destructive p-6">Failed to load /scan.json — {err}. Run the scanner first.</div></Shell>;
  if (!scan) return <Shell><div className="text-muted-foreground p-6">Loading scan…</div></Shell>;

  const { regime: r, narrative: n, gate_stats: g, meta } = scan;
  return (
    <Shell>
      {/* context strip */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border border-border bg-card px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <Label>regime</Label>
          <span className="uppercase text-sm" style={{ color: r.state === "risk_off" ? hsl(SC.bearish) : hsl(SC.bullish) }}>
            {r.state}
          </span>
          {r.fear_greed != null && <span className="text-muted-foreground text-sm">F&amp;G {r.fear_greed}</span>}
        </div>
        <div className="flex items-center gap-2">
          <Label>heating</Label>
          <span className="uppercase text-sm text-primary">{n.heating ? n.sector : "flat"}</span>
        </div>
        <div className="hidden md:flex items-center gap-2 min-w-0">
          <Label>topics</Label>
          <span className="text-muted-foreground text-sm truncate">{(n.trending_topics ?? []).slice(0, 4).join(" · ")}</span>
        </div>
        <div className="ml-auto flex items-center gap-4 text-sm text-muted-foreground">
          <span>{meta.total_calls} calls · {meta.classified} assets</span>
          <span style={{ color: hsl(VC.organic) }}>{g.organic_pct}% organic</span>
          <span style={{ color: hsl(VC.coordinated) }}>{g.filtered_coordinated_pct}% coord</span>
        </div>
      </div>

      {/* hot assets bar */}
      <div>
        <Label>hot assets — most called</Label>
        <ScrollArea className="mt-1">
          <div className="flex gap-2 pb-2">
            {scan.signals.slice(0, 16).map((s) => {
              const on = picked === s.symbol;
              return (
                <button key={s.symbol} onClick={() => setPicked(on ? null : s.symbol)}
                  className="shrink-0 border bg-card px-3 py-2 text-left transition-colors hover:border-primary"
                  style={{ borderColor: on ? hsl("193 44% 67%") : undefined }}>
                  <div className="flex items-center gap-2">
                    <Dot t={vc(s.classification)} />
                    <span className="font-semibold">{s.symbol}</span>
                    <span className="text-muted-foreground text-xs">{s.n_calls}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    score {s.score.toFixed(2)} · {s.distinct_authors} auth
                  </div>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* main grid: feed + trade ideas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between">
            <Label>social trades feed{picked ? ` · ${picked}` : ""}</Label>
            <div className="flex border border-border">
              {(["calls", "assets", "grouped"] as const).map((m) => (
                <button key={m} onClick={() => setView(m)}
                  className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${view === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          {view === "calls" && (
            <div className="space-y-1.5">
              {feed.map((c, i) => <CallRow key={i} c={c} />)}
            </div>
          )}

          {view === "assets" && (
            <Card className="p-0 overflow-hidden rounded-none">
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Asset", "Calls", "Verdict", "Score", "Auth", "Stance"].map((h) => (
                      <TableHead key={h} className="text-[11px] uppercase tracking-wider">{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(picked ? scan.signals.filter((s) => s.symbol === picked) : scan.signals).map((s) => (
                    <TableRow key={s.symbol} className="cursor-pointer" onClick={() => setPicked(picked === s.symbol ? null : s.symbol)}>
                      <TableCell className="font-semibold">{s.symbol}</TableCell>
                      <TableCell>{s.n_calls}</TableCell>
                      <TableCell><Tag v={s.classification} /></TableCell>
                      <TableCell>{s.score.toFixed(2)}</TableCell>
                      <TableCell>{s.distinct_authors}</TableCell>
                      <TableCell>
                        <span style={{ color: hsl(SC.bullish) }}>{s.stance_mix.bullish}▲</span>{" "}
                        <span style={{ color: hsl(SC.bearish) }}>{s.stance_mix.bearish}▼</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          {view === "grouped" && (
            <div className="space-y-2">
              {grouped.map(({ sym, calls, sig }) => (
                <Card key={sym} className="rounded-none gap-0 py-0">
                  <div className="flex items-center gap-2 border-b border-border px-3 py-2">
                    <Dot t={vc(sig?.classification)} />
                    <span className="font-semibold">{sym}</span>
                    {sig && <Tag v={sig.classification} />}
                    <span className="text-xs text-muted-foreground ml-auto">{calls.length} calls{sig ? ` · score ${sig.score.toFixed(2)}` : ""}</span>
                  </div>
                  <div className="divide-y divide-border">
                    {calls.slice(0, 6).map((c, i) => <CallRow key={i} c={c} compact />)}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* trade ideas */}
        <div className="space-y-2">
          <Label>trade ideas — confirmed</Label>
          <div className="space-y-1.5">
            {scan.trade_ideas.map((idea) => <IdeaCard key={idea.symbol} idea={idea} />)}
            {scan.trade_ideas.length === 0 && <div className="text-muted-foreground text-sm">no confirmed ideas this scan.</div>}
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Public Alpha</h1>
        <span className="text-muted-foreground text-sm">social trades — organic vs coordinated, confirmed</span>
      </div>
      {children}
    </main>
  );
}

function CallRow({ c, compact }: { c: Call; compact?: boolean }) {
  return (
    <div className={`flex items-start gap-3 border-border bg-card px-3 py-2 ${compact ? "" : "border"}`}>
      <div className="shrink-0 w-24">
        <div className="font-semibold truncate">{c.symbol}</div>
        {c.classification && <Tag v={c.classification} />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-medium truncate">{c.author}</span>
          <span className="uppercase" style={{ color: hsl(sc(c.stance)) }}>{c.stance ?? "—"}</span>
          <span className="text-muted-foreground">{c.source}</span>
          <span className="text-muted-foreground ml-auto">{ago(c.ts)}</span>
        </div>
        <div className="text-sm mt-0.5 text-foreground/90">{c.summary}</div>
      </div>
    </div>
  );
}

function IdeaCard({ idea }: { idea: Idea }) {
  const gate = (ok: boolean, label: string) => (
    <span className="text-[10px] uppercase tracking-wider" style={{ color: ok ? hsl(SC.bullish) : hsl(SC.bearish) }}>
      {ok ? "✓" : "✕"} {label}
    </span>
  );
  return (
    <Card className="rounded-none p-3 gap-1.5">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{idea.symbol}</span>
        <Tag v={idea.classification} />
        <span className="text-xs text-primary ml-auto">conf {idea.confidence}</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {gate(idea.narrative_heating, "heating")}
        {gate(idea.score >= 0.6, "organic")}
        {gate(idea.confirmed, "confirmed")}
        {gate(idea.regime_state === "risk_on" || idea.regime_state === "neutral", "regime")}
      </div>
      {idea.top_calls?.[0] && (
        <div className="text-xs text-muted-foreground truncate">
          {idea.top_calls[0].author}: {idea.top_calls[0].summary}
        </div>
      )}
    </Card>
  );
}
