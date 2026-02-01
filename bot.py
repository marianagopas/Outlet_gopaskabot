import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]                   # токен бота
SOURCE_CHAT_ID = -1003840384606                       # chat.id каналу джерела
TARGET_CHAT_ID = -1001321059832                       # chat.id каналу отримувача
SOURCE_USERNAME = "Gopaska_outlet"                   # username каналу джерела без @
# ================================================

# Тимчасове сховище для альбомів
media_buffer = {}
album_scheduled = set()

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not hasattr(update, "channel_post") or update.channel_post is None:
        return
    msg = update.channel_post

    # Логування
    print(f"Received message: chat.id={msg.chat.id}, type={msg.chat.type}, media_group_id={msg.media_group_id}")

    # Перевірка джерела
    if msg.chat.id != SOURCE_CHAT_ID:
        return

    # Генеруємо посилання на оригінальний пост
    source_post_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"

    group_id = msg.media_group_id

    # ===== Одиночне фото / відео =====
    if not group_id:
        caption = f"<a href='{source_post_link}'>Джерело</a>"

        if msg.photo:
            print("Sending single photo...")
            await context.bot.send_photo(
                chat_id=TARGET_CHAT_ID,
                photo=msg.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML"
            )
        elif msg.video:
            print("Sending single video...")
            await context.bot.send_video(
                chat_id=TARGET_CHAT_ID,
                video=msg.video.file_id,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            print("No media to send.")
        return

    # ===== Альбом / Карусель =====
    if group_id not in media_buffer:
        media_buffer[group_id] = []

    if msg.photo:
        media_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))

    if group_id not in album_scheduled:
        album_scheduled.add(group_id)
        # Чекати ~1.2 сек, щоб зібрати всі елементи альбому
        await context.application.job_queue.run_once(
            send_album, 1.2, data={"group_id": group_id, "link": source_post_link}
        )

async def send_album(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    group_id = job_data["group_id"]
    source_post_link = job_data["link"]

    if group_id not in media_buffer:
        return

    media_group = media_buffer[group_id]

    if media_group:
        # Додаємо клікабельний підпис лише останньому елементу
        media_group[-1].caption = f"<a href='{source_post_link}'>Джерело</a>"

        print(f"Sending album with {len(media_group)} items...")
        await context.bot.send_media_group(
            chat_id=TARGET_CHAT_ID,
            media=media_group
        )

    # Очищаємо буфер
    del media_buffer[group_id]
    album_scheduled.discard(group_id)

def main():
    print(f"Starting bot. SOURCE_CHAT_ID={SOURCE_CHAT_ID}, TARGET_CHAT_ID={TARGET_CHAT_ID}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, channel_forwarder))

    print("Bot running...")
    app.run_polling()  # тримає процес живим

if __name__ == "__main__":
    main()
