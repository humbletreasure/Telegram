# media.py
import json
import os
from datetime import datetime

MEDIA_DB = "media_store.json"

# =========================
# INIT STORAGE
# =========================
def _init_db():
    if not os.path.exists(MEDIA_DB):
        with open(MEDIA_DB, "w") as f:
            json.dump(
                {
                    "videos": [],
                    "pictures": [],
                    "user_progress": {}
                },
                f,
                indent=2
            )

_init_db()

# =========================
# LOAD / SAVE
# =========================
def _load():
    with open(MEDIA_DB, "r") as f:
        return json.load(f)

def _save(data):
    with open(MEDIA_DB, "w") as f:
        json.dump(data, f, indent=2)

# =========================
# UPLOAD MEDIA
# =========================
def upload_video(file_id: str, uploader_id: int):
    data = _load()
    data["videos"].append({
        "file_id": file_id,
        "uploaded_by": uploader_id,
        "uploaded_at": datetime.utcnow().isoformat()
    })
    _save(data)

def upload_picture(file_id: str, uploader_id: int):
    data = _load()
    data["pictures"].append({
        "file_id": file_id,
        "uploaded_by": uploader_id,
        "uploaded_at": datetime.utcnow().isoformat()
    })
    _save(data)

# =========================
# FETCH NEXT MEDIA FOR USER
# =========================
def _get_next_media(media_type: str, user_id: int):
    data = _load()
    media_list = data[media_type]

    if not media_list:
        return None

    user_progress = data["user_progress"].get(str(user_id), {})
    index = user_progress.get(media_type, 0)

    if index >= len(media_list):
        return None

    media = media_list[index]["file_id"]

    # Update progress
    user_progress[media_type] = index + 1
    data["user_progress"][str(user_id)] = user_progress
    _save(data)

    return media

def get_next_video_for_user(user_id: int):
    return _get_next_media("videos", user_id)

def get_next_picture_for_user(user_id: int):
    return _get_next_media("pictures", user_id)