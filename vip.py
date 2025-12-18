from database import set_vip, is_vip, get_user

# =========================
# VIP FUNCTIONS
# =========================

def make_user_vip(user_id):
    """
    Set a user as VIP
    """
    set_vip(user_id, 1)
    return f"✅ User {user_id} is now a VIP!"

def remove_vip(user_id):
    """
    Remove VIP status from a user
    """
    set_vip(user_id, 0)
    return f"✅ User {user_id} is no longer a VIP."

def check_vip_status(user_id):
    """
    Returns True if user is VIP, False otherwise
    """
    return is_vip(user_id)

def vip_info(user_id):
    """
    Returns user info including VIP status
    """
    user = get_user(user_id)
    if not user:
        return None
    info = {
        "user_id": user[0],
        "username": user[1],
        "age": user[2],
        "gender": user[3],
        "country": user[4],
        "vip": bool(user[5])
    }
    return info