import asyncio
import os
import random
import requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAEUuxKL4fmRPke8U9BvH7p2k6I-M0-yKic"
PEXELS_API_KEY = "VjznZIGQWVRr2ot6wxiihpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxmL"
ADMIN_ID = 6341390660
CHANNEL_ID = "@tvoia_opora"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- МИНИ-СЕРВЕР ДЛЯ CRON-JOB ---
app = Flask('')

@app.route('/')
def home():
    return "Бот работает и не спит!"

def run_web_server():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- ФУНКЦИИ БОТА ---
async def download_random_video():
    queries = ['nature', 'calm', 'aesthetic', 'mountains', 'forest']
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(url, headers=headers).json()
    video_data = random.choice(response['videos'])
    video_url = video_data['video_files'][0]['link']
    with open("bg_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)
    return "bg_video.mp4"

async def generate_video(text):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("v.mp3")
    bg_path = await download_random_video()
    video = VideoFileClip(bg_path)
    audio = AudioFileClip("v.mp3")
    if video.duration < audio.duration:
        from moviepy.video.fx.all import loop
        video = loop(video, duration=audio.duration)
    final = video.set_audio(audio).set_duration(audio.duration)
    final.write_videofile("result.mp4", codec="libx264", audio_codec="aac")
    video.close()
    audio.close()
    return "result.mp4"

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.from_user.id !=6341390660 : return
    status = await message.answer("🎬 Начинаю создание видео...")
    try:
        path = await generate_video(message.text)
        video_file = FSInputFile(path)
        await bot.send_video(chat_id=message.chat.id, video=video_file, caption="✅ Видео готово!")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # Запуск сервера для Cron-job
    asyncio.run(main())



    
