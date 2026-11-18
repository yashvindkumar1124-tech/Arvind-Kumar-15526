"""
YASH Token Generator - Telegram Bot + Mini App
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# ═══════════════════════════════════════════════════════════════
#   ⚙️ CONFIG — Add your details here
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9190836196:AAFhj0dYbaII3jLJEk1OXfTWNXLYqcKzYmc")

# Mini App URL (set this after you host the website)
# Example: https://your-app.vercel.app
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://your-app.vercel.app")

# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start command """
    user = update.effective_user
    name = user.first_name or "User"

    keyboard = [
        [
            InlineKeyboardButton(
                text="🔥 Open Token Generator",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ],
        [
            InlineKeyboardButton("📢 Channel", url="https://t.me/YASHBHAI_GC"),
            InlineKeyboardButton("💬 Support", url="https://t.me/YASHBHAIx")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"👋 Hello <b>{name}</b>!\n\n"
        f"💜 <b>YASH Token Generator</b>\n"
        f"Free Fire Access Token & JWT Generator\n\n"
        f"👇 Click the button below to open the Mini App:"
    )

    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /help command """
    text = (
        "📖 <b>How to use:</b>\n\n"
        "1. Press /start\n"
        "2. Click the <b>Open Token Generator</b> button\n"
        "3. The Mini App will open\n"
        "4. Paste your Eat Token\n"
        "5. Press Generate Token"
    )
    await update.message.reply_text(text, parse_mode="HTML")


def main():
    if not BOT_TOKEN or BOT_TOKEN.strip() == "" or "AAFhj0dYbaII3jLJEk1OXfTWNXLYqcKzYmc" not in BOT_TOKEN:
        print("❌ Error: BOT_TOKEN is not set properly!")
        print("   Set the BOT_TOKEN environment variable or paste it in bot.py.")
        return

    print("=" * 50)
    print("  💜 YASH Token Bot Starting...")
    print(f"  🌐 Mini App URL: {MINI_APP_URL}")
    print("=" * 50)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    print("✅ Bot is running... Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
