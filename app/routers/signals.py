from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Tuple, List, Optional
import os
from app.adapters.signal_models import SignalPayload
from app.services.telegram.client import TelegramService
from app.services.telegram.formatters import build_signal_message_md2, build_actions_keyboard
from app.services.telegram.registry import init_db, get_chat_id

router = APIRouter(prefix="/signals", tags=["signals"])

def _normalize_prices(payload: SignalPayload) -> Tuple[List[float], float | None, List[float]]:
    entries = payload.entries or ([payload.entry] if payload.entry is not None else [])
    tps = payload.tps or ([payload.tp] if payload.tp is not None else [])
    sl = payload.sl if payload.sl is not None else None
    return entries, sl, tps

def _push_default_from_env() -> bool:
    val = os.environ.get("PUSH_TELEGRAM_DEFAULT", "false").lower()
    return val in ("1", "true", "yes", "on")

def _resolve_target_chat_id(payload: SignalPayload) -> Optional[str]:
    if payload.target_chat_id:
        return payload.target_chat_id
    if payload.target_user_id:
        init_db()
        cid = get_chat_id(payload.target_user_id)
        if cid:
            return cid
        raise HTTPException(404, f"Chat ID untuk user_id '{payload.target_user_id}' belum terdaftar (klik deep-link dulu).")
    return None

async def _push_signal_to_telegram(payload: SignalPayload):
    entries, sl, tps = _normalize_prices(payload)
    tg = TelegramService()
    text = build_signal_message_md2(
        symbol=payload.symbol, side=payload.side,
        entries=entries, sl=sl, tps=tps,
        timeframe=payload.timeframe, extra_note=payload.note,
    )
    target_chat: Optional[str] = _resolve_target_chat_id(payload)
    keyboard = build_actions_keyboard() if (payload.enable_actions is None or payload.enable_actions) else None

    if payload.chart_image_url:
        return await tg.send_photo(photo_url=payload.chart_image_url, caption=text, chat_id=target_chat, reply_markup=keyboard)
    else:
        return await tg.send_message(text=text, chat_id=target_chat, reply_markup=keyboard)

@router.post("", summary="Terima sinyal & auto-push (photo/chart + inline keyboard)")
async def create_signal(payload: SignalPayload, background: BackgroundTasks):
    should_push = _push_default_from_env() if payload.push_telegram is None else bool(payload.push_telegram)
    if should_push:
        background.add_task(_push_signal_to_telegram, payload)
    entries, sl, tps = _normalize_prices(payload)
    target_chat = None
    try:
        target_chat = _resolve_target_chat_id(payload)
    except HTTPException as e:
        if should_push: raise
    return {
        "ok": True,
        "message": "signal accepted",
        "pushed_to_telegram": should_push,
        "target_chat_id": target_chat,
        "data": {
            "symbol": payload.symbol.upper(),
            "side": payload.side.upper(),
            "entries": entries,
            "sl": sl,
            "tps": tps,
            "timeframe": payload.timeframe,
            "note": payload.note,
            "chart_image_url": payload.chart_image_url,
            "enable_actions": bool(payload.enable_actions if payload.enable_actions is not None else True),
            "target_user_id": payload.target_user_id,
        },
    }

@router.api_route("/preset/btcusdt-long", methods=["GET", "POST"], summary="Preset: BTCUSDT LONG (GET/POST)")
async def preset_btcusdt_long(background: BackgroundTasks, push_telegram: bool | None = None, target_chat_id: str | None = None, target_user_id: str | None = None, chart_image_url: str | None = None):
    sample = SignalPayload(
        symbol="BTCUSDT", side="LONG",
        entries=[100000.0, 99800.0], sl=99200.0,
        tps=[100800.0, 101200.0, 101800.0],
        timeframe="1H", note="Sample preset via /signals/preset/btcusdt-long",
        push_telegram=push_telegram, target_chat_id=target_chat_id, target_user_id=target_user_id,
        chart_image_url=chart_image_url, enable_actions=True,
    )
    return await create_signal(sample, background)

@router.get("/ping", summary="Ping router signals")
async def ping():
    return {"ok": True}
