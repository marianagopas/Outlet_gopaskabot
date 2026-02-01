import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]                   # токен бота
SOURCE_CHAT_ID = -1003840384606                       # chat.id каналу джерела
TARGET_CHAT_ID = -1001321059832                       # chat.id каналу отримувача
SOURCE_USERNAME = "Gopaska_outlet"                   # username каналу джерела без @
# ================================================

# Буфер для поточного альбому
media_buffer = []
current_group_id = None
last_message_id = None

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global media_buffer, current_group_id, last_message_id

    if not hasattr(update, "channel_post") or update.channel_post is None:
        return
    msg = update.channel_post

    # Перевірка джерела
    if msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = msg.media_group_id
    last_message_id = msg.message_id

    # ===== Альбом / новий media_group_id =====
    if group_id != current_group_id:
        # Відправляємо попередній альбом, якщо він є
        if media_buffer:
            # Додаємо клікабельний підпис останньому елементу
            source_post_link = f"https://t.me/{SOURCE_USERNAME}/{last_message_id_prev}"
            media_buffer[-1].caption = f"<a href='{source_post_link}'>Джерело</a>"
            await context.bot.send_media_group(
                chat_id=TARGET_CHAT_ID,
                media=media_buffer
            )
            media_buffer = []

        current_group_id = group_id
        last_message_id_prev = last_message_id  # для підпису

    # ===== Додаємо медіа у буфер =====
    if msg.photo:
        media_buffer.append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer.append(InputMediaVideo(media=msg.video.file_id))
    else:
        # Одиночне повідомлення без медіа
        return

    # ===== Одиночні фото/відео (не альбом) =====
    if group_id is None:
        source_post_link = f"https://t.me/{SOURCE_USERNAME}/{last_message_id}"
        if msg.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHAT_ID,
                photo=msg.photo[-1].file_id,
                caption=f"<a href='{source_post_link}'>Джерело</a>",
                parse_mode="HTML"
            )
        elif msg.video:
            await context.bot.send_video(
                chat_id=TARGET_CHAT_ID,
                video=msg.video.file_id,
                caption=f"<a href='{source_post_link}'>Джерело</a>",
                parse_mode="HTML"
            )

async def flush_buffer(context: ContextTypes.DEFAULT_TYPE):
    """На випадок, якщо альбом залишився в буфері, відправляємо його"""
    global media_buffer, last_message_id
    if media_buffer:
        source_post_link = f"https://t.me/{SOURCE_USERNAME}/{last_message_id}"
        media_buffer[-1].caption = f"<a href='{source_post_link}'>Джерело</a>"
        await context.bot.send_media_group(
            chat_id=TARGET_CHAT_ID,
            media=media_buffer
        )
        media_buffer = []

def main():
    print(f"Starting bot. SOURCE_CHAT_ID={SOURCE_CHAT_ID}, TARGET_CHAT_ID={TARGET_CHAT_ID}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, channel_forwarder))

    # Додаємо job для очищення буфера раз на хвилину на випадок "завислих" альбомів
    app.job_queue.run_repeating(flush_buffer, interval=60, first=60)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
