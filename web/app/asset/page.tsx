"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import {
  type Call, type Idea, type Scan, type Signal,
  SC, age, ago, hsl, pct, sc, usd, vc,
} from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);

export default function AssetPage() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [sym, setSym] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setSym((new URLSearchParams(window.location.search).get("symbol") || "").toUpperCase());
    fetch("/scan.json").then((r) => { if (!r.ok) throw new Error(`scan.json ${r.status}`); return r.json(); })
      .then(setScan).catch((e) => setErr(String(e)));
  }, []);

  const sig: Signal | undefined = useMemo(() => scan?.signals.find((s) => s.symbol === sym), [scan, sym]);
  const idea: Idea | undefined = useMemo(() => scan?.trade_ideas.find((i) => i.symbol === sym), [scan, sym]);
  const calls: Call[] = useMemo(() => (scan?.feed ?? []).filter((c) => c.symbol === sym), [scan, sym]);

  const back = <Link href="/" className="text-muted-foreground hover:text-primary text-sm">← back</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed to load — {err}</div></Wrap>;
  if (!scan) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;
  if (!sig) return <Wrap>{back}<div className="text-muted-foreground p-6">No data for {sym || "—"} in this scan.</div></Wrap>;

  const m = sig.market;
  const cex = m?.cex_volume_24h || 0, dex = m?.dex_volume_24h || 0, tot = cex + dex || 1;
  const feats = Object.entries(sig.features ?? {});
  const id = sig.identity, perf = sig.performance, att = sig.attention, venues = sig.venues ?? [];

  return (
    <Wrap>
      <div className="flex items-center gap-3">{back}
        {id?.logo && /* eslint-disable-next-line @next/next/no-img-element */ <img src={id.logo} alt="" className="w-7 h-7" />}
        <h1 className="text-xl font-bold">{sig.symbol}</h1>
        {id?.is_new && <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border" style={{ color: hsl(SC.bearish), borderColor: hsl(SC.bearish, 0.4) }} title="listed < 30 days ago">NEW</span>}
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border"
          style={{ color: hsl(vc(sig.classification)), borderColor: hsl(vc(sig.classification), 0.35) }}>{sig.classification}</span>
        <span className="text-muted-foreground text-sm">organic score {sig.score.toFixed(2)} · {sig.n_calls} calls · {sig.distinct_authors} authors</span>
        {m && <span className="text-muted-foreground text-sm ml-auto">{m.kind === "tokenized_stock" ? `tokenized stock · ${m.chain}` : "crypto"}</span>}
      </div>

      {/* identity strip — tags · age · CMC attention · provenance */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
        {(id?.tags ?? []).slice(0, 5).map((t) => (
          <span key={t} className="px-1.5 py-px border border-border text-muted-foreground">{t}</span>
        ))}
        {id?.date_added && <span className="text-muted-foreground">listed {age(id.date_added)} ago</span>}
        {att && (att.on_cmc
          ? <span style={{ color: hsl(SC.bullish) }}>CMC ✓ trending — {att.sources.map((s) => s.replace("_", " ")).join(", ")}{att.rank ? ` · rank ${att.rank}` : ""}</span>
          : <span className="text-muted-foreground">not on CMC trending</span>)}
        <span className="ml-auto flex gap-3">
          {id?.urls?.website && <a className="text-muted-foreground hover:text-primary" href={id.urls.website} target="_blank" rel="noreferrer">site ↗</a>}
          {id?.urls?.twitter && <a className="text-muted-foreground hover:text-primary" href={id.urls.twitter} target="_blank" rel="noreferrer">twitter ↗</a>}
          {id?.urls?.explorer && <a className="text-muted-foreground hover:text-primary" href={id.urls.explorer} target="_blank" rel="noreferrer">explorer ↗</a>}
          {id?.urls?.source_code && <a className="text-muted-foreground hover:text-primary" href={id.urls.source_code} target="_blank" rel="noreferrer">code ↗</a>}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* market */}
        <Card className="rounded-none p-3 gap-2">
          <Label>market</Label>
          {m ? (
            <>
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                <Stat k="Price" v={usd(m.price)} />
                <Stat k="24h" v={pct(m.percent_change_24h)} color={(m.percent_change_24h ?? 0) >= 0 ? SC.bullish : SC.bearish} />
                <Stat k="7d" v={pct(m.percent_change_7d)} color={(m.percent_change_7d ?? 0) >= 0 ? SC.bullish : SC.bearish} />
                <Stat k="24h vol" v={usd(m.volume_24h)} />
                <Stat k="Market cap" v={usd(m.market_cap)} />
              </div>
              <div className="mt-1">
                <Label>CEX vs DEX volume</Label>
                <div className="flex h-3 mt-1 border border-border">
                  <div style={{ width: `${(cex / tot) * 100}%`, background: hsl("213 32% 52%") }} />
                  <div style={{ width: `${(dex / tot) * 100}%`, background: hsl("92 28% 65%") }} />
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5">CEX {usd(cex)} · DEX {usd(dex)}</div>
              </div>
              {perf && (
                <div className="mt-1">
                  <Label>price context</Label>
                  <div className="flex flex-wrap gap-x-6 gap-y-2 mt-0.5">
                    <Stat k="ATH" v={usd(perf.ath)} />
                    <Stat k="% from ATH" v={pct(perf.pct_from_ath)} color={(perf.pct_from_ath ?? 0) >= 0 ? SC.bullish : SC.bearish} />
                    {perf.ath_date && <Stat k="ATH date" v={age(perf.ath_date) + " ago"} />}
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs">
                    {(["7d", "30d", "90d", "365d"] as const).map((p) => (
                      <span key={p} className="text-muted-foreground">{p} <span style={{ color: hsl((perf.periods[p] ?? 0) >= 0 ? SC.bullish : SC.bearish) }}>{pct(perf.periods[p])}</span></span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : <div className="text-muted-foreground text-sm">no market data on CMC for this asset.</div>}
        </Card>

        {/* classifier */}
        <Card className="rounded-none p-3 gap-2">
          <Label>why — organic vs coordinated</Label>
          <ul className="space-y-0.5 text-sm">{sig.reasons.map((r, i) => <li key={i}>• {r}</li>)}</ul>
          {feats.length > 0 && (
            <div className="mt-1 space-y-1">
              <Label>signals (higher = more coordinated)</Label>
              {feats.map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 text-xs">
                  <span className="w-40 text-muted-foreground">{k.replace(/_/g, " ")}</span>
                  <div className="flex-1 h-2 border border-border"><div style={{ width: `${Math.min(1, v) * 100}%`, background: hsl(v >= 0.5 ? SC.bearish : "213 14% 45%") }} className="h-full" /></div>
                  <span className="w-10 text-right">{v.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
          {idea?.onchain && (
            <div className="mt-1">
              <Label>on-chain confirmation</Label>
              <div className="text-sm" style={{ color: idea.onchain.confirmed ? hsl(SC.bullish) : hsl(SC.bearish) }}>
                {idea.onchain.confirmed ? "confirmed" : "not confirmed"}</div>
              <ul className="text-[11px] text-muted-foreground">{idea.onchain.notes.slice(0, 4).map((nn, i) => <li key={i}>• {nn}</li>)}</ul>
            </div>
          )}
        </Card>
      </div>

      {/* top venues */}
      {venues.length > 0 && (
        <div>
          <Label>top venues — {venues.length} spot markets by 24h volume</Label>
          <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
            {venues.map((v, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-1.5">
                <span className="font-medium w-44 truncate">{v.exchange}</span>
                <span className="text-muted-foreground w-32">{v.pair}</span>
                <span className="text-muted-foreground w-20">{v.category}</span>
                <span className="ml-auto">{usd(v.volume_24h)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* calls */}
      <div>
        <Label>the calls — {calls.length} on {sig.symbol}</Label>
        <div className="space-y-1.5 mt-1">
          {calls.map((c, i) => (
            <div key={i} className="border border-border bg-card px-3 py-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium">{c.author}</span>
                <span className="uppercase" style={{ color: hsl(sc(c.stance)) }}>{c.stance ?? "—"}</span>
                <span className="text-muted-foreground">{c.source}</span>
                {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary">↗ source</a>}
                <span className="text-muted-foreground ml-auto">{ago(c.ts)}</span>
              </div>
              <div className="text-sm mt-0.5">{c.summary}</div>
            </div>
          ))}
        </div>
      </div>
    </Wrap>
  );
}

function Stat({ k, v, color }: { k: string; v: string; color?: string }) {
  return <div><div className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</div>
    <div className="text-base" style={color ? { color: hsl(color) } : undefined}>{v}</div></div>;
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1100px] px-4 py-4 space-y-3">{children}</main>;
}
