// Types + helpers for results/paste.json (produced by scripts/paste_browse.py).

export interface PasteTrade {
  id: string; ticker: string; direction: string | null; bucket: string | null; staked: boolean;
  speaker: string; speaker_name: string | null; speaker_verified: boolean;
  platform: string | null; instrument: string | null;
  video_seconds: number | null; video_url: string | null; author_date: string | null;
  entry_price: number | null; posted_price: number | null; peak_pct: number | null; market_cap_fmt: string | null;
  logo_url: string | null;
  headline_quote: string | null; thesis: string | null; trade_summary: string | null; ticker_context: string | null;
  edge_note: string | null; caveat: string | null; horizon: string | null; target: string | null;
  catalyst: { event?: string; date?: string } | null;
  facts: { fact?: string; quote?: string }[]; chain_steps: string[];
  source_url: string | null;
  since_call_pct?: number | null; cmc_symbol?: string | null; cmc_price?: number | null;
}
export interface PasteEpisode {
  id: string; show: string; title: string | null; url: string | null; platform: string | null;
  published_at: string | null; thumbnail: string | null; n_positions: number; n_ideas: number; trades: PasteTrade[];
}
export interface PasteSpeaker {
  handle: string; name: string | null; verified: boolean; platform: string | null;
  n_calls: number; long: number; short: number; shows: string[]; n_episodes: number; episodes: string[];
}
export interface PasteShow {
  slug: string; platform: string | null; streamer: string; streamer_name: string | null;
  n_episodes: number; n_trades: number; speakers: string[];
}
export interface Paste {
  generated_at: string; shows: PasteShow[]; speakers: Record<string, PasteSpeaker>; episodes: PasteEpisode[];
}

export function mmss(sec?: number | null): string {
  if (sec == null || sec < 0) return "";
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

export function dateFmt(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** Build an embeddable player URL for a Twitch VOD or YouTube video (host needed for Twitch's parent). */
export function embedSrc(url?: string | null, platform?: string | null, seconds?: number | null, host = "localhost"): string | null {
  if (!url) return null;
  const t = Math.max(0, seconds ?? 0);
  if (platform === "youtube" || /youtu/.test(url)) {
    const m = url.match(/[?&]v=([^&]+)/) || url.match(/youtu\.be\/([^?&]+)/) || url.match(/embed\/([^?&]+)/);
    return m ? `https://www.youtube.com/embed/${m[1]}?start=${t}` : null;
  }
  if (platform === "twitch" || /twitch/.test(url)) {
    const m = url.match(/videos\/(\d+)/);
    const h = Math.floor(t / 3600), mm = Math.floor((t % 3600) / 60), s = t % 60;
    return m ? `https://player.twitch.tv/?video=${m[1]}&parent=${host}&autoplay=false&time=${h}h${mm}m${s}s` : null;
  }
  return null;
}

export const dirColor = (d?: string | null) => (d === "long" ? "92 28% 65%" : d === "short" ? "355 52% 64%" : "213 14% 65%");
export const dirLabel = (d?: string | null) => (d === "long" ? "LONG" : d === "short" ? "SHORT" : "—");
