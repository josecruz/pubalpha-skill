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
