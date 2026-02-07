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

# Универсальный импорт MoviePy
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

# Настройки из Render
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

CHANNELS = {"psy": "@vasha_opora", "money": "@income_ideas"}
QUOTES_PSY = ["Твоя опора внутри тебя.", "Сложные времена создают сильных людей.", "Ты сильнее, чем ты думаешь."]
QUOTES_MONEY = ["Деньги приходят под запрос.", "Инвестируй в свои знания.", "Богатство начинается с мышления."]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

@app.route('/')
def index(): return "Бот в эфире!"

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("✅ Бот активен! Добавь меня в админы каналов. \nКоманда /test — проверить создание видео.")

@dp.message(Command("test"))
async def test_video(message: types.Message):
    await message.answer("🎬 Запускаю тест... Подожди немного.")
    path = await create_video_logic("Тестовая проверка прошла успешно!", "psy")
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path), caption="✅ Всё работает!")
        if os.path.exists(path): os.remove(path)
    else:
        await message.answer("❌ Ошибка Pexels! Проверь API ключ в настройках Render.")

# --- ЛОГИКА МОНТАЖА ---
async def get_pexels_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get('videos'):
                v_url = data['videos'][0]['video_files'][0]['link']
                async with session.get(v_url) as v_resp:
                    if v_resp.status == 200:
                        async with aiofiles.open("temp_v.mp4", 'wb') as f:
                            await f.write(await v_resp.read())
                        return "temp_v.mp4"
    return None

async def create_video_logic(text, category):
    q = "nature" if category == "psy" else "business"
    v_path = await get_pexels_video(q)
    if not v_path: return None
    
    await edge_tts.Communicate(text, "ru-RU-SvetlanaNeural").save("v.mp3")
    
    clip = VideoFileClip(v_path).subclip(0, 7)
    audio = AudioFileClip("v.mp3")
    final = clip.set_audio(audio)
    out = f"final_{category}.mp4"
    final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None)
    
    clip.close()
    audio.close()
    return out

# --- РАСПИСАНИЕ ---
async def post_psy():
    txt = random.choice(QUOTES_PSY)
    p = await create_video_logic(txt, "psy")
    if p:
        await bot.send_video(CHANNELS["psy"], FSInputFile(p), caption=txt)
        os.remove(p)

async def post_money():
    txt = random.choice(QUOTES_MONEY)
    p = await create_video_logic(txt, "money")
    if p:
        await bot.send_video(CHANNELS["money"], FSInputFile(p), caption=txt)
        os.remove(p)

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    
    sch = AsyncIOScheduler(timezone="Europe/Moscow")
    sch.add_job(post_psy, "cron", hour=9, minute=0)
    sch.add_job(post_money, "cron", hour=15, minute=0)
    sch.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
