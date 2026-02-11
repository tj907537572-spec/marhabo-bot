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

# Импорт MoviePy с правильными эффектами
from moviepy.editor import VideoFileClip, AudioFileClip
import moviepy.video.fx.all as vfx

# Настройки из Environment Variables в Render
TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
CHANNEL_PSY = os.getenv("CHANNEL_PSY")  # Твоя опора
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ")  # Идея и доход
MY_ID = os.getenv("MY_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Примеры текстов для автопостинга
texts_psy = ["Твоя сила внутри тебя. Верь в себя каждый день.", "Маленькие шаги ведут к большим целям."]
texts_biz = ["Успех — это сумма маленьких усилий, повторяемых изо дня в день.", "Инвестируй в свои знания."]

# Функция для порта 10000 (чтобы Render видел, что бот "Жив")
async def handle(request):
    return web.Response(text="Бот активен и работает 24/7!")

# ГЛАВНАЯ ЛОГИКА СОЗДАНИЯ ВИДЕО
async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=20&orientation=portrait"

    try:
        # 1. Качаем видео с Pexels
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        # 2. Озвучиваем текст
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Монтаж (MoviePy)
        clip = VideoFileClip(v_in)
        
        # Исправление длительности (duration) из твоих логов
        target_duration = min(clip.duration, 8) 
        clip = clip.subclip(0, target_duration)
        
        # Исправление resize (атрибут ошибки)
        clip = clip.fx(vfx.resize, height=480)
        
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        
        # Рендерим файл
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=15, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка в create_video_logic: {e}")
        return None
    finally:
        # Удаляем временные файлы
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

# Функция для отправки в каналы
async def post_to_channels():
    # Пост в первый канал
    res1 = await create_video_logic(random.choice(texts_psy), "auto1")
    if res1:
        await bot.send_video(CHANNEL_PSY, FSInputFile(res1), caption="📌 Совет дня")
        os.remove(res1)
    
    # Пост во второй канал
    res2 = await create_video_logic(random.choice(texts_biz), "auto2")
    if res2:
        await bot.send_video(CHANNEL_BIZ, FSInputFile(res2), caption="📈 Бизнес идея")
        os.remove(res2)

# Планировщик постов
async def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in ["09:00", "18:00"]:
            await post_to_channels()
            await asyncio.sleep(60) # Чтобы не спамить в течение этой минуты
        await asyncio.sleep(30)

# ОБРАБОТКА ТВОИХ СООБЩЕНИЙ (Бот слушает тебя)
@dp.message()
async def handle_admin_text(message: types.Message):
    # Проверка: пишет ли админ (ты)?
    if str(message.from_user.id) == str(MY_ID):
        user_msg = message.text
        
        if user_msg.lower().startswith("сделай"):
            clean_text = user_msg.lower().replace("сделай", "").strip()
            await message.answer(f"🚀 Начинаю создавать видео на тему: {clean_text}")
            
            video = await create_video_logic(clean_text, message.from_user.id)
            if video:
                await message.answer_video(FSInputFile(video), caption="Твоё видео готово!")
                os.remove(video)
            else:
                await message.answer("❌ Ошибка при создании видео.")
        else:
            await message.answer("Привет, Админ! Напиши 'Сделай [твой текст]', и я создам видео.")
    else:
        await message.answer("Я работаю только со своим создателем.")

# ЗАПУСК
async def main():
    # Веб-сервер для порта 10000
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()

    # Сброс старых сообщений (Conflict Error)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск планировщика
    asyncio.create_task(scheduler())
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
