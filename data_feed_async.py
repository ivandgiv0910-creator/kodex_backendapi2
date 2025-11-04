# data_feed_async.py
import asyncio
import pandas as pd
import httpx
from fastapi import HTTPException

# Urutan host fallback (cepat → mirror)
HOSTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://data-api.binance.vision",
]

# Batas waktu ketat
PER_ATTEMPT_TIMEOUT = 2.5   # detik per host
TOTAL_DEADLINE      = 8.0   # detik total (global budget)

HEADERS = {"User-Agent": "KodeX-Live/2.1"}

async def _fetch_klines(client: httpx.AsyncClient, host: str, params: dict) -> pd.DataFrame:
    url = f"{host}/api/v3/klines"
    print(f"[FETCH] {url} {params}")
    r = await client.get(url, params=params, timeout=PER_ATTEMPT_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"{host} -> {r.status_code} {r.text[:120]}")
    data = r.json()
    if not data:
        raise HTTPException(status_code=502, detail=f"{host} -> empty klines")
    cols = ["open_time","open","high","low","close","volume",
            "close_time","qav","trades","taker_base","taker_quote","ignore"]
    df = pd.DataFrame(data, columns=cols)
    for c in ("open","high","low","close","volume"):
        df[c] = df[c].astype(float)
    return df[["open_time","open","high","low","close","volume"]]

async def binance_klines(symbol: str, interval: str = "1m", limit: int = 200) -> pd.DataFrame:
    """
    Ambil klines dengan fallback multi-host.
    Dijaga: tidak boleh lebih dari TOTAL_DEADLINE detik (hard stop).
    """
    params = {"symbol": symbol.upper(), "interval": interval, "limit": int(limit)}
    last_err = None

    async with httpx.AsyncClient(headers=HEADERS, http2=True) as client:
        try:
            # Hard deadline untuk SELURUH operasi
            async with asyncio.timeout(TOTAL_DEADLINE):
                for host in HOSTS:
                    try:
                        return await _fetch_klines(client, host, params)
                    except (HTTPException, httpx.RequestError) as e:
                        last_err = f"{host} -> {type(e).__name__}: {e}"
                        print(f"[WARN] {last_err}")
                        # coba host berikutnya
                        continue
        except TimeoutError:
            last_err = f"GlobalTimeout>{TOTAL_DEADLINE}s"

    raise HTTPException(status_code=502, detail=f"Provider error (all hosts). last={last_err}")

async def last_price(symbol: str, interval: str = "1m") -> float:
    df = await binance_klines(symbol, interval, limit=1)
    return float(df.iloc[-1]["close"])
