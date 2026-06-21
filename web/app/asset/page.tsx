"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { PriceChart } from "@/components/price-chart";
import { Timeline } from "@/components/timeline";
import { AssetIcon, Avatar, ExchangeIcon, PlatformIcon, VerifiedBadge } from "@/components/icons";
import {
  type Call, type Idea, type Scan, type Signal,
  SC, age, ago, funding, hsl, pct, price, stanceLabel, usd, vc,
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
// Strip the source-namespace prefix, e.g. "paste_trade:all-in" → "all-in".
const srcName = (s?: string) => (s ? s.replace(/^[^:]+:/, "") : "");

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
  // one row per KOL — their most-recent call — for the "who / when / where" roster
  const roster: Call[] = useMemo(() => {
    const byAuthor = new Map<string, Call>();
    for (const c of calls) {
      const prev = byAuthor.get(c.author);
      if (!prev || new Date(c.ts).getTime() > new Date(prev.ts).getTime()) byAuthor.set(c.author, c);
    }
    return [...byAuthor.values()].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
  }, [calls]);

  const back = <Link href="/" className="text-muted-foreground hover:text-primary text-sm">← back</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed to load — {err}</div></Wrap>;
  if (!scan) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;
  if (!sig) return <Wrap>{back}<div className="text-muted-foreground p-6">No data for {sym || "—"} in this scan.</div></Wrap>;

  const m = sig.market;
  const cex = m?.cex_volume_24h || 0, dex = m?.dex_volume_24h || 0, tot = cex + dex || 1;
  const id = sig.identity, perf = sig.performance, att = sig.attention, venues = sig.venues ?? [];
  const perpVenues = sig.perp?.venues ?? [];
  const fundingColor = (fr: number | null | undefined) => ((fr ?? 0) >= 0 ? SC.bullish : SC.bearish);

  // thesis — strongest bull / bear case from the actual KOL call summaries
  const byConv = (a: Call, b: Call) => (b.conviction ?? 0) - (a.conviction ?? 0);
  const bullCase = (sig.top_calls ?? []).filter((c) => c.stance === "bullish").sort(byConv)[0];
  const bearCase = (sig.top_calls ?? []).filter((c) => c.stance === "bearish").sort(byConv)[0];

  return (
    <Wrap>
      {/* header — name · ticker · rank up top, price pulled up right beneath it (CMC-style IA) */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">{back}
          <AssetIcon logo={id?.logo} symbol={sig.symbol} size={30} />
          <h1 className="text-2xl font-bold">{sig.symbol}</h1>
          {m?.cmc_rank != null && m.kind !== "tokenized_stock" && <span className="text-[11px] text-muted-foreground border border-border px-1.5 py-px" title="CoinMarketCap rank">#{m.cmc_rank}</span>}
          {id?.is_new && <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border" style={{ color: hsl(SC.bearish), borderColor: hsl(SC.bearish, 0.4) }} title="listed < 30 days ago">NEW</span>}
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border"
            style={{ color: hsl(vc(sig.classification)), borderColor: hsl(vc(sig.classification), 0.35) }}>{sig.classification}</span>
          {m && <span className="text-muted-foreground text-sm ml-auto">{m.kind === "tokenized_stock" ? `tokenized stock · ${m.chain}` : "crypto"}</span>}
        </div>
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          {m?.price != null && <span className="text-3xl font-bold tracking-tight">{price(m.price)}</span>}
          {m?.percent_change_24h != null && (
            <span className="text-sm" style={{ color: hsl(m.percent_change_24h >= 0 ? SC.bullish : SC.bearish) }}>{pct(m.percent_change_24h)} <span className="text-muted-foreground">24h</span></span>
          )}
          {m?.percent_change_7d != null && (
            <span className="text-sm" style={{ color: hsl(m.percent_change_7d >= 0 ? SC.bullish : SC.bearish) }}>{pct(m.percent_change_7d)} <span className="text-muted-foreground">7d</span></span>
          )}
          <span className="ml-auto text-muted-foreground text-sm">organic score {sig.score.toFixed(2)} · {sig.n_calls} calls · {sig.distinct_authors} authors</span>
        </div>
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

      {/* price chart — self-contained: header · range selector · avatar markers · legend */}
      {sig.price_series && sig.price_series.length > 1 && (
        <PriceChart series={sig.price_series} calls={calls.map((c) => ({ ts: c.ts, stance: c.stance, entry_price: c.entry_price, author: c.author, source: c.source, platform: c.platform, since_call_pct: c.since_call_pct, summary: c.summary, verified: c.verified }))} />
      )}

      {/* market — its own full-width row below the chart */}
      <Card className="rounded-none p-3 gap-2">
        <Label>market</Label>
        {m ? (
          <>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <Stat k="Market cap" v={usd(m.market_cap)} />
              <Stat k="24h vol" v={usd(m.volume_24h)} />
              <Stat k="Vol / Mkt cap" v={m.market_cap ? `${((m.volume_24h ?? 0) / m.market_cap * 100).toFixed(2)}%` : "—"} />
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* thesis — plain-language read of what the KOLs are actually arguing */}
        <Card className="rounded-none p-3 gap-2">
          <Label>thesis</Label>
          {sig.sentiment && (() => {
            const s = sig.sentiment;
            const clr = s.label === "bullish" ? SC.bullish : s.label === "bearish" ? SC.bearish : SC.neutral;
            return (
              <div className="text-sm">
                <span className="uppercase" style={{ color: hsl(clr) }}>{s.label} lean</span>
                <span className="text-muted-foreground"> · {s.n_kols} voices · {s.bull} bull / {s.bear} bear</span>
              </div>
            );
          })()}
          {bullCase && (
            <div className="text-sm">
              <span className="text-[11px] uppercase tracking-wider" style={{ color: hsl(SC.bullish) }}>bull case</span>
              <p>{bullCase.summary} <span className="text-muted-foreground">— @{bullCase.author}</span></p>
            </div>
          )}
          {bearCase && (
            <div className="text-sm">
              <span className="text-[11px] uppercase tracking-wider" style={{ color: hsl(SC.bearish) }}>bear case</span>
              <p>{bearCase.summary} <span className="text-muted-foreground">— @{bearCase.author}</span></p>
            </div>
          )}
          {idea?.onchain && (
            <div className="flex items-baseline gap-2 text-sm border-t border-border pt-2">
              <span className="shrink-0" style={{ color: hsl(idea.onchain.confirmed ? SC.bullish : SC.neutral) }}>{idea.onchain.confirmed ? "✓" : "·"}</span>
              <span className="text-muted-foreground">{idea.onchain.confirmed ? "money is moving on-chain — confirmed" : "not yet confirmed on-chain"}</span>
            </div>
          )}
          <div className="text-sm border-t border-border pt-2">
            <span className="uppercase font-semibold" style={{ color: hsl(vc(sig.classification)) }}>{sig.classification}</span>
            <span className="text-muted-foreground"> — {VERDICT_BLURB[sig.classification]}</span>
          </div>
        </Card>

        {/* KOL sentiment + per-KOL roster (who · stance · when · where) */}
        {sig.sentiment && (() => {
          const s = sig.sentiment, stot = s.bull + s.bear + s.neutral || 1;
          const clr = s.label === "bullish" ? SC.bullish : s.label === "bearish" ? SC.bearish : SC.neutral;
          return (
            <Card className="rounded-none p-3 gap-2">
              <Label>KOL sentiment</Label>
              <div className="flex items-baseline gap-2">
                <span className="text-lg uppercase" style={{ color: hsl(clr) }}>{s.label}</span>
                <span className="text-muted-foreground text-sm">{s.score >= 0 ? "+" : ""}{s.score.toFixed(2)} · {s.n_kols} KOLs</span>
              </div>
              <div className="flex h-3 border border-border">
                <div style={{ width: `${(s.bull / stot) * 100}%`, background: hsl(SC.bullish) }} />
                <div style={{ width: `${(s.neutral / stot) * 100}%`, background: hsl(SC.neutral) }} />
                <div style={{ width: `${(s.bear / stot) * 100}%`, background: hsl(SC.bearish) }} />
              </div>
              <div className="text-[11px] text-muted-foreground">{s.bull} bull · {s.bear} bear · {s.neutral} neutral</div>
              {roster.length > 0 && (
                <div className="space-y-1 mt-1 border-t border-border pt-2">
                  {roster.slice(0, 8).map((c, i) => {
                    const stClr = c.stance === "bullish" ? SC.bullish : c.stance === "bearish" ? SC.bearish : SC.neutral;
                    return (
                      <div key={i} className="flex items-center gap-1.5 text-xs">
                        <Avatar handle={c.author} platform={c.platform} size={14} />
                        {c.source_id
                          ? <Link href={`/speaker?handle=${encodeURIComponent(c.author)}`} className="font-medium hover:text-primary truncate max-w-[100px]">{c.author}</Link>
                          : <span className="font-medium truncate max-w-[100px]">{c.author}</span>}
                        {c.verified && <VerifiedBadge size={11} />}
                        <span className="uppercase" style={{ color: hsl(stClr) }}>{stanceLabel(c.stance)}</span>
                        <span className="text-muted-foreground">{ago(c.ts)}</span>
                        {c.source_id
                          ? <Link href={`/stream?id=${encodeURIComponent(c.source_id)}${c.video_seconds ? `&t=${c.video_seconds}` : ""}`} className="text-muted-foreground hover:text-primary ml-auto truncate max-w-[90px]">{srcName(c.source)} ↗</Link>
                          : c.url
                            ? <a href={c.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary ml-auto truncate max-w-[90px]">{srcName(c.source)} ↗</a>
                            : <span className="text-muted-foreground ml-auto truncate max-w-[90px]">{srcName(c.source)}</span>}
                      </div>
                    );
                  })}
                  {roster.length > 8 && <div className="text-[11px] text-muted-foreground">+{roster.length - 8} more — see mentions below</div>}
                </div>
              )}
            </Card>
          );
        })()}
      </div>

      {/* breakout · perp · liquidations */}
      {((sig.breakout && sig.breakout.strength != null) || (sig.perp && sig.perp.bias) || sig.liquidations) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
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
          {sig.liquidations && (() => {
            const lq = sig.liquidations, lr = sig.leverage_read;
            const lp = lq.long_pct ?? 0.5;
            const lrClr = !lr ? SC.neutral
              : lr.label.includes("squeeze") ? SC.bullish
              : (lr.label.includes("cascade") || lr.label.includes("flush")) ? SC.bearish : SC.neutral;
            return (
              <Card className="rounded-none p-3 gap-2">
                <Label>liquidations (24h)</Label>
                <div className="flex flex-wrap gap-x-5 gap-y-1">
                  <Stat k="Total" v={usd(lq.total)} />
                  <Stat k="Long liq" v={usd(lq.long)} color={SC.bullish} />
                  <Stat k="Short liq" v={usd(lq.short)} color={SC.bearish} />
                  <Stat k="Open interest" v={usd(lq.open_interest)} />
                </div>
                <div className="mt-1">
                  <Label>long / short liquidations</Label>
                  <div className="flex h-3 mt-1 border border-border">
                    <div style={{ width: `${lp * 100}%`, background: hsl(SC.bullish) }} />
                    <div style={{ width: `${(1 - lp) * 100}%`, background: hsl(SC.bearish) }} />
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{Math.round(lp * 100)}% long · {Math.round((1 - lp) * 100)}% short</div>
                </div>
                {lr && (
                  <div className="text-sm border-t border-border pt-2">
                    <span className="uppercase" style={{ color: hsl(lrClr) }}>{lr.label}</span>
                    {lr.note && <span className="text-muted-foreground"> — {lr.note}</span>}
                  </div>
                )}
              </Card>
            );
          })()}
        </div>
      )}

      {/* CMC community pulse — top posts + news/articles for this asset */}
      {sig.community && (sig.community.posts.length > 0 || sig.community.articles.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {sig.community.posts.length > 0 && (
            <div>
              <Label>CMC community — {sig.community.n_posts} top posts · {sig.community.engagement.toLocaleString()} engagements</Label>
              <div className="mt-1 space-y-1.5">
                {sig.community.posts.map((p, i) => (
                  <div key={i} className="border border-border bg-card p-3">
                    <div className="flex items-center gap-1.5 text-xs">
                      <Avatar handle={p.author} size={16} />
                      <span className="font-medium truncate max-w-[160px]">{p.author}</span>
                      <span className="text-muted-foreground ml-auto">{ago(p.ts)} ago</span>
                    </div>
                    <div className="text-sm mt-1.5">{p.text}</div>
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-1.5">
                      <span>{p.likes.toLocaleString()} likes</span>
                      <span>{p.comments.toLocaleString()} comments</span>
                      {p.url && <a href={p.url} target="_blank" rel="noreferrer" className="hover:text-primary ml-auto">view ↗</a>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {sig.community.articles.length > 0 && (
            <div>
              <Label>news &amp; articles — {sig.community.articles.length}</Label>
              <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
                {sig.community.articles.map((a, i) => (
                  <a key={i} href={a.url ?? "#"} target="_blank" rel="noreferrer" className="block px-3 py-2 hover:bg-muted/30">
                    <div className="text-foreground">{a.title}</div>
                    <div className="text-[11px] text-muted-foreground mt-0.5">{a.source} · {ago(a.ts)} ago</div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* venues — spot + perp, two columns */}
      {(venues.length > 0 || perpVenues.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {venues.length > 0 && (
            <div>
              <Label>top venues — {venues.length} spot markets by 24h volume</Label>
              <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
                {venues.map((v, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-1.5">
                    <ExchangeIcon id={v.exchange_id} name={v.exchange} size={16} />
                    <span className="font-medium truncate">{v.exchange}</span>
                    <span className="text-muted-foreground text-xs shrink-0">{v.pair}</span>
                    <span className="ml-auto shrink-0">{usd(v.volume_24h)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {perpVenues.length > 0 && (
            <div>
              <Label>perp venues — {perpVenues.length} of {sig.perp?.n_venues ?? perpVenues.length} by 24h volume (funding / OI)</Label>
              <div className="mt-1 border border-border bg-card divide-y divide-border text-sm">
                {perpVenues.map((v, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-1.5">
                    <ExchangeIcon id={v.exchange_id} name={v.venue} size={16} />
                    <span className="font-medium truncate">{v.venue}</span>
                    <span className="text-[10px] uppercase tracking-wider px-1 border border-border text-muted-foreground shrink-0">{v.is_dex ? "DEX" : "CEX"}</span>
                    <span className="text-xs shrink-0" style={{ color: hsl(fundingColor(v.funding_rate)) }}>{funding(v.funding_rate)}</span>
                    <span className="text-muted-foreground text-xs shrink-0">OI {usd(v.oi)}</span>
                    <span className="ml-auto shrink-0">{usd(v.volume_24h)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
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
