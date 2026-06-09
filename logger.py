from config import ADMIN_ID

async def send_debug(bot, message: str):
    """Отправляет отладочное сообщение админу в Telegram"""
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        print(f"Ошибка отправки дебаг-сообщения: {e}")