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

# Умный импорт moviepy
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except (ImportError, ModuleNotFoundError):
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=10&orientation=portrait"

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

        # 3. Монтаж (упрощенный)
        clip = VideoFileClip(v_in)
        # Поддержка разных версий
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 6)
        else:
            clip = clip.subclip(0, 6)
            
        clip = clip.without_audio().resize(height=720)
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=20, logger=None)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Отправь мне текст для видео!")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith('/'): return
    m = await message.answer("🚀 Начинаю делать видео...")
    path = await create_video_logic(message.text, message.chat.id)
    
    if path and os.path.exists(path):
        await bot.send_video(message.chat.id, FSInputFile(path))
        os.remove(path)
        await m.delete()
    else:
        await message.answer("❌ Ошибка сборки. Попробуй еще раз.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
