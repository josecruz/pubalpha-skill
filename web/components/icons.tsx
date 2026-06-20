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

/** KOL avatar — deterministic monogram (real X pfps aren't reliably available). */
export function Avatar({ handle, size = 18 }: { handle: string; size?: number }) {
  return <Monogram label={handle} size={size} round />;
}
