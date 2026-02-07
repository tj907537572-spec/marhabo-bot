import os
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from edge_tts import Communicate
import aiohttp
import aiofiles

# Пытаемся импортировать moviepy аккуратно
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА СОЗДАНИЯ ВИДЕО ---
async def create_video_logic(text, category="psy"):
    query = "nature" if category == "psy" else "business"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    
    v_in, a_in, v_out = f"v_{category}.mp4", f"a_{category}.mp3", f"final_{category}.mp4"

    try:
        # 1. Загрузка видео
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        # 2. Озвучка
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Сборка
        clip = VideoFileClip(v_in)
        # Поддержка разных версий moviepy
        clip = clip.subclipped(0, 8) if hasattr(clip, "subclipped") else clip.subclip(0, 8)
        clip = clip.resize(height=1280)
        
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("test"))
async def test_cmd(message: types.Message):
    await message.answer("🎬 Начинаю сборку теста...")
    path = await create_video_logic("Бот работает и видео создается!", "psy")
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path), caption="✅ Тест пройден!")
        if os.path.exists(path): os.remove(path)
    else:
        await message.answer("❌ Ошибка. Проверь логи Render.")

@dp.message(F.text)
async def handle_any_text(message: types.Message):
    # Если это не команда, делаем видео
    if not message.text.startswith('/'):
        await message.answer(f"⏳ Делаю видео на твой текст: «{message.text}»")
        path = await create_video_logic(message.text, "psy")
        if path:
            await bot.send_video(message.chat.id, FSInputFile(path), caption="✨ Твое видео готово!")
            if os.path.exists(path): os.remove(path)
        else:
            await message.answer("❌ Ошибка при создании видео.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
