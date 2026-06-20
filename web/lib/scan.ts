// Types + helpers for results/scan.json (produced by scripts/scan.py).

export type Verdict = "organic" | "mixed" | "coordinated";

export interface Market {
  price: number | null; percent_change_24h: number | null; percent_change_7d: number | null;
  volume_24h: number | null; cex_volume_24h: number | null; dex_volume_24h: number | null;
  market_cap: number | null; kind: "crypto" | "tokenized_stock"; chain: string | null;
}
export interface Call {
  symbol: string; classification?: Verdict; score?: number; author: string; source: string;
  stance: string | null; conviction: number | null; summary: string; ts: string;
  engagement: Record<string, number>; url: string | null;
}
export interface Attention { on_cmc: boolean; sources: string[]; rank: number | null; }
export interface Identity {
  logo: string | null; tags: string[]; category: string | null;
  date_added: string | null; date_launched: string | null; description: string | null;
  urls: {
    website?: string | null; twitter?: string | null; reddit?: string | null;
    explorer?: string | null; source_code?: string | null; technical_doc?: string | null;
  };
  age_days: number | null; is_new: boolean;
}
export interface Performance {
  ath: number | null; ath_date: string | null; atl: number | null;
  pct_from_ath: number | null; roi_all_time: number | null;
  periods: Record<"7d" | "30d" | "90d" | "365d", number | null>;
}
export interface Venue {
  exchange: string | null; pair: string | null; category: string | null;
  volume_24h: number | null; price: number | null;
}
export interface Mover { symbol: string; name: string | null; rank: number | null; percent_change_24h?: number | null; }
export interface CmcOnly extends Mover { sources: string[]; }
export interface CmcAttention {
  most_visited: Mover[]; gainers: Mover[]; losers: Mover[]; community: Mover[];
  overlap: { corroborated: string[]; kol_only: string[]; cmc_only: CmcOnly[] };
}
export interface AltseasonIndex { value: number; classification: string; yearly_high?: number; yearly_low?: number; }
export interface FngTrend { points: { ts: number; value: number }[]; delta: number; direction: string; latest: number; }

export interface Signal {
  symbol: string; n_calls: number; classification: Verdict; score: number; reasons: string[];
  features?: Record<string, number>; distinct_authors: number; sources: string[];
  stance_mix: { bullish: number; bearish: number; neutral: number };
  latest_ts: string; top_calls: Call[]; market?: Market | null;
  attention?: Attention; identity?: Identity | null; performance?: Performance | null; venues?: Venue[];
}
export interface Idea {
  symbol: string; score: number; classification: Verdict; confidence: number; confirmed: boolean;
  narrative_heating: boolean; regime_state: string; entry_ready: boolean; reasons: string[];
  onchain: { confirmed: boolean; buy_sell_ratio?: number; liquidity_usd?: number; notes: string[] } | null;
  top_calls: Call[];
}
export interface Insights {
  total_market_cap?: number; total_volume_24h?: number; defi_volume_24h?: number;
  altcoin_volume_24h?: number; stablecoin_volume_24h?: number; btc_dominance?: number; eth_dominance?: number;
  surfaced_cex_volume_24h: number; surfaced_dex_volume_24h: number;
  verdict_split: { organic_pct: number; coordinated_pct: number; mixed_pct: number };
}
export interface Scan {
  generated_at: string;
  meta: { total_calls: number; unique_symbols: number; classified: number; trade_ideas: number };
  regime: {
    available: boolean; state: string; fear_greed?: number; btc_dominance?: number;
    altseason_index?: AltseasonIndex | null; fear_greed_trend?: FngTrend | null;
  };
  narrative: { heating: boolean; sector?: string; trending_topics?: string[]; available?: boolean };
  gate_stats: { clusters_seen: number; organic_pct: number; filtered_coordinated_pct: number; mixed_pct: number };
  market_insights: Insights;
  cmc_attention: CmcAttention;
  signals: Signal[]; trade_ideas: Idea[]; feed: Call[];
}

// ---- color helpers (SMUI / Nord palette) ----
export const VC: Record<string, string> = { organic: "92 28% 65%", mixed: "40 71% 73%", coordinated: "355 52% 64%" };
export const SC: Record<string, string> = { bullish: "92 28% 65%", bearish: "355 52% 64%", neutral: "213 14% 65%" };
export const hsl = (t: string, a?: number) => (a ? `hsl(${t} / ${a})` : `hsl(${t})`);
export const vc = (v?: string) => VC[v ?? "mixed"] ?? "213 14% 65%";
export const sc = (s?: string | null) => SC[s ?? "neutral"] ?? "213 14% 65%";

export function ago(iso?: string): string {
  if (!iso) return "";
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 3600) return `${Math.max(1, Math.round(d / 60))}m`;
  if (d < 86400) return `${Math.round(d / 3600)}h`;
  return `${Math.round(d / 86400)}d`;
}
export function usd(n?: number | null): string {
  if (n == null) return "—";
  const a = Math.abs(n);
  if (a >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}
export function pct(n?: number | null): string {
  return n == null ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}
export function age(iso?: string | null): string {
  if (!iso) return "";
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (d < 1) return "today";
  if (d < 60) return `${d}d`;
  if (d < 365) return `${Math.round(d / 30)}mo`;
  return `${(d / 365).toFixed(1)}y`;
}
