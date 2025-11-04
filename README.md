# Kode X Live Data API (v2.2.0)

FastAPI service to fetch live OHLCV data from Binance and compute indicators (EMA, RSI, MACD, BB).
Exposes simple endpoints for price, candles, and indicator summary so your Kode X GPT can call them via Actions.

## Endpoints
- `GET /health`
- `GET /market/price?symbol=BTCUSDT&timeframe=15m`
- `GET /market/candles?symbol=BTCUSDT&timeframe=15m&limit=300`
- `POST /market/indicators` with body:
  ```json
  {"symbol":"BTCUSDT","timeframe":"15m","style":"intraday","limit":300}
  ```

## Run locally
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://127.0.0.1:8000/docs
```

## Deploy
- Railway/Render: Procfile included
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
