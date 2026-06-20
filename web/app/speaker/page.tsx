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
  // every call by this speaker, with its episode, newest first
  const calls = useMemo(() => {
    const out: { t: PasteTrade; ep: PasteEpisode }[] = [];
    for (const ep of paste?.episodes ?? [])
      for (const t of ep.trades) if (t.speaker === handle) out.push({ t, ep });
    return out.sort((a, b) => (b.ep.published_at ?? "").localeCompare(a.ep.published_at ?? ""));
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
        <Label>activity</Label>
        <div className="flex flex-wrap gap-x-8 gap-y-2">
          <Stat k="Calls" v={String(sp.n_calls)} />
          <Stat k="Long" v={String(sp.long)} color={SC.bullish} />
          <Stat k="Short" v={String(sp.short)} color={SC.bearish} />
          <Stat k="Episodes" v={String(sp.n_episodes)} />
          <Stat k="Shows" v={sp.shows.join(", ")} />
        </div>
      </Card>

      <Label>calls — {calls.length}</Label>
      <div className="border border-border bg-card divide-y divide-border">
        {calls.map(({ t, ep }, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-sm">
            <span className="text-muted-foreground text-xs w-16 shrink-0">{dateFmt(ep.published_at)}</span>
            <AssetIcon logo={t.logo_url} symbol={t.ticker} size={16} />
            <Link href={`/asset?symbol=${encodeURIComponent(t.ticker)}`} className="font-semibold w-14 truncate hover:text-primary">{t.ticker}</Link>
            <span className="uppercase text-xs w-10 shrink-0" style={{ color: hsl(dirColor(t.direction)) }}>{dirLabel(t.direction)}</span>
            <span className="text-muted-foreground truncate flex-1 min-w-0">{t.headline_quote ?? t.thesis}</span>
            {t.since_call_pct != null && <span className="text-xs shrink-0 w-14 text-right" style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)}</span>}
            <Link href={`/stream?id=${encodeURIComponent(ep.id)}`} className="text-primary text-xs shrink-0 hover:underline" title="open stream at this call">▶ {mmss(t.video_seconds) || "stream"}</Link>
          </div>
        ))}
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
