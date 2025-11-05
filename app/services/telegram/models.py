import os
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


# =====================
# Database setup
# =====================
DB_PATH = os.getenv("TELEGRAM_DB_PATH", "sqlite:///./kodex_registry.db")

# sqlite but allow non-sqlite too
_engine_kwargs = {}
if DB_PATH.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DB_PATH, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================
# Model definitions
# =====================
class TgUser(Base):
    __tablename__ = "tg_users"

    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, unique=True, index=True, nullable=False)
    chat_id = Column(String, nullable=True, index=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=now_utc, nullable=False)

    subscriptions = relationship("TgSubscription", back_populates="user")


class TgPendingLink(Base):
    __tablename__ = "tg_pending_links"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    external_user_id = Column(String, nullable=False, index=True)
    expire_at = Column(DateTime, nullable=False, index=True)


class TgSubscription(Base):
    __tablename__ = "tg_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("tg_users.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    interval = Column(String, default="1m", nullable=False)
    window = Column(Integer, default=20, nullable=False)
    multiplier = Column(Float, default=2.0, nullable=False)
    last_alert_ts = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=now_utc, nullable=False)

    user = relationship("TgUser", back_populates="subscriptions")


# =====================
# Init DB
# =====================
def init_db() -> None:
    Base.metadata.create_all(bind=engine)
