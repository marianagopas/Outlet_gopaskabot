from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "ВАШ_ТОКЕН"
SOURCE_CHAT_ID = -1002509471176
TARGET_CHAT_ID = -1002133245347
SOURCE_USERNAME = "Gopaska_boutique_Italyclothing"

current_group_id = None
album_buffer = {}   # media_group_id -> {"photos": [...], "first_msg_id": ...}
sent_groups = set() # щоб не відправити двічі

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Відправляє альбом + підпис і повністю його закриває"""
    global current_group_id

    if group_id not in album_buffer:
        return

    if group_id in sent_groups:
        return  # захист від дублю

    album = album_buffer[group_id]

    # 1) Надсилаємо альбом
    media = [InputMediaPhoto(media=pid) for pid in album["photos"]]
    await context.bot.send_media_group(
        chat_id=TARGET_CHAT_ID,
        media=media
    )

    # 2) Підпис — посилання НА ПЕРШЕ ПОВІДОМЛЕННЯ ЦЬОГО АЛЬБОМУ
    first_msg_id = album["first_msg_id"]
    link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"

    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"<a href='{link}'>Переглянути альбом у джерелі</a>",
        parse_mode="HTML"
    )

    # 3) Повністю закриваємо альбом
    sent_groups.add(group_id)
    del album_buffer[group_id]

    if current_group_id == group_id:
        current_group_id = None

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_group_id

    msg = update.channel_post
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    new_group_id = getattr(msg, "media_group_id", None)

    # ======== АЛЬБОМ ========
    if new_group_id:
        # Якщо це ІНШИЙ альбом — спочатку відправляємо попередній
        if current_group_id and current_group_id != new_group_id:
            await send_album(context, current_group_id)

        # Якщо це перше фото нового альбому — створюємо запис
        if new_group_id not in album_buffer:
            album_buffer[new_group_id] = {
                "photos": [],
                "first_msg_id": msg.message_id
            }

        # Додаємо фото
        if msg.photo:
            album_buffer[new_group_id]["photos"].append(msg.photo[-1].file_id)

        current_group_id = new_group_id
        return

    # ======== ОДИНОЧНЕ ФОТО ========
    if msg.photo:
        # Якщо перед цим був альбом — спочатку закриваємо його
        if current_group_id:
            await send_album(context, current_group_id)

        link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"

        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=f"<a href='{link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
