import os
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp
import aiofiles

# Пытаемся импортировать moviepy максимально надежно для любой версии
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=15&orientation=portrait"

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

        # 3. Монтаж (Исправляем ошибку subclip/subclipped)
        clip = VideoFileClip(v_in)
        
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 6) # Для новой версии
        else:
            clip = clip.subclip(0, 6)    # Для старой версии
            
        clip = clip.resize(height=720)
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=20, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка монтажа: {e}")
        return None
    finally:
        # Чистим мусор сразу
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот запущен! Пришли текст, и я сделаю видео.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith('/'): return
    m = await message.answer("⏳ Собираю видео (около 30-40 сек)...")
    path = await create_video_logic(message.text, message.chat.id)
    
    if path and os.path.exists(path):
        await bot.send_video(message.chat.id, FSInputFile(path))
        os.remove(path)
        await m.delete()
    else:
        await message.answer("❌ Ошибка. Скорее всего, сервер перегружен.")

async def main():
    # Эта строчка УБИВАЕТ конфликт (выключает другие копии бота)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
