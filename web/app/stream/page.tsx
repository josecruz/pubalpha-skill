"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { VideoEmbed } from "@/components/video-embed";
import { type Paste, type PasteTrade, dateFmt, dirColor, dirLabel, mmss } from "@/lib/paste";
import { SC, hsl, pct, usd } from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);
const Ticker = ({ t }: { t: PasteTrade }) => (
  <span className="flex items-center gap-1.5">
    <AssetIcon logo={t.logo_url} symbol={t.ticker} size={16} />
    <Link href={`/asset?symbol=${encodeURIComponent(t.ticker)}`} className="font-semibold hover:text-primary">{t.ticker}</Link>
  </span>
);
const Dir = ({ d }: { d: string | null }) => <span className="uppercase text-xs" style={{ color: hsl(dirColor(d)) }}>{dirLabel(d)}</span>;

export default function StreamPage() {
  const [paste, setPaste] = useState<Paste | null>(null);
  const [id, setId] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [seek, setSeek] = useState(0);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setId(p.get("id") || "");
    setSeek(Number(p.get("t")) || 0);   // deep-link from a mention lands at its moment
    fetch("/paste.json").then((r) => { if (!r.ok) throw new Error(`paste.json ${r.status}`); return r.json(); })
      .then(setPaste).catch((e) => setErr(String(e)));
  }, []);

  const ep = useMemo(() => paste?.episodes.find((e) => e.id === id), [paste, id]);
  const back = <Link href="/streams" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← streams</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed — {err}</div></Wrap>;
  if (!paste) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;
  if (!ep) return <Wrap>{back}<div className="text-muted-foreground p-6">Episode not found.</div></Wrap>;

  const host = ep.trades[0]?.speaker ?? ep.show;
  const hostVerified = ep.trades.some((t) => t.speaker_verified);
  const seekable = ep.platform === "youtube" || ep.platform === "twitch"; // newsletters/tweets have no player

  return (
    <Wrap>
      <div className="flex items-center gap-3">{back}
        <Avatar handle={host} platform={ep.platform} size={22} />
        <Link href={`/speaker?handle=${encodeURIComponent(host)}`} className="font-semibold hover:text-primary">@{host}</Link>
        {hostVerified && <VerifiedBadge size={13} />}
        <PlatformIcon platform={ep.platform} size={14} />
        <span className="text-muted-foreground text-sm">{dateFmt(ep.published_at)}</span>
        <a href="https://paste.trade" target="_blank" rel="noreferrer" className="ml-auto text-xs text-muted-foreground hover:text-primary">source: paste.trade ↗</a>
      </div>
      <h1 className="text-base font-medium">{ep.title}</h1>

      <VideoEmbed key={seek} url={ep.url} platform={ep.platform} seconds={seek} />

      {/* trades list — click a timestamp to seek the player */}
      <div className="border border-border bg-card divide-y divide-border">
        {ep.trades.map((t) => (
          <div key={t.id} className="flex items-center gap-2 px-3 py-1.5 text-sm">
            <button onClick={() => setSeek(t.video_seconds ?? 0)} disabled={!seekable || t.video_seconds == null}
              className="text-primary text-xs w-12 shrink-0 text-left hover:underline disabled:text-muted-foreground disabled:no-underline" title="jump to this point">
              ▶ {mmss(t.video_seconds) || "—"}</button>
            <Ticker t={t} /><Dir d={t.direction} />
            <span className="text-muted-foreground truncate flex-1 min-w-0">{t.headline_quote ?? t.thesis}</span>
            {t.entry_price != null && <span className="text-muted-foreground text-xs shrink-0">{usd(t.entry_price)}</span>}
            {t.since_call_pct != null && <span className="text-xs shrink-0 w-14 text-right" style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)}</span>}
          </div>
        ))}
      </div>

      <Label>trades explained</Label>
      <div className="space-y-2">
        {ep.trades.map((t) => <TradeCard key={t.id} t={t} seekable={seekable} onSeek={() => setSeek(t.video_seconds ?? 0)} />)}
      </div>

      <div className="text-[11px] text-muted-foreground border-t border-border pt-2">
        Content from <a href={ep.url ?? "https://paste.trade"} target="_blank" rel="noreferrer" className="hover:text-primary">{ep.platform}</a> via{" "}
        <a href="https://paste.trade" target="_blank" rel="noreferrer" className="hover:text-primary">paste.trade</a>. Calls link to the CMC thesis where the ticker resolves.
      </div>
    </Wrap>
  );
}

function TradeCard({ t, seekable, onSeek }: { t: PasteTrade; seekable: boolean; onSeek: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="rounded-none p-3 gap-2">
      <div className="flex items-center gap-2 text-xs">
        <button onClick={onSeek} disabled={!seekable || t.video_seconds == null} className="text-primary hover:underline disabled:text-muted-foreground disabled:no-underline">▶ {mmss(t.video_seconds) || "—"}</button>
        {t.bucket && <span className="px-1.5 py-px border border-border uppercase tracking-wider text-muted-foreground">{t.bucket}</span>}
        {t.staked && <span className="px-1.5 py-px border uppercase tracking-wider" style={{ color: hsl("205 70% 60%"), borderColor: hsl("205 70% 60%", 0.4) }}>paste pick</span>}
        {(t.video_url || t.source_url) && <a href={t.video_url || t.source_url || "#"} target="_blank" rel="noreferrer" className="ml-auto text-muted-foreground hover:text-primary">source ↗</a>}
      </div>

      {t.headline_quote && <div className="text-base leading-snug">“{t.headline_quote}”</div>}

      <div className="flex items-center gap-2 text-xs">
        <Avatar handle={t.speaker} platform={t.platform} size={15} />
        <span className="font-medium">@{t.speaker}</span>
        {t.speaker_verified && <VerifiedBadge size={11} />}
      </div>

      {t.trade_summary && <div className="text-sm text-foreground/90">{t.trade_summary}</div>}

      {/* price box */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border border-border bg-background/40 px-3 py-2 text-sm">
        <Ticker t={t} /><Dir d={t.direction} />
        {t.entry_price != null && <span className="text-muted-foreground">@ {usd(t.entry_price)}</span>}
        {t.market_cap_fmt && <span className="text-muted-foreground text-xs">mcap {t.market_cap_fmt}</span>}
        <span className="ml-auto" />
        {t.since_call_pct != null
          ? <span className="font-medium" style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)} since call</span>
          : <a href={t.source_url ?? "https://paste.trade"} target="_blank" rel="noreferrer" className="text-xs text-muted-foreground hover:text-primary">live PnL on paste.trade ↗</a>}
        {t.peak_pct != null && <span className="text-xs text-muted-foreground">peak {pct(t.peak_pct)}</span>}
      </div>

      {(t.ticker_context || t.facts?.length || t.chain_steps?.length || t.catalyst || t.horizon || t.target) && (
        <button onClick={() => setOpen(!open)} className="text-xs text-muted-foreground hover:text-primary text-left">› {open ? "hide" : "show"} reasoning</button>
      )}
      {open && (
        <div className="space-y-2 text-sm border-t border-border pt-2">
          {t.ticker_context && <div className="text-muted-foreground">{t.ticker_context}</div>}
          {t.chain_steps?.length > 0 && <ul className="list-disc pl-5 space-y-0.5">{t.chain_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>}
          {t.facts?.length > 0 && (
            <div className="space-y-1">
              <Label>facts</Label>
              {t.facts.slice(0, 5).map((f, i) => <div key={i} className="text-muted-foreground">• {f.fact}{f.quote ? <span className="italic"> — “{f.quote}”</span> : null}</div>)}
            </div>
          )}
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
            {t.catalyst?.event && <span>catalyst: {t.catalyst.event}{t.catalyst.date ? ` (${t.catalyst.date})` : ""}</span>}
            {t.horizon && <span>horizon: {t.horizon}</span>}
            {t.target && <span>target: {t.target}</span>}
            {t.edge_note && <span>edge: {t.edge_note}</span>}
            {t.caveat && <span>caveat: {t.caveat}</span>}
          </div>
        </div>
      )}
    </Card>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[900px] px-4 py-4 space-y-3">{children}</main>;
}
