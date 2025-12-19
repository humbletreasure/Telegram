import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from analytics import log_upload, log_view, get_global_stats
from database import add_user
from media import (
    upload_video,
    upload_picture,
    get_next_video_for_user,
    get_next_picture_for_user
)
from chat import add_user_to_queue, pair_users, can_chat
from vip import init_vip_db, grant_vip, is_vip, get_active_vips, get_new_vips, get_uploads_today, get_views_today

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

REQUIRED_CHANNEL = "@adultplaygroundchannel"
REQUIRED_GROUP = "@adultplaygroundgroup"

BOT_OWNER_ID = 7276791218
BOT_OWNER_USERNAME = "Humble_Treasure"

user_state = {}
waiting_for_media = {}

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "User", 0, "", "")
    user_state[user.id] = "JOIN"

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/adultplaygroundchannel")],
        [InlineKeyboardButton("👥 Join Group", url="https://t.me/adultplaygroundgroup")],
        [InlineKeyboardButton("✅ Done", callback_data="join_done")]
    ]

    await update.message.reply_text(
        "🔞 18+ ONLY\n\nJoin BOTH channel & group, then click Done.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# JOIN CHECK
# =========================
async def join_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    try:
        c = await context.bot.get_chat_member(REQUIRED_CHANNEL, uid)
        g = await context.bot.get_chat_member(REQUIRED_GROUP, uid)
        if c.status in ["member","administrator","creator"] and g.status in ["member","administrator","creator"]:
            await show_main_menu(q, context)
        else:
            raise Exception
    except:
        await q.edit_message_text("❌ Join both channel & group first.")

# =========================
# MAIN MENU
# =========================
async def show_main_menu(q, context):
    keyboard = [
        [InlineKeyboardButton("💬 Chat", callback_data="menu_chat")],
        [InlineKeyboardButton("🎥 / 🖼 Media", callback_data="menu_media")],
        [InlineKeyboardButton("⭐ VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("ℹ Help", callback_data="menu_help")]
    ]
    await q.edit_message_text("🏠 Main Menu", reply_markup=InlineKeyboardMarkup(keyboard))

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "menu_chat":
        if not can_chat(uid) and not is_vip(uid):
            await q.edit_message_text("⚠ Daily limit reached. VIP removes limits.")
            return
        add_user_to_queue(uid)
        if pair_users(uid):
            await q.edit_message_text("💬 Paired. Start chatting.")
        else:
            await q.edit_message_text("⏳ Waiting for partner...")

    elif q.data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("👁 View Media", callback_data="media_view")],
            [InlineKeyboardButton("📤 Upload Media", callback_data="media_upload")],
            [InlineKeyboardButton("⬅ Back", callback_data="menu_back")]
        ]
        await q.edit_message_text("Choose:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "menu_vip":
        if is_vip(uid):
            await q.edit_message_text("⭐ You are already VIP.")
        else:
            await q.edit_message_text("⭐ Buy VIP — DM @" + BOT_OWNER_USERNAME)

    elif q.data == "menu_help":
        await q.edit_message_text("DM @" + BOT_OWNER_USERNAME)

    elif q.data == "menu_back":
        await show_main_menu(q, context)

# =========================
# MEDIA STEP
# =========================
async def media_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "media_view":
        keyboard = [
            [InlineKeyboardButton("🎥 Videos", callback_data="watch_videos")],
            [InlineKeyboardButton("🖼 Pictures", callback_data="watch_pictures")],
            [InlineKeyboardButton("⬅ Back", callback_data="menu_back")]
        ]
        await q.edit_message_text("View:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "media_upload":
        keyboard = [
            [InlineKeyboardButton("📤 Video", callback_data="upload_video")],
            [InlineKeyboardButton("📤 Picture", callback_data="upload_picture")],
            [InlineKeyboardButton("⬅ Back", callback_data="menu_back")]
        ]
        await q.edit_message_text("Upload:", reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# MEDIA ACTIONS
# =========================
async def media_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    vip = is_vip(uid)

    if q.data == "watch_videos":
        f, m = get_next_video_for_user(uid, vip)
        if f:
            await context.bot.send_video(uid, f)
            log_view(uid, "video", f)
        else:
            await q.edit_message_text(m)

    elif q.data == "watch_pictures":
        f, m = get_next_picture_for_user(uid, vip)
        if f:
            await context.bot.send_photo(uid, f)
            log_view(uid, "picture", f)
        else:
            await q.edit_message_text(m)

    elif q.data == "upload_video":
        waiting_for_media[uid] = "video"
        await q.edit_message_text("Send video (≤5MB)")

    elif q.data == "upload_picture":
        waiting_for_media[uid] = "picture"
        await q.edit_message_text("Send picture (≤1MB)")

    elif q.data == "menu_back":
        await show_main_menu(q, context)

# =========================
# MEDIA UPLOAD
# =========================
async def handle_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in waiting_for_media:
        return

    t = waiting_for_media[uid]

    if t == "video" and update.message.video:
        s, m = upload_video(uid, update.message.video.file_id, update.message.video.file_size/1e6)
        if s:
            log_upload(uid, "video", update.message.video.file_id)

    elif t == "picture" and update.message.photo:
        p = update.message.photo[-1]
        s, m = upload_picture(uid, p.file_id, p.file_size/1e6)
        if s:
            log_upload(uid, "picture", p.file_id)
    else:
        await update.message.reply_text("❌ Wrong file type.")
        return

    await update.message.reply_text(m)
    waiting_for_media.pop(uid)

# =========================
# VIP COMMAND (ADMIN)
# =========================
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage:\n/vip <user_id> <days>")
        return

    try:
        uid = int(context.args[0])
        days = int(context.args[1])
    except:
        await update.message.reply_text("User ID & days must be numbers.")
        return

    grant_vip(uid, days)
    await update.message.reply_text(f"✅ VIP granted to {uid} for {days} days")

    try:
        await context.bot.send_message(uid, f"⭐ You are VIP for {days} days!")
    except:
        pass

# =========================
# ADMIN DASHBOARD
# =========================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    keyboard = [
        [InlineKeyboardButton("Total Users", callback_data="admin_total_users")],
        [InlineKeyboardButton("Total Videos", callback_data="admin_total_videos")],
        [InlineKeyboardButton("Total Pictures", callback_data="admin_total_pictures")],
        [InlineKeyboardButton("Active VIP", callback_data="admin_active_vip")],
        [InlineKeyboardButton("Views Today", callback_data="admin_views_today")],
        [InlineKeyboardButton("New VIPs", callback_data="admin_new_vips")],
        [InlineKeyboardButton("Uploads Today", callback_data="admin_uploads")],
        [InlineKeyboardButton("Error Logs", callback_data="admin_errors")],
    ]
    await update.message.reply_text("🛠 Admin Dashboard", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    text = ""
    uid = update.effective_user.id

    if uid != BOT_OWNER_ID:
        await q.edit_message_text("❌ Unauthorized")
        return

    if q.data == "admin_total_users":
        text = f"Total Users: {get_global_stats().get('total_users',0)}"
    elif q.data == "admin_total_videos":
        text = f"Total Videos: {get_global_stats().get('total_videos',0)}"
    elif q.data == "admin_total_pictures":
        text = f"Total Pictures: {get_global_stats().get('total_pictures',0)}"
    elif q.data == "admin_active_vip":
        text = f"Active VIPs: {len(get_active_vips())}"
    elif q.data == "admin_views_today":
        text = f"Views Today: {get_views_today()}"
    elif q.data == "admin_new_vips":
        text = f"New VIPs: {len(get_new_vips())}"
    elif q.data == "admin_uploads":
        text = f"Uploads Today: {get_uploads_today()}"
    elif q.data == "admin_errors":
        text = "Error logs: [Check your server logs]"

    keyboard = [[InlineKeyboardButton("⬅ Back", callback_data="admin_back")]]
    if q.data == "admin_back":
        return await admin_command(update, context)

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# MAIN
# =========================
def main():
    init_vip_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(join_done_callback, pattern="join_done"))
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="menu_"))
    app.add_handler(CallbackQueryHandler(media_choice_handler, pattern="media_"))
    app.add_handler(CallbackQueryHandler(media_button_handler, pattern="watch_|upload_|menu_back"))
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="admin_"))

    # Media
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media_upload))

    print("✅ Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()