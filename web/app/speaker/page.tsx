"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { type Paste, type PasteEpisode, type PasteTrade, dateFmt, dirColor, dirLabel, mmss } from "@/lib/paste";
import { SC, hsl, pct } from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);

export default function SpeakerPage() {
  const [paste, setPaste] = useState<Paste | null>(null);
  const [handle, setHandle] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setHandle(new URLSearchParams(window.location.search).get("handle") || "");
    fetch("/paste.json").then((r) => { if (!r.ok) throw new Error(`paste.json ${r.status}`); return r.json(); })
      .then(setPaste).catch((e) => setErr(String(e)));
  }, []);

  const sp = paste?.speakers[handle];
  // every call by this speaker — episode trades + tweet-feed calls — newest first
  const calls = useMemo(() => {
    const out: { t: PasteTrade; ep: PasteEpisode | null }[] = [];
    for (const ep of paste?.episodes ?? [])
      for (const t of ep.trades) if (t.speaker === handle) out.push({ t, ep });
    for (const tw of paste?.tweets ?? [])
      if (tw.speaker === handle) out.push({ t: tw as unknown as PasteTrade, ep: null });
    return out.sort((a, b) =>
      ((b.ep?.published_at ?? (b.t as unknown as { published_at?: string }).published_at) ?? "")
        .localeCompare((a.ep?.published_at ?? (a.t as unknown as { published_at?: string }).published_at) ?? ""));
  }, [paste, handle]);

  const back = <Link href="/streams" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← streams</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed — {err}</div></Wrap>;
  if (!paste) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;
  if (!sp) return <Wrap>{back}<div className="text-muted-foreground p-6">No speaker “{handle}”.</div></Wrap>;

  return (
    <Wrap>
      <div className="flex items-center gap-3">{back}
        <Avatar handle={sp.handle} platform={sp.platform} size={28} />
        <h1 className="text-xl font-bold">@{sp.handle}</h1>
        {sp.verified && <VerifiedBadge size={14} />}
        <PlatformIcon platform={sp.platform} size={15} />
        {sp.name && <span className="text-muted-foreground text-sm">{sp.name}</span>}
        <a href="https://paste.trade" target="_blank" rel="noreferrer" className="ml-auto text-xs text-muted-foreground hover:text-primary">source: paste.trade ↗</a>
      </div>

      <Card className="rounded-none p-3 gap-2">
        <Label>activity & record</Label>
        <div className="flex flex-wrap gap-x-8 gap-y-2">
          <Stat k="Calls" v={String(sp.n_calls)} />
          <Stat k="Long" v={String(sp.long)} color={SC.bullish} />
          <Stat k="Short" v={String(sp.short)} color={SC.bearish} />
          {sp.win_rate != null && <Stat k="Win rate" v={`${Math.round(sp.win_rate * 100)}%`} />}
          {sp.total_pnl != null && <Stat k="Total PnL" v={pct(sp.total_pnl)} color={sp.total_pnl >= 0 ? SC.bullish : SC.bearish} />}
          {sp.role && <Stat k="Role" v={sp.role} />}
          <Stat k="Episodes" v={String(sp.n_episodes)} />
          <Stat k="Shows" v={sp.shows.join(", ")} />
        </div>
        {(sp.best || sp.worst) && (
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground border-t border-border pt-2">
            {sp.best?.ticker && <span>best: <span className="text-foreground">{sp.best.ticker}</span> {sp.best.pnl_pct != null && <span style={{ color: hsl(SC.bullish) }}>{pct(sp.best.pnl_pct)}</span>}</span>}
            {sp.worst?.ticker && <span>worst: <span className="text-foreground">{sp.worst.ticker}</span> {sp.worst.pnl_pct != null && <span style={{ color: hsl(SC.bearish) }}>{pct(sp.worst.pnl_pct)}</span>}</span>}
          </div>
        )}
      </Card>

      <Label>calls — {calls.length}</Label>
      <div className="border border-border bg-card divide-y divide-border">
        {calls.map(({ t, ep }, i) => {
          const date = ep?.published_at ?? (t as unknown as { published_at?: string | null }).published_at ?? null;
          return (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-sm">
              <span className="text-muted-foreground text-xs w-16 shrink-0">{dateFmt(date)}</span>
              <AssetIcon logo={t.logo_url} symbol={t.ticker} size={16} />
              <Link href={`/asset?symbol=${encodeURIComponent(t.ticker)}`} className="font-semibold w-14 truncate hover:text-primary">{t.ticker}</Link>
              <span className="uppercase text-xs w-10 shrink-0" style={{ color: hsl(dirColor(t.direction)) }}>{dirLabel(t.direction)}</span>
              <span className="text-muted-foreground truncate flex-1 min-w-0">{t.headline_quote ?? t.thesis}</span>
              {t.since_call_pct != null && <span className="text-xs shrink-0 w-14 text-right" style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)}</span>}
              {ep
                ? <Link href={`/stream?id=${encodeURIComponent(ep.id)}`} className="text-primary text-xs shrink-0 hover:underline" title="open stream at this call">▶ {mmss(t.video_seconds) || "stream"}</Link>
                : t.source_url
                  ? <a href={t.source_url} target="_blank" rel="noreferrer" className="text-primary text-xs shrink-0 hover:underline" title="open the post">post ↗</a>
                  : <span className="w-12 shrink-0" />}
            </div>
          );
        })}
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
