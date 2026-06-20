"""CoinMarketCap REST source — the deterministic data spine.

Implements MarketSource (quotes, ohlcv, onchain, regime_inputs), AttentionSource
(narrative), and a CallSource (fetch -> content news as call candidates). Uses the
Pro REST API (X-CMC_PRO_API_KEY). Paths/fields follow the official cmc-api-* skill
references; parsing is defensive (tolerant of field-name drift / missing fields) so
a single renamed key degrades one signal instead of breaking the funnel.

Backtest candles come from /v2/cryptocurrency/ohlcv/historical (BNB/CAKE/TWT are listed
assets — cleaner than DEX-pair OHLCV). On-chain confirmation uses /v1/dex/token/pools.
Holder data isn't exposed by the DEX API, so confirm.py simply doesn't gate on it.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from ..models import CallCandidate
from ..util import get_key

BASE = "https://pro-api.coinmarketcap.com"

# Known BSC contract addresses for on-chain confirmation (extend as needed).
BSC_CONTRACTS = {
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "TWT": "0x4B0F1812e5Df2A09796481Ff14017e6005508003",
    "BNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",   # WBNB
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
}


class CMCError(RuntimeError):
    pass


class CMCSource:
    name = "cmc"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.key = api_key or get_key("CMC_PRO_API_KEY", required=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-CMC_PRO_API_KEY": self.key, "Accept": "application/json"})
        self._id_symbol: Optional[Dict[int, str]] = None

    # --- low-level ------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        r = self.session.get(f"{BASE}{path}", params=params or {}, timeout=self.timeout)
        try:
            body = r.json()
        except ValueError:
            r.raise_for_status()
            raise CMCError(f"non-JSON response from {path}")
        status = (body or {}).get("status", {})
        if status.get("error_code"):
            raise CMCError(f"{path}: {status.get('error_message')}")
        if r.status_code >= 400:
            raise CMCError(f"{path}: HTTP {r.status_code}")
        return body.get("data", body)

    def _id_symbol_map(self) -> Dict[int, str]:
        if self._id_symbol is None:
            try:
                data = self._get("/v1/cryptocurrency/map", {"limit": 5000})
                self._id_symbol = {int(d["id"]): d.get("symbol", "") for d in data}
            except Exception:
                self._id_symbol = {}
        return self._id_symbol

    # --- MarketSource ---------------------------------------------------

    def quotes(self, symbols: List[str]) -> dict:
        data = self._get("/v2/cryptocurrency/quotes/latest", {"symbol": ",".join(symbols), "convert": "USD"})
        out = {}
        for _id, entry in (data or {}).items():
            entries = entry if isinstance(entry, list) else [entry]
            for e in entries:
                usd = (e.get("quote", {}) or {}).get("USD", {}) or {}
                out[e.get("symbol", _id)] = {
                    "price": usd.get("price"),
                    "percent_change_24h": usd.get("percent_change_24h"),
                }
        return out

    def ohlcv(self, symbol: str, interval: str, start: datetime, end: datetime) -> List[dict]:
        params = {
            "symbol": symbol.upper(), "convert": "USD", "interval": interval,
            "time_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": 10000,
        }
        data = self._get("/v2/cryptocurrency/ohlcv/historical", params)
        quotes = data.get("quotes") if isinstance(data, dict) else None
        if quotes is None and isinstance(data, dict):                       # data keyed by id
            for v in data.values():
                if isinstance(v, dict) and "quotes" in v:
                    quotes = v["quotes"]
                    break
        out = []
        for q in quotes or []:
            usd = (q.get("quote", {}) or {}).get("USD", {}) or {}
            out.append({
                "ts": q.get("time_open") or q.get("timestamp"),
                "open": usd.get("open"), "high": usd.get("high"),
                "low": usd.get("low"), "close": usd.get("close"), "volume": usd.get("volume"),
            })
        return [c for c in out if c["close"] is not None]

    def onchain(self, symbol: str) -> dict:
        contract = BSC_CONTRACTS.get(symbol.upper())
        metrics = {"price_runup_pct": self._runup_24h(symbol)}
        if not contract:
            metrics["notes"] = f"no known BSC contract for {symbol}; on-chain confirmation limited"
            return metrics
        try:
            data = self._get("/v1/dex/token/pools",
                             {"network_slug": "bsc", "contract_address": contract,
                              "sort": "liquidity", "sort_dir": "desc", "limit": 50})
        except Exception:
            data = self._get("/v4/dex/spot-pairs/latest",
                             {"network_slug": "bsc", "base_address": contract, "limit": 50})
        pools = (data.get("pools") if isinstance(data, dict) else None) or \
                (data.get("pairs") if isinstance(data, dict) else None) or \
                (data if isinstance(data, list) else [])
        liq = sum(_num(p.get("liquidity") or p.get("liquidity_usd")) for p in pools)
        buys = sum(_num(p.get("buys_24h") or p.get("num_transactions_buy_24h")) for p in pools)
        sells = sum(_num(p.get("sells_24h") or p.get("num_transactions_sell_24h")) for p in pools)
        metrics.update({
            "liquidity_usd": liq,
            "buy_volume_24h": buys,      # transaction counts (USD buy/sell split not exposed) — proxy
            "sell_volume_24h": sells,
            "pools": len(pools),
        })
        return metrics

    def _runup_24h(self, symbol: str) -> float:
        try:
            q = self.quotes([symbol]).get(symbol.upper(), {})
            return round(float(q.get("percent_change_24h") or 0.0), 2)
        except Exception:
            return 0.0

    def regime_inputs(self) -> dict:
        fg, fg_label = None, None
        try:
            d = self._get("/v3/fear-and-greed/latest")
            fg = int(d.get("value")) if d.get("value") is not None else None
            fg_label = d.get("value_classification")
        except Exception:
            pass
        dom, alt = None, None
        try:
            g = self._get("/v1/global-metrics/quotes/latest", {"convert": "USD"})
            dom = g.get("btc_dominance")
            if dom is not None:
                alt = max(0, min(100, round(100 - float(dom))))   # altseason proxy (no dedicated index)
        except Exception:
            pass
        return {"fear_greed": fg if fg is not None else 50,
                "fear_greed_label": fg_label,
                "btc_dominance": round(float(dom), 2) if dom is not None else 50.0,
                "altseason": alt if alt is not None else 50}

    # --- AttentionSource ------------------------------------------------

    def narrative(self, symbol: Optional[str] = None) -> dict:
        sector, heating, top = None, False, []
        try:
            cats = self._get("/v1/cryptocurrency/categories", {"limit": 5000})
            ranked = sorted(
                [c for c in cats if _num(c.get("num_tokens")) >= 5],
                key=lambda c: _num(c.get("avg_price_change")), reverse=True,
            )
            top = [{"name": c.get("name"), "avg_price_change": round(_num(c.get("avg_price_change")), 2)}
                   for c in ranked[:5]]
            if top:
                sector = top[0]["name"]
                heating = top[0]["avg_price_change"] > 0
        except Exception:
            pass
        trending = []
        try:
            t = self._get("/v1/community/trending/topic", {"limit": 5})
            trending = [x.get("name") for x in (t or []) if x.get("name")]
        except Exception:
            pass
        return {"heating": heating, "sector": sector, "top_categories": top,
                "trending_topics": trending, "source": "cmc_categories+community_trending",
                "available": True}

    # --- CallSource (CMC content news) ----------------------------------

    def fetch(self, since: Optional[datetime] = None, limit: int = 100) -> List[CallCandidate]:
        try:
            items = self._get("/v1/content/latest", {"limit": limit, "content_type": "news"})
        except Exception as e:
            print(f"  [cmc content] {type(e).__name__}: {e}")
            return []
        id_sym = self._id_symbol_map()
        out: List[CallCandidate] = []
        for it in items or []:
            ts = _parse_ts(it.get("released_at") or it.get("published_at") or it.get("created_at"))
            if ts is None:
                continue
            if since is not None and ts < _aware(since):
                continue
            coins = it.get("assets") or it.get("related_coins") or it.get("currencies") or []
            symbol = None
            for c in coins:
                cid = c.get("id") if isinstance(c, dict) else c
                symbol = id_sym.get(int(cid)) if str(cid).isdigit() else None
                if symbol:
                    break
            text = " ".join(filter(None, [it.get("title"), it.get("subtitle")]))
            if not text:
                continue
            out.append(CallCandidate(
                symbol=symbol, raw_text=text,
                author=it.get("source") or "cmc_news", source="cmc_news",
                ts=ts, url=it.get("source_url") or it.get("url"),
                engagement={}, stance=None, conviction=None,
            ))
        return out


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _parse_ts(s) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
