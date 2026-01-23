import asyncio
import os
import random
import requests
from flask import Flask
from threading import Thread
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAEUuxKL4fmRPke8U9BvH7p2k6I-M0-yKic"
PEXELS_API_KEY = "VjznZIGQWVRr2ot6wxiihpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxmL"
ADMIN_ID = 6341390660 # Ваш ID из BotFather

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (ПОРТ 10000) ---
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- ФУНКЦИИ СОЗДАНИЯ ВИДЕО ---
async def download_random_video():
    queries = ['nature', 'calm', 'mountains', 'aesthetic']
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(url, headers=headers).json()
    video_data = random.choice(response['videos'])
    video_url = video_data['video_files'][0]['link']
    
    video_path = "bg_video.mp4"
    with open(video_path, "wb") as f:
        f.write(requests.get(video_url).content)
    return video_path

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

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@dp.message(F.text)
async def handle_text(message: types.Message):
    # Проверка вашего ID
    if message.from_user.id != ADMIN_ID:
        return 
    
    status = await message.answer("🎬 Вижу текст! Начинаю создавать видео...")
    print(f"Админ прислал текст: {message.text}")
    
    try:
        path = await generate_video(message.text)
        video_file = FSInputFile(path)
        await bot.send_video(chat_id=message.chat.id, video=video_file, caption="✅ Видео готово!")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")
        print(f"Ошибка: {e}")

# --- ЗАПУСК ---
async def main():
    # Эта строка заставляет бота сбросить старые ошибки и начать слушать вас
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен и ждет сообщения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # Запуск сервера для Render
    asyncio.run(main()) # Запуск бота

