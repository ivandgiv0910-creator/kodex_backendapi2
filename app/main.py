# app/main.py
from fastapi import FastAPI

app = FastAPI(title="Kode X Backend API v2.1")

# Root check
@app.get("/")
def root():
    return {"ok": True, "service": "kodex_backendapi2", "version": "2.1"}

# === Include routers dengan import aman (tanpa ganggu modul lain) ===
# ... import & init FastAPI yang sudah ada

def _safe_include(path: str, attr: str):
    try:
        mod = __import__(path, fromlist=[attr])
        app.include_router(getattr(mod, attr))
    except Exception as e:
        print(f"[WARN] Failed to include {path}: {e}")

# routers lain yang sudah ada
_safe_include("app.routers.marketdata", "router")
_safe_include("app.routers.signals", "router")
_safe_include("app.routers.telegram_webhook", "router")
_safe_include("app.routers.market", "router")
_safe_include("app.routers.ai_adapter", "router")

# ✅ tambahkan baris ini
_safe_include("app.routers.patterns", "router")
