import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1941249302

# ЮMoney настройки (только номер кошелька!)
YOOMONEY_WALLET = "4100119535616904"  # ваш номер с картинки
YOOMONEY_SUCCESS_URL = "https://t.me/dropshopshipbot"  # или любая ссылка

# Telegram бот username (для возврата)
BOT_USERNAME = "DropShopBot"  # ваш username бота