import os
import random
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
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

# Каналы для автопостинга
CHANNELS = {
    "psy": "@vasha_opora",
    "money": "@income_ideas"
}

# Цитаты для автопостинга
QUOTES_PSY = ["Твоя сила внутри тебя.", "Каждый день — новый шанс.", "Верь в себя!"]
QUOTES_MONEY = ["Деньги любят движение.", "Инвестируй в знания.", "Богатство — это состояние ума."]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ СОЗДАНИЯ ВИДЕО ---
async def create_video_logic(text, category):
    # 1. Поиск видео на Pexels
    query = "nature" if category == "psy" else "business"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
    
    video_path = f"temp_v_{category}.mp4"
    audio_path = f"temp_a_{category}.mp3"
    output_path = f"final_{category}.mp4"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                video_url = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(video_url) as v_resp:
                    if v_resp.status == 200:
                        async with aiofiles.open(video_path, mode='wb') as f:
                            await f.write(await v_resp.read())

        # 2. Озвучка текста
        communicate = Communicate(text, "ru-RU-SvetlanaNeural")
        await communicate.save(audio_path)

        # 3. Монтаж через MoviePy
        clip = VideoFileClip(video_path).subclip(0, 8).resize(height=1280)
        audio = AudioFileClip(audio_path)
        
        # Накладываем текст (если ImageMagick настроен на сервере)
        # Если будет ошибка с текстом, можно оставить только видео + звук
        final = clip.set_audio(audio)
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        clip.close()
        audio.close()
        return output_path
    except Exception as e:
        logging.error(f"Ошибка при создании видео: {e}")
        return None

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 Бот запущен! \n1. Я сам пишу посты в каналы.\n2. Пришли мне любой текст, и я сделаю из него видео!")

@dp.message(Command("test"))
async def test_video(message: types.Message):
    await message.answer("🛠 Запускаю тест создания видео...")
    path = await create_video_logic("Тестовая проверка прошла успешно!", "psy")
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path), caption="✅ Тест пройден!")
        os.remove(path)
    else:
        await message.answer("❌ Ошибка. Проверь логи Render.")

# --- ГЛАВНАЯ ФУНКЦИЯ: ВИДЕО ПО ТВОЕМУ ТЕКСТУ ---
@dp.message()
async def handle_any_text(message: types.Message):
    if message.text and not message.text.startswith('/'):
        txt = message.text
        await message.answer(f"🎬 Принято! Делаю видео с твоим текстом:\n\n«{txt}»\n\nПодожди около минуты...")
        
        path = await create_video_logic(txt, "psy")
        
        if path:
            await bot.send_video(message.chat.id, FSInputFile(path), caption="✨ Твоё персональное видео готово!")
            os.remove(path) # Удаляем, чтобы не занимать место
            # Чистим временные файлы
            for f in [f"temp_v_psy.mp4", f"temp_a_psy.mp3"]:
                if os.path.exists(f): os.remove(f)
        else:
            await message.answer("❌ Не удалось создать видео. Попробуй текст покороче или проверь статус сервера.")

# --- РАСПИСАНИЕ (АВТОПОСТИНГ) ---
async def scheduled_post(category):
    quotes = QUOTES_PSY if category == "psy" else QUOTES_MONEY
    txt = random.choice(quotes)
    path = await create_video_logic(txt, category)
    if path:
        await bot.send_video(CHANNELS[category], FSInputFile(path), caption=txt)
        os.remove(path)

async def main():
    # Настройка расписания
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(scheduled_post, "cron", hour=9, minute=0, args=["psy"])
    scheduler.add_job(scheduled_post, "cron", hour=15, minute=0, args=["money"])
    scheduler.start()

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
