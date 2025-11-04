from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from loguru import logger
import os
import time
import httpx

# =========================
# Config & Security
# =========================
class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    API_TOKEN: str | None = None   # token internal untuk proteksi endpoint (optional)
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "gpt-4o-mini"   # default model OpenAI
    REQUEST_TIMEOUT: int = 60

settings = Settings()

app = FastAPI(title="kodex_backendapi2", version="1.0.0")

# CORS (atur origin sesuai kebutuhan UI kamu)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti dengan domain kamu kalau mau lebih ketat
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Schemas
# =========================
class AIMessage(BaseModel):
    role: str = Field(pattern="^(user|system|assistant)$")
    content: str

class AIRequest(BaseModel):
    messages: list[AIMessage]
    model: str | None = None
    temperature: float | None = 0.3
    max_tokens: int | None = 750

class AIResponse(BaseModel):
    model: str
    content: str
    usage: dict | None = None
    latency_ms: int

class AnalyzeInput(BaseModel):
    pair: str
    timeframe: str = "15m"
    context: dict | None = None

class AnalyzeResult(BaseModel):
    pair: str
    timeframe: str
    verdict: str
    entry: dict
    stops: dict
    targets: list[dict]
    notes: list[str]
    latency_ms: int

# =========================
# Helpers
# =========================
def ensure_auth(x_api_key: str | None):
    if settings.API_TOKEN:
        if not x_api_key or x_api_key != settings.API_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")
    # jika API_TOKEN tidak diset, endpoint terbuka (untuk dev)

def openai_headers():
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

# =========================
# Health & Meta
# =========================
@app.get("/")
def root():
    return {"status": "ok", "service": "kodex_backendapi2"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/version")
def version():
    return {"version": app.version, "model_default": settings.DEFAULT_MODEL}

# =========================
# AI Relay Endpoint
# =========================
@app.post("/ai", response_model=AIResponse)
async def ai_chat(req: AIRequest, request: Request, x_api_key: str | None = Header(default=None)):
    """
    Relay sederhana ke OpenAI Chat Completions (non-stream).
    Proteksi optional via header: X-API-KEY: <token>
    """
    ensure_auth(x_api_key)
    start = time.perf_counter()

    model = req.model or settings.DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in req.messages],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            r = await client.post(
                f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers=openai_headers(),
                json=payload,
            )
        r.raise_for_status()
        data = r.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"/ai ok model={model} latency={latency_ms}ms")

        return AIResponse(model=model, content=content, usage=usage, latency_ms=latency_ms)

    except httpx.HTTPStatusError as e:
        logger.error(f"/ai HTTP {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.exception("/ai error")
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Analyze Endpoint (kerangka awal — bisa kamu isi logic Kode X/Kode 4)
# =========================
@app.post("/analyze", response_model=AnalyzeResult)
async def analyze(inp: AnalyzeInput, x_api_key: str | None = Header(default=None)):
    """
    Kerangka analisis: taruh logic strategi kamu di sini (orderflow, OI, ATR, dll).
    Saat ini masih contoh dummy yang rapi agar bisa langsung dipakai & dihubungkan ke GPT.
    """
    ensure_auth(x_api_key)
    start = time.perf_counter()

    # --- Contoh placeholder (ganti dengan logika kamu) ---
    verdict = "wait-and-see"
    entry = {"type": "limit", "side": "long", "price": None}
    stops = {"sl": None, "ts": None}
    targets = [{"tp": None, "rr": None}]
    notes = [
        "Baseline belum konvergen; tunggu retrace ringan ke area value.",
        "Gunakan ukuran posisi konservatif; spread & volatilitas cek dulu.",
    ]
    # ------------------------------------------------------

    latency_ms = int((time.perf_counter() - start) * 1000)
    return AnalyzeResult(
        pair=inp.pair,
        timeframe=inp.timeframe,
        verdict=verdict,
        entry=entry,
        stops=stops,
        targets=targets,
        notes=notes,
        latency_ms=latency_ms,
    )

# =========================
# Local run (optional)
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
