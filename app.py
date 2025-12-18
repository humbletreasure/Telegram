import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from database import add_user, get_user, get_today_limits, increment_limit
from media import upload_video, upload_picture, get_next_video_for_user, get_next_picture_for_user
from chat import add_user_to_queue, pair_users, send_message, end_chat, can_chat
from vip import check_vip_status, make_user_vip

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

    # We skip actual Telegram join check in reply-based version
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
            await update.message.reply_text(f"💬 Paired! Start chatting with your partner now.")
        else:
            await update.message.reply_text("⏳ Waiting for a partner to join...")
    elif choice == "2":  # Videos
        file_id, msg = get_next_video_for_user(user_id, vip)
        if file_id:
            await update.message.reply_text(f"🎥 Video ready! File ID: {file_id}")
        else:
            await update.message.reply_text(msg)
    elif choice == "3":  # Pictures
        file_id, msg = get_next_picture_for_user(user_id, vip)
        if file_id:
            await update.message.reply_text(f"🖼 Picture ready! File ID: {file_id}")
        else:
            await update.message.reply_text(msg)
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
# MESSAGE HANDLER (CHAT REPLIES)
# =========================
async def handle_chat_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chat.active_chats:
        success, msg = send_message(user_id, update.message.text, context.bot.send_message)
        if not success:
            await update.message.reply_text(msg)

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Start & Setup
    app.add_handler(CommandHandler("start", start))

    # User flow handlers
    app.add_handler(MessageHandler(filters.Regex(r"done"), handle_join_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))

    # Chat messages
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_messages))
    # You can activate chat after integrating fully

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()