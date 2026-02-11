import os
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp
import aiofiles
from aiohttp import web
from datetime import datetime

# Импорт MoviePy
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip

# Данные из Environment Variables на Render
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Настройки каналов (Замени на свои ID или добавь в Environment)
CHANNEL_PSY = os.getenv("CHANNEL_PSY") # ID канала про психологию
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ") # ID канала про бизнес

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Контент для постов (примеры, можно дополнять)
texts_psy = [
    "Секрет спокойствия в умении отпускать то, что вы не можете контролировать.",
    "Ваша ментальная гигиена так же важна, как и физическая. Сделайте паузу.",
    "Психология успеха начинается с принятия своих поражений как опыта."
]

texts_biz = [
    "Лучшая идея для бизнеса — та, которая решает реальную проблему людей.",
    "Доход зависит не от того, сколько вы работаете, а от того, какую ценность создаете.",
    "Малый бизнес сегодня — это фундамент большой экономики завтра."
]

# Веб-сервер для бесплатной работы на Render
async def handle(request):
    return web.Response(text="Бот-админ работает и планирует посты!")

async def create_video(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    # Ищем видео природы для атмосферы
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
        logging.error(f"Ошибка видео: {e}")
        return None
    finally:
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

# Функция для публикации поста
async def send_daily_post(channel_id, texts):
    text = random.choice(texts)
    video_path = await create_video(text, "auto")
    if video_path:
        await bot.send_video(channel_id, FSInputFile(video_path), caption=text)
        os.remove(video_path)

# Планировщик задач
async def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        # Постим в 09:00 и в 18:00
        if now in ["09:00", "18:00"]:
            if CHANNEL_PSY:
                await send_daily_post(CHANNEL_PSY, texts_psy)
            if CHANNEL_BIZ:
                await send_daily_post(CHANNEL_BIZ, texts_biz)
            await asyncio.sleep(65) # Чтобы не постить дважды в одну минуту
        await asyncio.sleep(30)

async def main():
    # Запуск заглушки для бесплатного Render
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start() 

    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем планировщик фоном
    asyncio.create_task(scheduler())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

