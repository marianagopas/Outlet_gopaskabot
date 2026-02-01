import json
import os
import uuid
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from deep_translator import GoogleTranslator

BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHANNEL_ID = -1003840384606
TARGET_CHANNEL_ID = -1001321059832
ADMIN_ID = 522888907
SOURCE_USERNAME = "Gopaska_outlet"
DRAFTS_FILE = "drafts.json"

# --- Завантаження чернеток ---
if os.path.exists(DRAFTS_FILE):
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        try:
            drafts = json.load(f)
        except json.JSONDecodeError:
            drafts = {}
else:
    drafts = {}

def save_drafts():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

# --- Переклад ---
def translate_to_ukrainian(text):
    try:
        return GoogleTranslator(source='auto', target='uk').translate(text)
    except Exception:
        return text

def add_source_signature(text):
    link = f"https://t.me/{SOURCE_USERNAME}/"
    return f"{text}\n\n<a href='{link}'>Джерело</a>"

# --- Відправка чернетки адміну ---
async def send_draft_preview(context: ContextTypes.DEFAULT_TYPE, draft_id):
    draft = drafts[draft_id]

    # Фото / альбом (тільки перше фото)
    if draft.get("is_album"):
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=draft["photos"][0],
            caption=f"Чернетка (альбом)"
        )
    elif draft.get("photo"):
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=draft["photo"],
            caption=f"Чернетка"
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Чернетка"
        )

# --- Ловимо повідомлення з каналу ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message.chat_id != SOURCE_CHANNEL_ID:
        return

    text = message.caption or message.text or "Без тексту"
    text = translate_to_ukrainian(text)

    media_group_id = getattr(message, "media_group_id", None)

    if media_group_id:
        # Альбом
        if media_group_id not in drafts:
            drafts[media_group_id] = {
                "photos": [],
                "original_text": text,
                "is_album": True
            }

        if message.photo:
            drafts[media_group_id]["photos"].append(message.photo[-1].file_id)
        save_drafts()
    else:
        # Одиночне фото
        draft_id = str(uuid.uuid4())
        drafts[draft_id] = {
            "photo": message.photo[-1].file_id if message.photo else None,
            "original_text": text,
            "is_album": False
        }
        save_drafts()

# --- Відправка альбому з підписом ---
async def send_album(draft_id, context: ContextTypes.DEFAULT_TYPE):
    draft = drafts[draft_id]
    if draft.get("is_album"):
        media = [InputMediaPhoto(media=pid) for pid in draft["photos"]]
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=media)
        await asyncio.sleep(0.5)
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=add_source_signature(draft["original_text"]))
    elif draft.get("photo"):
        await context.bot.send_photo(chat_id=TARGET_CHANNEL_ID, photo=draft["photo"],
                                     caption=add_source_signature(draft["original_text"]))
    else:
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=add_source_signature(draft["original_text"]))
    # Видаляємо після відправки
    del drafts[draft_id]
    save_drafts()

# --- Обробка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]
    draft_id = data[1]

    if draft_id not in drafts:
        await query.edit_message_text("⚠️ Чернетка не знайдена.")
        return

    if action == "send":
        await send_album(draft_id, context)
        await query.edit_message_text("✅ Опубліковано у канал")
    elif action == "cancel":
        await query.edit_message_text("❌ Чернетка відхилена")
        del drafts[draft_id]
        save_drafts()

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
