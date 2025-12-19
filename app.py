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
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP, user_id)

        if channel_member.status in ["member", "administrator", "creator"] and \
           group_member.status in ["member", "administrator", "creator"]:
            user_state[user_id] = "AGE_SELECTION"
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
        [InlineKeyboardButton("🎥 Media", callback_data="menu_media")],
        [InlineKeyboardButton("⭐ VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("ℹ Help", callback_data="menu_help")],
        [InlineKeyboardButton("📜 Rules", callback_data="menu_rules")],
        [InlineKeyboardButton("🤖 About", callback_data="menu_about")]
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
    elif data == "menu_media":
        await send_media_menu(user_id, query, context)
    elif data == "menu_vip":
        await query.edit_message_text("⭐ VIP system loading...")
    elif data == "menu_help":
        await help_command(query, context)
    elif data == "menu_rules":
        await rules_command(query, context)
    elif data == "menu_about":
        await about_command(query, context)

# =========================
# MEDIA MENU BUTTONS
# =========================
async def send_media_menu(user_id, query_or_update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎥 Watch Videos", callback_data="watch_videos")],
        [InlineKeyboardButton("🖼 Watch Pictures", callback_data="watch_pictures")],
        [InlineKeyboardButton("⬆ Upload Video", callback_data="upload_video")],
        [InlineKeyboardButton("⬆ Upload Picture", callback_data="upload_picture")],
        [InlineKeyboardButton("⬅ Back to Main Menu", callback_data="menu_back")]
    ]
    if isinstance(query_or_update, Update):
        await query_or_update.message.reply_text("Choose an action:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query_or_update.edit_message_text("Choose an action:", reply_markup=InlineKeyboardMarkup(keyboard))

async def media_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    vip = check_vip_status(user_id)

    if query.data == "watch_videos":
        file_id, msg = get_next_video_for_user(user_id, vip)
        if file_id:
            await query.message.reply_video(file_id)
            log_view(user_id, "video", file_id)
        else:
            await query.message.reply_text(msg)

    elif query.data == "watch_pictures":
        file_id, msg = get_next_picture_for_user(user_id, vip)
        if file_id:
            await query.message.reply_photo(file_id)
            log_view(user_id, "picture", file_id)
        else:
            await query.message.reply_text(msg)

    elif query.data == "upload_video":
        waiting_for_media[user_id] = "video"
        await query.edit_message_text("Send your video file (max 5MB).")

    elif query.data == "upload_picture":
        waiting_for_media[user_id] = "picture"
        await query.edit_message_text("Send your picture file (max 1MB).")

    elif query.data == "menu_back":
        user_state[user_id] = "MAIN_MENU"
        await show_main_menu(query, context)

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
# /HELP, /RULES, /ABOUT COMMANDS
# =========================
BOT_OWNER_USERNAME = "Humble_Treasure"  # Replace with your Telegram username

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💬 Need help? You can DM the bot owner directly:\n"
        f"Telegram: @{BOT_OWNER_USERNAME}\n\n"
        "Or use the main menu /start to navigate the bot features."
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 Bot Rules:\n\n"
        "1️⃣ This space is strictly 18+.\n"
        "2️⃣ Be respectful to other users.\n"
        "3️⃣ Do not share illegal content.\n"
        "4️⃣ Spamming or harassment is prohibited.\n"
        "5️⃣ Follow instructions provided by the bot.\n"
        "6️⃣ VIP features are optional but offer extra perks.\n\n"
        "⚠ Violating rules may result in restriction or ban."
    )
    await update.message.reply_text(rules_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "🤖 About This Bot:\n\n"
        "This is an adult-only social bot for 18+ users to chat, "
        "share videos and pictures safely, and enjoy VIP features.\n\n"
        "• Fully interactive button-based navigation.\n"
        "• Supports chat pairing, media upload, and viewing.\n"
        "• Age verification and content restrictions in place.\n\n"
        "Use /start to begin your experience."
    )
    await update.message.reply_text(about_text)

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

    # Start command
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats))

    # CallbackQueryHandlers
    app.add_handler(CallbackQueryHandler(join_done_callback, pattern="join_done"))
    app.add_handler(CallbackQueryHandler(age_button_handler, pattern="age_"))
    app.add_handler(CallbackQueryHandler(gender_button_handler, pattern="gender_"))
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="menu_"))
    app.add_handler(CallbackQueryHandler(media_menu_handler, pattern="^(watch_|upload_|menu_back)$"))

    # Country input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country))

    # Media upload
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media_upload))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()