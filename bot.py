import json
import os
import asyncio
import uuid
from telegram import Update, InputMediaPhoto, InputMediaVideo
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

# Таймери для альбомів
album_timers = {}  # album_id -> asyncio.Task

def save_albums():
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(albums, f, ensure_ascii=False, indent=2)

# === Відправка альбому ===
async def send_album(album_id, context: ContextTypes.DEFAULT_TYPE):
    if album_id not in albums:
        return

    album = albums[album_id]
    media_items = album["media"]
    first_msg_id = album["first_message_id"]

    output_media = []
    for item in media_items:
        if item["type"] == "photo":
            output_media.append(InputMediaPhoto(media=item["file_id"]))
        elif item["type"] == "video":
            output_media.append(InputMediaVideo(media=item["file_id"]))

    if output_media:
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=output_media)

    # Клікабельний підпис Outlet після альбому
    caption = f"<a href='https://t.me/{SOURCE_USERNAME}/{first_msg_id}'>Outlet</a>"
    await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=caption, parse_mode="HTML")

    # Очищаємо після відправки
    del albums[album_id]
    save_albums()
    if album_id in album_timers:
        del album_timers[album_id]

# === Таймер на альбом ===
async def schedule_album_send(album_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(ALBUM_TIMEOUT)
    await send_album(album_id, context)

# === Ловимо повідомлення з каналу ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat_id != SOURCE_CHANNEL_ID:
        return

    media_group_id = getattr(message, "media_group_id", None)
    album_id = media_group_id or str(uuid.uuid4())

    # Створюємо альбом, якщо немає
    if album_id not in albums:
        albums[album_id] = {
            "media": [],
            "first_message_id": message.message_id
        }

    # Додаємо медіа
    if message.photo:
        file_id = message.photo[-1].file_id
        albums[album_id]["media"].append({"file_id": file_id, "type": "photo"})
    elif message.video:
        file_id = message.video.file_id
        albums[album_id]["media"].append({"file_id": file_id, "type": "video"})
    else:
        return  # ігноруємо інші типи

    save_albums()

    # Скасовуємо старий таймер, якщо є
    if album_id in album_timers:
        album_timers[album_id].cancel()

    # Запускаємо новий таймер
    task = asyncio.create_task(schedule_album_send(album_id, context))
    album_timers[album_id] = task

# === Main ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
