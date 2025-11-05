from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Routers
from app.routers.signals import router as signals_router
from app.routers.telegram_webhook import router as telegram_router
from fastapi import FastAPI
from marketdata import router as marketdata_router

# (opsional) kalau kamu sudah buat subs:
try:
    from app.routers.subscriptions import router as subs_router
    HAS_SUBS = True
except Exception:
    HAS_SUBS = False

app = FastAPI(title="KodeX Backend", version="1.0.0")
app = FastAPI(title="Kode X Backend API v2.1")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ MOUNT ROUTERS
app.include_router(signals_router)
app.include_router(telegram_router)
app.include_router(marketdata_router) 
if HAS_SUBS:
    app.include_router(subs_router)

@app.get("/")
def root():
    return {
        "app": "KodeX Backend",
        "env": os.environ.get("ENV", "production"),
        "telegram_default_push": os.environ.get("PUSH_TELEGRAM_DEFAULT", "false").lower() in ("1","true","yes","on")
    }

@app.get("/health")
def health():
    return {"ok": True}
