import asyncio
import os
import random
import logging
import requests
import textwrap
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, TextClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAErcRp2_iIAKr8N6fC89VhOoGgR0gx_814"
PEXELS_API_KEY = "VjznZIGQwVRr2ot6wxiiHpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxml"

CHANNELS = {
    "psy": "@vasha_opora",
    "money": "@income_ideas"
}

QUOTES_PSY = ["Твоя опора внутри тебя.", "Сложные времена создают сильных людей."]
QUOTES_MONEY = ["Лучшая инвестиция — это твоё образование.", "Идея стоит 1 доллар, реализация — миллион."]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(name)

@app.route('/')
def index(): return "Бот-админ работает!"

# --- ЛОГИКА ЗАГРУЗКИ ИЗ PEXELS ---
async def get_pexels_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    r = requests.get(url, headers=headers).json()
    if r.get('videos'):
        video_url = r['videos'][0]['video_files'][0]['link']
        with open("base_video.mp4", "wb") as f:
            f.write(requests.get(video_url).content)
        return "base_video.mp4"
    return None

# --- СОЗДАНИЕ ВИДЕО (Упрощенная версия для Render) ---
async def create_video_logic(text, category):
    query = "nature" if category == "psy" else "business"
    video_path = await get_pexels_video(query)
    if not video_path: return None
    
    # Озвучка
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    
    video = VideoFileClip(video_path).subclip(0, 7) # Берем 7 секунд
    audio = AudioFileClip("voice.mp3")
    
    final_video = video.set_audio(audio)
    output = f"result_{category}.mp4"
    final_video.write_videofile(output, codec="libx264", audio_codec="aac", fps=24)
    return output

# --- ФУНКЦИИ АВТОПОСТИНГА ---
async def auto_post_psy():
    text = random.choice(QUOTES_PSY)
    try:
        path = await create_video_logic(text, "psy")
        await bot.send_video(CHANNELS["psy"], FSInputFile(path), caption=text)
    except Exception as e:
        print(f"Ошибка в psy: {e}")

async def auto_post_money():
    text = random.choice(QUOTES_MONEY)
    try:
        path = await create_video_logic(text, "money")
        await bot.send_video(CHANNELS["money"], FSInputFile(path), caption=text)
    except Exception as e:
        print(f"Ошибка в money: {e}")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # Посты 2 раза в день
    scheduler.add_job(auto_post_psy, "cron", hour=9, minute=0)
    scheduler.add_job(auto_post_money, "cron", hour=15, minute=0)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
