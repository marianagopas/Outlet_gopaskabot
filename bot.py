import asyncio
import os
import json
from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606
TARGET_CHAT_ID = -1001321059832
SOURCE_USERNAME = "Gopaska_outlet"
ALBUM_DELAY = 2.0  # секунд, щоб зібрати всі фото альбому
LOG_FILE = "forward_log.txt"
# ================================================

# Буфер альбомів
album_buffer = {}  # media_group_id -> {"media": [], "first_msg_id": int}

def log_forward(message_type: str, link: str, count: int = 1):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message_type} | {count} items | {link}\n"
    print(entry.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Відправляємо альбом і підпис після збору"""
    if group_id not in album_buffer:
        return

    data = album_buffer[group_id]
    media_list = data["media"]
    first_msg_id = data["first_msg_id"]

    if media_list:
        # Відправка альбому
        await context.bot.send_media_group(
            chat_id=TARGET_CHAT_ID,
            media=media_list
        )

        # Після альбому окреме повідомлення-підпис
        source_link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"<a href='{source_link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )

        log_forward("ALBUM", source_link, len(media_list))

    # Очищуємо буфер
    del album_buffer[group_id]

async def album_timer(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Чекаємо ALBUM_DELAY перед відправкою альбому"""
    await asyncio.sleep(ALBUM_DELAY)
    await send_album(context, group_id)

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = getattr(msg, "media_group_id", None)

    # ===== Альбом =====
    if group_id:
        if group_id not in album_buffer:
            album_buffer[group_id] = {
                "media": [],
                "first_msg_id": msg.message_id
            }
            asyncio.create_task(album_timer(context, group_id))

        if msg.photo:
            album_buffer[group_id]["media"].append(InputMediaPhoto(media=msg.photo[-1].file_id))
        elif msg.video:
            album_buffer[group_id]["media"].append(InputMediaVideo(media=msg.video.file_id))
        return

    # ===== Одиночне фото/відео/текст =====
    source_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"
    caption = f"<a href='{source_link}'>Переглянути джерело</a>"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("PHOTO", source_link)
    elif msg.video:
        await context.bot.send_video(
            chat_id=TARGET_CHAT_ID,
            video=msg.video.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("VIDEO", source_link)
    elif msg.text:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"{msg.text}\n\n<a href='{source_link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )
        log_forward("TEXT", source_link)

def main():
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w", encoding="utf-8").close()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
