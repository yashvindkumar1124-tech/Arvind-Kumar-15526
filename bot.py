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
MINI_APP_URL = os.environ.get("https://yashbhai.vercel.app", "https://yashbhai.vercel.app")

# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start command """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🟢 Open Token Generator",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ],
        [
            InlineKeyboardButton("🔴 Channel", url="https://t.me/YASHBHAI_GC"),
            InlineKeyboardButton("🔴 Support", url="https://t.me/YASHBHAIx")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Telegram requires non-empty text
    await update.message.reply_text(
        "👋 Welcome to YASH Token Generator!\n\n"
        "Click the button below to open the Mini App 👇",
        reply_markup=reply_markup
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /help command """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🟢 Open Token Generator",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "ℹ️ Help\n\n"
        "Click the button below to open the Token Generator Mini App.",
        reply_markup=reply_markup
    )


def main():
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
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
