import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606     # канал джерела
TARGET_CHAT_ID = -1001321059832     # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet" # username джерела без @
# ================================================

# Буфер для альбомів
album_buffer = {}   # ключ: media_group_id -> list(InputMediaPhoto/Video)
album_first_msg = {} # media_group_id -> first_message_id

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    if group_id not in album_buffer:
        return

    media_list = album_buffer[group_id]
    first_msg_id = album_first_msg[group_id]

    if media_list:
        # Додаємо клікабельний caption для останнього елемента
        last_item = media_list[-1]
        if isinstance(last_item, InputMediaPhoto):
            media_list[-1] = InputMediaPhoto(
                media=last_item.media,
                caption=f"<a href='https://t.me/{SOURCE_USERNAME}/{first_msg_id}'>Джерело</a>",
                parse_mode="HTML"
            )
        elif isinstance(last_item, InputMediaVideo):
            media_list[-1] = InputMediaVideo(
                media=last_item.media,
                caption=f"<a href='https://t.me/{SOURCE_USERNAME}/{first_msg_id}'>Джерело</a>",
                parse_mode="HTML"
            )

        await context.bot.send_media_group(
            chat_id=TARGET_CHAT_ID,
            media=media_list
        )

    # Очищаємо буфер
    del album_buffer[group_id]
    del album_first_msg[group_id]

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

            # Таймер на відправку альбому через 1.5 сек
            asyncio.create_task(album_timer(context, group_id))

        # Додаємо медіа у буфер
        if msg.photo:
            album_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
        elif msg.video:
            album_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))
        return

    # ===== Одиночне фото/відео =====
    source_post_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"
    caption = f"<a href='{source_post_link}'>Джерело</a>"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )
    elif msg.video:
        await context.bot.send_video(
            chat_id=TARGET_CHAT_ID,
            video=msg.video.file_id,
            caption=caption,
            parse_mode="HTML"
        )
    elif msg.text:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"{msg.text}\n\n<a href='{source_post_link}'>Джерело</a>",
            parse_mode="HTML"
        )

async def album_timer(context: ContextTypes.DEFAULT_TYPE, group_id):
    await asyncio.sleep(1.5)
    await send_album(context, group_id)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
