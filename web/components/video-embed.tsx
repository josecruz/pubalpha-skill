"use client";

import { useEffect, useState } from "react";
import { embedSrc } from "@/lib/paste";

/** Embedded Twitch/YouTube player (Twitch needs the page host as `parent`). Falls back to a link. */
export function VideoEmbed({ url, platform, seconds }: { url?: string | null; platform?: string | null; seconds?: number | null }) {
  const [host, setHost] = useState("localhost");
  useEffect(() => { setHost(window.location.hostname); }, []);
  const src = embedSrc(url, platform, seconds, host);
  if (!src) {
    return url ? <a href={url} target="_blank" rel="noreferrer" className="text-sm text-primary">watch on {platform ?? "source"} ↗</a> : null;
  }
  return (
    <div className="w-full border border-border bg-black" style={{ aspectRatio: "16 / 9" }}>
      <iframe src={src} className="w-full h-full" allow="autoplay; fullscreen; picture-in-picture" allowFullScreen title="stream" />
    </div>
  );
}
