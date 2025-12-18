
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
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# BOT TOKEN FROM ENV
# =========================
BOT_TOKEN = "8587121023:AAGhCHgjTr7s95WH-IN17_z5cU8uHZC_wdY"
if not BOT_TOKEN:
    raise Exception("Please set the BOT_TOKEN environment variable!")

# =========================
# REQUIRED CHANNEL & GROUP
# =========================
REQUIRED_CHANNEL = "https://t.me/adultplaygroundchannel"
REQUIRED_GROUP = "https://t.me/adultplaygroundgroup"

# =========================
# IN-MEMORY USER STATE (DB LATER)
# =========================
user_state = {}
user_profile = {}

# =========================
# /START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or user.first_name or "User"

    user_state[user.id] = "JOIN_CHECK"

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("👥 Join Group", url=f"https://t.me/{REQUIRED_GROUP.replace('@','')}")],
        [InlineKeyboardButton("✅ Done", callback_data="check_join")]
    ]

    await update.message.reply_text(
        f"Hello @{username} 👋\n\n"
        "Welcome as a social user to the board.\n\n"
        "This is an adult space strictly for 18+ content.\n"
        "By continuing, you agree that you are responsible for your actions.\n\n"
        "⚠️ If you are under 18, you proceed at your own risk.\n\n"
        "To continue, you must join BOTH our channel and group.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# JOIN CHECK
# =========================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    try:
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP, user_id)

        if channel_member.status in ["member", "administrator", "creator"] and \
           group_member.status in ["member", "administrator", "creator"]:

            user_state[user_id] = "ASK_AGE"
            await query.edit_message_text("✅ Verified!\n\nPlease enter your age (18+ only):")
        else:
            raise Exception()

    except:
        await query.edit_message_text(
            "❌ You must join BOTH the channel and group.\n\n"
            "Please join them and click Done again."
        )

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

        keyboard = [
            [InlineKeyboardButton("♂ Male", callback_data="gender_male")],
            [InlineKeyboardButton("♀ Female", callback_data="gender_female")]
        ]

        await update.message.reply_text(
            "Select your gender:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await update.message.reply_text("Please enter a valid number for age.")

# =========================
# GENDER HANDLER
# =========================
async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text(
        "🏠 Main Menu\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# MENU ROUTER (PLACEHOLDERS)
# =========================
async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_chat":
        await query.edit_message_text("💬 Chat system loading...\n(Will be activated next)")
    elif query.data == "menu_videos":
        await query.edit_message_text("🎥 Video system loading...\n(Upload & watch coming next)")
    elif query.data == "menu_pictures":
        await query.edit_message_text("🖼 Picture system loading...\n(Upload & watch coming next)")
    elif query.data == "menu_vip":
        await query.edit_message_text("⭐ VIP system loading...\n(Subscription coming next)")
    elif query.data == "menu_help":
        await query.edit_message_text(
            "ℹ Help\n\n"
            "• Adults only (18+)\n"
            "• Be respectful\n"
            "• Follow rules\n\n"
            "Use /start to restart."
        )

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(gender_handler, pattern="gender_"))
    app.add_handler(CallbackQueryHandler(menu_router, pattern="menu_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()