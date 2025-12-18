# chat.py
import time

# In-memory storage
chat_queue = []
active_chats = {}  # user_id -> partner_id
chat_limits = {}   # user_id -> {date: count}

MAX_FREE_CHATS_PER_DAY = 50

def add_user_to_queue(user_id):
    if user_id not in chat_queue and user_id not in active_chats:
        chat_queue.append(user_id)

def pair_users(user_id):
    if user_id not in chat_queue:
        return None
    if len(chat_queue) < 2:
        return None  # wait for partner

    # Remove self from queue
    chat_queue.remove(user_id)
    # Pair with the first user in queue
    partner_id = chat_queue.pop(0)
    active_chats[user_id] = partner_id
    active_chats[partner_id] = user_id
    return partner_id

def end_chat(user_id):
    partner_id = active_chats.pop(user_id, None)
    if partner_id:
        active_chats.pop(partner_id, None)

def can_chat(user_id, vip=False):
    today = time.strftime("%Y-%m-%d")
    if vip:
        return True
    if user_id not in chat_limits:
        chat_limits[user_id] = {}
    if today not in chat_limits[user_id]:
        chat_limits[user_id][today] = 0
    return chat_limits[user_id][today] < MAX_FREE_CHATS_PER_DAY

def increment_chat_count(user_id):
    today = time.strftime("%Y-%m-%d")
    if user_id not in chat_limits:
        chat_limits[user_id] = {}
    if today not in chat_limits[user_id]:
        chat_limits[user_id][today] = 0
    chat_limits[user_id][today] += 1

def send_message(user_id, text, send_func):
    """
    send_func = context.bot.send_message
    Returns (success, message)
    """
    partner_id = active_chats.get(user_id)
    if not partner_id:
        return False, "❌ You are not paired with anyone yet."

    # For simplicity, free users see only country, VIP users see full info
    # Info can be pulled from database.py (get_user)
    send_func(chat_id=partner_id, text=text)
    increment_chat_count(user_id)
    return True, "Message sent."