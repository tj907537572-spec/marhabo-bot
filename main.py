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

# Настройки из Render
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
CHANNEL_PSY = os.getenv("CHANNEL_PSY")
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ")
MY_ID = os.getenv("MY_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция для веб-порта (чтобы Render не отключал)
async def handle(request):
    return web.Response(text="Бот активен 24/7")

# ЛОГИКА СОЗДАНИЯ ВИДЕО
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

        from moviepy.editor import VideoFileClip, AudioFileClip
        clip = VideoFileClip(v_in)
        # Исправленная команда из твоих логов
        clip = clip.subclipped(0, 8) if hasattr(clip, "subclipped") else clip.subclip(0, 8)
        clip = clip.resize(height=480)
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=15, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None
    finally:
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

# ОБРАБОТЧИК ТВОИХ СООБЩЕНИЙ
@dp.message()
async def handle_admin_text(message: types.Message):
    # Проверка, что пишет именно АДМИН
    if str(message.from_user.id) == str(MY_ID):
        user_text = message.text
        # Если просишь сделать видео
        if "сделай видео" in user_text.lower():
            clean_text = user_text.lower().replace("сделай видео", "").strip()
            await message.answer(f"⏳ Создаю видео с текстом: {clean_text}")
            video = await create_video_logic(clean_text, message.from_user.id)
            if video:
                await message.answer_video(FSInputFile(video), caption="Готово!")
                os.remove(video)
        else:
            await message.answer("Я тебя слышу! Если хочешь видео, напиши: Сделай видео [твой текст]")
    else:
        await message.answer("Я работаю только с админом.")

# Запуск бота
async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
