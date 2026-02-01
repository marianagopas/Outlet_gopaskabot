import json
import os
from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606     # канал джерела
TARGET_CHAT_ID = -1001321059832     # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet" # username джерела без @
LOG_FILE = "forward_log.txt"        # логування пересланих постів
# ================================================

# Буфер для альбомів
album_buffer = {}       # media_group_id -> list(InputMediaPhoto/Video)
album_first_msg = {}    # media_group_id -> message_id першого фото

# ================== Логування ==================
def log_forward(message_type: str, link: str, count: int = 1):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message_type} | {count} items | {link}\n"
    print(entry.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

# ================== ВІДПРАВКА АЛЬБОМУ ==================
async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    if group_id not in album_buffer:
        return

    media_list = album_buffer[group_id]
    first_msg_id = album_first_msg[group_id]
    source_link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"

    if not media_list:
        return

    # Додаємо підпис у вигляді окремого повідомлення після альбому
    await context.bot.send_media_group(
        chat_id=TARGET_CHAT_ID,
        media=media_list
    )

    # Підпис з посиланням на оригінал
    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"📎 Джерело: <a href='{source_link}'>Перейти</a>",
        parse_mode="HTML"
    )

    log_forward("ALBUM", source_link, count=len(media_list))

    # Очищаємо буфер
    del album_buffer[group_id]
    del album_first_msg[group_id]

# ================== ЛОВИМО ПОВІДОМЛЕННЯ ==================
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = getattr(msg, "media_group_id", None)

    # Якщо новий альбом (або одиночне фото)
    if group_id:
        # Якщо буфер вже містить інший альбом, його треба закрити
        existing_groups = list(album_buffer.keys())
        for g_id in existing_groups:
            if g_id != group_id:
                await send_album(context, g_id)

        # Створюємо або додаємо до буфера
        if group_id not in album_buffer:
            album_buffer[group_id] = []
            album_first_msg[group_id] = msg.message_id

        if msg.photo:
            album_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
        elif msg.video:
            album_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))
        return

    # ===== Одиночне фото/відео/текст =====
    source_post_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=f"📎 Джерело: <a href='{source_post_link}'>Перейти</a>",
            parse_mode="HTML"
        )
        log_forward("PHOTO", source_post_link)
    elif msg.video:
        await context.bot.send_video(
            chat_id=TARGET_CHAT_ID,
            video=msg.video.file_id,
            caption=f"📎 Джерело: <a href='{source_post_link}'>Перейти</a>",
            parse_mode="HTML"
        )
        log_forward("VIDEO", source_post_link)
    elif msg.text:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"{msg.text}\n\n📎 Джерело: <a href='{source_post_link}'>Перейти</a>",
            parse_mode="HTML"
        )
        log_forward("TEXT", source_post_link)

# ================== MAIN ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()
