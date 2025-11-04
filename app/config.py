import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "local")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    cors_allow_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "*")

    http_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    http_connect_timeout_seconds: float = float(os.getenv("HTTP_CONNECT_TIMEOUT_SECONDS", "5"))
    http_read_timeout_seconds: float = float(os.getenv("HTTP_READ_TIMEOUT_SECONDS", "10"))
    http_write_timeout_seconds: float = float(os.getenv("HTTP_WRITE_TIMEOUT_SECONDS", "10"))
    http_max_retries: int = int(os.getenv("HTTP_MAX_RETRIES", "2"))

    # ✅ perbaikan penting: dukungan flag HTTP/2
    http2_enabled: bool = os.getenv("HTTP2_ENABLED", "false").lower() == "true"

    # daftar host Binance
    binance_hosts: list[str] = tuple(
        h.strip() for h in os.getenv("BINANCE_HOSTS", "").split(",") if h.strip()
    )

settings = Settings()
