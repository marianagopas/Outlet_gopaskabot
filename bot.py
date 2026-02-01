import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]                  # Твій токен бота
SOURCE_CHAT_ID = int(os.environ["SOURCE_CHAT_ID"])   # chat.id каналу джерела
TARGET_CHANNEL = "@Outlet_brand_Gopaska_boutique"
SOURCE_LINK = "https://t.me/Gopaska_outlet"
# ================================================

# Тимчасове сховище для каруселей
media_buffer = {}
album_scheduled = set()  # щоб не відправляти альбом двічі

async def channel_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Перевірка на наявність channel_post
    if not hasattr(update, "channel_post") or update.channel_post is None:
        return
    msg = update.channel_post

    # Логування для дебагу
    print(f"Received message in chat_id={msg.chat.id}, type={msg.chat.type}")

    # Перевірка chat.id джерела
    if msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = msg.media_group_id

    # ===== ОДИНОЧНЕ ФОТО / ВІДЕО =====
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

    # ===== КАРУСЕЛЬ (АЛЬБОМ) =====
    if group_id not in media_buffer:
        media_buffer[group_id] = []

    if msg.photo:
        media_buffer[group_id].append(InputMediaPhoto(media=msg.photo[-1].file_id))
    elif msg.video:
        media_buffer[group_id].append(InputMediaVideo(media=msg.video.file_id))

    if group_id not in album_scheduled:
        album_scheduled.add(group_id)
        # Використовуємо application.job_queue для відправки альбому
        await context.application.job_queue.run_once(
            send_album, 1.2, data=group_id
        )

async def send_album(context: ContextTypes.DEFAULT_TYPE):
    group_id = context.job.data

    if group_id not in media_buffer:
        return

    media_group = media_buffer[group_id]
    if media_group:
        # Підпис лише до останнього елемента
        media_group[-1].caption = f"Джерело: {SOURCE_LINK}"
        await context.bot.send_media_group(
            chat_id=TARGET_CHANNEL,
            media=media_group
        )

    # Очищаємо пам'ять
    del media_buffer[group_id]
    album_scheduled.discard(group_id)

def main():
    print(f"SOURCE_CHAT_ID={SOURCE_CHAT_ID}, TARGET_CHANNEL={TARGET_CHANNEL}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Використовуємо фільтр ALL для всіх типів повідомлень
    app.add_handler(MessageHandler(filters.ALL, channel_forwarder))

    print("Bot running...")
    app.run_polling()  # блокує процес, щоб контейнер не закривався

if __name__ == "__main__":
    main()
