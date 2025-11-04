import pandas as pd

def ema(series: pd.Series, length: int):
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14):
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/length, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/length, adjust=False).mean()
    rs = up / down.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bb(series: pd.Series, length=20, mult=2.0):
    ma = series.rolling(length).mean()
    std = series.rolling(length).std(ddof=0)
    upper = ma + mult * std
    lower = ma - mult * std
    return upper, ma, lower

def summarize_signals(df: pd.DataFrame, style: str = ""):
    """Summarize signals from EMA/RSI/MACD/BB and return an eligibility flag."""
    close = df["close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    rsi14 = rsi(close)
    macd_l, macd_s, macd_h = macd(close)
    bb_u, bb_m, bb_l = bb(close)

    i = -1  # last candle
    trend = "bullish" if ema20.iloc[i] > ema50.iloc[i] else "bearish"
    momentum = "strong" if rsi14.iloc[i] >= 60 else ("weak" if rsi14.iloc[i] <= 40 else "moderate")
    macd_conf = "bullish" if macd_l.iloc[i] > macd_s.iloc[i] else "bearish"
    bb_pos = "upper" if close.iloc[i] > bb_m.iloc[i] else "lower"

    ok_trend = (trend == "bullish" and close.iloc[i] > ema20.iloc[i]) or (trend == "bearish" and close.iloc[i] < ema20.iloc[i])
    ok_mom = (trend == "bullish" and rsi14.iloc[i] >= 55) or (trend == "bearish" and rsi14.iloc[i] <= 45)
    ok_macd = (trend == "bullish" and macd_conf == "bullish") or (trend == "bearish" and macd_conf == "bearish")

    score = sum([ok_trend, ok_mom, ok_macd])
    if score == 3:
        eligibility = "ready"
    elif score == 2:
        eligibility = "potential"
    else:
        eligibility = "wait and see"

    return {
        "trend": trend,
        "momentum": momentum,
        "macd": macd_conf,
        "bb_side": bb_pos,
        "eligibility": eligibility,
        "values": {
            "price": float(close.iloc[i]),
            "ema20": float(ema20.iloc[i]),
            "ema50": float(ema50.iloc[i]),
            "rsi14": float(rsi14.iloc[i])
        }
    }
