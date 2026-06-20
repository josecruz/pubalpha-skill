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

# Reputable perp venues — used to drop wash-volume exchanges from the derivatives aggregate.
_MAJOR_PERP = {"binance", "bybit", "okx", "bitget", "gate.io", "gate", "deribit",
               "bitmex", "kraken", "hyperliquid", "kucoin", "htx", "mexc", "coinbase international"}

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
        code = status.get("error_code")
        if code is not None and str(code) not in ("0", ""):   # CMC returns 0 or "0" on success
            raise CMCError(f"{path}: {status.get('error_message') or 'error_code ' + str(code)}")
        if r.status_code >= 400:
            raise CMCError(f"{path}: HTTP {r.status_code}")
        return body.get("data", body) if isinstance(body, dict) else body

    def _id_symbol_map(self) -> Dict[int, str]:
        if self._id_symbol is None:
            try:
                data = self._get("/v1/cryptocurrency/map", {"limit": 5000})
                self._id_symbol = {int(d["id"]): d.get("symbol", "") for d in data}
            except Exception:
                self._id_symbol = {}
        return self._id_symbol

    # --- Entity resolution (universal: crypto + tokenized stocks across chains) ---

    _TOKENIZED_CAT = "604f2767ebccdd50cd175fd0"   # CMC "Tokenized Stock" category

    def _tokenized_index(self) -> dict:
        """Map underlying ticker -> [tokenized listings] (id, symbol, volume, chain). Cached.

        CMC carries 400+ tokenized stocks (xStock `<TICKER>X`, Ondo `<TICKER>on`) across chains;
        the call layer uses the plain underlying ticker, so this index bridges the two.
        """
        if getattr(self, "_tok_idx", None) is not None:
            return self._tok_idx
        idx: dict = {}
        try:
            d = self._get("/v1/cryptocurrency/category",
                          {"id": self._TOKENIZED_CAT, "limit": 1000, "convert": "USD"})
            for x in d.get("coins", []) or []:
                sym, name = (x.get("symbol") or "").strip(), x.get("name") or ""
                u = (x.get("quote", {}) or {}).get("USD", {}) or {}
                und = _underlying_ticker(sym, name)
                idx.setdefault(und.upper(), []).append({
                    "id": x.get("id"), "symbol": sym, "name": name, "underlying": und.upper(),
                    "volume_24h": u.get("volume_24h") or 0.0, "price": u.get("price"),
                    "percent_change_24h": u.get("percent_change_24h"),
                    "chain": (x.get("platform") or {}).get("name") or "native",
                    "token_address": (x.get("platform") or {}).get("token_address"),
                })
        except Exception as e:
            print(f"  [tokenized index] {type(e).__name__}: {e}")
        self._tok_idx = idx
        return idx

    def resolve(self, query: str) -> Optional[dict]:
        """Resolve a ticker or company name to a unified asset entity.

        Returns {kind, display, underlying, listing{id,symbol,volume_24h,chain,...}, aliases:set}.
        Tokenized stocks resolve to the highest-volume tradeable listing across chains/issuers;
        `aliases` are every ticker the calls might use (underlying + each tokenized symbol).
        """
        q = query.strip()
        qu = q.upper()
        idx = self._tokenized_index()
        listings = list(idx.get(qu, []))
        if not listings and len(q) >= 3:                       # company-name match, e.g. "micron"
            ql = q.lower()
            listings = [l for ls in idx.values() for l in ls if ql in l["name"].lower()]
        if listings:
            best = max(listings, key=lambda l: l.get("volume_24h") or 0)
            aliases = {qu, best["underlying"]} | {l["symbol"].upper() for l in listings}
            return {"kind": "tokenized_stock", "display": best["name"],
                    "underlying": best["underlying"], "listing": best, "aliases": aliases}
        info = self._resolve([qu]).get(qu)                     # crypto path
        if info and info.get("price") is not None:
            return {"kind": "crypto", "display": qu, "underlying": qu,
                    "listing": {"id": info["id"], "symbol": qu, "volume_24h": None, "chain": None},
                    "aliases": {qu}}
        return None

    # --- MarketSource ---------------------------------------------------

    def _resolve(self, symbols: List[str]) -> dict:
        """Pick the canonical token per symbol. CMC returns a LIST of all tokens sharing a
        symbol (many scam duplicates); the real/highest-ranked one is first and is the one
        with a USD price. Returns {symbol: {id, price, percent_change_24h}}."""
        data = self._get("/v2/cryptocurrency/quotes/latest", {"symbol": ",".join(symbols), "convert": "USD"})
        out = {}
        for key, entry in (data or {}).items():
            entries = entry if isinstance(entry, list) else [entry]
            chosen = None
            for e in entries:
                usd = (e.get("quote", {}) or {}).get("USD", {}) or {}
                if usd.get("price") is not None:
                    chosen = (e, usd)
                    break
            if chosen is None and entries:
                e0 = entries[0]
                chosen = (e0, (e0.get("quote", {}) or {}).get("USD", {}) or {})
            if chosen:
                e, usd = chosen
                out[e.get("symbol", key)] = {
                    "id": e.get("id"), "price": usd.get("price"),
                    "percent_change_24h": usd.get("percent_change_24h"),
                }
        return out

    def quotes(self, symbols: List[str]) -> dict:
        return {k: {"price": v["price"], "percent_change_24h": v["percent_change_24h"]}
                for k, v in self._resolve(symbols).items()}

    def ohlcv(self, symbol: str, interval: str, start: datetime, end: datetime) -> List[dict]:
        params = {
            "convert": "USD", "interval": interval,
            "time_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": 10000,
        }
        info = self._resolve([symbol]).get(symbol.upper())   # use canonical id (avoid symbol-collision tokens)
        if info and info.get("id"):
            params["id"] = info["id"]
        else:
            params["symbol"] = symbol.upper()
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
        """On-chain confirmation inputs. Prefer the rich DEX pools endpoint (liquidity + buy/sell);
        if it's unavailable for BSC on this tier, fall back to CMC's aggregated on-chain DEX volume
        (real, reliable) so confirmation still has a genuine 'money moving' signal."""
        usd = self._full_usd(symbol)
        metrics = {
            "price_runup_pct": round(float(usd.get("percent_change_24h") or 0.0), 2),
            "dex_volume_24h": _num(usd.get("dex_volume_24h")),
            "volume_24h": _num(usd.get("volume_24h")),
            "market_cap": _num(usd.get("market_cap")),
        }
        contract = BSC_CONTRACTS.get(symbol.upper())
        if contract:
            try:
                data = self._dex_pools(contract)
                pools = (data.get("pools") if isinstance(data, dict) else None) or \
                        (data if isinstance(data, list) else [])
                if pools:
                    metrics.update({
                        "liquidity_usd": sum(_num(p.get("liquidity") or p.get("liquidity_usd")) for p in pools),
                        "buy_volume_24h": sum(_num(p.get("buys_24h") or p.get("num_transactions_buy_24h")) for p in pools),
                        "sell_volume_24h": sum(_num(p.get("sells_24h") or p.get("num_transactions_sell_24h")) for p in pools),
                        "pools": len(pools),
                        "onchain_source": "cmc_dex_pools",
                    })
                    return metrics
            except Exception as e:
                metrics["dex_note"] = f"DEX pools unavailable ({e}); using aggregated DEX volume"
        metrics["onchain_source"] = "cmc_aggregated_dex_volume"
        return metrics

    def _dex_pools(self, contract: str, retries: int = 2):
        last = None
        for _ in range(retries + 1):
            try:
                return self._get("/v1/dex/token/pools",
                                 {"network_slug": "bsc", "contract_address": contract,
                                  "sort": "liquidity", "sort_dir": "desc", "limit": 10})
            except CMCError as e:
                last = e
                if "busy" not in str(e).lower():
                    break
        raise last or CMCError("dex pools failed")

    def _full_usd(self, symbol: str) -> dict:
        """Full USD quote block for the canonical token (volumes, market cap, % changes)."""
        try:
            data = self._get("/v2/cryptocurrency/quotes/latest", {"symbol": symbol.upper(), "convert": "USD"})
            entries = data.get(symbol.upper()) or []
            entries = entries if isinstance(entries, list) else [entries]
            for e in entries:
                usd = (e.get("quote", {}) or {}).get("USD", {}) or {}
                if usd.get("price") is not None:
                    return usd
            return (entries[0].get("quote", {}) or {}).get("USD", {}) if entries else {}
        except Exception:
            return {}

    def market_block(self, symbols) -> dict:
        """Rich per-symbol market block (batched). {symbol: {price, percent_change_24h/7d,
        volume_24h, cex_volume_24h, dex_volume_24h, market_cap, kind, chain}}.
        Crypto comes from quotes (highest-volume listing); tokenized stocks fall back to the index."""
        syms = sorted({s.upper() for s in symbols})
        valid = [s for s in syms if s.isalnum()]   # CMC rejects the whole batch on any non-alphanumeric symbol
        out: dict = {}
        for i in range(0, len(valid), 100):
            chunk = valid[i:i + 100]
            try:
                data = self._get("/v2/cryptocurrency/quotes/latest",
                                 {"symbol": ",".join(chunk), "convert": "USD", "skip_invalid": "true"})
            except Exception:
                continue
            for key, entry in (data or {}).items():
                entries = entry if isinstance(entry, list) else [entry]
                best, bestvol = None, -1.0
                for e in entries:
                    u = (e.get("quote", {}) or {}).get("USD", {}) or {}
                    if u.get("price") is None:
                        continue
                    v = _num(u.get("volume_24h"))
                    if v > bestvol:
                        bestvol, best = v, (e, u)
                if best:
                    e, u = best
                    out[(e.get("symbol") or key).upper()] = {
                        "id": e.get("id"),
                        "price": u.get("price"), "percent_change_24h": u.get("percent_change_24h"),
                        "percent_change_7d": u.get("percent_change_7d"), "volume_24h": u.get("volume_24h"),
                        "cex_volume_24h": u.get("cex_volume_24h"), "dex_volume_24h": u.get("dex_volume_24h"),
                        "market_cap": u.get("market_cap"), "kind": "crypto", "chain": None,
                    }
        idx = self._tokenized_index()                       # tokenized-stock override (active listing)
        for sym in syms:
            m = out.get(sym)
            if (not m or not _num(m.get("volume_24h"))) and sym in idx:
                b = max(idx[sym], key=lambda l: l.get("volume_24h") or 0)
                out[sym] = {
                    "id": b.get("id"),
                    "price": b.get("price"), "percent_change_24h": b.get("percent_change_24h"),
                    "percent_change_7d": None, "volume_24h": b.get("volume_24h"),
                    "cex_volume_24h": 0, "dex_volume_24h": b.get("volume_24h"),
                    "market_cap": None, "kind": "tokenized_stock", "chain": b.get("chain"),
                }
        return out

    def global_insights(self) -> dict:
        """Market-wide volume/cap insights from global-metrics."""
        try:
            g = self._get("/v1/global-metrics/quotes/latest", {"convert": "USD"})
            u = (g.get("quote", {}) or {}).get("USD", {}) or {}
            return {
                "total_market_cap": u.get("total_market_cap"), "total_volume_24h": u.get("total_volume_24h"),
                "defi_volume_24h": u.get("defi_volume_24h"), "altcoin_volume_24h": u.get("altcoin_volume_24h"),
                "stablecoin_volume_24h": u.get("stablecoin_volume_24h"),
                "btc_dominance": g.get("btc_dominance"), "eth_dominance": g.get("eth_dominance"),
            }
        except Exception:
            return {}

    # --- CMC attention (cross-ref the KOL calls against CMC's own crowd) ----

    def cmc_attention(self, limit: int = 30) -> dict:
        """CMC's own attention signals, to cross-reference against the KOL calls.
        Each list is [{symbol, name, rank, percent_change_24h}]; best-effort per list so a
        gated/missing endpoint (crypto trending needs Startup+) just drops one list."""
        def _coins(path, params):
            try:
                d = self._get(path, params)
                return d if isinstance(d, list) else (d.get("data") or [])
            except Exception as e:
                print(f"  [attention {path}] {type(e).__name__}: {e}")
                return []

        def _row(x):
            u = (x.get("quote", {}) or {}).get("USD", {}) or {}
            return {"symbol": (x.get("symbol") or "").upper(), "name": x.get("name"),
                    "rank": x.get("cmc_rank"), "percent_change_24h": u.get("percent_change_24h")}

        out = {
            "most_visited": [_row(x) for x in _coins(
                "/v1/cryptocurrency/trending/most-visited", {"limit": limit})],
            "gainers": [_row(x) for x in _coins(
                "/v1/cryptocurrency/trending/gainers-losers",
                {"limit": limit, "sort": "percent_change_24h", "sort_dir": "desc", "time_period": "24h"})],
            "losers": [_row(x) for x in _coins(
                "/v1/cryptocurrency/trending/gainers-losers",
                {"limit": limit, "sort": "percent_change_24h", "sort_dir": "asc", "time_period": "24h"})],
            "community": [],
        }
        for x in _coins("/v1/community/trending/token", {"limit": min(limit, 5)}):   # caps at 5
            out["community"].append({"symbol": (x.get("symbol") or "").upper(),
                                     "name": x.get("name"), "rank": x.get("rank")})
        return out

    # --- Asset identity + price context -------------------------------------

    def info(self, sym_to_id: dict) -> dict:
        """Batched metadata by canonical id (avoids symbol-collision scam tokens).
        {SYM: {logo, tags[], category, date_added, date_launched, description, urls{...}}}."""
        id_to_sym = {str(i): s for s, i in sym_to_id.items() if i}
        ids = list(id_to_sym.keys())
        out: dict = {}
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            try:
                d = self._get("/v2/cryptocurrency/info", {"id": ",".join(chunk)})
            except Exception as e:
                print(f"  [info] {type(e).__name__}: {e}")
                continue
            for k, entry in (d or {}).items():
                e = entry[0] if isinstance(entry, list) else entry
                sym = id_to_sym.get(str(k)) or (e.get("symbol") or "").upper()
                urls = e.get("urls", {}) or {}

                def _first(key):
                    v = urls.get(key)
                    if isinstance(v, list):
                        return v[0] if v else None
                    return v or None

                out[sym] = {
                    "logo": e.get("logo"), "tags": (e.get("tags") or [])[:6],
                    "category": e.get("category"), "date_added": e.get("date_added"),
                    "date_launched": e.get("date_launched"),
                    "description": (e.get("description") or "")[:280] or None,
                    "urls": {"website": _first("website"), "twitter": _first("twitter"),
                             "reddit": _first("reddit"), "explorer": _first("explorer"),
                             "source_code": _first("source_code"), "technical_doc": _first("technical_doc")},
                }
        return out

    def price_performance(self, sym_to_id: dict) -> dict:
        """Batched ATH/ATL + ROI ladder by canonical id.
        {SYM: {ath, ath_date, atl, pct_from_ath, roi_all_time, periods{7d,30d,90d,365d}}}."""
        id_to_sym = {str(i): s for s, i in sym_to_id.items() if i}
        ids = list(id_to_sym.keys())
        out: dict = {}
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            try:
                d = self._get("/v2/cryptocurrency/price-performance-stats/latest",
                              {"id": ",".join(chunk), "time_period": "all_time,7d,30d,90d,365d", "convert": "USD"})
            except Exception as e:
                print(f"  [price_performance] {type(e).__name__}: {e}")
                continue
            for k, entry in (d or {}).items():
                e = entry[0] if isinstance(entry, list) else entry
                sym = id_to_sym.get(str(k)) or (e.get("symbol") or "").upper()
                P = e.get("periods", {}) or {}

                def _pc(p):
                    return (((P.get(p) or {}).get("quote") or {}).get("USD") or {}).get("percent_change")

                allt = ((P.get("all_time") or {}).get("quote") or {}).get("USD") or {}
                ath, close = allt.get("high"), allt.get("close")
                pct_from_ath = round((close - ath) / ath * 100, 2) if (ath and close) else None
                out[sym] = {
                    "ath": ath, "ath_date": allt.get("high_timestamp"), "atl": allt.get("low"),
                    "pct_from_ath": pct_from_ath, "roi_all_time": allt.get("percent_change"),
                    "periods": {"7d": _pc("7d"), "30d": _pc("30d"), "90d": _pc("90d"), "365d": _pc("365d")},
                }
        return out

    def market_pairs(self, cid, limit: int = 20) -> list:
        """All venues an asset trades on (CEX + DEX), top by 24h volume:
        [{exchange, exchange_id, exchange_slug, pair, category, volume_24h, price}]."""
        try:
            d = self._get("/v2/cryptocurrency/market-pairs/latest",
                          {"id": str(cid), "limit": 500, "category": "spot", "convert": "USD"})   # all spot venues
        except Exception as e:
            print(f"  [market_pairs {cid}] {type(e).__name__}: {e}")
            return []
        pairs = (d.get("market_pairs") if isinstance(d, dict) else None) or []
        rows = []
        for p in pairs:
            q = p.get("quote", {}) or {}
            usd, rep = q.get("USD", {}) or {}, q.get("exchange_reported", {}) or {}
            ex = p.get("exchange") or {}
            rows.append({
                "exchange": ex.get("name"), "exchange_id": ex.get("id"), "exchange_slug": ex.get("slug"),
                "pair": p.get("market_pair"), "category": p.get("category"),
                "volume_24h": _num(usd.get("volume_24h")) or _num(rep.get("volume_24h_quote")),
                "price": usd.get("price") or rep.get("price"),
            })
        rows.sort(key=lambda r: r["volume_24h"] or 0, reverse=True)
        return rows[:limit]

    def altcoin_season(self) -> dict:
        """Real CMC Altcoin Season Index (0-100) — replaces the 100-BTC_dom proxy."""
        try:
            d = self._get("/v1/altcoin-season-index/latest")
            idx = d.get("altcoin_index")
            if idx is None:
                return {}
            idx = int(idx)
            cls = "altcoin_season" if idx >= 75 else ("bitcoin_season" if idx <= 25 else "neutral")
            return {"value": idx, "classification": cls,
                    "yearly_high": d.get("yearly_high"), "yearly_low": d.get("yearly_low")}
        except Exception as e:
            print(f"  [altcoin_season] {type(e).__name__}: {e}")
            return {}

    def fear_greed_trend(self, limit: int = 14) -> dict:
        """F&G over the last `limit` days: {points:[{ts,value}], delta, direction, latest}."""
        try:
            d = self._get("/v3/fear-and-greed/historical", {"limit": limit})
            rows = d if isinstance(d, list) else (d.get("data") or [])
            pts = []
            for r in rows:
                try:
                    pts.append({"ts": int(r.get("timestamp")), "value": int(r.get("value"))})
                except (TypeError, ValueError):
                    continue
            pts.sort(key=lambda x: x["ts"])   # oldest -> newest
            if not pts:
                return {}
            delta = pts[-1]["value"] - pts[0]["value"]
            direction = "rising" if delta > 2 else ("falling" if delta < -2 else "flat")
            return {"points": pts, "delta": delta, "direction": direction, "latest": pts[-1]["value"]}
        except Exception as e:
            print(f"  [fear_greed_trend] {type(e).__name__}: {e}")
            return {}

    # --- Derivatives (perp funding / open interest) ------------------------

    def derivatives(self, symbol: str, venue: Optional[str] = None, limit: int = 50) -> dict:
        """Perp aggregate for an asset across venues (funding / OI / volume).
        Optionally focus one venue (e.g. 'Binance'). Returns {funding_rate (vol-weighted),
        open_interest, perp_volume_24h, venue, venues:[{venue, oi, funding_rate, volume_24h, price}]}."""
        try:
            d = self._get("/v5/cryptocurrency/derivatives/market-pairs/list/latest",
                          {"crypto_symbol": symbol.upper(), "limit": limit})
        except Exception as e:
            print(f"  [derivatives {symbol}] {type(e).__name__}: {e}")
            return {}
        pairs = (d.get("market_pairs") if isinstance(d, dict) else None) or []
        rows = []
        for p in pairs:
            if (p.get("category") or "").lower() != "perpetual":
                continue
            quotes = p.get("exchange_reported_quotes") or []
            q = next((x for x in quotes if (x.get("convert_symbol") or "").upper() == "USD"), None) \
                or (quotes[0] if quotes else {})
            rows.append({
                "venue": (p.get("exchange") or {}).get("exchange_name"),
                "oi": _num(q.get("open_interest")), "funding_rate": q.get("funding_rate"),
                "volume_24h": _num(q.get("volume_24h_quote")), "price": q.get("price"),
            })
        if venue:
            vlow = venue.lower()
            rows = [r for r in rows if (r["venue"] or "").lower() == vlow] or rows
        elif any((r["venue"] or "").lower() in _MAJOR_PERP for r in rows):
            rows = [r for r in rows if (r["venue"] or "").lower() in _MAJOR_PERP]  # drop wash-volume venues
        if not rows:
            return {}
        rows.sort(key=lambda r: r["volume_24h"] or 0, reverse=True)
        fden = sum(r["volume_24h"] for r in rows if r["funding_rate"] is not None)
        fnum = sum((r["funding_rate"] or 0) * r["volume_24h"] for r in rows if r["funding_rate"] is not None)
        return {
            "funding_rate": (fnum / fden) if fden else rows[0].get("funding_rate"),
            "open_interest": sum(r["oi"] for r in rows),
            "perp_volume_24h": sum(r["volume_24h"] for r in rows),
            "venue": rows[0]["venue"], "venues": rows[:8],
        }

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
            trending = [(x.get("topic") or x.get("name") or "").rstrip("#").strip()
                        for x in (t or [])]
            trending = [x for x in trending if x]
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

    def calls_for(self, symbol: str, since: Optional[datetime] = None) -> List[CallCandidate]:
        """Per-coin call/mention layer from CMC community posts + news — makes ANY listed coin searchable.

        Community posts (people posting about the coin, with author/time/text/engagement) are the
        closest thing to 'calls'; news rounds it out. Returned as CallCandidates for calls.py.
        """
        info = self._resolve([symbol]).get(symbol.upper())
        if not info or not info.get("id"):
            return []
        cid, sym = info["id"], symbol.upper()
        out: List[CallCandidate] = []
        for path in ("/v1/content/posts/top", "/v1/content/posts/latest"):
            try:
                d = self._get(path, {"id": cid})
                rows = d if isinstance(d, list) else (d.get("list") or d.get("data") or [])
                for p in rows:
                    ts = _epoch_ms(p.get("post_time"))
                    text = (p.get("text_content") or "").strip()
                    if ts is None or not text:
                        continue
                    if since is not None and ts < _aware(since):
                        continue
                    out.append(CallCandidate(
                        symbol=sym, raw_text=text,
                        author=(p.get("owner") or {}).get("nickname") or "cmc_community",
                        source="cmc_community", ts=ts,
                        engagement={"likes": _num(p.get("like_count")), "comments": _num(p.get("comment_count"))},
                        url=p.get("comments_url"), stance=None, conviction=None,
                    ))
            except Exception:
                continue
        try:
            news = self._get("/v1/content/latest", {"id": cid, "limit": 20})
            news = news if isinstance(news, list) else (news.get("data") or [])
            for it in news:
                ts = _parse_ts(it.get("released_at") or it.get("created_at"))
                text = " ".join(filter(None, [it.get("title"), it.get("subtitle")]))
                if ts is None or not text:
                    continue
                if since is not None and ts < _aware(since):
                    continue
                out.append(CallCandidate(
                    symbol=sym, raw_text=text, author=it.get("source_name") or "cmc_news",
                    source="cmc_news", ts=ts, url=it.get("source_url"),
                    engagement={}, stance=None, conviction=None,
                ))
        except Exception:
            pass
        seen, uniq = set(), []                       # dedup near-identical (author + text head)
        for c in out:
            k = (c.author, c.raw_text[:48])
            if k not in seen:
                seen.add(k)
                uniq.append(c)
        return uniq


def _underlying_ticker(sym: str, name: str) -> str:
    """Strip the issuer suffix from a tokenized-stock symbol to get the real ticker.
    xStock: TSLAX->TSLA, SPYX->SPY. Ondo: MUon->MU, CRCLon->CRCL."""
    s = sym or ""
    nl = (name or "").lower()
    if "xstock" in nl and s.lower().endswith("x"):
        return s[:-1]
    if "ondo" in nl and s.lower().endswith("on"):
        return s[:-2]
    if "bstock" in nl and s.lower().endswith("b"):
        return s[:-1]
    if s.lower().endswith("on") and len(s) > 3:
        return s[:-2]
    if s.lower().endswith("x") and len(s) > 2:
        return s[:-1]
    return s


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


def _epoch_ms(v) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(v) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
