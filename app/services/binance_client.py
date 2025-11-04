import time, httpx, logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger("binance_client")
logging.basicConfig(level=logging.INFO)

def _http2():
    # aman kalau field belum ada
    return getattr(settings, "http2_enabled", False)

class BinanceHTTP:
    def __init__(self):
        self.hosts = list(settings.binance_hosts)
        if not self.hosts:
            raise RuntimeError("BINANCE_HOSTS tidak terdefinisi di .env")

        self.timeout = httpx.Timeout(
            connect=settings.http_connect_timeout_seconds,
            read=settings.http_read_timeout_seconds,
            write=settings.http_write_timeout_seconds,
            pool=settings.http_timeout_seconds,
        )
        self.max_retries = max(0, settings.http_max_retries)

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                return await client.get(url)
            except Exception as e:
                last_exc = e
                logger.warning(f"GET {url} gagal (attempt {attempt+1}/{self.max_retries+1}): {e}")
        if last_exc:
            raise last_exc

    async def ping_any(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, http2=_http2()) as client:
                for host in self.hosts:
                    url = f"{host}/api/v3/ping"
                    start = time.perf_counter()
                    try:
                        resp = await self._get(client, url)
                        latency_ms = round((time.perf_counter() - start) * 1000, 2)
                        if resp.status_code == 200:
                            return {"ok": True, "host": host, "status_code": resp.status_code,
                                    "latency_ms": latency_ms, "msg": "pong"}
                    except Exception as e:
                        logger.error(f"[FAIL] {host} error={e}")
        except Exception as e:
            return {"ok": False, "msg": f"client_error: {e.__class__.__name__}: {e}"}
        return {"ok": False, "msg": "all hosts timeout or failed", "hosts_tried": self.hosts}

    async def simple_get(self, path: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, http2=_http2()) as client:
            for host in self.hosts:
                try:
                    resp = await client.get(f"{host}{path}")
                    if resp.status_code == 200:
                        return {"ok": True, "data": resp.json()}
                except Exception as e:
                    logger.warning(f"{host}{path} failed: {e}")
        return {"ok": False, "msg": f"failed to fetch {path}"}

    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> Dict[str, Any]:
        path = f"/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
        return await self.simple_get(path)

    async def get_depth(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        path = f"/api/v3/depth?symbol={symbol.upper()}&limit={limit}"
        return await self.simple_get(path)

    async def get_book_ticker(self, symbol: str) -> Dict[str, Any]:
        path = f"/api/v3/ticker/bookTicker?symbol={symbol.upper()}"
        return await self.simple_get(path)

    async def get_avg_price(self, symbol: str) -> Dict[str, Any]:
        path = f"/api/v3/avgPrice?symbol={symbol.upper()}"
        return await self.simple_get(path)

binance_http = BinanceHTTP()
