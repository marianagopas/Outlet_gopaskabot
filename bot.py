import os
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]                   # токен бота
SOURCE_CHAT_ID = -1003840384606                       # chat.id каналу джерела
TARGET_CHAT_ID = -1001321059832                       # chat.id каналу отримувача
SOURCE_USERNAME = "Gopaska_outlet"                   # username каналу джерела без @
# ================================================

# Буфер для альбому
media_buffer = []
current_group_id = None
first_message_id_in_group = None
album_task = None

async def send_album(context: ContextTypes.DEFAULT_TYPE, buffer, first_msg_id):
    if not buffer:
        return
    # Додаємо клікабельний підпис лише останньому елементу
    source_post_link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"
    buffer[-1].caption = f"<a href='{source_post_link}'>Джерело</a>"

    await context.bot.send_media_group(
        chat_id=TARGET_CHAT_ID,
        media=buffer
    )

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global media_buffer, current_group_id, first_message_id_in_group, album_task

    msg = update.channel_post
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = msg.media_group_id

    # ===== Альбом / новий media_group_id =====
    if group_id != current_group_id:
        # Якщо був попередній альбом → відправляємо
        if media_buffer:
            # Відправляємо попередній альбом відразу
            await send_album(context, media_buffer, first_message_id_in_group)
            media_buffer = []
        current_group_id = group_id
        first_message_id_in_group = msg.message_id if group_id else None

    # ===== Додаємо медіа в буфер =====
    if msg.photo:
        media_buffer.append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer.append(InputMediaVideo(media=msg.video.file_id))
    else:
        return

    # ===== Якщо одиночне фото/відео (не альбом) =====
    if group_id is None:
        source_post_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"
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

    # ===== Старт таймера для відправки альбому (якщо альбом) =====
    if group_id and not album_task:
        # даємо 1.5 секунди, щоб прийшли всі елементи альбому
        album_task = asyncio.create_task(album_timer(context))

async def album_timer(context: ContextTypes.DEFAULT_TYPE):
    global media_buffer, current_group_id, first_message_id_in_group, album_task
    await asyncio.sleep(1.5)  # чекаємо поки всі елементи альбому прийдуть
    if media_buffer:
        await send_album(context, media_buffer, first_message_id_in_group)
        media_buffer = []
    album_task = None
    current_group_id = None
    first_message_id_in_group = None

def main():
    print(f"Starting bot. SOURCE_CHAT_ID={SOURCE_CHAT_ID}, TARGET_CHAT_ID={TARGET_CHAT_ID}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, channel_forwarder))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
