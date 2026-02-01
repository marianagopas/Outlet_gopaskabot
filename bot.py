import os
import json
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606  # канал джерела
TARGET_CHANNEL_ID = -1001321059832  # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet"  # username джерела без @
DRAFTS_FILE = "albums.json"

# Завантаження тимчасових альбомів
if os.path.exists(DRAFTS_FILE):
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        albums = json.load(f)
else:
    albums = {}  # media_group_id -> {"media": [], "first_msg_id": int, "type": "photo/video"}

def save_albums():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(albums, f, ensure_ascii=False, indent=2)

async def send_album(context: ContextTypes.DEFAULT_TYPE, album_id):
    """Відправка альбому з підписом на джерело"""
    album = albums.get(album_id)
    if not album:
        return

    media_list = album["media"]
    first_msg_id = album["first_msg_id"]
    link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"

    # Додаємо caption тільки до останнього елемента
    last_item = media_list[-1]
    if album["type"] == "photo":
        media_list[-1] = InputMediaPhoto(media=last_item.media, caption=f"<a href='{link}'>Джерело</a>", parse_mode="HTML")
    else:
        media_list[-1] = InputMediaVideo(media=last_item.media, caption=f"<a href='{link}'>Джерело</a>", parse_mode="HTML")

    await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=media_list)

    # Видаляємо альбом з JSON
    del albums[album_id]
    save_albums()
    print(f"Альбом {album_id} надіслано.")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.chat.id != SOURCE_CHANNEL_ID:
        return

    album_id = getattr(msg, "media_group_id", None) or f"single_{msg.message_id}"

    # Якщо це новий альбом або одиночне медіа, закриваємо попередній
    if album_id not in albums and getattr(msg, "media_group_id", None):
        # Перевіряємо, чи є інший альбом, який треба надіслати
        to_send = [aid for aid in albums if aid != album_id]
        for aid in to_send:
            await send_album(context, aid)

    if msg.photo:
        media_item = InputMediaPhoto(media=msg.photo[-1].file_id)
        media_type = "photo"
    elif msg.video:
        media_item = InputMediaVideo(media=msg.video.file_id)
        media_type = "video"
    else:
        # Якщо не фото/відео — ігноруємо
        return

    if album_id not in albums:
        albums[album_id] = {"media": [], "first_msg_id": msg.message_id, "type": media_type}

    albums[album_id]["media"].append(media_item)
    save_albums()

    # Якщо одиночне фото/відео без media_group_id — відправляємо відразу
    if getattr(msg, "media_group_id", None) is None:
        await send_album(context, album_id)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
