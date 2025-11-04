# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.routers.market import router as market_router
from app.routers.ai_adapter import router as ai_router

APP_TITLE = "Kode X Backend API"
APP_VERSION = "2.1"

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# --- CORS ---
origins = (
    ["*"]
    if settings.cors_allow_origins == "*"
    else [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(market_router, prefix="/market", tags=["market"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])

# --- Basic health & convenience routes ---
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/healthz", tags=["system"])
def healthz():
    return {"ok": True, "app": APP_TITLE, "version": APP_VERSION, "env": settings.app_env}

@app.get("/version", tags=["system"])
def version():
    return {"version": APP_VERSION}

@app.get("/config", tags=["system"], include_in_schema=False)
def config_preview():
    # Hanya untuk debug lokal. Jangan expose di production jika sensitif.
    return JSONResponse(
        {
            "env": settings.app_env,
            "port": settings.app_port,
            "cors_allow_origins": settings.cors_allow_origins,
            "http": {
                "timeout_seconds": settings.http_timeout_seconds,
                "connect_timeout": settings.http_connect_timeout_seconds,
                "read_timeout": settings.http_read_timeout_seconds,
                "write_timeout": settings.http_write_timeout_seconds,
                "max_retries": settings.http_max_retries,
                "http2_enabled": getattr(settings, "http2_enabled", False),
            },
            "binance_hosts_count": len(settings.binance_hosts),
        }
    )
