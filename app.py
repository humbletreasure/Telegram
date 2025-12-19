import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from analytics import log_upload, log_view, get_global_stats, get_user_stats
from database import add_user, get_user
from media import (
    upload_video,
    upload_picture,
    get_next_video_for_user,
    get_next_picture_for_user
)
from chat import add_user_to_queue, pair_users, send_message, end_chat, can_chat
from vip import check_vip_status

# =========================
# BOT TOKEN (FROM ENV)
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

# =========================
# REQUIRED CHANNEL & GROUP
# =========================
REQUIRED_CHANNEL = "@adultplaygroundchannel"
REQUIRED_GROUP = "@adultplaygroundgroup"

# =========================
# IN-MEMORY USER STATE
# =========================
user_state = {}
user_profile = {}
waiting_for_media = {}  # Track if user is uploading video/picture

# =========================
# /START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or user.first_name or "User"
    user_id = user.id

    add_user(user_id, username, 0, "", "")

    user_state[user_id] = "JOIN_CHECK"

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("👥 Join Group", url=f"https://t.me/{REQUIRED_GROUP.replace('@','')}")],
        [InlineKeyboardButton("✅ Done", callback_data="join_done")]
    ]

    await update.message.reply_text(
        f"Hello @{username} 👋\n\n"
        "Welcome as a social user to the board.\n\n"
        "This is an adult space strictly for 18+ content.\n"
        "By continuing, you agree that you are responsible for your actions.\n\n"
        "⚠️ If you are under 18, you proceed at your own risk.\n\n"
        "To continue, join BOTH our channel and group and then press Done.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# JOIN CHECK BUTTON
# =========================
async def join_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Real join check
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP, user_id)

        if channel_member.status in ["member", "administrator", "creator"] and \
           group_member.status in ["member", "administrator", "creator"]:
            user_state[user_id] = "AGE_SELECTION"
            # Start age selection with buttons
            await send_age_selector(query, context)
        else:
            raise Exception()
    except:
        await query.edit_message_text(
            "❌ You must join BOTH the channel and group.\n\n"
            "Please join them and click Done again."
        )

# =========================
# AGE SELECTION BUTTONS
# =========================
async def send_age_selector(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query_or_update.from_user.id
    # default age 18 if not set
    current_age = user_profile.get(user_id, {}).get("age", 18)
    keyboard = [
        [
            InlineKeyboardButton("⏫", callback_data="age_up"),
            InlineKeyboardButton(f"{current_age}", callback_data="age_display"),
            InlineKeyboardButton("⏬", callback_data="age_down"),
        ],
        [InlineKeyboardButton("✅ Confirm", callback_data="age_confirm")]
    ]
    if isinstance(query_or_update, Update):
        await query_or_update.message.reply_text("Select your age:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query_or_update.edit_message_text("Select your age:", reply_markup=InlineKeyboardMarkup(keyboard))

async def age_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_age = user_profile.get(user_id, {}).get("age", 18)

    if query.data == "age_up":
        if current_age < 60:
            current_age += 1
    elif query.data == "age_down":
        if current_age > 18:
            current_age -= 1
    elif query.data == "age_confirm":
        user_profile[user_id]["age"] = current_age
        user_state[user_id] = "GENDER_SELECTION"
        await send_gender_selector(query)
        return

    # Update current age
    user_profile.setdefault(user_id, {})["age"] = current_age
    await send_age_selector(query, context)

# =========================
# GENDER SELECTION
# =========================
async def send_gender_selector(query):
    keyboard = [
        [InlineKeyboardButton("♂ Male", callback_data="gender_male")],
        [InlineKeyboardButton("♀ Female", callback_data="gender_female")]
    ]
    await query.edit_message_text("Select your gender:", reply_markup=InlineKeyboardMarkup(keyboard))

async def gender_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gender = "Male" if query.data == "gender_male" else "Female"
    user_profile[user_id]["gender"] = gender
    user_state[user_id] = "ASK_COUNTRY"
    await query.edit_message_text("Please type your country:")

# =========================
# COUNTRY HANDLER
# =========================
async def handle_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "ASK_COUNTRY":
        return
    country = update.message.text.strip()
    user_profile[user_id]["country"] = country
    user_state[user_id] = "MAIN_MENU"
    await show_main_menu(update, context)

# =========================
# MAIN MENU
# =========================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Chat", callback_data="menu_chat")],
        [InlineKeyboardButton("🎥 Videos", callback_data="menu_videos")],
        [InlineKeyboardButton("🖼 Pictures", callback_data="menu_pictures")],
        [InlineKeyboardButton("⭐ VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("ℹ Help", callback_data="menu_help")]
    ]
    await update.message.reply_text("🏠 Main Menu\nChoose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    vip = check_vip_status(user_id)

    if data == "menu_chat":
        if not can_chat(user_id):
            await query.edit_message_text("⚠ Daily chat limit reached. Upgrade to VIP for unlimited chats.")
            return
        add_user_to_queue(user_id)
        partner_id = pair_users(user_id)
        if partner_id:
            await query.edit_message_text("💬 Paired! Start chatting now.")
        else:
            await query.edit_message_text("⏳ Waiting for a partner...")
    elif data == "menu_videos":
        user_state[user_id] = "VIDEO_MENU"
        await query.edit_message_text("🎥 Videos Menu:\nType 'watch' or 'upload'.")
    elif data == "menu_pictures":
        user_state[user_id] = "PICTURE_MENU"
        await query.edit_message_text("🖼 Pictures Menu:\nType 'watch' or 'upload'.")
    elif data == "menu_vip":
        await query.edit_message_text("⭐ VIP system loading...")
    elif data == "menu_help":
        await query.edit_message_text(
            "ℹ Help\n• Adults only (18+)\n• Be respectful\n• Follow rules\nUse /start to restart."
        )

# =========================
# VIDEO & PICTURE HANDLERS
# =========================
async def handle_video_picture_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()
    vip = check_vip_status(user_id)

    if user_state.get(user_id) == "VIDEO_MENU":
        if text == "watch":
            file_id, msg = get_next_video_for_user(user_id, vip)
            if file_id:
                await update.message.reply_video(file_id)
                log_view(user_id, "video", file_id)
            else:
                await update.message.reply_text(msg)
        elif text == "upload":
            waiting_for_media[user_id] = "video"
            await update.message.reply_text("Send your video file (max 5MB).")
        else:
            await update.message.reply_text("Type 'watch' or 'upload'.")
    elif user_state.get(user_id) == "PICTURE_MENU":
        if text == "watch":
            file_id, msg = get_next_picture_for_user(user_id, vip)
            if file_id:
                await update.message.reply_photo(file_id)
                log_view(user_id, "picture", file_id)
            else:
                await update.message.reply_text(msg)
        elif text == "upload":
            waiting_for_media[user_id] = "picture"
            await update.message.reply_text("Send your picture file (max 1MB).")
        else:
            await update.message.reply_text("Type 'watch' or 'upload'.")

# =========================
# HANDLE MEDIA UPLOAD
# =========================
async def handle_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in waiting_for_media:
        return
    media_type = waiting_for_media[user_id]
    file = None
    file_size_mb = 0

    if media_type == "video" and update.message.video:
        file = update.message.video
        file_size_mb = file.file_size / (1024*1024)
        success, msg = upload_video(user_id, file.file_id, file_size_mb)
        if success:
            log_upload(user_id, "video", file.file_id)
    elif media_type == "picture" and update.message.photo:
        file = update.message.photo[-1]
        file_size_mb = file.file_size / (1024*1024)
        success, msg = upload_picture(user_id, file.file_id, file_size_mb)
        if success:
            log_upload(user_id, "picture", file.file_id)
    else:
        await update.message.reply_text("❌ Invalid file type.")
        return

    await update.message.reply_text(msg)
    if success:
        waiting_for_media.pop(user_id)

# =========================
# ADMIN /stats
# =========================
BOT_OWNER_ID = 7276791218  # Replace with your numeric Telegram ID
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Not authorized.")
        return
    global_stats = get_global_stats()
    await update.message.reply_text(f"📊 Global Stats:\n\n{global_stats}")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Start
    app.add_handler(CommandHandler("start", start))

    # Admin stats
    app.add_handler(CommandHandler("stats", stats))

    # Join done
    app.add_handler(CallbackQueryHandler(join_done_callback, pattern="join_done"))

    # Age buttons
    app.add_handler(CallbackQueryHandler(age_button_handler, pattern="age_"))

    # Gender buttons
    app.add_handler(CallbackQueryHandler(gender_button_handler, pattern="gender_"))

    # Menu buttons
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="menu_"))

    # Country input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country))

    # Menu text handling
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_picture_menu))

    # Media upload
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media_upload))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()