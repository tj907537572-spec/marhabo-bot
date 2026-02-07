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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Универсальный импорт MoviePy (для любой версии)
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
    except ImportError:
        logging.error("Не удалось импортировать MoviePy! Проверьте requirements.txt")

# --- НАСТРОЙКИ (Берем из Environment Variables на Render) ---
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
    return "Бот-админ активен и работает!"

# --- ЗАГРУЗКА ВИДЕО ИЗ PEXELS ---
async def get_pexels_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get('videos'):
                video_url = data['videos'][0]['video_files'][0]['link']
                async with session.get(video_url) as video_resp:
                    if video_resp.status == 200:
                        async with aiofiles.open("base_video.mp4", mode='wb') as f:
                            await f.write(await video_resp.read())
                        return "base_video.mp4"
    return None

# --- МОНТАЖ ВИДЕО ---
async def create_video_logic(text, category):
    query = "nature" if category == "psy" else "business"
    video_path = await get_pexels_video(query)
    if not video_path: return None
    
    # Озвучка текста
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    
    # Создание клипа
    video = VideoFileClip(video_path).subclip(0, 7)
    audio = AudioFileClip("voice.mp3")
    final_video = video.set_audio(audio)
    
    output = f"result_{category}.mp4"
    # Параметры для стабильной работы на сервере
    final_video.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, temp_audiofile=f'temp_{category}.m4a', remove_temp=True)
    
    video.close()
    audio.close()
    return output

# --- ФУНКЦИИ ПОСТИНГА ---
async def auto_post_psy():
    text = random.choice(QUOTES_PSY)
    try:
        path = await create_video_logic(text, "psy")
        if path:
            await bot.send_video(CHANNELS["psy"], FSInputFile(path), caption=text)
    except Exception as e:
        logging.error(f"Ошибка в блоке PSY: {e}")

async def auto_post_money():
    text = random.choice(QUOTES_MONEY)
    try:
        path = await create_video_logic(text, "money")
        if path:
            await bot.send_video(CHANNELS["money"], FSInputFile(path), caption=text)
    except Exception as e:
        logging.error(f"Ошибка в блоке MONEY: {e}")

# --- ЗАПУСК ---
async def main():
    # Планировщик (время МСК)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(auto_post_psy, "cron", hour=9, minute=0)
    scheduler.add_job(auto_post_money, "cron", hour=15, minute=0)
    scheduler.start()

    # Запуск Flask для Render
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()

    # Удаляем вебхуки и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")

