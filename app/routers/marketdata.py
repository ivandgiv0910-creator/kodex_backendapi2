# app/routers/marketdata.py
from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
import httpx
import asyncio

router = APIRouter(prefix="/marketdata", tags=["marketdata"])

# --- Konfigurasi dasar ---
BINANCE_BASE = "https://api.binance.com"
BINANCE_TIMEOUT = 8.0   # detik
MAX_LIMIT = 1000
CACHE_TTL = 10.0        # detik

SUPPORTED_TF = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h", "12h": "12h",
    "1d": "1d",
}

_cache: Dict[str, tuple[float, Any]] = {}

def _cache_key(symbol: str, timeframe: str, limit: int, since: Optional[int]) -> str:
    return f"{symbol.upper()}|{timeframe}|{limit}|{since or 0}"

def _get_cached(key: str):
    rec = _cache.get(key)
    if not rec:
        return None
    expires_at, data = rec
    if time.time() <= expires_at:
        return data
    _cache.pop(key, None)
    return None

def _set_cache(key: str, data: Any):
    _cache[key] = (time.time() + CACHE_TTL, data)

def _validate_timeframe(tf: str) -> str:
    tf = tf.strip().lower()
    if tf not in SUPPORTED_TF:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe '{tf}'. Allowed: {', '.join(SUPPORTED_TF.keys())}")
    return SUPPORTED_TF[tf]

def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None:
        return 200
    try:
        limit = int(limit)
    except:
        raise HTTPException(status_code=400, detail="limit must be an integer")
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    return min(limit, MAX_LIMIT)

def _normalize_klines(kl: List[list]) -> List[Dict[str, Any]]:
    # Binance kline schema:
    # [0] open_time, [1] open, [2] high, [3] low, [4] close, [5] volume, [6] close_time, ...
    out = []
    for k in kl:
        out.append({
            "open_time": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": int(k[6]),
        })
    return out

async def _binance_klines(
    client: httpx.AsyncClient,
    symbol: str,
    interval: str,
    limit: int,
    since: Optional[int] = None
) -> List[Dict[str, Any]]:
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if since:
        params["startTime"] = since
    url = f"{BINANCE_BASE}/api/v3/klines"

    last_err = None
    for attempt in range(3):
        try:
            r = await client.get(url, params=params, timeout=BINANCE_TIMEOUT)
            if r.status_code == 429:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and data.get("code"):
                raise HTTPException(status_code=502, detail=f"Binance error {data.get('code')}: {data.get('msg')}")
            if not isinstance(data, list):
                raise HTTPException(status_code=502, detail="Unexpected response from Binance")
            return _normalize_klines(data)
        except (httpx.HTTPError, httpx.ConnectError, httpx.ReadTimeout) as e:
            last_err = e
            await asyncio.sleep(0.35 * (attempt + 1))
    raise HTTPException(status_code=502, detail=f"Upstream error from Binance: {repr(last_err)}")

@router.get("")
async def get_marketdata_query(
    symbols: str = Query(..., description="Daftar simbol dipisah koma, contoh: BTCUSDT,ETHUSDT"),
    timeframe: str = Query(..., description="Contoh: 1m,5m,15m,30m,1h,2h,4h,1d"),
    limit: Optional[int] = Query(200, description=f"Jumlah candle, max {MAX_LIMIT}"),
    since: Optional[int] = Query(None, description="Start time (ms since epoch) opsional"),
) -> Dict[str, Any]:
    tf = _validate_timeframe(timeframe)
    lim = _clamp_limit(limit)
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        raise HTTPException(status_code=400, detail="symbols cannot be empty")

    results: Dict[str, Any] = {"timeframe": tf, "limit": lim, "since": since, "data": {}}
    async with httpx.AsyncClient() as client:
        for sym in syms:
            key = _cache_key(sym, tf, lim, since)
            cached = _get_cached(key)
            if cached is not None:
                results["data"][sym] = cached
                continue
            kl = await _binance_klines(client, sym, tf, lim, since)
            _set_cache(key, kl)
            results["data"][sym] = kl
    return results

@router.get("/{symbol}/{timeframe}")
async def get_marketdata_symbol(
    symbol: str,
    timeframe: str,
    limit: Optional[int] = Query(200, description=f"Jumlah candle, max {MAX_LIMIT}"),
    since: Optional[int] = Query(None, description="Start time (ms since epoch) opsional")
) -> Dict[str, Any]:
    tf = _validate_timeframe(timeframe)
    lim = _clamp_limit(limit)
    key = _cache_key(symbol, tf, lim, since)
    cached = _get_cached(key)
    if cached is not None:
        return {"symbol": symbol.upper(), "timeframe": tf, "limit": lim, "since": since, "data": cached}
    async with httpx.AsyncClient() as client:
        kl = await _binance_klines(client, symbol, tf, lim, since)
    _set_cache(key, kl)
    return {"symbol": symbol.upper(), "timeframe": tf, "limit": lim, "since": since, "data": kl}
