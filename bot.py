import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]                  # токен бота
SOURCE_CHAT_ID = -1003840384606                      # твій chat.id джерела
TARGET_CHANNEL = "@Outlet_brand_Gopaska_boutique"
SOURCE_LINK = "https://t.me/Gopaska_outlet"
# ================================================

# Тимчасове сховище для каруселей
media_buffer = {}
album_scheduled = set()  # щоб не відправляти альбом двічі

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not hasattr(update, "channel_post") or update.channel_post is None:
        return
    msg = update.channel_post

    # Логування для дебагу
    print(f"Received message: chat.id={msg.chat.id}, type={msg.chat.type}, media_group_id={msg.media_group_id}")

    # Перевірка chat.id джерела
    if msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = msg.media_group_id

    # ===== ОДИНОЧНЕ ФОТО / ВІДЕО =====
    if not group_id:
        caption = f"\n\nДжерело: {SOURCE_LINK}"

        if msg.photo:
            print("Sending photo...")
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=msg.photo[-1].file_id,
                caption=caption
            )
        elif msg.video:
            print("Sending video...")
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL,
                video=msg.video.file_id,
                caption=caption
            )
        else:
            print("No photo/video to send.")
        return

    # ===== КАРУСЕЛЬ (АЛЬБОМ) =====
    if group_id not in media_buffer:
        media_buffer[group_id] = []

    if msg.photo:
        media_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))

    if group_id not in album_scheduled:
        album_scheduled.add(group_id)
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
        print(f"Sending album with {len(media_group)} items...")
        await context.bot.send_media_group(
            chat_id=TARGET_CHANNEL,
            media=media_group
        )

    del media_buffer[group_id]
    album_scheduled.discard(group_id)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, channel_forwarder))
    print("Bot running...")
    app.run_polling()  # тримає контейнер живим

if __name__ == "__main__":
    main()
