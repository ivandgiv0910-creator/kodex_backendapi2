import time, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from app.services.telegram.models import (
    SessionLocal, init_db, TgUser, TgPendingLink, TgSubscription
)

init_db()

# ---------- Helpers ----------
def now_utc():
    return datetime.now(timezone.utc)

def gen_code() -> str:
    # buat kode pendek untuk linking Telegram <-> User
    return secrets.token_hex(3)  # contoh: 'a1b2c3'

# ---------- Linking ----------
def create_link_code(external_user_id: str, ttl_minutes: int = 15) -> dict:
    """Buat kode link Telegram untuk user eksternal"""
    db: Session = SessionLocal()
    try:
        # Pastikan user ada
        user = db.query(TgUser).filter_by(external_user_id=external_user_id).first()
        if not user:
            user = TgUser(external_user_id=external_user_id)
            db.add(user)
            db.flush()

        # Buat kode baru
        code = gen_code()
        pending = TgPendingLink(
            code=code,
            external_user_id=external_user_id,
            expire_at=now_utc() + timedelta(minutes=ttl_minutes)
        )
        db.add(pending)
        db.commit()
        return {"code": code, "expire_at_utc": pending.expire_at.isoformat()}
    finally:
        db.close()

def consume_link_code(code: str, chat_id: str, username: Optional[str]) -> bool:
    """Validasi dan simpan koneksi Telegram"""
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

def get_user_by_chat(chat_id:
