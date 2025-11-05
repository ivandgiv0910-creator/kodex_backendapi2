# app/main.py
from fastapi import FastAPI

app = FastAPI(title="Kode X Backend API v2.1")

# Root check
@app.get("/")
def root():
    return {"ok": True, "service": "kodex_backendapi2", "version": "2.1"}

# === Include routers dengan import aman (tanpa ganggu modul lain) ===
def _safe_include(import_path: str, attr: str = "router"):
    """
    Import router secara aman.
    Kalau modul belum ada / sementara bermasalah, app tetap jalan.
    """
    try:
        mod = __import__(import_path, fromlist=[attr])
        router = getattr(mod, attr, None)
        if router:
            app.include_router(router)
            return True
    except Exception:
        # Biar silent: kita tidak ingin produksi crash hanya karena 1 router gagal import
        return False
    return False

# Router yang sudah ada di projectmu:
_safe_include("app.routers.marketdata", "router")         # (baru) Market Data
_safe_include("app.routers.signals", "router")            # Endpoint /signals
_safe_include("app.routers.telegram_webhook", "router")   # Webhook Telegram
_safe_include("app.routers.market", "router")             # (kalau ada)
_safe_include("app.routers.ai_adapter", "router")         # (kalau ada)
