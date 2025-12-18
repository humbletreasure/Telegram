from database import get_today_limits, increment_limit, is_vip
from datetime import datetime
from collections import deque

# =========================
# GLOBAL VARIABLES
# =========================
waiting_users = deque()  # Users waiting for a chat
active_chats = {}        # {user_id: partner_id}
FREE_CHAT_LIMIT = 50     # max chats per 24h for free users

# =========================
# CHAT FUNCTIONS
# =========================
def can_chat(user_id):
    """Check if user can start a chat (based on free/VIP limits)"""
    if is_vip(user_id):
        return True
    limits = get_today_limits(user_id)
    return limits["chats_done"] < FREE_CHAT_LIMIT

def add_user_to_queue(user_id):
    """Add user to waiting queue"""
    if user_id not in waiting_users and user_id not in active_chats:
        waiting_users.append(user_id)

def pair_users(user_id):
    """Pair a user with someone from the queue"""
    if user_id in active_chats:
        return active_chats[user_id]  # Already chatting

    while waiting_users:
        partner_id = waiting_users.popleft()
        if partner_id != user_id and partner_id not in active_chats:
            # Pair them
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            return partner_id
    # No partner available yet
    add_user_to_queue(user_id)
    return None

def end_chat(user_id):
    """End an active chat"""
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        if partner_id in active_chats:
            del active_chats[partner_id]
        return partner_id
    return None

def send_message(user_id, message, send_func):
    """
    Send a message to the paired user only.
    send_func = a function to actually send the message, e.g., bot.send_message
    """
    if user_id not in active_chats:
        return False, "❌ You are not in an active chat."
    partner_id = active_chats[user_id]

    # Increment chat counter for free users
    if not is_vip(user_id):
        increment_limit(user_id, "chat")
    if not is_vip(partner_id):
        increment_limit(partner_id, "chat")

    send_func(partner_id, message)
    return True, None