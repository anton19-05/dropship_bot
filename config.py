import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из секретного файла

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1941249302