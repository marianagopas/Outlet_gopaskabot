import json
import os
import uuid
import asyncio
import re
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606
TARGET_CHANNEL_ID = -1001321059832
DRAFTS_FILE = "drafts.json"

# --- Завантаження чернеток ---
if os.path.exists(DRAFTS_FILE):
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        drafts = json.load(f)
else:
    drafts = {}

def save_drafts():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

# --- Ловимо повідомлення ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message.chat_id != SOURCE_CHANNEL_ID:
        return

    media_group_id = getattr(message, "media_group_id", None)
    message_id = message.message_id
    photo_id = message.photo[-1].file_id if message.photo else None
    source_link = f"https://t.me/c/{str(SOURCE_CHANNEL_ID)[4:]}/{message_id}"  # посилання на джерело

    if media_group_id:
        # Якщо альбом новий — зберігаємо попередній, якщо є
        if media_group_id not in drafts:
            # Закриваємо всі інші альбоми
            for g_id in list(drafts.keys()):
                if drafts[g_id].get("is_album"):
                    await send_album(context, g_id)
            drafts[media_group_id] = {
                "photos": [],
                "first_message_id": message_id,
                "is_album": True
            }

        if photo_id:
            drafts[media_group_id]["photos"].append(photo_id)
        save_drafts()
    else:
        # Одиночне фото
        if photo_id:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=photo_id,
                caption=f"📎 Джерело: <a href='{source_link}'>Перейти</a>",
                parse_mode="HTML"
            )
            save_drafts()

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    draft = drafts.get(group_id)
    if not draft:
        return
    photos = draft["photos"]
    first_msg_id = draft["first_message_id"]
    source_link = f"https://t.me/c/{str(SOURCE_CHANNEL_ID)[4:]}/{first_msg_id}"

    if photos:
        media_list = [InputMediaPhoto(media=pid) for pid in photos]
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=media_list)
        # Підпис після альбому
        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=f"📎 Джерело: <a href='{source_link}'>Перейти</a>",
            parse_mode="HTML"
        )

    del drafts[group_id]
    save_drafts()

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
