"use client";

import { useState } from "react";
import { Area, CartesianGrid, ComposedChart, Scatter, XAxis, YAxis } from "recharts";
import { ChartContainer, type ChartConfig } from "@/components/ui/chart";
import { type PricePoint, SC, hsl, pct, sc, stanceLabel, usd } from "@/lib/scan";
import { Avatar, VerifiedBadge } from "@/components/icons";

export type ChartCall = {
  ts: string;
  stance: string | null;
  entry_price?: number | null;
  author?: string;
  source?: string;
  platform?: string | null;
  since_call_pct?: number | null;
  summary?: string;
  verified?: boolean;
};

type Cluster = { time: number; value: number; items: ChartCall[] };

const DAY = 86400000; // ms
const RANGES: { key: string; ms: number }[] = [
  { key: "1D", ms: 1 * DAY },
  { key: "7D", ms: 7 * DAY },
  { key: "1M", ms: 30 * DAY },
  { key: "3M", ms: 90 * DAY },
  { key: "1Y", ms: 365 * DAY },
  { key: "ALL", ms: Infinity },
];
const chartConfig = { value: { label: "Price" } } satisfies ChartConfig;

const fmtDate = (ms: number) => new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const shortSource = (s?: string) => (s ? s.split(":").pop() || s : "");

// linear-interpolate the price line at an arbitrary time so a call's dot sits on the line
function priceAt(line: { time: number; value: number }[], t: number): number {
  if (t <= line[0].time) return line[0].value;
  if (t >= line[line.length - 1].time) return line[line.length - 1].value;
  for (let i = 1; i < line.length; i++) {
    if (t <= line[i].time) {
      const a = line[i - 1], b = line[i];
      return a.value + (b.value - a.value) * ((t - a.time) / (b.time - a.time || 1));
    }
  }
  return line[line.length - 1].value;
}

// Price chart on shadcn/Recharts: straight area line + real axes/grid. Each KOL call
// is a Scatter point sharing the chart axes, so the caller's pfp sits ON the line at
// the call's price (clustered with +N; hover shows the thesis).
export function PriceChart({ series, calls }: {
  series: PricePoint[];
  calls?: ChartCall[];
}) {
  const [hover, setHover] = useState<{ cx: number; cy: number; cluster: Cluster } | null>(null);

  const all = (series ?? []).map((p) => ({ time: new Date(p.ts).getTime(), value: p.close })).sort((a, b) => a.time - b.time);
  const fullSpan = all.length > 1 ? all[all.length - 1].time - all[0].time : DAY;
  const ranges = RANGES.map((r) => ({ ...r, ms: r.ms === Infinity ? Math.max(fullSpan, DAY) : r.ms }));
  const [winMs, setWinMs] = useState(() => (7 * DAY <= fullSpan ? 7 * DAY : Math.max(fullSpan, DAY)));

  if (all.length < 2) return null;

  const lastTime = all[all.length - 1].time;
  const leftEdge = lastTime - winMs;
  const line = all.filter((p) => p.time >= leftEdge);
  const data = line.length >= 2 ? line : all.slice(-2);

  const vals = data.map((p) => p.value);
  const lo = Math.min(...vals), hi = Math.max(...vals), padY = (hi - lo) * 0.12 || hi * 0.02;
  const yMin = lo - padY, yMax = hi + padY;
  const x0 = data[0].time, x1 = data[data.length - 1].time;
  const up = data[data.length - 1].value >= data[0].value;
  const lineColor = hsl(up ? SC.bullish : SC.bearish);
  const xticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(x0 + (x1 - x0) * f));

  // calls in the visible window, clustered by time proximity, snapped onto the line
  const winCalls = (calls ?? [])
    .map((c) => ({ c, t: new Date(c.ts).getTime() }))
    .filter((m) => m.t >= x0 && m.t <= x1)
    .sort((a, b) => a.t - b.t);
  const gap = (x1 - x0) * 0.045;
  const clusters: Cluster[] = [];
  for (const { c, t } of winCalls) {
    const last = clusters[clusters.length - 1];
    if (last && t - last.time < gap) last.items.push(c);
    else clusters.push({ time: t, value: 0, items: [c] });
  }
  for (const cl of clusters) {
    cl.items.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
    cl.time = new Date(cl.items[0].ts).getTime();
    cl.value = priceAt(data, cl.time);
  }

  const rangeKey = ranges.find((r) => r.ms === winMs)?.key ?? "7D";
  const rangeText = rangeKey === "ALL" ? "all time" : `last ${rangeKey}`;

  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">price — {rangeText} · {winCalls.length} calls marked</span>
        <div className="flex border border-border">
          {ranges.map((r) => (
            <button key={r.key} type="button" onClick={() => { setWinMs(r.ms); setHover(null); }}
              className={`text-[11px] uppercase tracking-wider px-2 py-0.5 ${winMs === r.ms ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              {r.key}
            </button>
          ))}
        </div>
      </div>

      <div className="relative mt-1" onMouseLeave={() => setHover(null)}>
        <ChartContainer config={chartConfig} className="h-44 w-full border border-border bg-card">
          <ComposedChart data={data} margin={{ top: 10, right: 8, bottom: 4, left: 8 }}>
            <defs>
              <linearGradient id="ll-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={0.25} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={hsl("217 17% 28%", 0.4)} />
            <XAxis dataKey="time" type="number" scale="time" domain={[x0, x1]} ticks={xticks}
              tickFormatter={fmtDate} tickLine={false} axisLine={false}
              tick={{ fontSize: 10, fill: "hsl(213 14% 65%)" }} minTickGap={20} />
            <YAxis dataKey="value" orientation="right" domain={[yMin, yMax]} width={52}
              tickFormatter={(v) => usd(v)} tickLine={false} axisLine={false} tickCount={4}
              tick={{ fontSize: 10, fill: "hsl(213 14% 65%)" }} />
            <Area dataKey="value" type="linear" stroke={lineColor} strokeWidth={1.8}
              fill="url(#ll-fill)" dot={false} isAnimationActive={false} />
            <Scatter data={clusters} dataKey="value" isAnimationActive={false}
              shape={(props: { cx?: number; cy?: number; payload?: Cluster }) => {
                const { cx, cy, payload } = props;
                if (cx == null || cy == null || !payload) return <g />;
                const rep = payload.items[0], n = payload.items.length;
                return (
                  <foreignObject x={cx - 13} y={cy - 13} width={26} height={26} style={{ overflow: "visible" }}>
                    <div className="relative h-[26px] w-[26px] flex items-center justify-center"
                      onMouseEnter={() => setHover({ cx, cy, cluster: payload })}>
                      <span className="block rounded-full" style={{ boxShadow: `0 0 0 2px ${hsl(sc(rep.stance))}` }}>
                        <Avatar handle={rep.author ?? "?"} platform={rep.platform} size={20} />
                      </span>
                      {n > 1 && (
                        <span className="absolute -bottom-1 -right-1 min-w-[14px] rounded-full border border-border bg-background px-0.5 text-center text-[8px] leading-[13px] text-foreground">+{n - 1}</span>
                      )}
                    </div>
                  </foreignObject>
                );
              }} />
          </ComposedChart>
        </ChartContainer>

        {hover && (() => {
          const below = hover.cy < 90;
          return (
            <div className="pointer-events-none absolute z-10 w-72 border border-border bg-background px-2 py-1.5 text-[11px] shadow-md"
              style={{ left: hover.cx, top: hover.cy, transform: `translateX(-50%) translateY(${below ? "16px" : "calc(-100% - 16px)"})` }}>
              {hover.cluster.items.slice(0, 4).map((c, i) => (
                <div key={i} className={i ? "mt-1.5 border-t border-border pt-1.5" : ""}>
                  <div className="flex items-center gap-1.5">
                    <Avatar handle={c.author ?? "?"} platform={c.platform} size={16} />
                    {c.author && <span className="font-medium">@{c.author}</span>}
                    {c.verified && <VerifiedBadge size={11} />}
                    <span className="ml-auto uppercase" style={{ color: hsl(sc(c.stance)) }}>{stanceLabel(c.stance)}</span>
                  </div>
                  <div className="text-muted-foreground mt-0.5">
                    {fmtDate(new Date(c.ts).getTime())}
                    {(c.platform || c.source) && ` · ${[c.platform, shortSource(c.source)].filter(Boolean).join("/")}`}
                    {c.since_call_pct != null && <span style={{ color: hsl(c.since_call_pct >= 0 ? SC.bullish : SC.bearish) }}> · {pct(c.since_call_pct)}</span>}
                  </div>
                  {c.summary && <div className="mt-1 text-foreground">{c.summary}</div>}
                </div>
              ))}
              {hover.cluster.items.length > 4 && <div className="mt-1 text-[10px] text-muted-foreground">+{hover.cluster.items.length - 4} more calls here</div>}
            </div>
          );
        })()}
      </div>

      <div className="flex gap-3 text-[10px] uppercase tracking-wider text-muted-foreground mt-1">
        <span style={{ color: hsl(SC.bullish) }}>● long call</span>
        <span style={{ color: hsl(SC.bearish) }}>● short call</span>
        <span style={{ color: hsl(SC.neutral) }}>● watch</span>
      </div>
    </div>
  );
}
