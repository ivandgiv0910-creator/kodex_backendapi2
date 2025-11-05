from typing import List, Optional, Dict, Any
import datetime as dt

def build_signal_message_md2(
    symbol: str,
    side: str,
    entries: List[float],
    sl: Optional[float],
    tps: List[float],
    timeframe: Optional[str] = None,
    extra_note: Optional[str] = None,
) -> str:
    """
    Hati-hati karakter spesial MarkdownV2 — kita jaga teks tetap sederhana.
    Jika TELEGRAM_PARSE_MODE dikosongkan, ini akan diperlakukan plain text (aman).
    """
    lines = []
    lines.append("📣 Sinyal Baru")
    lines.append(f"Symbol: {symbol.upper()}")
    lines.append(f"Side: {side.upper()}" + (f" · TF: {timeframe.upper()}" if timeframe else ""))
    if entries:
        lines.append("Entry: " + ", ".join(str(x) for x in entries))
    if sl is not None:
        lines.append(f"SL: {sl}")
    if tps:
        lines.append("TP: " + ", ".join(str(x) for x in tps))
    if extra_note:
        lines.append(f"\nNote: {extra_note}")
    lines.append("\n_Auto-push via KodeX_")
    return "\n".join(lines)

def build_actions_keyboard() -> Dict[str, Any]:
    """
    Inline keyboard sederhana:
    - Close
    - SL -> BE
    - SL -> TP1
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🛑 Close", "callback_data": "sig|CLOSE"},
                {"text": "SL → BE", "callback_data": "sig|SL|BE"},
                {"text": "SL → TP1", "callback_data": "sig|SL|TP1"},
            ]
        ]
    }

def stamp_now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def apply_action_to_text(original: str, action_desc: str) -> str:
    """
    Tambah baris update di bawah pesan asli.
    """
    marker = "\n\n———"
    if marker not in original:
        original = f"{original}{marker}\nUpdates:"
    return f"{original}\n• {stamp_now()} · {action_desc}"
