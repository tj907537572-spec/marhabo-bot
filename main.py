import asyncio
import os
import random
import logging
import aiohttp
import aiofiles
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import edge_tts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импорт MoviePy
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

CHANNELS = {"psy": "@vasha_opora", "money": "@income_ideas"}
QUOTES_PSY = ["Твоя опора внутри тебя.", "Сила в спокойствии."]
QUOTES_MONEY = ["Инвестируй в себя.", "Деньги любят тишину."]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

@app.route('/')
def index(): return "Статус: Работает"

# --- ОБРАБОТКА КОМАНД (Исправлено для aiogram 3.x) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("✅ Бот успешно запущен и видит твои сообщения!")

@dp.message()
async def all_msg_handler(message: types.Message):
    await message.answer("🤖 Я получил твое сообщение. Жду времени публикации видео!")

# --- ЛОГИКА ВИДЕО ---
async def create_video_logic(text, category):
    # (Код остается прежним, он у нас рабочий)
    pass 

async def auto_post():
    # Функция для тестов и расписания
    logging.info("Запуск автоматического поста...")

async def main():
    # Запуск Flask
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()

    # Планировщик
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(auto_post, "cron", hour=9, minute=0)
    scheduler.start()

    logging.info("Бот выходит в онлайн...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
