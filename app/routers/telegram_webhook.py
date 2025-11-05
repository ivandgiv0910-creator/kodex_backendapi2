from fastapi import APIRouter, Request, HTTPException
import os, hmac, hashlib, base64
from typing import Optional
from app.services.telegram.client import TelegramService
from app.services.telegram.registry import init_db, upsert_link, get_chat_id, all_links
from app.services.telegram.formatters import apply_action_to_text, build_actions_keyboard

router = APIRouter(prefix="/telegram", tags=["telegram"])

def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

def _sign_payload(user_id: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode((user_id + ":" + base64.urlsafe_b64encode(mac).decode()).encode()).decode()

def _verify_and_extract(token: str, secret: str) -> Optional[str]:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, mac_b64 = raw.split(":", 1)
        mac_expected = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).digest()
        if base64.urlsafe_b64encode(mac_expected).decode() == mac_b64:
            return user_id
        return None
    except Exception:
        return None

@router.get("/debug/ping", summary="Ping Telegram getMe (cek token)")
async def debug_ping():
    tg = TelegramService()
    resp = await tg.ping()
    token = _env("TELEGRAM_BOT_TOKEN", "")
    masked = (token[:6] + "..." + token[-4:]) if token else ""
    return {"token_masked": masked, "ping": resp}

@router.get("/get_webhook_info", summary="Lihat status webhook di Telegram")
async def get_webhook_info():
    tg = TelegramService()
    return await tg.get_webhook_info()

@router.get("/link", summary="Buat tautan deep-link Telegram untuk user_id")
async def make_link(user_id: str):
    bot_username = _env("TELEGRAM_BOT_USERNAME", "")
    secret = _env("TELEGRAM_WEBHOOK_SECRET", "")
    if not bot_username or not secret:
        raise HTTPException(500, "TELEGRAM_BOT_USERNAME/TELEGRAM_WEBHOOK_SECRET belum di-set.")
    token = _sign_payload(user_id, secret)
    url = f"https://t.me/{bot_username}?start={token}"
    return {"user_id": user_id, "deep_link": url}

@router.post("/set_webhook", summary="Set Telegram webhook (butuh PUBLIC_BASE_URL)")
async def set_webhook():
    public_base = _env("PUBLIC_BASE_URL", "")
    secret = _env("TELEGRAM_WEBHOOK_SECRET", "")
    if not public_base or not secret:
        raise HTTPException(400, "PUBLIC_BASE_URL/TELEGRAM_WEBHOOK_SECRET belum di-set.")
    tg = TelegramService()
    return await tg.set_webhook(public_base, secret)

@router.post("/delete_webhook", summary="Delete Telegram webhook")
async def delete_webhook():
    tg = TelegramService()
    return await tg.delete_webhook()

@router.get("/links", summary="List semua link user_id ↔ chat_id")
async def list_links():
    return {"items": all_links()}

@router.post("/webhook", summary="Endpoint webhook (Telegram -> Backend)")
async def webhook(request: Request, secret: str):
    if secret != _env("TELEGRAM_WEBHOOK_SECRET", ""):
        raise HTTPException(403, "Forbidden: bad secret")

    init_db()
    data = await request.json()

    message = data.get("message") or data.get("channel_post")
    if message:
        chat = message.get("chat", {})
        text = message.get("text") or ""
        chat_id = str(chat.get("id"))
        username = chat.get("username")
        first = chat.get("first_name")
        last = chat.get("last_name")

        if text.startswith("/start "):
            token = text.split(" ", 1)[1].strip()
            user_id = _verify_and_extract(token, _env("TELEGRAM_WEBHOOK_SECRET", ""))
            if not user_id:
                raise HTTPException(400, "Invalid start payload")
            upsert_link(user_id=user_id, chat_id=chat_id, username=username, first=first, last=last)
            tg = TelegramService()
            await tg.send_message(f"✅ Link sukses.\nUser: {user_id}", chat_id=chat_id)
            return {"ok": True, "linked": {"user_id": user_id, "chat_id": chat_id}}

        return {"ok": True, "note": "message ignored"}

    callback = data.get("callback_query")
    if callback:
        cq_id = callback["id"]
        msg = callback.get("message", {})
        chat_id = str(msg["chat"]["id"])
        message_id = int(msg["message_id"])
        original_text = msg.get("text") or msg.get("caption") or ""
        data_str = callback.get("data", "")
        tg = TelegramService()

        parts = data_str.split("|")
        action_text = None
        if len(parts) >= 2 and parts[0] == "sig":
            if parts[1] == "CLOSE":
                action_text = "❎ Position closed (manual)"
            elif parts[1] == "SL" and len(parts) == 3:
                if parts[2] == "BE":
                    action_text = "🔒 SL moved to BE"
                elif parts[2] == "TP1":
                    action_text = "🔒 SL moved to TP1"
        if not action_text:
            await tg.answer_callback_query(cq_id, "Unknown action", show_alert=False)
            return {"ok": False, "reason": "unknown action"}

        from app.services.telegram.formatters import build_actions_keyboard, apply_action_to_text
        new_text = apply_action_to_text(original_text, action_text)
        await tg.edit_message_text(chat_id=chat_id, message_id=message_id, new_text=new_text, reply_markup=build_actions_keyboard())
        await tg.answer_callback_query(cq_id, "Updated ✓", show_alert=False)
        return {"ok": True, "edited": True}

    return {"ok": True, "note": "no message/callback payload"}
