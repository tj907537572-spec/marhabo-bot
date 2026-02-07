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

# Пытаемся импортировать инструменты для видео
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def create_video_logic(text):
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=10&orientation=portrait"
    
    v_in, a_in, v_out = "video_temp.mp4", "audio_temp.mp3", "result.mp4"

    try:
        # 1. Качаем фон
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        # 2. Делаем голос
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Собираем видео
        clip = VideoFileClip(v_in)
        # Проверка на версию библиотеки
        clip = clip.subclip(0, 8) if hasattr(clip, "subclip") else clip.subclipped(0, 8)
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

@dp.message(Command("test"))
async def test_cmd(message: types.Message):
    await message.answer("🎬 Собираю видео-тест...")
    path = await create_video_logic("Бот снова в строю!")
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path))
        if os.path.exists(path): os.remove(path)
    else:
        await message.answer("❌ Ошибка. Проверь логи Render.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if not message.text.startswith('/'):
        await message.answer(f"⏳ Делаю видео на твой текст: «{message.text}»")
        path = await create_video_logic(message.text)
        if path:
            await bot.send_video(message.chat.id, FSInputFile(path))
            if os.path.exists(path): os.remove(path)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
