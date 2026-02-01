import asyncio
import os
from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606     # канал джерела
TARGET_CHAT_ID = -1001321059832     # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet" # username джерела без @
ALBUM_DELAY = 1.5                   # час очікування на збирання альбому
LOG_FILE = "forward_log.txt"        # логування пересланих постів
# ================================================

# Буфер для альбомів
album_buffer = {}       # media_group_id -> list(InputMediaPhoto/Video)
album_first_msg = {}    # media_group_id -> first message_id

def log_forward(message_type: str, link: str, count: int = 1):
    """Логування пересланих постів у файл та консоль"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message_type} | {count} items | {link}\n"
    print(entry.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Відправка альбому після таймера"""
    if group_id not in album_buffer:
        return

    media_list = album_buffer[group_id]
    first_msg_id = album_first_msg[group_id]

    if media_list:
        # Додаємо клікабельний caption для останнього елемента
        last_item = media_list[-1]
        link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"
        if isinstance(last_item, InputMediaPhoto):
            media_list[-1] = InputMediaPhoto(
                media=last_item.media,
                caption=f"<a href='{link}'>Джерело</a>",
                parse_mode="HTML"
            )
        elif isinstance(last_item, InputMediaVideo):
            media_list[-1] = InputMediaVideo(
                media=last_item.media,
                caption=f"<a href='{link}'>Джерело</a>",
                parse_mode="HTML"
            )

        await context.bot.send_media_group(
            chat_id=TARGET_CHAT_ID,
            media=media_list
        )
        log_forward("ALBUM", link, count=len(media_list))

    # Очищаємо буфер
    del album_buffer[group_id]
    del album_first_msg[group_id]

async def album_timer(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Чекаємо ALBUM_DELAY секунд перед відправкою альбому"""
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
            album_buffer[group_id] = []
            album_first_msg[group_id] = msg.message_id
            asyncio.create_task(album_timer(context, group_id))

        if msg.photo:
            album_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
        elif msg.video:
            album_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))
        return

    # ===== Одиночне фото/відео/текст =====
    source_post_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"
    caption = f"<a href='{source_post_link}'>Джерело</a>"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("PHOTO", source_post_link)
    elif msg.video:
        await context.bot.send_video(
            chat_id=TARGET_CHAT_ID,
            video=msg.video.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("VIDEO", source_post_link)
    elif msg.text:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"{msg.text}\n\n<a href='{source_post_link}'>Джерело</a>",
            parse_mode="HTML"
        )
        log_forward("TEXT", source_post_link)

async def main_async():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Бот запущений...")
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    # Створюємо лог файл, якщо його немає
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w", encoding="utf-8").close()
    asyncio.run(main_async())
