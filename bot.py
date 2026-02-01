import json
import os
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# === Налаштування ===
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606
TARGET_CHANNEL_ID = -1001321059832
SOURCE_USERNAME = "Gopaska_outlet"  # username каналу без @
JSON_FILE = "albums.json"
ALBUM_TIMEOUT = 10  # секунд

# === Завантаження або створення JSON ===
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        albums = json.load(f)
else:
    albums = {}

# Буфер для таймерів
album_timers = {}  # media_group_id -> asyncio.Task

def save_albums():
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(albums, f, ensure_ascii=False, indent=2)

# === Відправка альбому ===
async def send_album(media_group_id, context: ContextTypes.DEFAULT_TYPE):
    if media_group_id not in albums:
        return

    album = albums[media_group_id]
    media_items = album["media"]
    first_msg_id = album["first_message_id"]

    output_media = []
    for i, item in enumerate(media_items):
        caption = None
        if i == len(media_items) - 1:
            caption = f"<a href='https://t.me/{SOURCE_USERNAME}/{first_msg_id}'>Outlet</a>"
        output_media.append(InputMediaPhoto(media=item["file_id"], caption=caption))

    if output_media:
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=output_media)

    # Очищаємо після відправки
    del albums[media_group_id]
    save_albums()
    if media_group_id in album_timers:
        del album_timers[media_group_id]

# === Таймер на альбом ===
async def schedule_album_send(media_group_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(ALBUM_TIMEOUT)
    await send_album(media_group_id, context)

# === Ловимо повідомлення з каналу ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat_id != SOURCE_CHANNEL_ID:
        return

    media_group_id = getattr(message, "media_group_id", None)
    if not message.photo:
        return  # поки працюємо лише з фото

    file_id = message.photo[-1].file_id

    if media_group_id:
        # Новий альбом
        if media_group_id not in albums:
            albums[media_group_id] = {
                "media": [],
                "first_message_id": message.message_id
            }

        albums[media_group_id]["media"].append({"file_id": file_id})
        save_albums()

        # Скасовуємо старий таймер, якщо є
        if media_group_id in album_timers:
            album_timers[media_group_id].cancel()

        # Запускаємо новий таймер
        task = asyncio.create_task(schedule_album_send(media_group_id, context))
        album_timers[media_group_id] = task
    else:
        # Одиночне фото
        caption = f"<a href='https://t.me/{SOURCE_USERNAME}/{message.message_id}'>Outlet</a>"
        await context.bot.send_photo(chat_id=TARGET_CHANNEL_ID, photo=file_id, caption=caption)

# === Main ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
