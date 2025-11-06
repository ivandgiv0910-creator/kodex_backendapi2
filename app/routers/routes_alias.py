# app/routers/routes_alias.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Optional
import time

alias = APIRouter()

@alias.get("/jit_plugin/getPatternsSingle")
async def alias_get_patterns_single(
    symbol: str,
    timeframe: str,
    limit: Optional[int] = 300,
    request: Request = None
):
    """
    Alias untuk kompatibilitas GPT Actions.
    Query: ?symbol=BTCUSDT&timeframe=1h&limit=300
    TODO: sambungkan ke fungsi core analisa kamu kalau sudah siap.
    """
    # --- STUB aman: ganti dengan call ke logic asli kamu bila ada ---
    # from app.routers.patterns import get_patterns_single_core
    # return await get_patterns_single_core(symbol, timeframe, int(limit or 300))
    # ----------------------------------------------------------------
    return JSONResponse({
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bars": int(limit or 300),
        "trend": "sideway",
        "momentum": "moderate",
        "atr14": 0.0,
        "last_close": 0.0,
        "majorPattern": None,
        "candlestick": None,
        "plan": {
            "long":  {"entry": 0.0, "sl": 0.0, "tp1": 0.0, "tp2": 0.0},
            "short": {"entry": 0.0, "sl": 0.0, "tp1": 0.0, "tp2": 0.0}
        },
        "generated_at": int(time.time() * 1000)
    })
