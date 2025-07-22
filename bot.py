
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

print(">>> BOT IS BOOTING...")
print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))
print("ADMINS:", os.getenv("ADMINS"))
print("CHANNEL_ID:", os.getenv("CHANNEL_ID"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif dan menerima perintah.")

def is_admin(user_id):
    return user_id in ADMINS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("Ini admin panel.")
    else:
        await update.message.reply_text("Kamu bukan admin.")

def main():
    print("🤖 Bot siap jalan.")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adminpanel", admin_panel))
    app.run_polling()

if __name__ == "__main__":
    main()
