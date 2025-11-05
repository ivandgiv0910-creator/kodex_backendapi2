from pydantic import BaseModel, Field
from typing import List, Optional

class SignalPayload(BaseModel):
    # Wajib
    symbol: str = Field(..., description="contoh: BTCUSDT / XAUUSD / EURUSD")
    side: str = Field(..., description="BUY/SELL/LONG/SHORT")

    # Harga (boleh single atau list)
    entries: Optional[List[float]] = Field(default=None, description="list entry price")
    entry: Optional[float] = Field(default=None, description="single entry jika tidak pakai entries")
    sl: Optional[float] = Field(default=None, description="stop loss")
    tps: Optional[List[float]] = Field(default=None, description="list take profit")
    tp: Optional[float] = Field(default=None, description="single take profit")

    timeframe: Optional[str] = Field(default=None, description="1m/5m/15m/1h/4h/1d")
    note: Optional[str] = Field(default=None, description="catatan tambahan")

    # Push control
    push_telegram: Optional[bool] = Field(default=None, description="override default .env untuk push")
    target_chat_id: Optional[str] = Field(default=None, description="kirim ke chat id tertentu")
    target_user_id: Optional[str] = Field(default=None, description="kirim ke user_id (di-resolve ke chat_id dari registry)")

    # Phase-3 additions
    chart_image_url: Optional[str] = Field(default=None, description="URL gambar chart untuk dikirim via sendPhoto")
    enable_actions: Optional[bool] = Field(default=True, description="tampilkan inline keyboard aksi (Close/SL)")
