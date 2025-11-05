import asyncio, time
from datetime import datetime, timezone
from app.services.binance_client import get_klines
from app.services.telegram.client import send_message
from app.services.telegram.registry import (
    active_subscriptions, set_last_alert
)

async def _scan_once():
    subs = active_subscriptions()
    now_epoch = int(time.time())
    for s in subs:
        try:
            if s.last_alert_ts and now_epoch - s.last_alert_ts < 120:
                continue
            kl = await get_klines(s.symbol, s.interval, limit=max(50, s.window + 5))
            vols = [float(k[5]) for k in kl]
            if len(vols) < s.window + 1:
                continue
            baseline = sum(vols[-1 - s.window:-1]) / s.window
            current = vols[-1]
            if baseline > 0 and current >= s.multiplier * baseline:
                last = kl[-1]
                ts = datetime.fromtimestamp(last[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                close = float(last[4]); ratio = current / baseline
                # ambil chat_id via relationship
                chat_id = s.user.chat_id if s.user else None
                if not chat_id:
                    continue
                msg = (
                    f"🚨 <b>Volume Spike</b>\n"
                    f"Pair: <b>{s.symbol}</b> | TF: <b>{s.interval}</b>\n"
                    f"Waktu: {ts}\nClose: <b>{close}</b>\n"
                    f"Volume: <b>{current:.2f}</b> (Baseline {baseline:.2f} × {ratio:.2f})"
                )
                await send_message(chat_id, msg)
                set_last_alert(s.id, now_epoch)
        except Exception as e:
            print("[telegram.worker] error:", e)

async def volume_loop():
    await asyncio.sleep(2)
    print("[telegram.worker] started")
    while True:
        await _scan_once()
        await asyncio.sleep(20)
