"use client";

import { useState } from "react";

// Deterministic hue from a string (stable per ticker/handle).
function hue(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h) % 360;
}

function Monogram({ label, size, round }: { label: string; size: number; round?: boolean }) {
  const ch = (label || "?").replace(/[^a-zA-Z0-9]/g, "").charAt(0).toUpperCase() || "?";
  const h = hue(label || "?");
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center align-middle ${round ? "rounded-full" : "rounded-sm"}`}
      style={{ width: size, height: size, fontSize: size * 0.46, lineHeight: 1, fontWeight: 600,
               background: `hsl(${h} 28% 26%)`, color: `hsl(${h} 55% 78%)` }}
      aria-hidden
    >{ch}</span>
  );
}

/** Asset coin logo (CMC) with a monogram fallback. */
export function AssetIcon({ logo, symbol, size = 18 }: { logo?: string | null; symbol: string; size?: number }) {
  const [bad, setBad] = useState(false);
  if (logo && !bad) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={logo} alt="" width={size} height={size} onError={() => setBad(true)}
      className="inline-block align-middle rounded-full shrink-0" style={{ width: size, height: size }} />;
  }
  return <Monogram label={symbol} size={size} />;
}

/** Exchange logo (CMC) by exchange id, monogram fallback. */
export function ExchangeIcon({ id, name, size = 16 }: { id?: number | null; name?: string | null; size?: number }) {
  const [bad, setBad] = useState(false);
  const url = id ? `https://s2.coinmarketcap.com/static/img/exchanges/64x64/${id}.png` : null;
  if (url && !bad) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt="" width={size} height={size} onError={() => setBad(true)}
      className="inline-block align-middle rounded-sm shrink-0" style={{ width: size, height: size }} />;
  }
  return <Monogram label={name || "?"} size={size} />;
}

/** KOL avatar — real pfp via unavatar (twitch for twitch shows, else x), monogram fallback. */
export function Avatar({ handle, platform, size = 18 }: { handle: string; platform?: string | null; size?: number }) {
  const [bad, setBad] = useState(false);
  const provider = platform === "twitch" ? "twitch" : "x";
  const url = `https://unavatar.io/${provider}/${encodeURIComponent(handle)}?fallback=false`;
  if (handle && !bad) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt="" width={size} height={size} onError={() => setBad(true)}
      className="inline-block align-middle rounded-full shrink-0 object-cover" style={{ width: size, height: size }} />;
  }
  return <Monogram label={handle} size={size} round />;
}

/** Small verified check (a KOL whose account is verified on paste.trade / CMC). */
export function VerifiedBadge({ size = 13 }: { size?: number }) {
  return (
    <span className="inline-flex shrink-0 items-center justify-center rounded-full align-middle"
      style={{ width: size, height: size, background: "hsl(205 70% 55%)", color: "white", fontSize: size * 0.7, lineHeight: 1 }}
      title="verified speaker">✓</span>
  );
}

const PLATFORM_COLOR: Record<string, string> = { twitch: "9146FF", youtube: "FF0000", x: "9aa4b2", twitter: "9aa4b2" };
/** Brand platform icon (where a call was made) via the simpleicons CDN. */
export function PlatformIcon({ platform, size = 13 }: { platform?: string | null; size?: number }) {
  const [bad, setBad] = useState(false);
  if (!platform || bad) return null;
  const slug = platform === "twitter" ? "x" : platform;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={`https://cdn.simpleicons.org/${slug}/${PLATFORM_COLOR[platform] ?? "9aa4b2"}`} alt={platform}
    title={platform} width={size} height={size} onError={() => setBad(true)}
    className="inline-block align-middle shrink-0 opacity-80" style={{ width: size, height: size }} />;
}
