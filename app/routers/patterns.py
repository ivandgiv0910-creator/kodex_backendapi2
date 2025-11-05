# app/routers/patterns.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import httpx, asyncio, math, statistics, time

router = APIRouter(prefix="/patterns", tags=["patterns"])

# --- sumber data (mirror untuk hindari 451) ---
BINANCE_BASE = "https://api4.binance.com"
TIMEOUT = 8.0
MAX_LIMIT = 1000
SUPPORTED_TF = {"1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d"}

# ---- util dasar ----
def _atr(rows: List[Dict[str, float]], period: int = 14) -> float:
    if len(rows) < period + 1: return 0.0
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i-1]["close"]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    if len(trs) < period: return 0.0
    return statistics.fmean(trs[-period:])

def _sma(vals: List[float], p: int) -> float:
    if len(vals) < p: return float("nan")
    return statistics.fmean(vals[-p:])

def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1: return float("nan")
    gains, losses = [], []
    for i in range(1, len(closes)):
        chg = closes[i] - closes[i-1]
        gains.append(max(chg, 0.0))
        losses.append(abs(min(chg, 0.0)))
    ag, al = _sma(gains, period), _sma(losses, period)
    if math.isnan(ag) or math.isnan(al) or al == 0: return 100.0
    rs = ag / al
    return 100.0 - 100.0/(1.0 + rs)

async def _fetch_klines(symbol: str, tf: str, limit: int) -> List[Dict[str, Any]]:
    if tf not in SUPPORTED_TF: raise HTTPException(400, f"Unsupported timeframe {tf}")
    limit = min(MAX_LIMIT, max(50, int(limit or 300)))
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": tf, "limit": limit}
    last_err = None
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                r = await client.get(url, params=params, timeout=TIMEOUT)
                if r.status_code == 451:
                    raise HTTPException(451, "Binance regional restriction (HTTP 451)")
                if r.status_code == 429:
                    await asyncio.sleep(0.5*(attempt+1)); continue
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list): raise HTTPException(502, "Unexpected upstream response")
                out = []
                for k in data:
                    out.append({
                        "open_time": int(k[0]),
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]),  "close": float(k[4]),
                        "volume": float(k[5]), "close_time": int(k[6])
                    })
                return out
            except HTTPException:
                raise
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.3*(attempt+1))
    raise HTTPException(502, f"Upstream error: {repr(last_err)}")

# ---- candlestick pattern (single candle) ----
def _candle_pattern(rows: List[Dict[str, float]]) -> str:
    if not rows: return "neutral"
    c = rows[-1]; body = abs(c["close"]-c["open"]); rng=c["high"]-c["low"]
    if rng <= 0: return "neutral"
    upper = c["high"] - max(c["close"], c["open"])
    lower = min(c["close"], c["open"]) - c["low"]
    small = body <= rng*0.1
    if small: return "Doji (indecision)"
    if lower >= rng*0.5 and upper <= rng*0.2: return "Hammer (bullish reversal)"
    if upper >= rng*0.5 and lower <= rng*0.2: return "Shooting Star (bearish reversal)"
    if len(rows) >= 2:
        p = rows[-2]
        bull_engulf = c["close"]>c["open"] and p["close"]<p["open"] and c["close"]>=p["open"] and c["open"]<=p["close"]
        bear_engulf = c["close"]<c["open"] and p["close"]>p["open"] and c["open"]>=p["close"] and c["close"]<=p["open"]
        if bull_engulf: return "Bullish Engulfing"
        if bear_engulf: return "Bearish Engulfing"
        inside = c["high"]<=p["high"] and c["low"]>=p["low"]
        if inside: return "Inside Bar (continuation)"
    return "neutral"

# ---- zigzag (swing) ----
def _zigzag(rows: List[Dict[str, float]], atr_mult: float = 1.5) -> List[Dict[str, Any]]:
    if len(rows) < 20: return []
    atr14 = _atr(rows, 14)
    if atr14 <= 0: return []
    thr = atr14 * atr_mult
    piv = []
    direction = 0  # 1 up, -1 down
    last_p = rows[0]["close"]
    last_i = 0
    for i in range(1, len(rows)):
        d = rows[i]["close"] - last_p
        if direction >= 0 and d >= thr:
            piv.append({"type":"low","idx":last_i,"price":rows[last_i]["low"]})
            direction = -1
            last_p = rows[i]["close"]; last_i = i
        elif direction <= 0 and -d >= thr:
            piv.append({"type":"high","idx":last_i,"price":rows[last_i]["high"]})
            direction = 1
            last_p = rows[i]["close"]; last_i = i
        else:
            if rows[i]["low"] < rows[last_i]["low"] and direction <= 0:
                last_i = i
            if rows[i]["high"] > rows[last_i]["high"] and direction >= 0:
                last_i = i
    # add final
    piv = sorted(piv, key=lambda x: x["idx"])
    return piv[-12:]  # keep recent

# ---- helper: near (±pct) ----
def _near(a: float, b: float, pct: float = 0.02) -> bool:
    if b == 0: return False
    return abs(a-b)/abs(b) <= pct

# ---- structural pattern detectors ----
def _detect_double_triple(piv: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    if len(piv) < 5: return None
    highs = [p for p in piv if p["type"]=="high"]
    lows  = [p for p in piv if p["type"]=="low"]
    # Double Top
    if len(highs) >= 2 and _near(highs[-1]["price"], highs[-2]["price"], 0.02):
        neck = lows[-1]["price"] if lows else None
        return {"name":"Double Top","direction":"bearish","neckline":neck,"points":[highs[-2], highs[-1]],"confidence":0.7}
    # Double Bottom
    if len(lows) >= 2 and _near(lows[-1]["price"], lows[-2]["price"], 0.02):
        neck = highs[-1]["price"] if highs else None
        return {"name":"Double Bottom","direction":"bullish","neckline":neck,"points":[lows[-2], lows[-1]],"confidence":0.7}
    # Triple Top
    if len(highs) >= 3 and _near(highs[-1]["price"], highs[-2]["price"]) and _near(highs[-2]["price"], highs[-3]["price"]):
        neck = lows[-1]["price"] if lows else None
        return {"name":"Triple Top","direction":"bearish","neckline":neck,"points":highs[-3:],"confidence":0.75}
    # Triple Bottom
    if len(lows) >= 3 and _near(lows[-1]["price"], lows[-2]["price"]) and _near(lows[-2]["price"], lows[-3]["price"]):
        neck = highs[-1]["price"] if highs else None
        return {"name":"Triple Bottom","direction":"bullish","neckline":neck,"points":lows[-3:],"confidence":0.75}
    return None

def _detect_hs(piv: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    # Head & Shoulders: high, higher-high (head), lower-high ; neckline by connecting lows between them
    highs = [p for p in piv if p["type"]=="high"]
    lows  = [p for p in piv if p["type"]=="low"]
    if len(highs) < 3 or len(lows) < 2: return None
    L, M, R = highs[-3], highs[-2], highs[-1]
    if M["price"] > L["price"] and M["price"] > R["price"] and _near(L["price"], R["price"], 0.05):
        neck = (lows[-1]["price"] + lows[-2]["price"]) / 2.0
        return {"name":"Head & Shoulders","direction":"bearish","neckline":neck,"points":[L,M,R],"confidence":0.8}
    # Inverse
    lows3 = lows[-3:] if len(lows) >= 3 else []
    highs2 = highs[-2:] if len(highs) >= 2 else []
    if len(lows3)==3 and len(highs2)>=1:
        L2,M2,R2 = lows3[0], lows3[1], lows3[2]
        if M2["price"] < L2["price"] and M2["price"] < R2["price"] and _near(L2["price"], R2["price"], 0.05):
            neck = sum([h["price"] for h in highs2])/len(highs2)
            return {"name":"Inverse Head & Shoulders","direction":"bullish","neckline":neck,"points":[L2,M2,R2],"confidence":0.8}
    return None

def _detect_rectangle_triangle(piv: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    if len(piv) < 6: return None
    highs = [p["price"] for p in piv if p["type"]=="high"]
    lows  = [p["price"] for p in piv if p["type"]=="low"]
    if len(highs)>=3 and len(lows)>=3:
        # rectangle: highs ~ flat & lows ~ flat
        if max(highs[-3:]) - min(highs[-3:]) <= statistics.fmean(highs[-3:]) * 0.01 and \
           max(lows[-3:]) - min(lows[-3:]) <= statistics.fmean(lows[-3:])  * 0.01:
            return {"name":"Rectangle (Range)","direction":"neutral","neckline": None,"points":piv[-6:],"confidence":0.65}
        # triangles (rough)
        if highs[-1] < highs[-2] < highs[-3] and lows[-1] > lows[-2] > lows[-3]:
            return {"name":"Symmetrical Triangle","direction":"breakout","neckline": None,"points":piv[-6:],"confidence":0.7}
        if highs[-1] < highs[-2] < highs[-3] and _near(lows[-1], statistics.fmean(lows[-3:]), 0.01):
            return {"name":"Descending Triangle","direction":"bearish","neckline": statistics.fmean(lows[-3:]),"points":piv[-6:],"confidence":0.72}
        if lows[-1] > lows[-2] > lows[-3] and _near(highs[-1], statistics.fmean(highs[-3:]), 0.01):
            return {"name":"Ascending Triangle","direction":"bullish","neckline": statistics.fmean(highs[-3:]),"points":piv[-6:],"confidence":0.72}
    return None

def _detect_flag_pennant(rows: List[Dict[str,float]]) -> Optional[Dict[str,Any]]:
    # deteksi sederhana: impuls (±2x ATR) lalu konsolidasi miring <= 1/2 panjang impuls
    if len(rows) < 60: return None
    atr14 = _atr(rows, 14)
    closes = [r["close"] for r in rows]
    # impuls terakhir ~ 30 bar
    cA, cB = closes[-50], closes[-30]
    move = abs(cB - cA)
    if move < atr14*2: return None
    # konsolidasi 30→now: rentang kecil
    seg = rows[-30:]
    rng = max(r["high"] for r in seg) - min(r["low"] for r in seg)
    if rng <= move*0.5:
        dirn = "bullish" if cB>cA else "bearish"
        name = "Flag"  # Pennant butuh cek konvergen; cukup Flag dulu
        return {"name":f"{name} ({dirn} continuation)","direction":dirn,"neckline":None,"points":[], "confidence":0.68}
    return None

def _build_plan(rows: List[Dict[str,float]], pattern: Optional[Dict[str,Any]]) -> Dict[str,Any]:
    atr14 = _atr(rows, 14)
    px = rows[-1]["close"]
    if not pattern:
        # generic plan
        return {
            "long":  {"entry": round(px-0.2*atr14,2), "sl": round(px-1.0*atr14,2), "tp1": round(px+0.8*atr14,2), "tp2": round(px+1.6*atr14,2)},
            "short": {"entry": round(px+0.2*atr14,2), "sl": round(px+1.0*atr14,2), "tp1": round(px-0.8*atr14,2), "tp2": round(px-1.6*atr14,2)},
        }
    # pattern-based
    neck = pattern.get("neckline", px)
    dirn = pattern.get("direction", "neutral")
    if dirn == "bullish":
        return {
            "long":  {"entry": round((neck or px)+0.3*atr14,2), "sl": round(px-1.0*atr14,2), "tp1": round(px+0.8*atr14,2), "tp2": round(px+1.6*atr14,2)},
            "short": {"entry": round(px+0.4*atr14,2),          "sl": round((neck or px)+1.0*atr14,2), "tp1": round(px-0.8*atr14,2), "tp2": round(px-1.6*atr14,2)},
        }
    if dirn == "bearish":
        return {
            "long":  {"entry": round(px-0.4*atr14,2),          "sl": round((neck or px)-1.0*atr14,2), "tp1": round(px+0.8*atr14,2), "tp2": round(px+1.6*atr14,2)},
            "short": {"entry": round((neck or px)-0.3*atr14,2), "sl": round(px+1.0*atr14,2), "tp1": round(px-0.8*atr14,2), "tp2": round(px-1.6*atr14,2)},
        }
    # neutral/breakout
    return {
        "long":  {"entry": round(px+0.2*atr14,2), "sl": round(px-1.0*atr14,2), "tp1": round(px+0.8*atr14,2), "tp2": round(px+1.6*atr14,2)},
        "short": {"entry": round(px-0.2*atr14,2), "sl": round(px+1.0*atr14,2), "tp1": round(px-0.8*atr14,2), "tp2": round(px-1.6*atr14,2)},
    }

def _stage(rows: List[Dict[str,float]], pattern: Optional[Dict[str,Any]]) -> str:
    if not pattern: return "none"
    px = rows[-1]["close"]
    neck = pattern.get("neckline")
    if neck is None: return "in-progress"
    # breakout / retest / below
    if pattern["direction"] == "bullish":
        if px > neck*1.003: return "breakout/above-neckline"
        if abs(px-neck)/neck <= 0.003: return "retest-neckline"
        return "pre-breakout"
    if pattern["direction"] == "bearish":
        if px < neck*0.997: return "breakdown/below-neckline"
        if abs(px-neck)/neck <= 0.003: return "retest-neckline"
        return "pre-breakdown"
    return "in-progress"

def _rsi_divergence(rows: List[Dict[str,float]]) -> Optional[str]:
    if len(rows) < 30: return None
    closes = [r["close"] for r in rows]
    rsis = []
    for i in range(10, len(closes)):
        rsis.append(_rsi(closes[:i], 14))
    if len(rsis) < 5: return None
    # very simple: lower low price but higher low RSI (bullish div)
    pA, pB = closes[-10], closes[-1]
    rA, rB = rsis[-10], rsis[-1]
    if pB < pA and rB > rA: return "Bullish RSI divergence"
    if pB > pA and rB < rA: return "Bearish RSI divergence"
    return None

@router.get("/{symbol}/{timeframe}")
async def analyze_patterns(
    symbol: str,
    timeframe: str,
    limit: Optional[int] = Query(300, description=f"Bars, max {MAX_LIMIT}")
) -> Dict[str, Any]:
    rows = await _fetch_klines(symbol, timeframe, limit or 300)
    if not rows: raise HTTPException(502, "No data")

    # pre-metrics
    atr14 = _atr(rows, 14)
    closes = [r["close"] for r in rows]
    vols   = [r.get("volume",0.0) for r in rows]
    vol_surge = len(vols)>=14 and vols[-1] > 1.8 * _sma(vols, 14)
    atr_spike = atr14 > 1.5 * _sma([max(r["high"]-r["low"], 1e-9) for r in rows], 20)

    # candlestick pattern
    candle_pat = _candle_pattern(rows)

    # swing & structural
    piv = _zigzag(rows, atr_mult=1.5)
    major = _detect_hs(piv) or _detect_double_triple(piv) or _detect_rectangle_triangle(piv) or _detect_flag_pennant(rows)
    stage = _stage(rows, major)
    plan  = _build_plan(rows, major)
    rsi_div = _rsi_divergence(rows)

    # trend & momentum (sederhana)
    ema20 = _sma(closes, 20); ema50 = _sma(closes, 50)
    trend = "bullish" if ema20 > ema50 else ("bearish" if ema20 < ema50 else "sideway")
    momentum = "strong" if abs(closes[-1]-closes[-6]) > atr14*0.6 else ("moderate" if abs(closes[-1]-closes[-6]) > atr14*0.2 else "weak")

    resp = {
        "symbol": symbol.upper(), "timeframe": timeframe,
        "bars": len(rows), "atr14": round(atr14, 6),
        "trend": trend, "momentum": momentum,
        "candlestickPattern": candle_pat,
        "majorPattern": major or None,
        "stage": stage,
        "confirmations": {
            "volumeSurge": bool(vol_surge),
            "atrSpike": bool(atr_spike),
            "rsiDivergence": rsi_div or None
        },
        "plan": plan,
        "levels": {
            "last_close": rows[-1]["close"],
            "recent_high": max(r["high"] for r in rows[-30:]),
            "recent_low":  min(r["low"]  for r in rows[-30:])
        },
        "generated_at": int(time.time()*1000)
    }
    return resp
