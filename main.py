import os
import random
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp
import aiofiles
from aiohttp import web

# Импорт MoviePy с защитой
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip

# Берем данные из настроек Render
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
CHANNEL_PSY = os.getenv("CHANNEL_PSY")  # Твоя опора
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ")  # Идея и доход
MY_ID = os.getenv("MY_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Примеры текстов (можешь заменить на свои)
texts_psy = ["Спокойствие — это суперсила. Сделайте глубокий вдох.", "Ваш путь уникален, не сравнивайте себя с другими."]
texts_biz = ["Бизнес — это решение проблем других за деньги.", "Начните с малого, но думайте масштабно."]

async def handle(request):
    return web.Response(text="Бот-админ работает 24/7!")

async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=15&orientation=portrait"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        clip = VideoFileClip(v_in)
        # Исправляем ошибку subclip/subclipped из твоих логов
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 8)
        else:
            clip = clip.subclip(0, 8)
            
        clip = clip.resize(height=480)
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=15, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка монтажа: {e}")
        return None
    finally:
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

async def post_to_channel(channel_id, texts):
    if not channel_id: return
    text = random.choice(texts)
    video = await create_video_logic(text, "auto")
    if video:
        await bot.send_video(channel_id, FSInputFile(video), caption=text)
        os.remove(video)

# ПЛАНИРОВЩИК (Scheduler) для работы 24/7
async def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        # Посты в 09:00 и 18:00
        if now == "09:00":
            await post_to_channel(CHANNEL_PSY, texts_psy)
        if now == "18:00":
            await post_to_channel(CHANNEL_BIZ, texts_biz)
        await asyncio.sleep(60)

@dp.message(Command("test"))
async def test_cmd(message: types.Message):
    await message.answer("Запускаю тест видео для каналов...")
    await post_to_channel(CHANNEL_PSY, texts_psy)
    await post_to_channel(CHANNEL_BIZ, texts_biz)

async def main():
    # Запуск сервера для порта 10000 (бесплатно на Render)
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

    # Сброс старых обновлений (убирает Conflict)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск планировщика в фоне
    asyncio.create_task(scheduler())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
