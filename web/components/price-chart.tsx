"use client";

import { type PricePoint, SC, hsl, sc } from "@/lib/scan";

// Lightweight dependency-free SVG price chart (line + area) with call markers.
// Markers are thin vertical lines colored by stance (green=long, red=short).
export function PriceChart({ series, calls }: {
  series: PricePoint[];
  calls?: { ts: string; stance: string | null }[];
}) {
  if (!series || series.length < 2) return null;
  const W = 1000, H = 220, pad = 8;
  const xs = series.map((p) => new Date(p.ts).getTime());
  const ys = series.map((p) => p.close);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (t: number) => pad + (W - 2 * pad) * (maxX === minX ? 0.5 : (t - minX) / (maxX - minX));
  const sy = (v: number) => H - pad - (H - 2 * pad) * (maxY === minY ? 0.5 : (v - minY) / (maxY - minY));
  const line = series.map((p, i) => `${i ? "L" : "M"}${sx(xs[i]).toFixed(1)},${sy(p.close).toFixed(1)}`).join(" ");
  const area = `${line} L${sx(maxX).toFixed(1)},${(H - pad).toFixed(1)} L${sx(minX).toFixed(1)},${(H - pad).toFixed(1)} Z`;
  const up = ys[ys.length - 1] >= ys[0];
  const stroke = hsl(up ? SC.bullish : SC.bearish);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-44 border border-border bg-card">
      <path d={area} fill={hsl(up ? SC.bullish : SC.bearish, 0.1)} />
      <path d={line} fill="none" stroke={stroke} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      {(calls ?? []).map((c, i) => {
        const t = new Date(c.ts).getTime();
        if (t < minX || t > maxX) return null;
        const x = sx(t);
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={pad} y2={H - pad} stroke={hsl(sc(c.stance), 0.45)} strokeWidth={1} vectorEffect="non-scaling-stroke" />
            <circle cx={x} cy={pad} r={3} fill={hsl(sc(c.stance))} />
          </g>
        );
      })}
    </svg>
  );
}
