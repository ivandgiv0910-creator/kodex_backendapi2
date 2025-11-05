# app/routers/patterns.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import httpx, asyncio, statistics, math, time

router = APIRouter(prefix="/patterns", tags=["patterns"])

# ---- healthcheck (untuk verifikasi mount) ----
@router.get("/health")
def patterns_health():
    return {"ok": True, "router": "patterns", "ts": int(time.time())}

# ----------------------------
#  > DI BAWAH INI versi ringkas fetch + analisa
# ----------------------------
TIMEOUT = 8.0
MAX_LIMIT = 1000
SUPPORTED_TF = {"1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d"}

async def _fetch_klines(symbol: str, tf: str, limit: int) -> List[Dict[str, Any]]:
    if tf not in SUPPORTED_TF:
        raise HTTPException(400, f"Unsupported timeframe {tf}")
    limit = min(MAX_LIMIT, max(50, int(limit or 300)))
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
            try:
                r = await client.get(f"{base}/api/v3/klines",
                                     params={"symbol": symbol.upper(), "interval": tf, "limit": limit},
                                     timeout=TIMEOUT)
                if r.status_code == 451:  # regional block -> coba mirror berikutnya
                    continue
                if r.status_code == 429:
                    await asyncio.sleep(0.5); continue
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list):
                    continue
                return [
                    {
                        "open_time": int(k[0]),
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]),  "close": float(k[4]),
                        "volume": float(k[5]), "close_time": int(k[6]),
                    } for k in data
                ]
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.3)
                continue
    raise HTTPException(502, f"All Binance mirrors failed: {repr(last_err)}")

def _sma(vals: List[float], p: int) -> float:
    return statistics.fmean(vals[-p:]) if len(vals) >= p else float("nan")

def _atr(rows: List[Dict[str, float]], p: int = 14) -> float:
    if len(rows) < p+1: return 0.0
    trs = []
    for i in range(1, len(rows)):
        h,l,pc = rows[i]["high"], rows[i]["low"], rows[i-1]["close"]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return statistics.fmean(trs[-p:])

@router.get("/{symbol}/{timeframe}")
async def analyze_patterns(symbol: str, timeframe: str, limit: Optional[int] = Query(300)):
    rows = await _fetch_klines(symbol, timeframe, limit or 300)
    if not rows: raise HTTPException(502, "No data")
    atr14 = _atr(rows, 14)
    closes = [r["close"] for r in rows]
    ema20, ema50 = _sma(closes, 20), _sma(closes, 50)
    trend = "bullish" if ema20 > ema50 else ("bearish" if ema20 < ema50 else "sideway")
    momentum = "strong" if abs(closes[-1]-closes[-6]) > atr14*0.6 else ("moderate" if abs(closes[-1]-closes[-6]) > atr14*0.2 else "weak")
    px = closes[-1]
    plan = {
        "long":  {"entry": round(px-0.2*atr14,2), "sl": round(px-1.0*atr14,2), "tp1": round(px+0.8*atr14,2), "tp2": round(px+1.6*atr14,2)},
        "short": {"entry": round(px+0.2*atr14,2), "sl": round(px+1.0*atr14,2), "tp1": round(px-0.8*atr14,2), "tp2": round(px-1.6*atr14,2)},
    }
    return {
        "symbol": symbol.upper(), "timeframe": timeframe, "bars": len(rows),
        "trend": trend, "momentum": momentum, "atr14": round(atr14, 6),
        "plan": plan, "last_close": px, "generated_at": int(time.time()*1000)
    }
