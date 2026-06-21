// Capture the web dashboard screenshots used in the READMEs.
//
// One-off setup (playwright is intentionally NOT a package.json dependency):
//   npm install --no-save --no-package-lock playwright
//   npx playwright install chromium
//
// Then, with the dev server running on existing data (no re-scan needed):
//   npm run dev            # in another shell — serves public/scan.json + paste.json
//   node scripts/shoot.mjs
//
// Override the target with BASE=http://localhost:3000 node scripts/shoot.mjs
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const BASE = process.env.BASE || "http://localhost:3000";
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), "../../docs/img");

// Routes are query-param based (no dynamic segments). Asset/stream picked for rich data.
// Feed/list pages scroll forever, so capture a bounded "hero" viewport (h). The asset thesis
// is the deep-dive page — capture it full so chart → venues → leverage → community → calls show.
const SHOTS = [
  { file: "web-dashboard.png", path: "/", h: 1600 },
  { file: "web-streams.png", path: "/streams", h: 1450 },
  { file: "web-stream.png", path: "/stream?id=b61f3588-a", h: 1750 },
  { file: "web-setups.png", path: "/setups", h: 1250 },
  { file: "web-intel.png", path: "/intel", full: true },
  { file: "web-asset.png", path: "/asset?symbol=BTC", full: true },
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 }, deviceScaleFactor: 1 });
for (const { file, path, h, full } of SHOTS) {
  const page = await ctx.newPage();
  if (h) await page.setViewportSize({ width: 1500, height: h });
  await page.goto(BASE + path, { waitUntil: "load", timeout: 60000 });
  // settle data fetches + external avatar/logo images; networkidle can stall on those, so cap it
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(2500); // let Recharts + images finish painting
  await page.screenshot({ path: resolve(OUT, file), fullPage: !!full });
  console.log("shot", file, "<-", path, full ? "(full)" : `(${h}px)`);
  await page.close();
}
await browser.close();
console.log("done ->", OUT);
