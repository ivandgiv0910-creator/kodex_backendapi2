from pydantic import BaseModel, Field

class SnapshotQuery(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])  # Binance symbol
    timeframe: str = Field(..., examples=["1m","5m","15m","30m","1h","4h","1d"])  # Binance intervals
    limit: int = 300

class IndicatorsQuery(SnapshotQuery):
    style: str | None = Field(None, examples=["scalping", "intraday", "swing", "positional"])
