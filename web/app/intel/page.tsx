"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import {
  type CmcOnly, type Mover, type Scan, type Signal,
  SC, hsl, pct, usd, vc,
} from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);
const Asset = ({ s }: { s: string }) => (
  <Link href={`/asset?symbol=${encodeURIComponent(s)}`} className="font-semibold hover:underline hover:text-primary">{s}</Link>
);
function Dot({ t }: { t: string }) {
  return <span className="inline-block w-[6px] h-[6px] rounded-full align-middle" style={{ background: hsl(t) }} />;
}

export default function IntelPage() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/scan.json").then((r) => { if (!r.ok) throw new Error(`scan.json ${r.status}`); return r.json(); })
      .then(setScan).catch((e) => setErr(String(e)));
  }, []);

  const sigBy = useMemo(
    () => Object.fromEntries((scan?.signals ?? []).map((s) => [s.symbol, s])) as Record<string, Signal>,
    [scan]);

  const back = <Link href="/" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← dashboard</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed to load — {err}</div></Wrap>;
  if (!scan) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;

  const ca = scan.cmc_attention;
  const ov = ca?.overlap;
  const r = scan.regime;
  const alt = r.altseason_index;
  const fg = r.fear_greed_trend;

  return (
    <Wrap>
      <div className="flex items-baseline gap-3">
        {back}
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Market Intel</h1>
        <span className="text-muted-foreground text-sm">CMC&apos;s own crowd vs the KOL calls</span>
        <Link href="/setups" className="ml-auto text-sm text-muted-foreground hover:text-primary uppercase tracking-wider">Setups →</Link>
      </div>

      {/* CMC crowd vs the calls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <CrowdCol title="corroborated" hint="called AND trending on CMC — strongest" color={SC.bullish}
          syms={ov?.corroborated ?? []} sigBy={sigBy} />
        <CrowdCol title="KOL-only" hint="called, but CMC's crowd isn't watching — unconfirmed hype" color={SC.neutral}
          syms={ov?.kol_only ?? []} sigBy={sigBy} />
        <Card className="rounded-none p-3 gap-2">
          <div className="flex items-baseline gap-2"><Label>CMC-only</Label>
            <span className="text-[11px] text-muted-foreground">trending on CMC, nobody&apos;s calling — under-called</span></div>
          <div className="space-y-1">
            {(ov?.cmc_only ?? []).map((c: CmcOnly) => (
              <div key={c.symbol} className="flex items-center gap-2 text-sm">
                <Asset s={c.symbol} />
                <span className="text-muted-foreground text-xs truncate">{c.name}</span>
                {c.rank != null && <span className="text-muted-foreground text-xs">#{c.rank}</span>}
                {c.percent_change_24h != null && (
                  <span className="ml-auto text-xs" style={{ color: hsl(c.percent_change_24h >= 0 ? SC.bullish : SC.bearish) }}>{pct(c.percent_change_24h)}</span>
                )}
              </div>
            ))}
            {(ov?.cmc_only ?? []).length === 0 && <div className="text-muted-foreground text-sm">—</div>}
          </div>
        </Card>
      </div>

      {/* market movers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <MoverCol title="top gainers (24h)" rows={ca?.gainers ?? []} sigBy={sigBy} />
        <MoverCol title="top losers (24h)" rows={ca?.losers ?? []} sigBy={sigBy} />
        <MoverCol title="most visited" rows={ca?.most_visited ?? []} sigBy={sigBy} />
      </div>

      {/* regime detail */}
      <Card className="rounded-none p-3 gap-3">
        <Label>regime detail</Label>
        <div className="flex flex-wrap gap-x-10 gap-y-4">
          <div>
            <Label>altcoin season index</Label>
            {alt ? (
              <>
                <div className="text-2xl">{alt.value}<span className="text-muted-foreground text-sm ml-1">/100 · {alt.classification.replace("_", " ")}</span></div>
                <div className="relative h-2 mt-1 w-56 border border-border">
                  <div className="absolute inset-y-0 left-0 bg-primary/60" style={{ width: `${alt.value}%` }} />
                </div>
                {alt.yearly_high != null && <div className="text-[11px] text-muted-foreground mt-0.5">yr range {alt.yearly_low}–{alt.yearly_high} · ≥75 = altseason, ≤25 = bitcoin season</div>}
              </>
            ) : <div className="text-muted-foreground text-sm">—</div>}
          </div>
          <div>
            <Label>fear &amp; greed (14d)</Label>
            {fg ? (
              <>
                <div className="text-2xl">{fg.latest}
                  <span className="text-sm ml-2" style={{ color: hsl(fg.direction === "rising" ? SC.bullish : fg.direction === "falling" ? SC.bearish : SC.neutral) }}>
                    {fg.direction === "rising" ? "▲" : fg.direction === "falling" ? "▼" : "→"} {fg.delta >= 0 ? "+" : ""}{fg.delta}</span>
                </div>
                <div className="flex items-end gap-[3px] h-10 mt-1">
                  {fg.points.map((p, i) => (
                    <div key={i} title={`${p.value}`} style={{ height: `${Math.max(6, p.value)}%`, width: 6, background: hsl(p.value < 25 ? SC.bearish : p.value < 55 ? "40 71% 73%" : SC.bullish) }} />
                  ))}
                </div>
              </>
            ) : <div className="text-muted-foreground text-sm">—</div>}
          </div>
          <div>
            <Label>dominance</Label>
            <div className="text-2xl">{r.btc_dominance != null ? `${r.btc_dominance.toFixed(1)}%` : "—"}<span className="text-muted-foreground text-sm ml-1">BTC</span></div>
            <div className="text-[11px] text-muted-foreground mt-0.5">regime: {r.state}</div>
          </div>
        </div>
      </Card>
    </Wrap>
  );
}

function CrowdCol({ title, hint, color, syms, sigBy }: {
  title: string; hint: string; color: string; syms: string[]; sigBy: Record<string, Signal>;
}) {
  return (
    <Card className="rounded-none p-3 gap-2">
      <div className="flex items-baseline gap-2">
        <Label>{title}</Label><span className="text-sm" style={{ color: hsl(color) }}>{syms.length}</span>
      </div>
      <div className="text-[11px] text-muted-foreground -mt-1">{hint}</div>
      <div className="flex flex-wrap gap-1.5">
        {syms.map((s) => {
          const sig = sigBy[s];
          return (
            <span key={s} className="inline-flex items-center gap-1.5 border border-border px-2 py-1 text-sm">
              {sig && <Dot t={vc(sig.classification)} />}<Asset s={s} />
              {sig && <span className="text-muted-foreground text-xs">{sig.n_calls}</span>}
            </span>
          );
        })}
        {syms.length === 0 && <span className="text-muted-foreground text-sm">—</span>}
      </div>
    </Card>
  );
}

function MoverCol({ title, rows, sigBy }: { title: string; rows: Mover[]; sigBy: Record<string, Signal> }) {
  return (
    <Card className="rounded-none p-3 gap-2">
      <Label>{title}</Label>
      <div className="space-y-1">
        {rows.slice(0, 12).map((m, i) => {
          const sig = m.symbol ? sigBy[m.symbol] : undefined;
          return (
            <div key={`${m.symbol}-${i}`} className="flex items-center gap-2 text-sm">
              {sig && <Dot t={vc(sig.classification)} />}
              <Asset s={m.symbol} />
              <span className="text-muted-foreground text-xs truncate max-w-[120px]">{m.name}</span>
              {m.percent_change_24h != null ? (
                <span className="ml-auto text-xs" style={{ color: hsl(m.percent_change_24h >= 0 ? SC.bullish : SC.bearish) }}>{pct(m.percent_change_24h)}</span>
              ) : m.rank != null ? <span className="ml-auto text-muted-foreground text-xs">#{m.rank}</span> : null}
            </div>
          );
        })}
        {rows.length === 0 && <div className="text-muted-foreground text-sm">— (needs Startup+ tier for crypto trending)</div>}
      </div>
    </Card>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">{children}</main>;
}
