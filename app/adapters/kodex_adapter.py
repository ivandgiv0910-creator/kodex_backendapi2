from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math, statistics

# ---------- util indikator sederhana ----------
def sma(arr: List[float], n: int) -> Optional[float]:
    if len(arr) < n: return None
    return sum(arr[-n:]) / n

def ema(arr: List[float], n: int) -> Optional[float]:
    if len(arr) < n: return None
    k = 2 / (n + 1)
    e = sum(arr[:n]) / n
    for v in arr[n:]:
        e = v * k + e * (1 - k)
    return e

def rsi(arr: List[float], n: int = 14) -> Optional[float]:
    if len(arr) < n + 1: return None
    gains, losses = [], []
    for i in range(-n, 0):
        ch = arr[i] - arr[i-1]
        gains.append(max(0, ch))
        losses.append(max(0, -ch))
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def true_range(h: float, l: float, pc: float) -> float:
    return max(h - l, abs(h - pc), abs(l - pc))

def atr(ohlc: List[List[float]], n: int = 14) -> Optional[float]:
    if len(ohlc) < n + 1: return None
    trs = []
    for i in range(-n, 0):
        h, l, c_prev = ohlc[i][1], ohlc[i][2], ohlc[i-1][3]
        trs.append(true_range(h, l, c_prev))
    return sum(trs) / n

# ---------- adapter utama ----------
@dataclass
class SignalConfig:
    atr_mult_sl: float = 1.8
    atr_mult_tp1: float = 1.2
    atr_mult_tp2: float = 2.4
    min_pad_pct: float = 0.001  # 0.1% jaga jarak min

class KodexAdapter:
    def __init__(self, closes: List[float], highs: List[float], lows: List[float]):
        self.closes = closes
        self.highs = highs
        self.lows = lows
        self.ohlc = [[None, h, l, c] for h, l, c in zip(highs, lows, closes)]

    def analyze(self) -> Dict[str, Any]:
        last = self.closes[-1]
        sma20 = sma(self.closes, 20)
        sma50 = sma(self.closes, 50)
        ema21 = ema(self.closes, 21)
        rsi14 = rsi(self.closes, 14)
        atr14 = atr(self.ohlc, 14)

        bias = "neutral"
        if sma20 and last > sma20: bias = "bullish"
        if sma20 and last < sma20: bias = "bearish"

        cross = None
        if sma20 and sma50:
            cross = "golden" if sma20 > sma50 else "death"

        vol = statistics.pstdev(self.closes[-20:]) if len(self.closes) >= 20 else 0.0

        # confidence sederhana: alignment indikator
        score = 0
        if bias == "bullish": score += 1
        if cross == "golden": score += 1
        if ema21 and last > ema21: score += 1
        if rsi14 and 50 < rsi14 < 75: score += 1
        if atr14: score += 1
        confidence = round(min(0.2 * score, 0.95), 2)  # 0..0.95

        return {
            "last": last,
            "sma20": sma20, "sma50": sma50, "ema21": ema21,
            "rsi14": rsi14, "atr14": atr14, "vol_sigma": vol,
            "bias": bias, "crossover": cross, "confidence": confidence,
        }

    def build_setup(self, cfg: SignalConfig = SignalConfig()) -> Dict[str, Any]:
        info = self.analyze()
        price = info["last"]
        a = info["atr14"] or (price * cfg.min_pad_pct)
        pad = max(a, price * cfg.min_pad_pct)

        if info["bias"] == "bullish":
            sl = round(price - cfg.atr_mult_sl * pad, 2)
            tp1 = round(price + cfg.atr_mult_tp1 * pad, 2)
            tp2 = round(price + cfg.atr_mult_tp2 * pad, 2)
            side = "LONG"
            entry = {"type": "limit-pullback", "note": "buy minor dip above EMA21" }
        elif info["bias"] == "bearish":
            sl = round(price + cfg.atr_mult_sl * pad, 2)
            tp1 = round(price - cfg.atr_mult_tp1 * pad, 2)
            tp2 = round(price - cfg.atr_mult_tp2 * pad, 2)
            side = "SHORT"
            entry = {"type": "limit-bounce", "note": "sell minor bounce below EMA21" }
        else:
            return {
                "ok": True,
                "side": "WAIT",
                "reason": "No edge vs SMA20",
                "analytics": info
            }

        rr1 = round(abs(tp1 - price) / abs(price - sl), 2) if price != sl else None
        rr2 = round(abs(tp2 - price) / abs(price - sl), 2) if price != sl else None

        return {
            "ok": True,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": [tp1, tp2],
            "rr": {"tp1": rr1, "tp2": rr2},
            "analytics": info
        }

def build_from_klines(klines: List[List[Any]]) -> KodexAdapter:
    closes = [float(k[4]) for k in klines]
    highs  = [float(k[2]) for k in klines]
    lows   = [float(k[3]) for k in klines]
    return KodexAdapter(closes, highs, lows)
