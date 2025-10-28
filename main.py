from fastapi import FastAPI, HTTPException
import requests, pandas as pd, pandas_ta as ta
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="Kode X Market API", version="2.1")

def fetch_ohlcv_binance(symbol: str, timeframe: str, limit: int = 300):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": timeframe, "limit": min(limit, 1000)}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise HTTPException(502, f"Binance error: {r.text}")
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume","close_time",
        "qav","num_trades","taker_base","taker_quote","ignore"
    ])
    df["time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["time","open","high","low","close","volume"]]
    return df

def style_from_tf(tf: str):
    if tf in ["1m","5m","15m"]:
        return "scalping"
    if tf in ["30m","1h"]:
        return "intraday"
    if tf in ["4h","1d"]:
        return "swing"
    return "positional"

def indicator_presets(style: str):
    if style == "scalping":
        return dict(ema_fast=9, ema_slow=21, bb_len=20, bb_dev=2.2, macd=(8,21,5), rsi=7)
    if style == "intraday":
        return dict(ema_fast=20, ema_slow=50, bb_len=20, bb_dev=2.0, macd=(12,26,9), rsi=14)
    if style == "swing":
        return dict(ema_fast=50, ema_slow=200, bb_len=20, bb_dev=2.0, macd=(12,26,9), rsi=14)
    return dict(ema_fast=100, ema_slow=200, bb_len=20, bb_dev=2.0, macd=(12,26,9), rsi=14)

def compute_indicators(df: pd.DataFrame, style: str):
    p = indicator_presets(style)
    df["ema_fast"] = ta.ema(df["close"], length=p["ema_fast"])
    df["ema_slow"] = ta.ema(df["close"], length=p["ema_slow"])
    bb = ta.bbands(df["close"], length=p["bb_len"], std=p["bb_dev"])
    macd = ta.macd(df["close"], fast=p["macd"][0], slow=p["macd"][1], signal=p["macd"][2])
    df["rsi"] = ta.rsi(df["close"], length=p["rsi"])
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    last = df.iloc[-1]
    return {
        "ema_fast": float(last["ema_fast"]),
        "ema_slow": float(last["ema_slow"]),
        "bb_middle": float(bb.iloc[-1,1]),
        "bb_upper": float(bb.iloc[-1,0]),
        "bb_lower": float(bb.iloc[-1,2]),
        "macd": {
            "line": float(macd.iloc[-1,0]),
            "signal": float(macd.iloc[-1,1]),
            "hist": float(macd.iloc[-1,2])
        },
        "rsi": float(last["rsi"]),
        "atr": float(last["atr"])
    }

@app.get("/market/snapshot")
def market_snapshot(symbol: str, timeframe: str = "15m", limit: int = 300):
    df = fetch_ohlcv_binance(symbol, timeframe, limit)
    price = float(df["close"].iloc[-1])
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "provider_time": df["time"].iloc[-1].isoformat(),
        "price": price,
    }

@app.post("/market/indicators")
def market_indicators(symbol: str, timeframe: str = "15m", style: Optional[str] = None, limit: int = 300):
    df = fetch_ohlcv_binance(symbol, timeframe, limit)
    style = style or style_from_tf(timeframe)
    indicators = compute_indicators(df, style)
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "style": style,
        "price": float(df["close"].iloc[-1]),
        "indicators": indicators
    }

@app.get("/")
def root():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
