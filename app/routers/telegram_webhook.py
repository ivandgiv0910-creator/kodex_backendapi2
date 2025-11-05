from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse

from app.config import TELEGRAM_WEBHOOK_SECRET
from app.services.telegram.client import send_message
from app.services.telegram.registry import (
    consume_link_code, get_user_by_chat, list_user_subscriptions
)

router = APIRouter(prefix="/telegram", tags=["Telegram Webhook"])

def _check_secret(secret_header: str | None):
    if TELEGRAM_WEBHOOK_SECRET and secret_header != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

@router.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    _check_secret(x_telegram_bot_api_secret_token)

    data = await request.json()
    message = data.get("message") or data.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id")) if chat.get("id") is not None else None
    username = chat.get("username")

    if not text or not chat_id:
        return JSONResponse({"ok": True})

    if text.startswith("/start"):
        await send_message(chat_id, "Halo! Gunakan:\n/link <kode>\n/status")
    elif text.startswith("/link"):
        parts = text.split()
        if len(parts) != 2:
            await send_message(chat_id, "Format: /link <kode>")
        else:
            ok = consume_link_code(parts[1], chat_id, username)
            if ok:
                await send_message(chat_id, "Akun berhasil terhubung ✅. Kamu akan menerima notifikasi di sini.")
            else:
                await send_message(chat_id, "Kode tidak valid / kadaluarsa.")
    elif text.startswith("/status"):
        user = get_user_by_chat(chat_id)
        if not user:
            await send_message(chat_id, "Belum terhubung. Gunakan /link <kode>.")
        else:
            subs = list_user_subscriptions(user.id)
            label = ", ".join([f"{s.symbol}@{s.interval}{'✅' if s.is_active else '⛔'}" for s in subs]) or "tidak ada"
            await send_message(chat_id, f"Terhubung sebagai <b>{user.external_user_id}</b>\nSubs: {label}")
    else:
        await send_message(chat_id, "Perintah tersedia: /start, /link <kode>, /status")

    return JSONResponse({"ok": True})
