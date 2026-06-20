"use client";

import Link from "next/link";
import { AssetIcon, Avatar, PlatformIcon, VerifiedBadge } from "@/components/icons";
import { type Call, SC, ago, hsl, pct, stanceLabel } from "@/lib/scan";

type LogoMap = Record<string, string | null | undefined>;

/** Compact chronological timeline of KOL calls (mentions). Set showAsset=false on a single-asset page. */
export function Timeline({ feed, logoBy, showAsset = true }: { feed: Call[]; logoBy?: LogoMap; showAsset?: boolean }) {
  return (
    <div className="relative pl-5">
      <div className="absolute left-[6px] top-2 bottom-2 w-px bg-border" />
      <div className="space-y-0.5">
        {feed.map((c, i) => {
          const col = c.stance === "bullish" ? SC.bullish : c.stance === "bearish" ? SC.bearish : SC.neutral;
          return (
            <div key={i} className="relative flex items-center gap-2 text-sm py-1">
              <span className="absolute -left-[18px] w-[9px] h-[9px] rounded-full ring-2 ring-background" style={{ background: hsl(col) }} />
              <span className="text-muted-foreground text-xs w-9 shrink-0 text-right">{ago(c.ts)}</span>
              <Avatar handle={c.author} platform={c.platform} size={16} />
              {c.source_id
                ? <Link href={`/speaker?handle=${encodeURIComponent(c.author)}`} className="font-medium text-xs truncate max-w-[110px] hover:text-primary">{c.author}</Link>
                : <span className="font-medium text-xs truncate max-w-[110px]">{c.author}</span>}
              {c.verified && <VerifiedBadge size={12} />}
              <PlatformIcon platform={c.platform} size={12} />
              <span className="uppercase text-[10px] w-10 shrink-0" style={{ color: hsl(col) }}>{stanceLabel(c.stance)}</span>
              {showAsset && (
                <span className="flex items-center gap-1 shrink-0">
                  <AssetIcon logo={logoBy?.[c.symbol]} symbol={c.symbol} size={16} />
                  <Link href={`/asset?symbol=${encodeURIComponent(c.symbol)}`} className="font-semibold hover:text-primary">{c.symbol}</Link>
                </span>
              )}
              {c.since_call_pct != null && (
                <span className="text-xs shrink-0" style={{ color: hsl(c.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}>{pct(c.since_call_pct)}</span>
              )}
              <span className="text-muted-foreground truncate flex-1 min-w-0 hidden md:block">{c.summary}</span>
              {c.source_id && (
                <Link href={`/stream?id=${encodeURIComponent(c.source_id)}${c.video_seconds ? `&t=${c.video_seconds}` : ""}`}
                  className="text-muted-foreground hover:text-primary shrink-0 text-xs" title="open the source stream">↗</Link>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
