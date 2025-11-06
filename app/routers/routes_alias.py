# routes_alias.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional

alias = APIRouter()

@alias.get("/jit_plugin/getPatternsSingle")
async def alias_get_patterns_single(symbol: str, timeframe: str, limit: Optional[int] = 300, request: Request = None):
    """
    Alias untuk menjaga kompatibilitas GPT Action:
    - Menerima query ?symbol=BTCUSDT&timeframe=1h&limit=300
    - Meneruskan ke handler asli yang ada di /patterns/{symbol}/{timeframe}
    """
    # Jika kamu ingin meneruskan ke handler internal, kamu bisa import fungsi handler asli dan panggil langsung.
    # Contoh (sesuaikan nama modul/fungsinya):
    #
    #   from routes_patterns import get_patterns_single_core
    #   return await get_patterns_single_core(symbol, timeframe, limit)
    #
    # Jika handler asli ada di app instance yang sama sebagai route lain, opsi paling aman adalah
    # duplikasi pemanggilan fungsi core. Sementara, berikut stub aman yang tidak merusak layanan lain.

    # --- START: ganti blok di bawah ini dengan call ke logic asli kamu ---
    # Stub respons minimal (agar connector GPT tidak error saat alias diaktifkan)
    import time
    return JSONResponse({
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bars": limit or 300,
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
    # --- END STUB ---
