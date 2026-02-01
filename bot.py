import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "тут_токен_якщо_нема_env")
SOURCE_CHANNEL = "@Gopaska_outlet"
TARGET_CHANNEL = "@Outlet_brand_Gopaska_boutique"
SOURCE_LINK = "https://t.me/Gopaska_outlet"

media_buffer = {}
album_scheduled = set()

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat.username != SOURCE_CHANNEL.replace("@", ""):
        return

    group_id = msg.media_group_id

    if not group_id:
        caption = f"\n\nДжерело: {SOURCE_LINK}"
        if msg.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=msg.photo[-1].file_id,
                caption=caption
            )
        elif msg.video:
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL,
                video=msg.video.file_id,
                caption=caption
            )
        return

    if group_id not in media_buffer:
        media_buffer[group_id] = []

    if msg.photo:
        media_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))

    if group_id not in album_scheduled:
        album_scheduled.add(group_id)
        # Використовуємо application.job_queue замість context.job_queue
        await context.application.job_queue.run_once(
            send_album, 1.2, data=group_id
        )

async def send_album(context: ContextTypes.DEFAULT_TYPE):
    group_id = context.job.data
    if group_id not in media_buffer:
        return

    media_group = media_buffer[group_id]
    if media_group:
        media_group[-1].caption = f"Джерело: {SOURCE_LINK}"
        await context.bot.send_media_group(chat_id=TARGET_CHANNEL, media=media_group)

    del media_buffer[group_id]
    album_scheduled.discard(group_id)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Додаємо handler
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_forwarder))

    print("Bot running...")
    app.run_polling()  # <- блокуючий виклик, тримає контейнер живим

if __name__ == "__main__":
    main()
