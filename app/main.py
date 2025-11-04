from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from loguru import logger
import os, time, math
import httpx
from typing import List, Optional


# =========================
# Config
# =========================
class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    API_TOKEN: Optional[str] = None            # proteksi endpoint
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    REQUEST_TIMEOUT: int = 60

settings = Settings()

app = FastAPI(title="kodex_backendapi2", version="1.0.0")

# CORS (boleh dipersempit nanti)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    messages: List[AIMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 750

class AIResponse(BaseModel):
    model: str
    content: str
    usage: Optional[dict] = None
    latency_ms: int

# ---- Analyze payloads ----
class OHLC(BaseModel):
    high: List[float] = []
    low: List[float] = []
    close: List[float] = []

class AnalyzeInput(BaseModel):
    pair: str
    timeframe: str = "15m"
    capital: Optional[float] = 100.0
    risk_pct: Optional[float] = 1.0
    side_preference: Optional[str] = Field(default=None, description="long|short|none")
    ohlc: Optional[OHLC] = None
    context: Optional[dict] = None

class AnalyzeResult(BaseModel):
    pair: str
    timeframe: str
    verdict: str
    confidence: float
    entry: dict
    stops: dict
    targets: List[dict]
    sizing: dict
    blocks: dict
    notes: List[str]
    latency_ms: int

# =========================
# Helpers
# =========================
def ensure_auth(x_api_key: Optional[str]):
    """Require X-API-KEY if API_TOKEN is set."""
    if settings.API_TOKEN:
        if not x_api_key or x_api_key != settings.API_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

def openai_headers():
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

def sma(arr: List[float], n: int) -> float:
    if not arr or len(arr) < n:
        return sum(arr) / max(len(arr), 1)
    return sum(arr[-n:]) / n

def atr(ohlc: OHLC, n: int = 14) -> Optional[float]:
    """ATR sederhana tanpa dependensi eksternal."""
    if not ohlc or not ohlc.high or not ohlc.low or not ohlc.close:
        return None
    H, L, C = ohlc.high, ohlc.low, ohlc.close
    m = min(len(H), len(L), len(C))
    if m < 2:
        return None
    trs = []
    for i in range(1, m):
        tr = max(H[i] - L[i], abs(H[i] - C[i-1]), abs(L[i] - C[i-1]))
        trs.append(tr)
    if len(trs) < 1:
        return None
    n = min(n, len(trs))
    return sum(trs[-n:]) / n

def momentum_score(closes: List[float], lookback: int = 20) -> float:
    """Skor momentum sederhana: slope vs noise (0..1)."""
    if not closes or len(closes) < 3:
        return 0.5
    lookback = min(lookback, len(closes))
    window = closes[-lookback:]
    # slope ~ difference between last and first
    slope = window[-1] - window[0]
    avg_range = (max(window) - min(window)) or 1e-9
    score = 0.5 + 0.5 * (slope / avg_range)
    return max(0.0, min(1.0, score))

def rr_targets(entry: float, sl: float, side: str, rr_list=(1.0, 1.5, 2.0)):
    tps = []
    for rr in rr_list:
        if side == "long":
            tp = entry + rr * (entry - sl)
        else:
            tp = entry - rr * (sl - entry)
        tps.append({"tp": round(tp, 2), "rr": rr})
    return tps

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
# /ai : OpenAI relay (non-stream)
# =========================
@app.post("/ai", response_model=AIResponse)
async def ai_chat(req: AIRequest, request: Request, x_api_key: Optional[str] = Header(default=None)):
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
# /analyze : Kerangka KODE 4
# =========================
@app.post("/analyze", response_model=AnalyzeResult)
async def analyze(inp: AnalyzeInput, x_api_key: Optional[str] = Header(default=None)):
    """
    KODE 4 – ringkas:
    - microstructure: momentum, bias side
    - volatility: ATR, jarak SL/TP
    - risk: position sizing dari risk_pct
    - execution: jenis order & trigger
    """
    ensure_auth(x_api_key)
    t0 = time.perf_counter()

    closes = inp.ohlc.close if inp.ohlc and inp.ohlc.close else []
    last_price = closes[-1] if closes else None

    # 1) Momentum & Bias
    mom = momentum_score(closes, lookback=20) if closes else 0.5
    bias = "long" if mom >= 0.55 else ("short" if mom <= 0.45 else "neutral")

    # honor side_preference
    if inp.side_preference in ("long", "short"):
        bias = inp.side_preference

    # 2) Volatility
    _atr = atr(inp.ohlc, n=14) if inp.ohlc else None
    # fallback ATR jika tidak ada data: gunakan placeholder 0.5% dari harga
    if _atr is None:
        if last_price:
            _atr = 0.005 * last_price
        else:
            _atr = 1.0

    # 3) Entry, SL, TP (pakai ATR multiple)
    if not last_price:
        # jika tidak ada harga, pakai 100 sebagai dummy agar struktur jalan
        last_price = 100.0

    if bias == "long":
        entry_price = last_price  # bisa diganti limit-retrace di phase berikut
        sl = entry_price - 1.2 * _atr
        tps = rr_targets(entry_price, sl, "long", rr_list=(1.0, 1.5, 2.0))
    elif bias == "short":
        entry_price = last_price
        sl = entry_price + 1.2 * _atr
        tps = rr_targets(entry_price, sl, "short", rr_list=(1.0, 1.5, 2.0))
    else:
        # neutral → wait & see
        entry_price = last_price
        sl = None
        tps = []

    # 4) Sizing (risk-based)
    capital = max(0.0, float(inp.capital or 100.0))
    risk_pct = max(0.1, float(inp.risk_pct or 1.0))  # minimal 0.1%
    risk_amt = capital * (risk_pct / 100.0)
    pip = abs(entry_price - sl) if sl is not None else None
    qty = (risk_amt / pip) if pip and pip > 0 else 0.0

    # 5) Verdict & Confidence
    if bias == "neutral":
        verdict = "wait-and-see"
        confidence = 0.45
    else:
        verdict = f"bias-{bias}"
        # confidence gabungan: momentum + (ATR normalisasi kecil)
        conf_mom = mom
        conf_vol = max(0.0, min(1.0, 1 - ( _atr / max(1e-9, last_price * 0.03) )))  # lebih kecil atr → lebih yakin
        confidence = round(0.6*conf_mom + 0.4*conf_vol, 2)

    # 6) Blocks laporan (meniru struktur Kode 4)
    blocks = {
        "microstructure": {
            "momentum_score": round(mom, 2),
            "bias": bias,
        },
        "volatility": {
            "atr14": round(_atr, 2),
        },
        "risk": {
            "capital": capital,
            "risk_pct": risk_pct,
            "risk_amount": round(risk_amt, 2),
        },
        "execution": {
            "order_type": "limit-if-retrace" if bias != "neutral" else "-",
            "trigger_hint": "konfirmasi pullback ringan & rejection satu candle",
        },
        "context": inp.context or {},
    }

    notes = []
    if bias == "neutral":
        notes.append("Baseline belum konvergen; tunggu struktur lebih jelas.")
    else:
        notes.append("Masuk di retrace, hindari entry di puncak candle.")
        notes.append("Gunakan ukuran posisi konservatif di fase awal.")

    latency_ms = int((time.perf_counter() - t0) * 1000)

    return AnalyzeResult(
        pair=inp.pair,
        timeframe=inp.timeframe,
        verdict=verdict,
        confidence=confidence,
        entry={"price": round(entry_price, 2), "side": bias if bias != "neutral" else None},
        stops={"sl": round(sl, 2) if sl else None, "trail": None},
        targets=tps,
        sizing={
            "qty": round(qty, 4),
            "risk_amount": round(risk_amt, 2),
            "pip_distance": round(pip, 4) if pip else None
        },
        blocks=blocks,
        notes=notes,
        latency_ms=latency_ms,
    )


# =========================
# Local run
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
