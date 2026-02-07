import os
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from edge_tts import Communicate
import aiohttp
import aiofiles
from moviepy.editor import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def create_video_logic(text, category):
    query = "nature" if category == "psy" else "business"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=10&orientation=portrait"
    
    # Пути к файлам
    v_in = f"v_{category}.mp4"
    a_in = f"a_{category}.mp3"
    v_out = f"final_{category}.mp4"

    try:
        # 1. Качаем видео
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    if vr.status == 200:
                        async with aiofiles.open(v_in, mode='wb') as f:
                            await f.write(await vr.read())

        # 2. Делаем озвучку
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Монтаж (Исправлено под новую версию MoviePy)
        clip = VideoFileClip(v_in)
        
        # Проверка версии: пробуем subclipped (новая), если нет - subclip (старая)
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 8).resize(height=1280)
        else:
            clip = clip.subclip(0, 8).resize(height=1280)
            
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        # Сохранение
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"ОШИБКА: {e}")
        return None

@dp.message(Command("test"))
async def test_cmd(message: types.Message):
    await message.answer("🎬 Начинаю сборку... Пожалуйста, подожди минуту.")
    path = await create_video_logic("Проверка работы видео успешно завершена!", "psy")
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path), caption="✅ Готово!")
        if os.path.exists(path): os.remove(path)
    else:
        await message.answer("❌ Ошибка в коде. Посмотри логи в Render.")

@dp.message()
async def handle_text(message: types.Message):
    if message.text and not message.text.startswith('/'):
        await message.answer(f"⏳ Делаю видео на твой текст: «{message.text}»")
        path = await create_video_logic(message.text, "psy")
        if path:
            await bot.send_video(message.chat.id, FSInputFile(path), caption="✨ Твоё видео!")
            if os.path.exists(path): os.remove(path)
        else:
            await message.answer("❌ Не удалось создать видео.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


