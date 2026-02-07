import asyncio
import os
import random
import logging
import aiohttp
import aiofiles
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, filters
from aiogram.types import FSInputFile
import edge_tts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Универсальный импорт MoviePy
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

# Настройки
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
    return "Бот активен!"

# Проверка бота (ответит на любое сообщение)
@dp.message()
async def cmd_start(message: types.Message):
    await message.answer("Бот работает и готов к отправке видео по расписанию!")

# Функция загрузки и монтажа (без изменений)
async def get_pexels_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get('videos'):
                video_url = data['videos'][0]['video_files'][0]['link']
                async with session.get(video_url) as v_resp:
                    if v_resp.status == 200:
                        async with aiofiles.open("base_video.mp4", mode='wb') as f:
                            await f.write(await v_resp.read())
                        return "base_video.mp4"
    return None

async def create_video_logic(text, category):
    query = "nature" if category == "psy" else "business"
    path = await get_pexels_video(query)
    if not path: return None
    await edge_tts.Communicate(text, "ru-RU-SvetlanaNeural").save("voice.mp3")
    video = VideoFileClip(path).subclip(0, 7)
    audio = AudioFileClip("voice.mp3")
    final = video.set_audio(audio)
    output = f"res_{category}.mp4"
    final.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, remove_temp=True)
    video.close()
    audio.close()
    return output

async def auto_post_psy():
    text = random.choice(QUOTES_PSY)
    try:
        path = await create_video_logic(text, "psy")
        if path: await bot.send_video(CHANNELS["psy"], FSInputFile(path), caption=text)
    except Exception as e: logging.error(f"Ошибка PSY: {e}")

async def auto_post_money():
    text = random.choice(QUOTES_MONEY)
    try:
        path = await create_video_logic(text, "money")
        if path: await bot.send_video(CHANNELS["money"], FSInputFile(path), caption=text)
    except Exception as e: logging.error(f"Ошибка MONEY: {e}")

# Запуск Flask в отдельном потоке
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

async def main():
    # 1. Запускаем Flask
    Thread(target=run_flask, daemon=True).start()
    
    # 2. Запускаем расписание
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(auto_post_psy, "cron", hour=9, minute=0)
    scheduler.add_job(auto_post_money, "cron", hour=15, minute=0)
    scheduler.start()

    # 3. Запускаем бота
    logging.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
