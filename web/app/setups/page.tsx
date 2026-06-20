"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AssetIcon } from "@/components/icons";
import {
  type PerpSetup, type Scan, type SpotSetup,
  SC, funding, hsl, pct, usd, vc,
} from "@/lib/scan";

const Label = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[11px] uppercase tracking-[1.5px] text-muted-foreground">{children}</span>
);
const Asset = ({ s }: { s: string }) => (
  <Link href={`/asset?symbol=${encodeURIComponent(s)}`} className="font-semibold hover:underline hover:text-primary">{s}</Link>
);
const Tag = ({ v }: { v: string }) => (
  <span className="text-[10px] uppercase tracking-wider px-1.5 py-px border"
    style={{ color: hsl(vc(v)), borderColor: hsl(vc(v), 0.35) }}>{v}</span>
);
const TH = ({ children }: { children: React.ReactNode }) => (
  <TableHead className="text-[11px] uppercase tracking-wider">{children}</TableHead>
);

export default function SetupsPage() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/scan.json").then((r) => { if (!r.ok) throw new Error(`scan.json ${r.status}`); return r.json(); })
      .then(setScan).catch((e) => setErr(String(e)));
  }, []);

  const back = <Link href="/" className="text-muted-foreground hover:text-primary text-sm uppercase tracking-wider">← dashboard</Link>;
  if (err) return <Wrap>{back}<div className="text-destructive p-6">Failed to load — {err}</div></Wrap>;
  if (!scan) return <Wrap>{back}<div className="text-muted-foreground p-6">Loading…</div></Wrap>;

  const { spot, perp, disclaimer } = scan.setups;
  const logoBy: Record<string, string | null | undefined> = Object.fromEntries(scan.signals.map((s) => [s.symbol, s.identity?.logo]));
  return (
    <Wrap>
      <div className="flex items-baseline gap-3">
        {back}
        <h1 className="text-lg font-bold uppercase tracking-[2px]">Setups</h1>
        <span className="text-muted-foreground text-sm">breakout candidates to help spot a move</span>
        <Link href="/intel" className="ml-auto text-sm text-muted-foreground hover:text-primary uppercase tracking-wider">Market Intel →</Link>
      </div>
      <div className="border border-border bg-card px-3 py-2 text-[11px] text-muted-foreground">⚠ {disclaimer}</div>

      {/* spot breakout candidates */}
      <div>
        <Label>spot breakout candidates — social-confirmed first</Label>
        <Card className="p-0 overflow-hidden rounded-none mt-1">
          <Table>
            <TableHeader><TableRow>
              <TH>Asset</TH><TH>Setup</TH><TH>vs 20d-high</TH><TH>Vol×</TH><TH>7d mom</TH>
              <TH>KOL sentiment</TH><TH>Strength</TH>
            </TableRow></TableHeader>
            <TableBody>
              {spot.map((s: SpotSetup) => (
                <TableRow key={s.symbol}>
                  <TableCell className="flex items-center gap-2"><AssetIcon logo={logoBy[s.symbol]} symbol={s.symbol} size={16} /><Asset s={s.symbol} /><Tag v={s.classification} /></TableCell>
                  <TableCell>
                    {s.is_breakout
                      ? <span style={{ color: hsl(SC.bullish) }}>● BREAKOUT</span>
                      : <span className="text-muted-foreground">building</span>}
                    {s.social_confirmed && <span className="ml-1" style={{ color: hsl(SC.bullish) }} title="organic bullish KOLs">✓ social</span>}
                  </TableCell>
                  <TableCell style={{ color: (s.pct_above_20d_high ?? 0) >= 0 ? hsl(SC.bullish) : hsl(SC.bearish) }}>{pct(s.pct_above_20d_high)}</TableCell>
                  <TableCell>{s.vol_mult != null ? `${s.vol_mult.toFixed(2)}×` : "—"}</TableCell>
                  <TableCell style={{ color: (s.mom_7d ?? 0) >= 0 ? hsl(SC.bullish) : hsl(SC.bearish) }}>{pct(s.mom_7d)}</TableCell>
                  <TableCell style={{ color: hsl(s.sentiment_label === "bullish" ? SC.bullish : s.sentiment_label === "bearish" ? SC.bearish : SC.neutral) }}>
                    {s.sentiment_label} {s.sentiment_score >= 0 ? "+" : ""}{s.sentiment_score.toFixed(2)}</TableCell>
                  <TableCell><Bar v={s.strength} /></TableCell>
                </TableRow>
              ))}
              {spot.length === 0 && <TableRow><TableCell colSpan={7} className="text-muted-foreground">no spot candidates this scan.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </Card>
      </div>

      {/* perp breakout candidates */}
      <div>
        <Label>perp breakout candidates — funding / open interest</Label>
        <Card className="p-0 overflow-hidden rounded-none mt-1">
          <Table>
            <TableHeader><TableRow>
              <TH>Asset</TH><TH>Venue</TH><TH>Funding</TH><TH>Open interest</TH><TH>Perp vol 24h</TH>
              <TH>Setup</TH><TH>Bias</TH><TH>Score</TH>
            </TableRow></TableHeader>
            <TableBody>
              {perp.map((p: PerpSetup) => (
                <TableRow key={p.symbol}>
                  <TableCell className="flex items-center gap-2"><AssetIcon logo={logoBy[p.symbol]} symbol={p.symbol} size={16} /><Asset s={p.symbol} /></TableCell>
                  <TableCell className="text-muted-foreground">{p.venue ?? "—"}</TableCell>
                  <TableCell style={{ color: (p.funding_rate ?? 0) >= 0 ? hsl(SC.bullish) : hsl(SC.bearish) }}>{funding(p.funding_rate)}</TableCell>
                  <TableCell>{usd(p.open_interest)}</TableCell>
                  <TableCell>{usd(p.perp_volume_24h)}</TableCell>
                  <TableCell>{p.is_breakout ? <span style={{ color: hsl(SC.bullish) }}>● BREAKOUT</span> : <span className="text-muted-foreground">building</span>}</TableCell>
                  <TableCell className="text-xs">{p.bias}</TableCell>
                  <TableCell><Bar v={p.score} /></TableCell>
                </TableRow>
              ))}
              {perp.length === 0 && <TableRow><TableCell colSpan={8} className="text-muted-foreground">no perp candidates this scan.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </Card>
      </div>

      <div className="text-[11px] text-muted-foreground">
        Mirrors the CMC Skill Hub skills <span className="text-foreground">scan_spot_altcoin_breakout_with_social_confirmation</span>,{" "}
        <span className="text-foreground">screen_perp_breakout_candidates</span> and{" "}
        <span className="text-foreground">altcoin_kol_sentiment</span> — computed natively over CMC data + the call layer.
      </div>
    </Wrap>
  );
}

function Bar({ v }: { v: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 border border-border"><div className="h-full" style={{ width: `${Math.min(1, v) * 100}%`, background: hsl(SC.bullish) }} /></div>
      <span className="text-xs text-muted-foreground">{v.toFixed(2)}</span>
    </div>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1500px] px-4 py-4 space-y-3">{children}</main>;
}
