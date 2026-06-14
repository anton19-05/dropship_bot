import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1941249302

# ЮMoney настройки (только номер кошелька!)
YOOMONEY_WALLET = "4100119535616904"
YOOMONEY_SUCCESS_URL = "https://t.me/dropshopshipbot"

# Telegram бот username (для возврата)
BOT_USERNAME = "DropShopBot"

# Supabase настройки (берутся из переменных окружения)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")