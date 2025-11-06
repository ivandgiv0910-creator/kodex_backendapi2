import asyncio
from fastapi import FastAPI

# ==========================
# Import router yang SUDAH ADA
# ==========================
from app.routers import (
    ai_adapter,
    market,
    marketdata,
    patterns,
    signals
    from app.routers.routes_alias import alias as alias_router




)

# ==========================
# Import router & worker baru (Telegram)
# ==========================
from app.routers import telegram_webhook, telegram_api
from app.services.telegram.worker import volume_loop


# ==========================
# Inisialisasi FastAPI
# ==========================
app = FastAPI(title="Kodex BackendAPI v2")


# ==========================
# Include semua router lama (TETAP)
# ==========================
app.include_router(ai_adapter.router)
app.include_router(market.router)
app.include_router(marketdata.router)
app.include_router(patterns.router)
app.include_router(signals.router)
app.include_router(alias_router, prefix="")

# ==========================
# Include router Telegram baru
# ==========================
app.include_router(telegram_webhook.router)
app.include_router(telegram_api.router)


# ==========================
# Event startup — jalankan background worker volume spike
# ==========================
@app.on_event("startup")
async def _startup():
    # Worker volume loop berjalan di background tanpa mengganggu request utama
    asyncio.create_task(volume_loop())
    print("[startup] Kodex BackendAPI v2 aktif — Telegram worker dimulai ✅")


# ==========================
# Root endpoint (health check)
# ==========================
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "kodex_backendapi2",
        "message": "Service aktif dan siap menerima webhook Telegram 🚀"
    }
