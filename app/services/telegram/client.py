import asyncio, httpx, os
from typing import Optional, Dict, Any
from app.config import settings

def _get_env(name: str, default: str = "") -> str:
    return getattr(settings, name, os.environ.get(name, default))

class TelegramService:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        disable_preview: Optional[bool] = None,
        retry_max: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self.bot_token = bot_token or _get_env("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or _get_env("TELEGRAM_CHAT_ID", "")
        self.parse_mode = parse_mode if parse_mode is not None else _get_env("TELEGRAM_PARSE_MODE", "MarkdownV2")
        self.disable_preview = (_get_env("TELEGRAM_DISABLE_WEB_PAGE_PREVIEW", "true").lower() == "true") if disable_preview is None else disable_preview
        self.retry_max = int(retry_max or _get_env("TELEGRAM_RETRY_MAX", "3"))
        self.timeout_seconds = int(timeout_seconds or _get_env("TELEGRAM_TIMEOUT_SECONDS", "10"))
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _is_configured(self, chat_id: Optional[str] = None) -> bool:
        return bool(self.bot_token) and bool(chat_id or self.chat_id)

    async def ping(self) -> dict:
        if not self.bot_token:
            return {"ok": False, "error": "BOT_TOKEN_EMPTY"}
        url = f"{self.base_url}/getMe"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            r = await client.get(url)
            try:
                data = r.json()
            except Exception:
                data = {"ok": False, "status": r.status_code, "text": r.text}
            return {"status": r.status_code, "data": data}

    async def set_webhook(self, public_base_url: str, secret: str) -> dict:
        url = f"{self.base_url}/setWebhook"
        wh_url = f"{public_base_url.rstrip('/')}/telegram/webhook?secret={secret}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            r = await client.post(url, data={"url": wh_url, "drop_pending_updates": True})
            return r.json()

    async def delete_webhook(self) -> dict:
        url = f"{self.base_url}/deleteWebhook"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            r = await client.post(url, data={"drop_pending_updates": True})
            return r.json()

    async def _post(self, method: str, payload: Dict[str, Any]) -> dict:
        url = f"{self.base_url}/{method}"
        delay = 0.8
        last_exc = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for _ in range(max(1, self.retry_max)):
                try:
                    resp = await client.post(url, data=payload)
                    if resp.status_code == 200:
                        return resp.json()
                    data = resp.json()
                    if resp.status_code == 429:
                        retry_after = data.get("parameters", {}).get("retry_after", 1)
                        await asyncio.sleep(float(retry_after)); continue
                    await asyncio.sleep(delay); delay = min(delay * 2, 6.4)
                except Exception as e:
                    last_exc = e; await asyncio.sleep(delay); delay = min(delay * 2, 6.4)
        return {"ok": False, "error": f"HTTP error on {method}. last_exception={last_exc}"}

    async def send_message(self, text: str, chat_id: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        target = chat_id or self.chat_id
        if not self._is_configured(target):
            return {"ok": False, "error": "Telegram not configured"}
        payload = {"chat_id": target, "text": text, "disable_web_page_preview": self.disable_preview}
        if self.parse_mode: payload["parse_mode"] = self.parse_mode
        if reply_markup: payload["reply_markup"] = httpx.JSONEncoder().encode(reply_markup)
        return await self._post("sendMessage", payload)

    async def send_photo(self, photo_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        target = chat_id or self.chat_id
        if not self._is_configured(target):
            return {"ok": False, "error": "Telegram not configured"}
        payload = {"chat_id": target, "photo": photo_url}
        if caption: payload["caption"] = caption
        if self.parse_mode: payload["parse_mode"] = self.parse_mode
        if reply_markup: payload["reply_markup"] = httpx.JSONEncoder().encode(reply_markup)
        return await self._post("sendPhoto", payload)

    async def edit_message_text(self, chat_id: str, message_id: int, new_text: str, reply_markup: Optional[dict] = None) -> dict:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": new_text}
        if self.parse_mode: payload["parse_mode"] = self.parse_mode
        if reply_markup: payload["reply_markup"] = httpx.JSONEncoder().encode(reply_markup)
        return await self._post("editMessageText", payload)

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False) -> dict:
        payload = {"callback_query_id": callback_query_id}
        if text: payload["text"] = text
        if show_alert: payload["show_alert"] = True
        return await self._post("answerCallbackQuery", payload)
