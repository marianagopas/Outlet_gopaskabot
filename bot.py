import json
import os
import uuid
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# === Налаштування ===
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606
TARGET_CHANNEL_ID = -1001321059832
SOURCE_USERNAME = "Gopaska_outlet"  # username каналу без @
JSON_FILE = "albums.json"

# === Завантаження або створення JSON ===
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        albums = json.load(f)
else:
    albums = {}

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
    for i, item in enumerate(media_items):
        caption = None
        if i == len(media_items) - 1:
            # Клікабельний підпис під словом Outlet
            caption = f"<a href='https://t.me/c/{str(album['source_channel_id'])[4:]}/{first_msg_id}'>Outlet</a>"
        if item["type"] == "photo":
            output_media.append(InputMediaPhoto(media=item["file_id"], caption=caption))
        elif item["type"] == "video":
            output_media.append(InputMediaVideo(media=item["file_id"], caption=caption))

    if output_media:
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=output_media)

    # Видаляємо альбом після відправки
    del albums[album_id]
    save_albums()

# === Ловимо повідомлення з каналу ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat_id != SOURCE_CHANNEL_ID:
        return

    media_group_id = getattr(message, "media_group_id", None)
    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        return  # поки тільки фото і відео

    # Якщо альбом
    if media_group_id:
        # Новий альбом
        if media_group_id not in albums:
            # Закриваємо старі альбоми, що ще не відправлені
            for aid in list(albums.keys()):
                await send_album(aid, context)

            albums[media_group_id] = {
                "media": [],
                "first_message_id": message.message_id,
                "source_channel_id": SOURCE_CHANNEL_ID
            }

        albums[media_group_id]["media"].append({"file_id": file_id, "type": media_type})
        save_albums()
    else:
        # Одиночне фото/відео як окремий альбом
        album_id = str(uuid.uuid4())
        albums[album_id] = {
            "media": [{"file_id": file_id, "type": media_type}],
            "first_message_id": message.message_id,
            "source_channel_id": SOURCE_CHANNEL_ID
        }
        save_albums()
        await send_album(album_id, context)

# === Main ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
