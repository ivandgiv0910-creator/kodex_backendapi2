from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone
import os

# =====================
# Database setup
# =====================
DB_PATH = os.getenv("TELEGRAM_DB_PATH", "sqlite:///./kodex_registry.db")

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================
# Model definitions
# =====================

class TgUser(Base):
    __tablename__ = "tg_users"

    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, unique=True, index=True)
    chat_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    subscriptions = relationship("TgSubscription", back_populates="user")


class TgPendingLink(Base):
    __tablename__ = "tg_pending_links"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    external_user_id = Column(String, nullable=False)
    expire_at = Column(DateTime, nullable=False)


class TgSubscription(Base):
    __tablename__ = "tg_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, Fore_
