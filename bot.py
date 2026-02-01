import asyncio
import json
import uuid
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo

# --- КОНФІГУРАЦІЯ ---
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606
TARGET_CHANNEL_ID = -1001321059832
JSON_FILE = "albums.json"
# --------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Завантаження або створення JSON ---
if __import__("os").path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        albums = json.load(f)
else:
    albums = {}

def save_albums():
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(albums, f, ensure_ascii=False, indent=2)

# --- Відправка альбому ---
async def send_album(album_id: str):
    album = albums.get(album_id)
    if not album:
        return

    media_items = album["media"]
    first_msg_id = album["first_message_id"]

    output_media = []
    for i, item in enumerate(media_items):
        caption = None
        if i == len(media_items) - 1:
            # Клікабельний підпис Outlet
            caption = f"<a href='https://t.me/c/{str(SOURCE_CHANNEL_ID)[4:]}/{first_msg_id}'>Outlet</a>"
        if item["type"] == "photo":
            output_media.append(InputMediaPhoto(media=item["file_id"], caption=caption))
        elif item["type"] == "video":
            output_media.append(InputMediaVideo(media=item["file_id"], caption=caption))

    if output_media:
        await bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=output_media)

    # Після відправки видаляємо альбом
    del albums[album_id]
    save_albums()

# --- Перевірка та відправка всіх готових альбомів ---
async def process_ready_albums(new_id: str):
    ready = []
    for aid in albums:
        if aid != new_id and not albums[aid].get("sent"):
            ready.append(aid)
    for aid in ready:
        albums[aid]["sent"] = True
        await send_album(aid)

# --- Обробка повідомлень з каналу ---
@dp.message(F.chat.id == SOURCE_CHANNEL_ID)
async def handle_message(message: Message):
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
        return  # поки тільки фото/відео

    # Генеруємо id альбому для одиночного фото/відео
    album_id = str(media_group_id) if media_group_id else str(uuid.uuid4())

    # --- Закриваємо попередні альбоми ---
    await process_ready_albums(album_id)

    # --- Додаємо медіа до альбому ---
    if album_id not in albums:
        albums[album_id] = {
            "media": [],
            "first_message_id": message.message_id,
            "sent": False
        }

    albums[album_id]["media"].append({"file_id": file_id, "type": media_type})
    save_albums()

# --- Main ---
async def main():
    print("Бот запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
