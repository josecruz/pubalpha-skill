"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { Timeline } from "@/components/timeline";
import {
  type Call, type CmcAttention, type Idea, type Scan, type Signal,
  SC, ago, hsl, pct, sc, stanceLabel, usd, vc,
} from "@/lib/scan";

type LogoMap = Record<string, string | null | undefined>;

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);
function Tag({ v }: { v: string }) {
  return <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border"
    style={{ color: hsl(vc(v)), borderColor: hsl(vc(v), 0.35) }}>{v}</span>;
}
function Dot({ t }: { t: string }) {
  return <span className="inline-block w-[6px] h-[6px] rounded-full align-middle" style={{ background: hsl(t) }} />;
}
const Asset = ({ s }: { s: string }) => (
  <Link href={`/asset?symbol=${encodeURIComponent(s)}`} className="font-semibold hover:underline hover:text-primary">{s}</Link>
);

export default function Page() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<"timeline" | "calls" | "assets" | "grouped">("timeline");

  useEffect(() => {
    fetch("/scan.json")
      .then((r) => { if (!r.ok) throw new Error(`scan.json ${r.status}`); return r.json(); })
      .then(setScan).catch((e) => setErr(String(e)));
  }, []);

  const grouped = useMemo(() => {
    const by: Record<string, Call[]> = {};
    for (const c of scan?.feed ?? []) (by[c.symbol] ??= []).push(c);
    const sigBy = Object.fromEntries((scan?.signals ?? []).map((s) => [s.symbol, s]));
    return Object.entries(by).map(([sym, calls]) => ({ sym, calls, sig: sigBy[sym] as Signal | undefined }))
      .sort((a, b) => b.calls.length - a.calls.length);
  }, [scan]);

  const logoBy: LogoMap = useMemo(
    () => Object.fromEntries((scan?.signals ?? []).map((s) => [s.symbol, s.identity?.logo])), [scan]);

  if (err) return <Shell><div className="text-destructive p-6">Failed to load /scan.json — {err}. Run the scanner first.</div></Shell>;
  if (!scan) return <Shell><div className="text-muted-foreground p-6">Loading scan…</div></Shell>;

  const { regime: r, narrative: n, market_insights: mi, meta } = scan;
  return (
    <Shell>
      {/* context strip */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border border-border bg-card px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <Label>regime</Label>
          <span className="uppercase text-sm" style={{ color: r.state === "risk_off" ? hsl(SC.bearish) : hsl(SC.bullish) }}>{r.state}</span>
          {r.fear_greed != null && (
            <span className="text-muted-foreground text-sm">
              F&amp;G {r.fear_greed}
              {r.fear_greed_trend && <FngArrow dir={r.fear_greed_trend.direction} delta={r.fear_greed_trend.delta} />}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Label>heating</Label>
          <span className="uppercase text-sm text-primary">{n.heating ? n.sector : "flat"}</span>
        </div>
        <div className="hidden md:flex items-center gap-2 min-w-0">
          <Label>topics</Label>
          <span className="text-muted-foreground text-sm truncate">{(n.trending_topics ?? []).slice(0, 4).join(" · ")}</span>
        </div>
        <div className="ml-auto text-sm text-muted-foreground">{meta.total_calls} calls · {meta.classified} assets</div>
      </div>

      {/* market insights */}
      <MarketInsights mi={mi} regime={r} />

      {/* CMC attention cross-ref strip */}
      <AttentionStrip ca={scan.cmc_attention} />

      {/* setups teaser */}
      <SetupsStrip setups={scan.setups} />

      {/* hot assets */}
      <div>
        <Label>hot assets — most called (click for detail)</Label>
        <ScrollArea className="mt-1">
          <div className="flex gap-2 pb-2">
            {scan.signals.slice(0, 16).map((s) => (
              <Link key={s.symbol} href={`/asset?symbol=${encodeURIComponent(s.symbol)}`}
                className="shrink-0 border border-border bg-card px-3 py-2 hover:border-primary transition-colors">
                <div className="flex items-center gap-2">
                  <AssetIcon logo={s.identity?.logo} symbol={s.symbol} size={18} />
                  <span className="font-semibold">{s.symbol}</span>
                  <Dot t={vc(s.classification)} />
                  <span className="text-muted-foreground text-xs">{s.n_calls}</span>
                  {s.attention?.on_cmc && <span className="text-[9px] uppercase tracking-wider" style={{ color: hsl(SC.bullish) }} title="trending on CMC too">CMC ✓</span>}
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5">
                  {s.market?.price != null ? `${usd(s.market.price)} ${pct(s.market.percent_change_24h)}` : `score ${s.score.toFixed(2)}`}
                </div>
              </Link>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* feed + trade ideas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between">
            <Label>social trades feed</Label>
            <div className="flex border border-border">
              {(["timeline", "calls", "assets", "grouped"] as const).map((m) => (
                <button key={m} onClick={() => setView(m)}
                  className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${view === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{m}</button>
              ))}
            </div>
          </div>

          {view === "timeline" && <Timeline feed={scan.feed} logoBy={logoBy} />}

          {view === "calls" && <div className="space-y-1.5">{scan.feed.map((c, i) => <CallRow key={i} c={c} logo={logoBy[c.symbol]} />)}</div>}

          {view === "assets" && (
            <Card className="p-0 overflow-hidden rounded-none">
              <Table>
                <TableHeader><TableRow>
                  {["Asset", "Calls", "Verdict", "Score", "Price", "24h", "CEX vol", "DEX vol"].map((h) => (
                    <TableHead key={h} className="text-[11px] uppercase tracking-wider">{h}</TableHead>))}
                </TableRow></TableHeader>
                <TableBody>
                  {scan.signals.map((s) => (
                    <TableRow key={s.symbol}>
                      <TableCell><span className="flex items-center gap-2"><AssetIcon logo={s.identity?.logo} symbol={s.symbol} size={16} /><Asset s={s.symbol} /></span></TableCell>
                      <TableCell>{s.n_calls}</TableCell>
                      <TableCell><Tag v={s.classification} /></TableCell>
                      <TableCell>{s.score.toFixed(2)}</TableCell>
                      <TableCell>{usd(s.market?.price)}</TableCell>
                      <TableCell style={{ color: (s.market?.percent_change_24h ?? 0) >= 0 ? hsl(SC.bullish) : hsl(SC.bearish) }}>{pct(s.market?.percent_change_24h)}</TableCell>
                      <TableCell>{usd(s.market?.cex_volume_24h)}</TableCell>
                      <TableCell>{usd(s.market?.dex_volume_24h)}</TableCell>
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
                    <AssetIcon logo={sig?.identity?.logo} symbol={sym} size={18} /><Asset s={sym} />
                    {sig && <Tag v={sig.classification} />}
                    <span className="text-xs text-muted-foreground ml-auto">{calls.length} calls{sig ? ` · score ${sig.score.toFixed(2)}` : ""}</span>
                  </div>
                  <div className="divide-y divide-border">{calls.slice(0, 6).map((c, i) => <CallRow key={i} c={c} logo={logoBy[c.symbol]} compact />)}</div>
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Label>trade ideas — confirmed</Label>
          <div className="space-y-1.5">
            {scan.trade_ideas.map((idea) => <IdeaCard key={idea.symbol} idea={idea} logo={logoBy[idea.symbol]} />)}
            {scan.trade_ideas.length === 0 && <div className="text-muted-foreground text-sm">no confirmed ideas this scan.</div>}
          </div>
        </div>
      </div>
    </Shell>
  );
}

function MarketInsights({ mi, regime }: { mi: Scan["market_insights"]; regime: Scan["regime"] }) {
  const cex = mi.surfaced_cex_volume_24h || 0, dex = mi.surfaced_dex_volume_24h || 0;
  const tot = cex + dex || 1;
  const alt = regime.altseason_index;
  const tiles: [string, string][] = [
    ["Total mcap", usd(mi.total_market_cap)], ["24h volume", usd(mi.total_volume_24h)],
    ["DeFi 24h", usd(mi.defi_volume_24h)], ["BTC dom", mi.btc_dominance != null ? `${mi.btc_dominance.toFixed(1)}%` : "—"],
    ["ETH dom", mi.eth_dominance != null ? `${mi.eth_dominance.toFixed(1)}%` : "—"],
  ];
  return (
    <Card className="rounded-none p-3 gap-2">
      <Label>market insights</Label>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {tiles.map(([k, v]) => (
          <div key={k}><div className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</div><div className="text-base">{v}</div></div>
        ))}
        {alt && (
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">Altseason idx</div>
            <div className="text-base">{alt.value}<span className="text-muted-foreground text-xs ml-1">/100 · {alt.classification.replace("_", " ")}</span></div>
          </div>
        )}
        <div className="min-w-[220px] flex-1">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">CEX vs DEX volume (surfaced)</div>
          <div className="flex h-3 mt-1 border border-border">
            <div style={{ width: `${(cex / tot) * 100}%`, background: hsl("213 32% 52%") }} />
            <div style={{ width: `${(dex / tot) * 100}%`, background: hsl(VCgreen) }} />
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">CEX {usd(cex)} · DEX {usd(dex)}</div>
        </div>
      </div>
    </Card>
  );
}
const VCgreen = "92 28% 65%";

export function FngArrow({ dir, delta }: { dir: string; delta: number }) {
  const up = dir === "rising", down = dir === "falling";
  const color = up ? SC.bullish : down ? SC.bearish : SC.neutral;
  return <span className="ml-1" style={{ color: hsl(color) }} title={`F&G ${dir} (${delta >= 0 ? "+" : ""}${delta} / 14d)`}>
    {up ? "▲" : down ? "▼" : "→"}{delta >= 0 ? "+" : ""}{delta}</span>;
}

function SetupsStrip({ setups }: { setups: Scan["setups"] }) {
  const { spot, perp } = setups;
  if (!spot?.length && !perp?.length) return null;
  const breaking = spot.filter((s) => s.is_breakout).length;
  const confirmed = spot.filter((s) => s.social_confirmed).length;
  const top = spot.slice(0, 4);
  return (
    <Link href="/setups" className="flex flex-wrap items-center gap-x-4 gap-y-1 border border-border bg-card px-3.5 py-2 hover:border-primary transition-colors">
      <Label>setups</Label>
      <span className="text-sm"><span style={{ color: hsl(SC.bullish) }}>{breaking}</span> <span className="text-muted-foreground">breaking out</span></span>
      <span className="text-sm"><span style={{ color: hsl(SC.bullish) }}>{confirmed}</span> <span className="text-muted-foreground">social-confirmed</span></span>
      <span className="text-sm"><span className="text-primary">{perp.length}</span> <span className="text-muted-foreground">perp candidates</span></span>
      <span className="hidden md:inline text-muted-foreground text-sm">· {top.map((s) => s.symbol).join(" · ")}</span>
      <span className="ml-auto text-primary text-sm">Setups →</span>
    </Link>
  );
}

function AttentionStrip({ ca }: { ca: CmcAttention }) {
  if (!ca?.overlap) return null;
  const { corroborated, kol_only, cmc_only } = ca.overlap;
  return (
    <Link href="/intel" className="flex flex-wrap items-center gap-x-4 gap-y-1 border border-border bg-card px-3.5 py-2 hover:border-primary transition-colors">
      <Label>cmc crowd vs calls</Label>
      <span className="text-sm"><span style={{ color: hsl(SC.bullish) }}>{corroborated.length}</span> <span className="text-muted-foreground">corroborated</span></span>
      <span className="text-sm"><span style={{ color: hsl(SC.neutral) }}>{kol_only.length}</span> <span className="text-muted-foreground">KOL-only</span></span>
      <span className="text-sm"><span className="text-primary">{cmc_only.length}</span> <span className="text-muted-foreground">CMC-only (under-called)</span></span>
      <span className="ml-auto text-primary text-sm">Market Intel →</span>
    </Link>
  );
}

function CallRow({ c, logo, compact }: { c: Call; logo?: string | null; compact?: boolean }) {
  return (
    <div className={`flex items-start gap-3 border-border bg-card px-3 py-2 ${compact ? "" : "border"}`}>
      <div className="shrink-0 w-[68px] flex items-center gap-1.5">
        <AssetIcon logo={logo} symbol={c.symbol} size={18} /><Asset s={c.symbol} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-xs">
          <Avatar handle={c.author} platform={c.platform} size={15} />
          {c.source_id
            ? <Link href={`/speaker?handle=${encodeURIComponent(c.author)}`} className="font-medium truncate hover:text-primary">{c.author}</Link>
            : <span className="font-medium truncate">{c.author}</span>}
          {c.verified && <VerifiedBadge size={12} />}
          <PlatformIcon platform={c.platform} size={12} />
          <span className="uppercase" style={{ color: hsl(sc(c.stance)) }}>{stanceLabel(c.stance)}</span>
          {c.source_id
            ? <Link href={`/stream?id=${encodeURIComponent(c.source_id)}${c.video_seconds ? `&t=${c.video_seconds}` : ""}`} className="text-muted-foreground hover:text-primary">{c.source} ↗</Link>
            : c.url && <a href={c.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary">{c.source} ↗</a>}
          {c.since_call_pct != null && (
            <span title="since the call" style={{ color: hsl(c.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(c.since_call_pct)}</span>
          )}
          <span className="text-muted-foreground ml-auto">{ago(c.ts)}</span>
        </div>
        <div className="text-sm mt-0.5 text-foreground/90">{c.summary}</div>
      </div>
    </div>
  );
}

function IdeaCard({ idea, logo }: { idea: Idea; logo?: string | null }) {
  const gate = (ok: boolean, label: string) => (
    <span className="text-[10px] uppercase tracking-wider" style={{ color: ok ? hsl(SC.bullish) : hsl(SC.bearish) }}>{ok ? "✓" : "✕"} {label}</span>
  );
  return (
    <Card className="rounded-none p-3 gap-1.5">
      <div className="flex items-center gap-2"><AssetIcon logo={logo} symbol={idea.symbol} size={18} /><Asset s={idea.symbol} /><Tag v={idea.classification} />
        <span className="text-xs text-primary ml-auto">conf {idea.confidence}</span></div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {gate(idea.narrative_heating, "heating")}{gate(idea.score >= 0.6, "organic")}
        {gate(idea.confirmed, "confirmed")}{gate(idea.regime_state === "risk_on" || idea.regime_state === "neutral", "regime")}
      </div>
      {idea.top_calls?.[0] && <div className="text-xs text-muted-foreground truncate">{idea.top_calls[0].author}: {idea.top_calls[0].summary}</div>}
    </Card>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Public Alpha</h1>
        <span className="text-muted-foreground text-sm">social trades — organic vs coordinated, confirmed</span>
        <div className="ml-auto flex gap-4">
          <Link href="/streams" className="text-sm text-muted-foreground hover:text-primary uppercase tracking-wider">Streams →</Link>
          <Link href="/setups" className="text-sm text-muted-foreground hover:text-primary uppercase tracking-wider">Setups →</Link>
          <Link href="/intel" className="text-sm text-muted-foreground hover:text-primary uppercase tracking-wider">Market Intel →</Link>
        </div>
      </div>
      {children}
    </main>
  );
}
