import os
import random
from datetime import datetime, date
from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler, filters
)
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Table, MetaData, select, and_
from sqlalchemy.orm import sessionmaker

# Env vars
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL")

# DB Setup
engine = create_engine(DATABASE_URL)
metadata = MetaData()

whitelist_table = Table("whitelist", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, unique=True))

log_table = Table("log", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("message", String),
    Column("image_used", String),
    Column("timestamp", DateTime))

quota_table = Table("quota", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("date", Date),
    Column("count", Integer))

metadata.create_all(engine)

# Tambahan table ban
ban_table = Table("ban", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, unique=True))
metadata.create_all(engine)

def is_banned(user_id):
    with Session() as session:
        return session.execute(select(ban_table).where(ban_table.c.user_id == user_id)).first() is not None

# Update fungsi handle_text untuk cek banned
if is_banned(uid):
    await update.message.reply_text("⛔ Kamu diblokir dari penggunaan bot.")
    return

# Tambahan tombol panel admin
[InlineKeyboardButton("⛔ Ban User", callback_data="ban_user"),
 InlineKeyboardButton("✅ Unban User", callback_data="unban_user")],
[InlineKeyboardButton("📋 Daftar Banned", callback_data="list_ban")]

# Tambahan di handle_callback
elif query.data == "list_ban":
    banned = session.execute(select(ban_table)).fetchall()
    text = "⛔ Banned Users:
" + "\n".join([str(u.user_id) for u in banned]) if banned else "📭 Tidak ada user yang diblokir."
    await query.edit_message_text(text)
elif query.data in ["ban_user", "unban_user"]:
    context.user_data["action"] = query.data
    await query.edit_message_text("Kirim ID user yang ingin diproses:")

# Tambahan di handle_admin_text
elif action == "ban_user":
    session.execute(ban_table.insert().values(user_id=target_id).prefix_with("ON CONFLICT DO NOTHING"))
    await update.message.reply_text(f"⛔ User {target_id} diblokir.")
elif action == "unban_user":
    session.execute(ban_table.delete().where(ban_table.c.user_id == target_id))
    await update.message.reply_text(f"✅ User {target_id} tidak diblokir lagi.")
Session = sessionmaker(bind=engine)

IMAGE_FOLDER = "images"

# Helper
def is_admin(user_id):
    return user_id in ADMINS

def is_whitelisted(user_id):
    with Session() as session:
        return session.execute(select(whitelist_table).where(whitelist_table.c.user_id == user_id)).first() is not None

def increment_quota(user_id):
    today = date.today()
    with Session() as session:
        result = session.execute(select(quota_table).where(and_(quota_table.c.user_id == user_id, quota_table.c.date == today))).first()
        if result:
            count = result[0].count
            if count >= 3:
                return False
            session.execute(quota_table.update().where(and_(quota_table.c.user_id == user_id, quota_table.c.date == today)).values(count=count+1))
        else:
            session.execute(quota_table.insert().values(user_id=user_id, date=today, count=1))
        session.commit()
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Gunakan bot ini untuk mengirim pesan anonim ke channel jika kamu sudah diizinkan.")

# Command admin
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    buttons = [
        [InlineKeyboardButton("👥 Lihat Whitelist", callback_data="list_whitelist")],
        [InlineKeyboardButton("➕ Tambah User", callback_data="add_user"),
         InlineKeyboardButton("❌ Hapus User", callback_data="remove_user")],
        [InlineKeyboardButton("📊 Log Terakhir", callback_data="view_log")]
    ]
    await update.message.reply_text("🛠 Admin Panel", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id): return
    with Session() as session:
        if query.data == "list_whitelist":
            users = session.execute(select(whitelist_table)).fetchall()
            text = "✅ Whitelist Users:
" + "\n".join([str(u.user_id) for u in users]) if users else "📭 Tidak ada user."
            await query.edit_message_text(text)
        elif query.data == "view_log":
            logs = session.execute(select(log_table).order_by(log_table.c.timestamp.desc()).limit(5)).fetchall()
            if not logs:
                await query.edit_message_text("📭 Belum ada log.")
                return
            log_text = "\n".join([f"{l.timestamp} - {l.user_id}: {l.message[:30]}" for l in logs])
            await query.edit_message_text("📊 Log Terakhir:\n" + log_text)
        elif query.data in ["add_user", "remove_user"]:
            context.user_data["action"] = query.data
            await query.edit_message_text("Kirim ID user yang ingin diproses:")

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    action = context.user_data.get("action")
    if not action: return
    try:
        target_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("ID tidak valid.")
        return
    with Session() as session:
        if action == "add_user":
            session.execute(whitelist_table.insert().values(user_id=target_id).prefix_with("ON CONFLICT DO NOTHING"))
            await update.message.reply_text(f"✅ User {target_id} ditambahkan.")
        else:
            session.execute(whitelist_table.delete().where(whitelist_table.c.user_id == target_id))
            await update.message.reply_text(f"❌ User {target_id} dihapus.")
        session.commit()
    context.user_data["action"] = None

# Posting
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_admin(uid) and context.user_data.get("action"):
        return await handle_admin_text(update, context)
    if not is_whitelisted(uid):
        await update.message.reply_text("❌ Kamu belum diizinkan.")
        return
    if not increment_quota(uid):
        await update.message.reply_text("⚠️ Batas 3 kiriman per hari tercapai.")
        return
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Pesan kosong.")
        return
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not images:
        await update.message.reply_text("Gambar tidak ditemukan.")
        return
    img = random.choice(images)
    with open(os.path.join(IMAGE_FOLDER, img), 'rb') as f:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=InputFile(f), caption=f"🗣️ Kiriman anonim:\n\n{text}")
    with Session() as session:
        session.execute(log_table.insert().values(user_id=uid, message=text, image_used=img, timestamp=datetime.utcnow()))
        session.commit()
    await update.message.reply_text("✅ Terkirim secara anonim.")

async def reject_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Hanya pesan teks yang diizinkan.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(~filters.TEXT, reject_non_text))
    print("🤖 Bot siap jalan.")
    app.run_polling()

if __name__ == "__main__":
    main()
