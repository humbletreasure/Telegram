import sqlite3
from datetime import datetime, timedelta

DB_NAME = "adult_playground.db"

# =========================
# DATABASE INITIALIZATION
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            age INTEGER,
            gender TEXT,
            country TEXT,
            vip INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Daily limits table
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_limits (
            user_id INTEGER,
            date TEXT,
            videos_watched INTEGER DEFAULT 0,
            pictures_viewed INTEGER DEFAULT 0,
            chats_done INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, date)
        )
    ''')

    # Media table (store file_ids)
    c.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploader_id INTEGER,
            type TEXT,
            file_id TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# =========================
# USER FUNCTIONS
# =========================
def add_user(user_id, username, age, gender, country):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username, age, gender, country)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, age, gender, country))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def set_vip(user_id, status=1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET vip = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def is_vip(user_id):
    user = get_user(user_id)
    return user[5] == 1 if user else False  # vip column

# =========================
# DAILY LIMIT FUNCTIONS
# =========================
def get_today_limits(user_id):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT videos_watched, pictures_viewed, chats_done FROM daily_limits WHERE user_id = ? AND date = ?', (user_id, today))
    row = c.fetchone()
    if not row:
        # Initialize limits for today
        c.execute('INSERT OR IGNORE INTO daily_limits (user_id, date) VALUES (?, ?)', (user_id, today))
        conn.commit()
        row = (0, 0, 0)
    conn.close()
    return {"videos_watched": row[0], "pictures_viewed": row[1], "chats_done": row[2]}

def increment_limit(user_id, type_):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if type_ == "video":
        c.execute('UPDATE daily_limits SET videos_watched = videos_watched + 1 WHERE user_id = ? AND date = ?', (user_id, today))
    elif type_ == "picture":
        c.execute('UPDATE daily_limits SET pictures_viewed = pictures_viewed + 1 WHERE user_id = ? AND date = ?', (user_id, today))
    elif type_ == "chat":
        c.execute('UPDATE daily_limits SET chats_done = chats_done + 1 WHERE user_id = ? AND date = ?', (user_id, today))
    conn.commit()
    conn.close()

# =========================
# MEDIA FUNCTIONS
# =========================
def add_media(uploader_id, file_id, type_):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO media (uploader_id, type, file_id) VALUES (?, ?, ?)', (uploader_id, type_, file_id))
    conn.commit()
    conn.close()

def get_media(type_):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT file_id FROM media WHERE type = ? ORDER BY uploaded_at ASC', (type_,))
    files = c.fetchall()
    conn.close()
    return [f[0] for f in files]  # return list of file_ids

# =========================
# INIT DB WHEN IMPORTED
# =========================
init_db()