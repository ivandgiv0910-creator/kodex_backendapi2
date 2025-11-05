import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

# Re-export init_db supaya modul lain bisa: from app.services.telegram.registry import init_db
from app.services.telegram.models import (
    SessionLocal,
    init_db,
    TgUser,
    TgPendingLink,
    TgSubscription,
)

# ======================
# Helpers
# ======================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def gen_code() -> str:
    """Kode pendek untuk /link <code> (6 hex chars)."""
    return secrets.token_hex(3)  # contoh: 'a1b2c3'


# ======================
# Linking
# ======================

def create_link_code(external_user_id: str, ttl_minutes: int = 15) -> dict:
    """
    Buat kode link Telegram untuk user eksternal (ID dari sistem kamu).
    Return: {"code": "...", "expire_at_utc": "..."}
    """
    db: Session = SessionLocal()
    try:
        # upsert user
        user = db.query(TgUser).filter_by(external_user_id=external_user_id).first()
        if not user:
            user = TgUser(external_user_id=external_user_id)
            db.add(user)
            db.flush()

        code = gen_code()
        pending = TgPendingLink(
            code=code,
            external_user_id=external_user_id,
            expire_at=now_utc() + timedelta(minutes=ttl_minutes),
        )
        db.add(pending)
        db.commit()
        return {"code": code, "expire_at_utc": pending.expire_at.isoformat()}
    finally:
        db.close()


def consume_link_code(code: str, chat_id: str, username: Optional[str]) -> bool:
    """
    Validasi kode /link dan simpan hubungan user <-> chat_id Telegram.
    Return: True jika sukses, False jika kode invalid/kadaluarsa.
    """
    db: Session = SessionLocal()
    try:
        pending = db.query(TgPendingLink).filter_by(code=code).first()
        if not pending or pending.expire_at < now_utc():
            return False

        user = db.query(TgUser).filter_by(external_user_id=pending.external_user_id).first()
        if not user:
            user = TgUser(external_user_id=pending.external_user_id)
            db.add(user)
            db.flush()

        user.chat_id = chat_id
        user.username = username
        db.delete(pending)
        db.commit()
        return True
    finally:
        db.close()


def get_user_by_chat(chat_id: str) -> Optional[TgUser]:
    """Ambil entity user berdasarkan telegram chat_id."""
    db: Session = SessionLocal()
    try:
        return db.query(TgUser).filter_by(chat_id=chat_id).first()
    finally:
        db.close()


def get_chat_id(external_user_id: str) -> Optional[str]:
    """
    Helper yang sering dipakai modul lain:
    Ambil chat_id Telegram dari external_user_id.
    """
    db: Session = SessionLocal()
    try:
        user = db.query(TgUser).filter_by(external_user_id=external_user_id).first()
        return user.chat_id if (user and user.chat_id) else None
    finally:
        db.close()


# ======================
# Subscriptions
# ======================

def create_subscription(
    external_user_id: str,
    symbol: str,
    interval: str,
    window: int,
    multiplier: float,
) -> int:
    """
    Tambah subscription deteksi volume spike untuk user tertentu.
    Return: subscription_id
    """
    db: Session = SessionLocal()
    try:
        user = db.query(TgUser).filter_by(external_user_id=external_user_id).first()
        if not user or not user.chat_id:
            raise ValueError("User belum link Telegram")

        sub = TgSubscription(
            user_id=user.id,
            symbol=symbol.upper(),
            interval=interval,
            window=window,
            multiplier=multiplier,
            is_active=True,
        )
        db.add(sub)
        db.commit()
        return sub.id
    finally:
        db.close()


def toggle_subscription(sub_id: int, is_active: bool) -> bool:
    db: Session = SessionLocal()
    try:
        s = db.query(TgSubscription).filter_by(id=sub_id).first()
        if not s:
            return False
        s.is_active = is_active
        db.commit()
        return True
    finally:
        db.close()


def list_user_subscriptions(user_id: int) -> List[TgSubscription]:
    db: Session = SessionLocal()
    try:
        return db.query(TgSubscription).filter_by(user_id=user_id).all()
    finally:
        db.close()


def active_subscriptions() -> List[TgSubscription]:
    db: Session = SessionLocal()
    try:
        return db.query(TgSubscription).filter_by(is_active=True).all()
    finally:
        db.close()


def set_last_alert(sub_id: int, ts: int) -> None:
    db: Session = SessionLocal()
    try:
        s = db.query(TgSubscription).filter_by(id=sub_id).first()
        if s:
            s.last_alert_ts = ts
            db.commit()
    finally:
        db.close()
