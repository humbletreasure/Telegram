import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from database import add_user, get_user
from media import upload_video, upload_picture, get_next_video_for_user, get_next_picture_for_user
from chat import add_user_to_queue, pair_users, send_message, end_chat, can_chat
from vip import check_vip_status

# =========================
# BOT TOKEN
# =========================
BOT_TOKEN = "8587121023:AAGhCHgjTr7s95WH-IN17_z5cU8uHZC_wdY"

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

    # Initialize user in DB
    add_user(user_id, username, 0, "", "")

    user_state[user_id] = "JOIN_CHECK"

    await update.message.reply_text(
        f"Hello @{username} 👋\n\n"
        "Welcome as a social user to the board.\n\n"
        "This is an adult space strictly for 18+ content.\n"
        "By continuing, you agree that you are responsible for your actions.\n\n"
        "⚠️ If you are under 18, you proceed at your own risk.\n\n"
        "To continue, please type 'done' after joining our channel and group:\n"
        f"📢 Channel: {REQUIRED_CHANNEL}\n"
        f"👥 Group: {REQUIRED_GROUP}"
    )

# =========================
# JOIN CHECK
# =========================
async def handle_join_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if user_state.get(user_id) != "JOIN_CHECK" or text != "done":
        return

    # Skip actual Telegram join check for reply-based flow
    user_state[user_id] = "ASK_AGE"
    await update.message.reply_text("✅ Verified! Please enter your age (18+ only):")

# =========================
# AGE HANDLER
# =========================
async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) != "ASK_AGE":
        return

    try:
        age = int(update.message.text)
        if age < 18:
            await update.message.reply_text("❌ Access denied. This space is strictly 18+.")
            return

        user_profile[user_id] = {"age": age}
        user_state[user_id] = "ASK_GENDER"
        await update.message.reply_text("Please type your gender (Male/Female):")
    except:
        await update.message.reply_text("Please enter a valid number for age.")

# =========================
# GENDER HANDLER
# =========================
async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "ASK_GENDER":
        return

    gender = update.message.text.strip().capitalize()
    if gender not in ["Male", "Female"]:
        await update.message.reply_text("Please type Male or Female.")
        return

    user_profile[user_id]["gender"] = gender
    user_state[user_id] = "ASK_COUNTRY"
    await update.message.reply_text("Please type your country:")

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
    await update.message.reply_text(
        "🏠 Main Menu\n\n"
        "1️⃣ Chat\n"
        "2️⃣ Videos\n"
        "3️⃣ Pictures\n"
        "4️⃣ VIP\n"
        "5️⃣ Help\n\n"
        "Type the number of your choice:"
    )
    user_state[update.effective_user.id] = "MENU_CHOICE"

# =========================
# MENU CHOICE HANDLER
# =========================
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "MENU_CHOICE":
        return

    choice = update.message.text.strip()
    vip = check_vip_status(user_id)

    if choice == "1":  # Chat
        if not can_chat(user_id):
            await update.message.reply_text("⚠ You reached your daily chat limit. Upgrade to VIP for unlimited.")
            return
        add_user_to_queue(user_id)
        partner_id = pair_users(user_id)
        if partner_id:
            await update.message.reply_text("💬 Paired! Start chatting with your partner now.")
        else:
            await update.message.reply_text("⏳ Waiting for a partner to join...")
    elif choice == "2":  # Videos
        await update.message.reply_text(
            "🎥 Videos Menu:\n"
            "Type 'watch' to watch videos or 'upload' to send a video."
        )
        user_state[user_id] = "VIDEO_MENU"
    elif choice == "3":  # Pictures
        await update.message.reply_text(
            "🖼 Pictures Menu:\n"
            "Type 'watch' to view pictures or 'upload' to send a picture."
        )
        user_state[user_id] = "PICTURE_MENU"
    elif choice == "4":  # VIP
        await update.message.reply_text("⭐ VIP system loading...\nUpgrade functionality coming soon.")
    elif choice == "5":  # Help
        await update.message.reply_text(
            "ℹ Help\n\n"
            "• Adults only (18+)\n"
            "• Be respectful\n"
            "• Follow rules\n\n"
            "Type the number of the menu to navigate."
        )
    else:
        await update.message.reply_text("❌ Invalid choice. Please type a number from 1 to 5.")

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
                await update.message.reply_text(f"🎥 Video ready! File ID: {file_id}")
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
                await update.message.reply_text(f"🖼 Picture ready! File ID: {file_id}")
            else:
                await update.message.reply_text(msg)
        elif text == "upload":
            waiting_for_media[user_id] = "picture"
            await update.message.reply_text("Send your picture file (max 1MB).")
        else:
            await update.message.reply_text("Type 'watch' or 'upload'.")

# =========================
# HANDLE FILES
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
    elif media_type == "picture" and update.message.photo:
        file = update.message.photo[-1]  # highest quality
        file_size_mb = file.file_size / (1024*1024)
    else:
        await update.message.reply_text("❌ Invalid file type. Try again.")
        return

    # Upload via media.py
    if media_type == "video":
        success, msg = upload_video(user_id, file.file_id, file_size_mb)
    else:
        success, msg = upload_picture(user_id, file.file_id, file_size_mb)

    await update.message.reply_text(msg)
    if success:
        waiting_for_media.pop(user_id)

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Start command
    app.add_handler(CommandHandler("start", start))

    # Join, age, gender, country
    app.add_handler(MessageHandler(filters.Regex(r"done"), handle_join_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country))

    # Menu
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_picture_menu))

    # Media upload
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media_upload))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()