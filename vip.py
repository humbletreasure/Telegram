import sqlite3
import time

DB_NAME = "vip.db"

def init_vip_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS vip_users (
            user_id INTEGER PRIMARY KEY,
            expires_at INTEGER
        )
    """)
    conn.commit()
    conn.close()

def grant_vip(user_id: int, days: int):
    expires_at = int(time.time()) + days * 86400
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO vip_users (user_id, expires_at) VALUES (?, ?)",
        (user_id, expires_at)
    )
    conn.commit()
    conn.close()

def is_vip(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False

    expires_at = row[0]
    if time.time() > expires_at:
        remove_vip(user_id)
        return False

    return True

def remove_vip(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_vip_expiry(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None