"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { type Paste, type PasteEpisode, type PasteShow, type PasteTweet, dateFmt, dirColor, dirLabel } from "@/lib/paste";
import { SC, hsl, pct } from "@/lib/scan";

const MEDIUM_LABEL: Record<string, string> = {
  podcast: "Podcasts", newsletter: "Newsletters", youtube: "Video", twitch: "Streams", tweet: "Tweets",
};

function topSpeaker(ep: PasteEpisode): string {
  const c: Record<string, number> = {};
  for (const t of ep.trades) c[t.speaker] = (c[t.speaker] ?? 0) + 1;
  return Object.entries(c).sort((a, b) => b[1] - a[1])[0]?.[0] ?? ep.show;
}

export default function StreamsPage() {
  const [paste, setPaste] = useState<Paste | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<"shows" | "tweets">("shows");
  const [show, setShow] = useState<string>("all");
  const [speaker, setSpeaker] = useState<string>("all");
  const [q, setQ] = useState<string>("");
  const [sort, setSort] = useState<"newest" | "trades">("newest");
  const [limit, setLimit] = useState(90);

  useEffect(() => {
    fetch("/paste.json").then((r) => { if (!r.ok) throw new Error(`paste.json ${r.status}`); return r.json(); })
      .then(setPaste).catch((e) => setErr(String(e)));
  }, []);

  // reset paging when filters change (render-time reset, no effect)
  const filterSig = `${tab}|${show}|${speaker}|${q}|${sort}`;
  const [prevSig, setPrevSig] = useState(filterSig);
  if (filterSig !== prevSig) { setPrevSig(filterSig); setLimit(90); }

  const ticker = q.trim().toUpperCase();

  const eps = useMemo(() => {
    let list = paste?.episodes ?? [];
    if (show !== "all") list = list.filter((e) => e.show === show);
    if (speaker !== "all") list = list.filter((e) => e.trades.some((t) => t.speaker === speaker));
    if (ticker) list = list.filter((e) => e.trades.some((t) => t.ticker.includes(ticker)));
    list = [...list].sort((a, b) => sort === "trades"
      ? b.trades.length - a.trades.length
      : (b.published_at ?? "").localeCompare(a.published_at ?? ""));
    return list;
  }, [paste, show, speaker, ticker, sort]);

  const tweets = useMemo(() => {
    let list = paste?.tweets ?? [];
    if (speaker !== "all") list = list.filter((t) => t.speaker === speaker);
    if (ticker) list = list.filter((t) => t.ticker.includes(ticker));
    return list; // already newest-first from the builder
  }, [paste, speaker, ticker]);

  if (err) return <Wrap><div className="text-destructive p-6">Failed to load /paste.json — {err}. Run the scanner.</div></Wrap>;
  if (!paste) return <Wrap><div className="text-muted-foreground p-6">Loading…</div></Wrap>;

  const speakers = Object.values(paste.speakers).sort((a, b) => b.n_calls - a.n_calls);
  const totalTrades = paste.shows.reduce((n, s) => n + s.n_trades, 0);
  const episodicShows = paste.shows.filter((s) => !s.is_feed);
  const nTweets = paste.tweets?.length ?? 0;
  // group the show <select> options by medium
  const byMedium = new Map<string, PasteShow[]>();
  for (const s of [...episodicShows].sort((a, b) => b.n_trades - a.n_trades)) {
    const k = s.medium ?? s.platform ?? "other";
    const arr = byMedium.get(k) ?? [];
    if (!byMedium.has(k)) byMedium.set(k, arr);
    arr.push(s);
  }
  const rows = tab === "shows" ? eps.length : tweets.length;

  return (
    <Wrap>
      <div className="flex items-baseline gap-3 flex-wrap">
        <Link href="/" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← dashboard</Link>
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Streams</h1>
        <span className="text-muted-foreground text-sm">
          {paste.shows.length} shows · {paste.episodes.length} episodes · {nTweets} tweets · {totalTrades} calls · {speakers.length} speakers
        </span>
        <a href="https://paste.trade" target="_blank" rel="noreferrer" className="ml-auto text-xs text-muted-foreground hover:text-primary">source: paste.trade ↗</a>
      </div>

      {/* tabs */}
      <div className="flex border-b border-border">
        {(["shows", "tweets"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-xs uppercase tracking-wider px-3 py-1.5 -mb-px border-b-2 ${tab === t ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t === "shows" ? `Shows (${episodicShows.length})` : `Tweets (${nTweets})`}
          </button>
        ))}
      </div>

      {/* filters */}
      <div className="flex flex-wrap items-center gap-3">
        {tab === "shows" && (
          <select value={show} onChange={(e) => setShow(e.target.value)}
            className="bg-card border border-border text-sm px-2 py-1 text-foreground max-w-[220px]">
            <option value="all">all shows</option>
            {[...byMedium.entries()].map(([m, list]) => (
              <optgroup key={m} label={MEDIUM_LABEL[m] ?? m}>
                {list.map((s) => <option key={s.slug} value={s.slug}>{s.name ?? s.slug} ({s.n_trades})</option>)}
              </optgroup>
            ))}
          </select>
        )}
        <select value={speaker} onChange={(e) => setSpeaker(e.target.value)}
          className="bg-card border border-border text-sm px-2 py-1 text-foreground max-w-[220px]">
          <option value="all">all speakers</option>
          {speakers.slice(0, 400).map((s) => <option key={s.handle} value={s.handle}>{s.handle} ({s.n_calls})</option>)}
        </select>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="ticker…"
          className="bg-card border border-border text-sm px-2 py-1 text-foreground w-28 placeholder:text-muted-foreground" />
        {tab === "shows" && (
          <div className="flex border border-border">
            {(["newest", "trades"] as const).map((s) => (
              <button key={s} onClick={() => setSort(s)}
                className={`text-[11px] uppercase tracking-wider px-2.5 py-1 ${sort === s ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{s === "trades" ? "most calls" : "newest"}</button>
            ))}
          </div>
        )}
        <span className="text-xs text-muted-foreground ml-auto">{rows} {tab === "shows" ? "episodes" : "tweets"}</span>
      </div>

      {tab === "shows" ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {eps.slice(0, limit).map((e) => <EpisodeCard key={e.id} e={e} />)}
          {eps.length === 0 && <div className="text-muted-foreground text-sm">no episodes match.</div>}
        </div>
      ) : (
        <div className="border border-border bg-card divide-y divide-border">
          {tweets.slice(0, limit).map((t) => <TweetRow key={t.id} t={t} />)}
          {tweets.length === 0 && <div className="text-muted-foreground text-sm p-3">no tweets match.</div>}
        </div>
      )}

      {rows > limit && (
        <button onClick={() => setLimit((n) => n + 120)}
          className="mx-auto block text-xs uppercase tracking-wider border border-border px-4 py-1.5 text-muted-foreground hover:text-foreground hover:border-primary">
          show more ({rows - limit} more)
        </button>
      )}
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
          <span className="text-muted-foreground text-[10px] uppercase tracking-wider border border-border px-1">{e.show}</span>
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

function TweetRow({ t }: { t: PasteTweet }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-sm">
      <span className="text-muted-foreground text-xs w-16 shrink-0">{dateFmt(t.published_at)}</span>
      <Avatar handle={t.speaker} platform={t.platform} size={16} />
      <Link href={`/speaker?handle=${encodeURIComponent(t.speaker)}`} className="text-xs w-28 truncate shrink-0 hover:text-primary">@{t.speaker}</Link>
      {t.speaker_verified && <VerifiedBadge size={11} />}
      <AssetIcon logo={t.logo_url} symbol={t.ticker} size={16} />
      <Link href={`/asset?symbol=${encodeURIComponent(t.ticker)}`} className="font-semibold w-14 truncate hover:text-primary">{t.ticker}</Link>
      <span className="uppercase text-xs w-10 shrink-0" style={{ color: hsl(dirColor(t.direction)) }}>{dirLabel(t.direction)}</span>
      <span className="text-muted-foreground truncate flex-1 min-w-0">{t.headline_quote ?? t.thesis}</span>
      {t.since_call_pct != null && <span className="text-xs shrink-0 w-14 text-right" style={{ color: hsl(t.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(t.since_call_pct)}</span>}
      {t.source_url && <a href={t.source_url} target="_blank" rel="noreferrer" className="text-primary text-xs shrink-0 hover:underline" title="open the post">post ↗</a>}
    </div>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">{children}</main>;
}
