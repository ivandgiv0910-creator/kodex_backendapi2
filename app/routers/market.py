from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from ..services.binance_client import binance_http

router = APIRouter()

def _bad(res):  # helper untuk balikan 502 kalau upstream gagal
    return JSONResponse(content=res, status_code=502)

@router.get("/ping")
async def market_ping():
    res = await binance_http.ping_any()
    return res if res.get("ok") else _bad(res)

@router.get("/time")
async def market_time():
    res = await binance_http.simple_get("/api/v3/time")
    return res if res.get("ok") else _bad(res)

@router.get("/exchangeInfo")
async def exchange_info():
    res = await binance_http.simple_get("/api/v3/exchangeInfo")
    return res if res.get("ok") else _bad(res)

@router.get("/ticker")
async def ticker(symbol: str = Query("BTCUSDT", description="contoh: BTCUSDT / ETHUSDT / XAUUSDT")):
    res = await binance_http.simple_get(f"/api/v3/ticker/price?symbol={symbol.upper()}")
    return res if res.get("ok") else _bad(res)

@router.get("/klines")
async def klines(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h", description="1m 3m 5m 15m 1h 4h 1d ..."),
    limit: int = Query(100, ge=1, le=1000),
):
    res = await binance_http.get_klines(symbol, interval, limit)
    return res if res.get("ok") else _bad(res)

@router.get("/depth")
async def depth(
    symbol: str = Query("BTCUSDT"),
    limit: int = Query(50, ge=5, le=5000),
):
    res = await binance_http.get_depth(symbol, limit)
    return res if res.get("ok") else _bad(res)

@router.get("/bookTicker")
async def book_ticker(symbol: str = Query("BTCUSDT")):
    res = await binance_http.get_book_ticker(symbol)
    return res if res.get("ok") else _bad(res)

@router.get("/avgPrice")
async def avg_price(symbol: str = Query("BTCUSDT")):
    res = await binance_http.get_avg_price(symbol)
    return res if res.get("ok") else _bad(res)
