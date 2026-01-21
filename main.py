import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Для расписания
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# --- ТВОИ ДАННЫЕ ---
TOKEN = "8275988872:AAEUuxKL4fmRPke8U3HYpziS9M3ZJ6UBa_Y"
ADMIN_ID = 6341390660
CHANNEL_ID = "@tvoia_opora"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Очередь для постов (храним пути к готовым видео)
posts_queue = []

# 1. Функция озвучки (Светлана)
async def get_voice(text, filename):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save(filename)

# 2. Функция для генерации видео
async def generate_video(text):
    # Здесь должна быть логика для генерации видео
    # Например, можно использовать библиотеку moviepy
    # Для примера, создадим простое видео
    video = VideoFileClip("example_video.mp4")
    audio = AudioFileClip("example_audio.mp3")
    final_clip = video.set_audio(audio)
    final_clip.write_videofile("result_video.mp4")
    return "result_video.mp4"

# 3. Функция, которая САМА постит по расписанию
async def send_scheduled_post():
    if posts_queue:
        video_path = posts_queue.pop(0) # Берем самое первое видео из очереди
        video = FSInputFile(video_path)
        await bot.send_video(chat_id=CHANNEL_ID, video=video, caption="🌿 Твоя минута спокойствия... #психология")
        print("Пост опубликован по расписанию!")

# Настройка расписания (по Москве/твоему времени)
scheduler.add_job(send_scheduled_post, "cron", hour="09,14,20", minute=0)
scheduler.start()

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer("🎙 Светлана начала озвучку. Видео добавлено в очередь на публикацию (09:00, 14:00, 20:00).")
    
    # Здесь логика:
    # 1. voice = await get_voice(message.text, "v.mp3")
    # 2. video = await generate_video(message.text)
    # 3. result = await merge_audio_video(video, voice)
    
    # Имитируем добавление в очередь
    video_path = await generate_video(message.text)
    posts_queue.append(video_path) 
    await message.answer(f"✅ Готово! В очереди сейчас видео: {len(posts_queue)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
