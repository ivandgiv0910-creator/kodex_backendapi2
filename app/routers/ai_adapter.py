from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from ..services.binance_client import binance_http
from ..adapters.kodex_adapter import build_from_klines, SignalConfig

router = APIRouter()

@router.get("/analyze")
async def ai_analyze(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    limit: int = Query(200, ge=60, le=1000),
):
    kl = await binance_http.get_klines(symbol, interval, limit)
    if not kl.get("ok"):
        return JSONResponse(content={"ok": False, "msg": "cannot fetch klines", "detail": kl}, status_code=502)

    adapter = build_from_klines(kl["data"])
    res = adapter.analyze()
    return {"ok": True, "symbol": symbol.upper(), "interval": interval, "analysis": res}

@router.get("/signal")
async def ai_signal(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    limit: int = Query(200, ge=60, le=1000),
    atr_sl: float = Query(1.8, description="ATR multiplier for SL"),
    atr_tp1: float = Query(1.2),
    atr_tp2: float = Query(2.4),
):
    kl = await binance_http.get_klines(symbol, interval, limit)
    if not kl.get("ok"):
        return JSONResponse(content={"ok": False, "msg": "cannot fetch klines", "detail": kl}, status_code=502)

    adapter = build_from_klines(kl["data"])
    cfg = SignalConfig(atr_mult_sl=atr_sl, atr_mult_tp1=atr_tp1, atr_mult_tp2=atr_tp2)
    setup = adapter.build_setup(cfg)

    return {
        "ok": True,
        "symbol": symbol.upper(),
        "interval": interval,
        **setup
    }
