"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { PriceChart } from "@/components/price-chart";
import { Timeline } from "@/components/timeline";
import { AssetIcon, Avatar, ExchangeIcon, PlatformIcon, VerifiedBadge } from "@/components/icons";
import {
  type Call, type Idea, type Scan, type Signal,
  SC, age, ago, funding, hsl, pct, stanceLabel, usd, vc,
} from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);

// Plain-language read of the classifier — turns each feature (higher = more coordinated) into a finding.
const VERDICT_BLURB: Record<string, string> = {
  organic: "These look like genuine, independent calls — not a coordinated push.",
  coordinated: "These show the hallmarks of a coordinated pump.",
  mixed: "Mixed — some genuine interest, some signs of coordination.",
};
const SIGNAL_ROWS: { key: string; label: string; text: Record<string, string> }[] = [
  { key: "timing_clustering", label: "Timing", text: { organic: "spread over time, not bunched", coordinated: "jammed into a tight window", mixed: "somewhat bunched together", na: "—" } },
  { key: "author_concentration", label: "Authors", text: { organic: "many independent accounts", coordinated: "a few accounts repeating", mixed: "a handful of accounts", na: "—" } },
  { key: "language_similarity", label: "Wording", text: { organic: "varied, original phrasing", coordinated: "near-identical copypasta", mixed: "some repeated phrasing", na: "—" } },
  { key: "low_substance", label: "Substance", text: { organic: "real theses, not just hype", coordinated: "pure urgency / hype", mixed: "mixed substance", na: "—" } },
  { key: "onchain_pump", label: "Pump check", text: { organic: "no pump pattern on-chain", coordinated: "price spiking on thin liquidity", mixed: "some on-chain froth", na: "not checked on-chain" } },
];
function signalState(v: number | undefined): "organic" | "coordinated" | "mixed" | "na" {
  if (v == null) return "na";
  return v < 0.34 ? "organic" : v > 0.66 ? "coordinated" : "mixed";
}
const STATE_ICON: Record<string, string> = { organic: "✓", coordinated: "✕", mixed: "~", na: "·" };
const STATE_COLOR: Record<string, string> = { organic: SC.bullish, coordinated: SC.bearish, mixed: "40 71% 73%", na: SC.neutral };

export default function AssetPage() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [sym, setSym] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const [callsView, setCallsView] = useState<"timeline" | "cards">("timeline");

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
  const id = sig.identity, perf = sig.performance, att = sig.attention, venues = sig.venues ?? [];
  const perpVenues = sig.perp?.venues ?? [];
  const fundingColor = (fr: number | null | undefined) => ((fr ?? 0) >= 0 ? SC.bullish : SC.bearish);

  return (
    <Wrap>
      <div className="flex items-center gap-3">{back}
        <AssetIcon logo={id?.logo} symbol={sig.symbol} size={28} />
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

      {/* price chart with call markers */}
      {sig.price_series && sig.price_series.length > 1 && (
        <div>
          <div className="flex items-baseline justify-between">
            <Label>price — last {sig.price_series.length}d · {calls.length} calls marked</Label>
            <span className="text-[11px] text-muted-foreground">
              {usd(Math.min(...sig.price_series.map((p) => p.close)))} – {usd(Math.max(...sig.price_series.map((p) => p.close)))}
            </span>
          </div>
          <div className="mt-1"><PriceChart series={sig.price_series} calls={calls.map((c) => ({ ts: c.ts, stance: c.stance }))} /></div>
          <div className="flex gap-3 text-[10px] uppercase tracking-wider text-muted-foreground mt-1">
            <span style={{ color: hsl(SC.bullish) }}>● long call</span>
            <span style={{ color: hsl(SC.bearish) }}>● short call</span>
            <span style={{ color: hsl(SC.neutral) }}>● watch</span>
          </div>
        </div>
      )}

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

        {/* why — plain language */}
        <Card className="rounded-none p-3 gap-2">
          <Label>why this verdict</Label>
          <div className="flex items-baseline gap-2">
            <span className="text-base uppercase font-semibold" style={{ color: hsl(vc(sig.classification)) }}>{sig.classification}</span>
            <span className="text-sm text-muted-foreground">{VERDICT_BLURB[sig.classification]}</span>
          </div>
          <div className="space-y-1 mt-0.5">
            {SIGNAL_ROWS.map((row) => {
              const st = signalState(sig.features?.[row.key]);
              return (
                <div key={row.key} className="flex items-baseline gap-2 text-sm">
                  <span className="w-4 text-center shrink-0" style={{ color: hsl(STATE_COLOR[st]) }}>{STATE_ICON[st]}</span>
                  <span className="w-28 shrink-0 text-muted-foreground">{row.label}</span>
                  <span className="flex-1">{row.text[st]}</span>
                </div>
              );
            })}
            {idea?.onchain && (
              <div className="flex items-baseline gap-2 text-sm border-t border-border pt-2 mt-1">
                <span className="w-4 text-center shrink-0" style={{ color: hsl(idea.onchain.confirmed ? SC.bullish : SC.neutral) }}>{idea.onchain.confirmed ? "✓" : "·"}</span>
                <span className="w-28 shrink-0 text-muted-foreground">Confirmation</span>
                <span className="flex-1">{idea.onchain.confirmed ? "money is moving on-chain — confirmed" : "not yet confirmed on-chain"}</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* decision signals — KOL sentiment · breakout · perp */}
      {(sig.sentiment || sig.breakout || sig.perp) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {sig.sentiment && (() => {
            const s = sig.sentiment, tot = s.bull + s.bear + s.neutral || 1;
            const clr = s.label === "bullish" ? SC.bullish : s.label === "bearish" ? SC.bearish : SC.neutral;
            return (
              <Card className="rounded-none p-3 gap-2">
                <Label>KOL sentiment</Label>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg uppercase" style={{ color: hsl(clr) }}>{s.label}</span>
                  <span className="text-muted-foreground text-sm">{s.score >= 0 ? "+" : ""}{s.score.toFixed(2)} · {s.n_kols} KOLs</span>
                </div>
                <div className="flex h-3 border border-border">
                  <div style={{ width: `${(s.bull / tot) * 100}%`, background: hsl(SC.bullish) }} />
                  <div style={{ width: `${(s.neutral / tot) * 100}%`, background: hsl(SC.neutral) }} />
                  <div style={{ width: `${(s.bear / tot) * 100}%`, background: hsl(SC.bearish) }} />
                </div>
                <div className="text-[11px] text-muted-foreground">{s.bull} bull · {s.bear} bear · {s.neutral} neutral</div>
              </Card>
            );
          })()}
          {sig.breakout && sig.breakout.strength != null && (
            <Card className="rounded-none p-3 gap-2">
              <Label>breakout (spot)</Label>
              <div className="text-sm">
                {sig.breakout.is_breakout
                  ? <span style={{ color: hsl(SC.bullish) }}>● BREAKOUT</span>
                  : <span className="text-muted-foreground">building</span>}
                {sig.breakout.social_confirmed && <span className="ml-2" style={{ color: hsl(SC.bullish) }}>✓ social-confirmed</span>}
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                <Stat k="vs 20d-high" v={pct(sig.breakout.pct_above_20d_high)} color={(sig.breakout.pct_above_20d_high ?? 0) >= 0 ? SC.bullish : SC.bearish} />
                <Stat k="Vol×" v={sig.breakout.vol_mult != null ? `${sig.breakout.vol_mult.toFixed(2)}×` : "—"} />
                <Stat k="ATR%" v={sig.breakout.atr_pct != null ? `${sig.breakout.atr_pct.toFixed(1)}%` : "—"} />
                <Stat k="Strength" v={(sig.breakout.strength ?? 0).toFixed(2)} />
              </div>
            </Card>
          )}
          {sig.perp && sig.perp.bias && (
            <Card className="rounded-none p-3 gap-2">
              <Label>perp (derivatives)</Label>
              <div className="text-sm">{sig.perp.bias} <span className="text-muted-foreground">· {sig.perp.n_venues ?? (sig.perp.venues?.length || 0)} venues</span></div>
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                <Stat k="Funding" v={funding(sig.perp.funding_rate)} color={(sig.perp.funding_rate ?? 0) >= 0 ? SC.bullish : SC.bearish} />
                <Stat k="Open interest" v={usd(sig.perp.open_interest)} />
                <Stat k="Perp vol 24h" v={usd(sig.perp.perp_volume_24h)} />
              </div>
              {sig.perp.long_share != null && (
                <div className="mt-1">
                  <Label>long / short lean (funding-implied)</Label>
                  <div className="flex h-3 mt-1 border border-border">
                    <div style={{ width: `${sig.perp.long_share * 100}%`, background: hsl(SC.bullish) }} />
                    <div style={{ width: `${(1 - sig.perp.long_share) * 100}%`, background: hsl(SC.bearish) }} />
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{Math.round(sig.perp.long_share * 100)}% long · {Math.round((1 - sig.perp.long_share) * 100)}% short</div>
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* top venues */}
      {venues.length > 0 && (
        <div>
          <Label>top venues — {venues.length} spot markets by 24h volume</Label>
          <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
            {venues.map((v, i) => (
              <div key={i} className="flex items-center gap-2.5 px-3 py-1.5">
                <ExchangeIcon id={v.exchange_id} name={v.exchange} size={16} />
                <span className="font-medium w-40 truncate">{v.exchange}</span>
                <span className="text-muted-foreground w-28">{v.pair}</span>
                <span className="text-muted-foreground w-20 text-xs">{v.category}</span>
                <span className="ml-auto">{usd(v.volume_24h)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* perp venues (CEX + DEX) */}
      {perpVenues.length > 0 && (
        <div>
          <Label>perp venues — {perpVenues.length} of {sig.perp?.n_venues ?? perpVenues.length} by 24h volume (funding / OI)</Label>
          <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
            {perpVenues.map((v, i) => (
              <div key={i} className="flex items-center gap-2.5 px-3 py-1.5">
                <ExchangeIcon id={v.exchange_id} name={v.venue} size={16} />
                <span className="font-medium w-36 truncate">{v.venue}</span>
                <span className="text-[10px] uppercase tracking-wider px-1 border border-border text-muted-foreground">{v.is_dex ? "DEX" : "CEX"}</span>
                <span className="text-xs" style={{ color: hsl(fundingColor(v.funding_rate)) }}>funding {funding(v.funding_rate)}</span>
                <span className="text-muted-foreground text-xs">OI {usd(v.oi)}</span>
                <span className="ml-auto">{usd(v.volume_24h)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* mentions — timeline (default) or paste.trade-style cards */}
      <div>
        <div className="flex items-center justify-between">
          <Label>mentions — {calls.length} on {sig.symbol}</Label>
          <div className="flex border border-border">
            {(["timeline", "cards"] as const).map((m) => (
              <button key={m} onClick={() => setCallsView(m)}
                className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${callsView === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{m}</button>
            ))}
          </div>
        </div>

        {callsView === "timeline" && <div className="mt-2"><Timeline feed={calls} showAsset={false} /></div>}

        {callsView === "cards" && (
        <div className="space-y-1.5 mt-1">
          {calls.map((c, i) => {
            const stClr = c.stance === "bullish" ? SC.bullish : c.stance === "bearish" ? SC.bearish : SC.neutral;
            return (
              <div key={i} className="border border-border bg-card p-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-1.5 py-px border text-[10px] uppercase tracking-wider" style={{ color: hsl(stClr), borderColor: hsl(stClr, 0.4) }}>{stanceLabel(c.stance)}</span>
                  <Avatar handle={c.author} platform={c.platform} size={16} />
                  {c.source_id
                    ? <Link href={`/speaker?handle=${encodeURIComponent(c.author)}`} className="font-medium hover:text-primary">{c.author}</Link>
                    : <span className="font-medium">{c.author}</span>}
                  {c.verified && <VerifiedBadge size={12} />}
                  <PlatformIcon platform={c.platform} size={12} />
                  {c.source_id
                    ? <Link href={`/stream?id=${encodeURIComponent(c.source_id)}${c.video_seconds ? `&t=${c.video_seconds}` : ""}`} className="text-muted-foreground hover:text-primary">{c.source} ↗</Link>
                    : c.url
                      ? <a href={c.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary">{c.source} ↗</a>
                      : <span className="text-muted-foreground">{c.source}</span>}
                  <span className="text-muted-foreground ml-auto">{ago(c.ts)} ago</span>
                </div>
                <div className="text-sm mt-1.5 text-foreground">{c.summary}</div>
                {c.entry_price != null && (
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 border-t border-border pt-2 text-sm">
                    <span className="font-semibold">{sig.symbol}</span>
                    <span className="uppercase text-xs" style={{ color: hsl(stClr) }}>{stanceLabel(c.stance)}</span>
                    <span className="text-muted-foreground">@ {usd(c.entry_price)}</span>
                    <span className="ml-auto text-muted-foreground">now {usd(m?.price)}</span>
                    {c.since_call_pct != null && (
                      <span className="font-medium" style={{ color: hsl(c.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(c.since_call_pct)}</span>
                    )}
                    <span className="text-muted-foreground text-xs">since call {ago(c.ts)}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        )}
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
