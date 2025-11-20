import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Язык ответов (используется в приветствии и подсказках)
BOT_LANGUAGE = os.getenv('BOT_LANGUAGE', 'uz')

# OpenAI API настройки
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Проверка наличия необходимых переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
