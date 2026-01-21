import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip

# --- ДАННЫЕ —--
# Рекомендуется использовать os.getenv("BOT_TOKEN"), но для запуска вставляю ваш:
TOKEN = "8275988872:AAEUuxKL4fmRPke8U9BvH7p2k6I-M0-yKic"
ADMIN_ID = 6341390660
CHANNEL_ID = "@tvoia_opora"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

posts_queue = []

# 1. Функция озвучки
async def get_voice(text, filename):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save(filename)

# 2. Функция для генерации видео
async def generate_video(text):
    # ПРОВЕРКА: Если файлов нет, бот выдаст ошибку, но не выключится
    if not os.path.exists("example_video.mp4"):
        print("Ошибка: Файл example_video.mp4 не найден!")
        return None
        
    video = VideoFileClip("example_video.mp4")
    # Здесь логика озвучки должна создавать v.mp3
    if os.path.exists("v.mp3"):
        audio = AudioFileClip("v.mp3")
        final_clip = video.set_audio(audio)
        final_clip.write_videofile("result_video.mp4", codec="libx264")
        return "result_video.mp4"
    return None

# 3. Функция публикации
async def send_scheduled_post():
    if posts_queue:
        video_path = posts_queue.pop(0)
        if os.path.exists(video_path):
            video = FSInputFile(video_path)
            await bot.send_video(chat_id=CHANNEL_ID, video=video, caption="🌿 Твоя минута спокойствия... #психология")
            print("Пост опубликован!")

# Настройка расписания
scheduler.add_job(send_scheduled_post, "cron", hour="09,14,20", minute=0)

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer("🎙 Начинаю обработку. Подождите...")
    
    # Озвучка
    await get_voice(message.text, "v.mp3")
    
    # Генерация
    video_path = await generate_video(message.text)
    
    if video_path:
        posts_queue.append(video_path) 
        await message.answer(f"✅ Видео готово и добавлено в очередь. Всего в очереди: {len(posts_queue)}")
    else:
        await message.answer("❌ Ошибка: загрузите файл example_video.mp4 на сервер!")

async def main():
    # Запуск планировщика внутри main
    scheduler.start()
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

    
