# analytics.py
import json
import os
from datetime import datetime

ANALYTICS_DB = "analytics.json"

# =========================
# INIT STORAGE
# =========================
def _init_db():
    if not os.path.exists(ANALYTICS_DB):
        with open(ANALYTICS_DB, "w") as f:
            json.dump(
                {
                    "uploads": [],
                    "views": [],
                    "user_activity": {}
                },
                f,
                indent=2
            )

_init_db()

# =========================
# LOAD / SAVE
# =========================
def _load():
    with open(ANALYTICS_DB, "r") as f:
        return json.load(f)

def _save(data):
    with open(ANALYTICS_DB, "w") as f:
        json.dump(data, f, indent=2)

# =========================
# LOG MEDIA UPLOAD
# =========================
def log_upload(user_id: int, media_type: str, file_id: str):
    data = _load()
    data["uploads"].append({
        "user_id": user_id,
        "media_type": media_type,
        "file_id": file_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Track user activity
    user_act = data["user_activity"].get(str(user_id), {"uploads": 0, "views": 0})
    user_act["uploads"] += 1
    data["user_activity"][str(user_id)] = user_act

    _save(data)

# =========================
# LOG MEDIA VIEW
# =========================
def log_view(user_id: int, media_type: str, file_id: str):
    data = _load()
    data["views"].append({
        "user_id": user_id,
        "media_type": media_type,
        "file_id": file_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Track user activity
    user_act = data["user_activity"].get(str(user_id), {"uploads": 0, "views": 0})
    user_act["views"] += 1
    data["user_activity"][str(user_id)] = user_act

    _save(data)

# =========================
# GET GLOBAL STATS
# =========================
def get_global_stats():
    data = _load()
    return {
        "total_uploads": len(data["uploads"]),
        "total_views": len(data["views"]),
        "active_users": len(data["user_activity"])
    }

# =========================
# GET USER STATS
# =========================
def get_user_stats(user_id: int):
    data = _load()
    return data["user_activity"].get(str(user_id), {"uploads": 0, "views": 0})