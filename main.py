import asyncio
import os
import random
import logging
import requests
import textwrap
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Добавьте в requirements.txt

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAHpernZv9mZScnQz2nBCkK-yiNfiZLGQhM"
PEXELS_API_KEY = "VjznZIGQwVRr2ot6wxiiHpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxml"
ADMIN_ID = 6341390660

CHANNELS = {
    "psy": "@tvoya_opora",
    "money": "@income_ideas"
}

# --- БАЗА ИДЕЙ (Для автопилота) ---
QUOTES_PSY = [
    "Твоя опора внутри тебя. Не ищи её в других.",
    "Сложные времена создают сильных людей.",
    "Психология успеха начинается с тишины в голове.",
    "Ты — это не твои ошибки. Ты — это то, как ты их исправил."
]

QUOTES_MONEY = [
    "Деньги приходят к тем, кто решает проблемы других.",
    "Лучшая инвестиция — это твоё образование.",
    "Идея стоит 1 доллар, реализация стоит миллион.",
    "Не работай ради денег. Заставляй деньги работать на себя."
]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- ЛОГИКА (ФОТО И ВИДЕО) ---
# (Функции create_text_overlay, create_video_logic, create_image_post берем из прошлых сообщений)

# --- ФУНКЦИИ ДЛЯ АВТОПОСТИНГА ---

async def auto_post_psy():
    text = random.choice(QUOTES_PSY)
    # Выбираем случайный формат: 50% видео, 50% фото
    if random.choice([True, False]):
        path = await create_video_logic(text, "psy")
        await bot.send_video(CHANNELS["psy"], FSInputFile(path), caption=f"{text}\n#автопост #опора")
    else:
        path = create_image_post(text, "psy")
        await bot.send_photo(CHANNELS["psy"], FSInputFile(path), caption=f"{text}\n#автопост #психология")

async def auto_post_money():
    text = random.choice(QUOTES_MONEY)
    if random.choice([True, False]):
        path = await create_video_logic(text, "money")
        await bot.send_video(CHANNELS["money"], FSInputFile(path), caption=f"{text}\n#автопост #доход")
    else:
        path = create_image_post(text, "money")
        await bot.send_photo(CHANNELS["money"], FSInputFile(path), caption=f"{text}\n#автопост #бизнес")

# --- ЗАПУСК ---

async def main():
    # Настройка планировщика
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Добавляем задачи по времени
    scheduler.add_job(auto_post_psy, "cron", hour=9, minute=0) # Каждый день в 9 утра
    scheduler.add_job(auto_post_money, "cron", hour=15, minute=0) # Каждый день в 3 часа дня
    
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



