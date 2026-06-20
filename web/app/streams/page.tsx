"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { type Paste, type PasteEpisode, dateFmt, dirColor, dirLabel } from "@/lib/paste";
import { SC, hsl, pct, usd } from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);

function topSpeaker(ep: PasteEpisode): string {
  const c: Record<string, number> = {};
  for (const t of ep.trades) c[t.speaker] = (c[t.speaker] ?? 0) + 1;
  return Object.entries(c).sort((a, b) => b[1] - a[1])[0]?.[0] ?? ep.show;
}

export default function StreamsPage() {
  const [paste, setPaste] = useState<Paste | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [show, setShow] = useState<string>("all");
  const [speaker, setSpeaker] = useState<string>("all");
  const [sort, setSort] = useState<"newest" | "trades">("newest");

  useEffect(() => {
    fetch("/paste.json").then((r) => { if (!r.ok) throw new Error(`paste.json ${r.status}`); return r.json(); })
      .then(setPaste).catch((e) => setErr(String(e)));
  }, []);

  const eps = useMemo(() => {
    let list = paste?.episodes ?? [];
    if (show !== "all") list = list.filter((e) => e.show === show);
    if (speaker !== "all") list = list.filter((e) => e.trades.some((t) => t.speaker === speaker));
    list = [...list].sort((a, b) => sort === "trades"
      ? b.trades.length - a.trades.length
      : (b.published_at ?? "").localeCompare(a.published_at ?? ""));
    return list;
  }, [paste, show, speaker, sort]);

  if (err) return <Wrap><div className="text-destructive p-6">Failed to load /paste.json — {err}. Run the scanner.</div></Wrap>;
  if (!paste) return <Wrap><div className="text-muted-foreground p-6">Loading…</div></Wrap>;

  const speakers = Object.values(paste.speakers).sort((a, b) => b.n_calls - a.n_calls);
  const totalTrades = paste.shows.reduce((n, s) => n + s.n_trades, 0);

  return (
    <Wrap>
      <div className="flex items-baseline gap-3 flex-wrap">
        <Link href="/" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← dashboard</Link>
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Streams</h1>
        <span className="text-muted-foreground text-sm">{paste.episodes.length} episodes · {totalTrades} calls · {speakers.length} speakers</span>
        <a href="https://paste.trade" target="_blank" rel="noreferrer" className="ml-auto text-xs text-muted-foreground hover:text-primary">source: paste.trade ↗</a>
      </div>

      {/* filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex border border-border">
          {["all", "threadguy", "all-in"].map((s) => (
            <button key={s} onClick={() => setShow(s)}
              className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${show === s ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{s}</button>
          ))}
        </div>
        <select value={speaker} onChange={(e) => setSpeaker(e.target.value)}
          className="bg-card border border-border text-sm px-2 py-1 text-foreground">
          <option value="all">all speakers</option>
          {speakers.map((s) => <option key={s.handle} value={s.handle}>{s.handle} ({s.n_calls})</option>)}
        </select>
        <div className="flex border border-border">
          {(["newest", "trades"] as const).map((s) => (
            <button key={s} onClick={() => setSort(s)}
              className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${sort === s ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{s === "trades" ? "most calls" : "newest"}</button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {eps.map((e) => <EpisodeCard key={e.id} e={e} />)}
        {eps.length === 0 && <div className="text-muted-foreground text-sm">no episodes match.</div>}
      </div>
    </Wrap>
  );
}

function EpisodeCard({ e }: { e: PasteEpisode }) {
  const host = topSpeaker(e);
  const ht = e.trades.find((t) => t.speaker === host);
  const preview = e.trades.slice(0, 4);
  return (
    <Link href={`/stream?id=${encodeURIComponent(e.id)}`}>
      <Card className="rounded-none p-3 gap-2 hover:border-primary transition-colors h-full">
        <div className="flex items-center gap-2">
          <Avatar handle={host} platform={e.platform} size={22} />
          <span className="font-semibold">@{host}</span>
          {ht?.speaker_verified && <VerifiedBadge size={12} />}
          <PlatformIcon platform={e.platform} size={13} />
          <span className="text-muted-foreground text-xs ml-auto">{dateFmt(e.published_at)}</span>
        </div>
        <div className="text-sm font-medium line-clamp-2">{e.title}</div>
        <div className="text-[11px] text-muted-foreground">{e.n_positions} positions · {e.n_ideas} ideas</div>
        <div className="divide-y divide-border border-t border-border">
          {preview.map((t) => (
            <div key={t.id} className="flex items-center gap-2 py-1 text-xs">
              <AssetIcon logo={t.logo_url} symbol={t.ticker} size={16} />
              <span className="font-semibold w-14 truncate">{t.ticker}</span>
              <span className="uppercase w-10" style={{ color: hsl(dirColor(t.direction)) }}>{dirLabel(t.direction)}</span>
              <span className="text-muted-foreground truncate flex-1 min-w-0">{t.headline_quote ?? t.thesis}</span>
              {t.since_call_pct != null && <span style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)}</span>}
            </div>
          ))}
        </div>
      </Card>
    </Link>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">{children}</main>;
}
