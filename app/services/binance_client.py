import asyncio
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

DEFAULT_TIMEOUT = httpx.Timeout(10.0, read=15.0)

class BinanceHTTP:
    def __init__(self, hosts: Optional[List[str]] = None):
        self.hosts = hosts or [
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://data-api.binance.vision",
        ]
        self._idx = 0
        self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, http2=True)

    def _current_host(self) -> str:
        return self.hosts[self._idx % len(self.hosts)]

    def _rotate(self):
        self._idx = (self._idx + 1) % len(self.hosts)

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        GET dengan retry & rotate host. Path harus diawali '/'.
        """
        if not path.startswith("/"):
            path = "/" + path

        last_err = None
        for _ in range(len(self.hosts)):
            base = self._current_host()
            url = base + path
            try:
                resp = await self._client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()
                # kalau 404 di host data-api, coba host lain
                last_err = Exception(f"HTTP {resp.status_code} on {url}: {resp.text[:160]}")
            except Exception as e:
                last_err = e
            # rotate dan coba lagi
            self._rotate()
        raise last_err or Exception("All Binance hosts failed")

    async def close(self):
        await self._client.aclose()


# Instance global yang dipakai modul lain
binance_http = BinanceHTTP(getattr(settings, "binance_hosts", None))


# Convenience helpers
async def get_klines(symbol: str, interval: str, limit: int = 200):
    """
    Return: list klines seperti standar Binance:
    [
      [ openTime, open, high, low, close, volume, closeTime, ... ],
      ...
    ]
    """
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": min(max(int(limit), 1), 1000),
    }
    data = await binance_http.get("/api/v3/klines", params=params)
    return data


async def get_price(symbol: str) -> float:
    data = await binance_http.get("/api/v3/ticker/price", params={"symbol": symbol.upper()})
    # response: {"symbol":"BTCUSDT","price":"103456.12000000"}
    return float(data["price"])
