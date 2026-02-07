import asyncio
import os
import random
import logging
import aiohttp
import aiofiles
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
import edge_tts
# Исправленные импорты для MoviePy
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

CHANNELS = {
    "psy": "@vasha_opora",
    "money": "@income_ideas"
}

QUOTES_PSY = ["Твоя опора внутри тебя.", "Сложные времена создают сильных людей."]
QUOTES_MONEY = ["Лучшая инвестиция — это твоё образование.", "Идея стоит 1 доллар, реализация — миллион."]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

@app.route('/')
def index(): 
    return "Бот-админ активен!"

# --- ЗАГРУЗКА ВИДЕО ---
async def get_pexels_video(query):
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0"
    }
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get('videos'):
                video_url = data['videos'][0]['video_files'][0]['link']
                async with session.get(video_url) as video_resp:
                    if video_resp.status == 200:
                        content = await video_resp.read()
                        async with aiofiles.open("base_video.mp4", mode='wb') as f:
                            await f.write(content)
                        return "base_video.mp4"
    return None

# --- СОЗДАНИЕ ВИДЕО ---
async def create_video_logic(text, category):
    query = "nature" if category == "psy" else "business"
    video_path = await get_pexels_video(query)
    if not video_path: return None
    
    # Озвучка
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    
    # Монтаж
    video = VideoFileClip(video_path).subclip(0, 7)
    audio = AudioFileClip("voice.mp3")
    final_video = video.set_audio(audio)
    
    output = f"result_{category}.mp4"
    # Параметр temp_audiofile важен для серверов без прав записи в системные папки
    final_video.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, temp_audiofile=f'temp_{category}.m4a', remove_temp=True)
    
    video.close()
    audio.close()
    return output

async def auto_post_psy():
    text = random.choice(QUOTES_PSY)
    try:
        path = await create_video_logic(text, "psy")
        if path:
            await bot.send_video(CHANNELS["psy"], FSInputFile(path), caption=text)
    except Exception as e:
        logging.error(f"Ошибка в psy: {e}")

async def auto_post_money():
    text = random.choice(QUOTES_MONEY)
    try:
        path = await create_video_logic(text, "money")
        if path:
            await bot.send_video(CHANNELS["money"], FSInputFile(path), caption=text)
    except Exception as e:
        logging.error(f"Ошибка в money: {e}")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(auto_post_psy, "cron", hour=9, minute=0)
    scheduler.add_job(auto_post_money, "cron", hour=15, minute=0)
    scheduler.start()

    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
