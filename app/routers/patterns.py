from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional   # ⬅️ WAJIB ADA
import httpx, asyncio, math, statistics, time

router = APIRouter(prefix="/patterns", tags=["patterns"])

# --- ganti fungsi lama _fetch_klines di patterns.py dengan ini ---

async def _fetch_klines(symbol: str, tf: str, limit: int) -> List[Dict[str, Any]]:
    if tf not in SUPPORTED_TF:
        raise HTTPException(400, f"Unsupported timeframe {tf}")
    limit = min(MAX_LIMIT, max(50, int(limit or 300)))

    # daftar mirror yang akan dicoba berurutan
    mirrors = [
        "https://api4.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api.binance.us"
    ]

    last_err = None
    async with httpx.AsyncClient() as client:
        for base in mirrors:
            url = f"{base}/api/v3/klines"
            params = {"symbol": symbol.upper(), "interval": tf, "limit": limit}
            try:
                r = await client.get(url, params=params, timeout=TIMEOUT)
                if r.status_code == 451:
                    # coba mirror berikutnya
                    continue
                if r.status_code == 429:
                    await asyncio.sleep(0.5)
                    continue
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list):
                    continue
                return [
                    {
                        "open_time": int(k[0]),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "close_time": int(k[6])
                    }
                    for k in data
                ]
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.3)
                continue
    raise HTTPException(502, f"All Binance mirrors failed: {repr(last_err)}")
