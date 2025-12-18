from database import add_media, get_media, increment_limit, get_today_limits
from telegram import Update
from telegram.ext import CallbackContext
import os

# =========================
# CONSTANTS
# =========================
VIDEO_LIMIT_MB = 5
PICTURE_LIMIT_MB = 1
FREE_VIDEO_MAX = 10
FREE_PICTURE_MAX = 10

# =========================
# CHECK LIMITS
# =========================
def can_watch_video(user_id, is_vip):
    if is_vip:
        return True
    limits = get_today_limits(user_id)
    return limits["videos_watched"] < FREE_VIDEO_MAX

def can_watch_picture(user_id, is_vip):
    if is_vip:
        return True
    limits = get_today_limits(user_id)
    return limits["pictures_viewed"] < FREE_PICTURE_MAX

# =========================
# MEDIA UPLOAD
# =========================
def upload_video(user_id, file_id, file_size_mb):
    if file_size_mb > VIDEO_LIMIT_MB:
        return False, f"❌ Video size exceeds {VIDEO_LIMIT_MB}MB. Please compress and try again."
    add_media(user_id, file_id, "video")
    return True, "✅ Video uploaded successfully!"

def upload_picture(user_id, file_id, file_size_mb):
    if file_size_mb > PICTURE_LIMIT_MB:
        return False, f"❌ Picture size exceeds {PICTURE_LIMIT_MB}MB. Please resize and try again."
    add_media(user_id, file_id, "picture")
    return True, "✅ Picture uploaded successfully!"

# =========================
# GET MEDIA
# =========================
def get_next_video_for_user(user_id, is_vip):
    if not can_watch_video(user_id, is_vip):
        return None, "⚠ You have reached your daily limit of videos."
    videos = get_media("video")
    if not videos:
        return None, "⚠ No videos available at the moment."
    # Get the first video (you can implement more advanced tracking later)
    file_id = videos[0]
    if not is_vip:
        increment_limit(user_id, "video")
    return file_id, None

def get_next_picture_for_user(user_id, is_vip):
    if not can_watch_picture(user_id, is_vip):
        return None, "⚠ You have reached your daily limit of pictures."
    pictures = get_media("picture")
    if not pictures:
        return None, "⚠ No pictures available at the moment."
    file_id = pictures[0]
    if not is_vip:
        increment_limit(user_id, "picture")
    return file_id, None