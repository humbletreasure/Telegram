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
import asyncio

# =========================
# BOT TOKEN
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
# IN-MEMORY STATE
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
        "Welcome as a social user to the board.\n"
        "This is an adult space strictly for 18+ content.\n"
        "By continuing, you agree that you are responsible for your actions.\n\n"
        "⚠️ If you are under 18, you proceed at your own risk.\n\n"
        "Join BOTH our channel and group, then press Done.",
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
            "❌ You must join BOTH the channel and group.\nClick Done again after joining."
        )

# =========================
# AGE SELECTION
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
        if current_age < 60: current_age += 1
    elif query.data == "age_down":
        if current_age > 18: current_age -= 1
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
    user_state[user_id] = "COUNTRY_SELECTION"
    await send_country_selector(query)

# =========================
# COUNTRY SELECTION
# =========================
COUNTRIES = ["Nigeria", "USA", "UK", "India", "Canada", "Germany", "France", "Other"]
async def send_country_selector(query):
    keyboard = [[InlineKeyboardButton(c, callback_data=f"country_{c}")] for c in COUNTRIES]
    await query.edit_message_text("Select your country:", reply_markup=InlineKeyboardMarkup(keyboard))

async def country_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    country = query.data.replace("country_", "")
    user_profile[user_id]["country"] = country
    user_state[user_id] = "MAIN_MENU"
    await show_main_menu(query, context)

# =========================
# MAIN MENU
# =========================
async def show_main_menu(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Chat", callback_data="menu_chat")],
        [InlineKeyboardButton("🎥/🖼 Media", callback_data="menu_media")],
        [InlineKeyboardButton("⭐ VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("ℹ Help", callback_data="menu_help")],
        [InlineKeyboardButton("📜 Rules", callback_data="menu_rules")],
        [InlineKeyboardButton("🤖 About", callback_data="menu_about")]
    ]
    text = "🏠 Main Menu\nChoose an option:"
    if isinstance(query_or_update, Update):
        await query_or_update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query_or_update.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
        await send_media_choice(query)
    elif data == "menu_vip":
        await query.edit_message_text("⭐ VIP system loading...")
    elif data == "menu_help":
        await query.edit_message_text(f"💬 DM the bot owner: @{BOT_OWNER_USERNAME}")
    elif data == "menu_rules":
        await query.edit_message_text(
            "📜 Bot Rules:\n1. 18+ only\n2. Be respectful\n3. No illegal content\n4. No spamming\n5. Follow instructions"
        )
    elif data == "menu_about":
        await query.edit_message_text(
            "🤖 About:\nAdult social bot. Chat, upload videos/pictures, VIP perks, button navigation."
        )

# =========================
# MEDIA CHOICE
# =========================
async def send_media_choice(query):
    keyboard = [
        [InlineKeyboardButton("🎥 Watch Videos", callback_data="watch_videos")],
        [InlineKeyboardButton("🖼 Watch Pictures", callback_data="watch_pictures")],
        [InlineKeyboardButton("📤 Upload Video", callback_data="upload_video")],
        [InlineKeyboardButton("📤 Upload Picture", callback_data="upload_picture")],
        [InlineKeyboardButton("⬅ Back", callback_data="menu_back")]
    ]
    await query.edit_message_text("Select an action:", reply_markup=InlineKeyboardMarkup(keyboard))

async def media_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    vip = check_vip_status(user_id)
    data = query.data

    if data == "watch_videos":
        file_id, msg = get_next_video_for_user(user_id, vip)
        if file_id:
            await context.bot.send_video(chat_id=user_id, video=file_id)
            log_view(user_id, "video", file_id)
        else:
            await query.edit_message_text(msg)
    elif data == "watch_pictures":
        file_id, msg = get_next_picture_for_user(user_id, vip)
        if file_id:
            await context.bot.send_photo(chat_id=user_id, photo=file_id)
            log_view(user_id, "picture", file_id)
        else:
            await query.edit_message_text(msg)
    elif data == "upload_video":
        waiting_for_media[user_id] = "video"
        await query.edit_message_text("Send your video file (max 5MB).")
    elif data == "upload_picture":
        waiting_for_media[user_id] = "picture"
        await query.edit_message_text("Send your picture file (max 1MB).")
    elif data == "menu_back":
        await show_main_menu(query, context)

# =========================
# MEDIA UPLOAD
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
        if success: log_upload(user_id, "video", file.file_id)
    elif media_type == "picture" and update.message.photo:
        file = update.message.photo[-1]
        file_size_mb = file.file_size / (1024*1024)
        success, msg = upload_picture(user_id, file.file_id, file_size_mb)
        if success: log_upload(user_id, "picture", file.file_id)
    else:
        await update.message.reply_text("❌ Invalid file type.")
        return

    await update.message.reply_text(msg)
    if success:
        waiting_for_media.pop(user_id)

# =========================
# BOT HELP
# =========================
BOT_OWNER_USERNAME = "Humble_Treasure"
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 DM @{BOT_OWNER_USERNAME} for help!")

# =========================
# ADMIN STATS
# =========================
BOT_OWNER_ID = 7276791218
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
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats))

    # Join Done
    app.add_handler(CallbackQueryHandler(join_done_callback, pattern="join_done"))

    # Age buttons
    app.add_handler(CallbackQueryHandler(age_button_handler, pattern="age_"))

    # Gender buttons
    app.add_handler(CallbackQueryHandler(gender_button_handler, pattern="gender_"))

    # Country buttons
    app.add_handler(CallbackQueryHandler(country_button_handler, pattern="country_"))

    # Main menu buttons
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="menu_"))

    # Media buttons
    app.add_handler(CallbackQueryHandler(media_button_handler, pattern="watch_|upload_|menu_back"))

    # Media upload
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media_upload))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())