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

# Надежный импорт MoviePy
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
    url = "https://api.pexels.com/videos/search?query=nature&per_page=10&orientation=portrait"

    try:
        # 1. Скачиваем фон
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        # 2. Озвучка текста
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Монтаж (решение проблемы AttributeError)
        clip = VideoFileClip(v_in)
        
        # Проверка версии библиотеки для команды обрезки
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 7)
        else:
            clip = clip.subclip(0, 7)
            
        clip = clip.resize(height=480) # Облегчаем задачу серверу Render
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        # Сохранение с минимальной нагрузкой на процессор
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=15, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка создания видео: {e}")
        return None
    finally:
        # Чистим временные файлы
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот-админ готов к работе! Пришли текст, и я сделаю видео.")

@dp.message(Command("test"))
async def test_cmd(message: types.Message):
    m = await message.answer("🎬 Запускаю тест создания видео...")
    path = await create_video_logic("Тестовое видео для проверки работы бота!", message.chat.id)
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path))
        os.remove(path)
        await m.delete()
    else:
        await message.answer("❌ Ошибка сборки видео. Проверь логи в Render.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith('/'): return
    m = await message.answer("⏳ Создаю видео, это займет около 30-40 секунд...")
    path = await create_video_logic(message.text, message.chat.id)
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path))
        os.remove(path)
        await m.delete()
    else:
        await message.answer("❌ Ошибка при создании видео. Попробуй текст покороче.")

async def main():
    # РЕШЕНИЕ ОШИБКИ CONFLICT: сбрасываем старые обновления
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
