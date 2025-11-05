import os, sqlite3, time
from typing import Optional, Tuple, List, Dict

# Lokasi file database di root project
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "kodex_registry.db"))

def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS tg_links(
            user_id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            linked_at INTEGER NOT NULL
        );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_tg_links_chat ON tg_links(chat_id);")
        c.commit()

def upsert_link(user_id: str, chat_id: str, username: Optional[str], first: Optional[str], last: Optional[str]) -> None:
    with _conn() as c:
        c.execute("""
            INSERT INTO tg_links(user_id, chat_id, username, first_name, last_name, linked_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id, username=excluded.username,
                first_name=excluded.first_name, last_name=excluded.last_name, linked_at=excluded.linked_at
        """, (user_id, chat_id, username, first, last, int(time.time())))
        c.commit()

def get_chat_id(user_id: str) -> Optional[str]:
    with _conn() as c:
        cur = c.execute("SELECT chat_id FROM tg_links WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None

def get_by_chat_id(chat_id: str) -> Optional[Dict]:
    with _conn() as c:
        cur = c.execute("SELECT user_id, chat_id, username, first_name, last_name, linked_at FROM tg_links WHERE chat_id=?", (chat_id,))
        r = cur.fetchone()
        if not r: return None
        return {"user_id": r[0], "chat_id": r[1], "username": r[2], "first_name": r[3], "last_name": r[4], "linked_at": r[5]}

def all_links() -> List[Dict]:
    with _conn() as c:
        cur = c.execute("SELECT user_id, chat_id, username, first_name, last_name, linked_at FROM tg_links ORDER BY linked_at DESC")
        return [{"user_id": r[0], "chat_id": r[1], "username": r[2], "first_name": r[3], "last_name": r[4], "linked_at": r[5]} for r in cur.fetchall()]
