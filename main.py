import asyncio
import os
import random
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAGyaKaHI42ykqCA3MO8ceSpWAqy4K-_Se8"
PEXELS_API_KEY = "VjznZIGQWVRr2ot6wxiihpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxmL"
ADMIN_ID = 6341390660
CHANNEL_ID = "@tvoia_opora"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
posts_queue = []

# Функция поиска и скачивания видео с Pexels
async def download_random_video():
    queries = ['nature', 'calm', 'aesthetic', 'mountains', 'sea', 'forest']
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    
    response = requests.get(url, headers=headers).json()
    video_data = random.choice(response['videos'])
    # Берем ссылку на мобильное качество, чтобы Render не завис
    video_url = video_data['video_files'][0]['link']
    
    with open("bg_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)
    return "bg_video.mp4"

async def generate_video(text):
    # 1. Озвучка текста
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("v.mp3")
    
    # 2. Авто-поиск фона
    bg_path = await download_random_video()
    
    # 3. Сборка видео и звука
    video = VideoFileClip(bg_path)
    audio = AudioFileClip("v.mp3")
    
    # Если видео короче голоса, зацикливаем
    if video.duration < audio.duration:
        from moviepy.video.fx.all import loop
        video = loop(video, duration=audio.duration)
    
    final = video.set_audio(audio).set_duration(audio.duration)
    final.write_videofile("result.mp4", codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True)
    
    video.close()
    audio.close()
    return "result.mp4"

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    status = await message.answer("🔍 Ищу красивый фон и озвучиваю текст...")
    try:
        path = await generate_video(message.text)
        video_file = FSInputFile(path)
        await bot.send_video(chat_id=message.chat.id, video=video_file, caption="✅ Ваше видео готово!")
        # Добавляем в очередь для канала
        posts_queue.append(path)
    except Exception as e:
        await status.edit_text(f"❌ Произошла ошибка: {e}")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


    
