import asyncio
import os
import random
import requests
from flask import Flask
from threading import Thread
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAEUuxKL4fmRPke8U9BvH7p2k6I-M0-yKic"
PEXELS_API_KEY = "VjznZIGQWVRr2ot6wxiihpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxmL"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask('')

@app.route('/')
def home(): return "Бот работает!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- ФУНКЦИИ ВИДЕО ---
async def download_random_video():
    queries = ['nature', 'calm', 'aesthetic']
    url = f"https://api.pexels.com/videos/search?query={random.choice(queries)}&per_page=10&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(url, headers=headers).json()
    video_url = random.choice(response['videos'])['video_files'][0]['link']
    with open("bg.mp4", "wb") as f: f.write(requests.get(video_url).content)
    return "bg.mp4"

async def generate_video(text):
    # 1. Голос
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("v.mp3")
    
    # 2. Видео фон
    bg_path = await download_random_video()
    video = VideoFileClip(bg_path)
    audio = AudioFileClip("v.mp3")
    
    if video.duration < audio.duration:
        from moviepy.video.fx.all import loop
        video = loop(video, duration=audio.duration)
    
    video = video.set_audio(audio).set_duration(audio.duration)

    # 3. Субтитры (Текст на экране)
    try:
        # Создаем текстовый слой (белый текст с черной обводкой)
        txt = TextClip(text, fontsize=50, color='white', font='Arial', method='caption', 
                       size=(video.w*0.8, None), stroke_color='black', stroke_width=2)
        txt = txt.set_position('center').set_duration(audio.duration)
        final = CompositeVideoClip([video, txt])
    except Exception as e:
        print(f"Ошибка субтитров: {e}. Будет только голос.")
        final = video

    final.write_videofile("res.mp4", codec="libx264", audio_codec="aac", fps=24)
    video.close()
    audio.close()
    return "res.mp4"

# --- ОБРАБОТКА ---
@dp.message()
async def handle(message: types.Message):
    # Печатаем ID для проверки
    print(f"Сообщение от {message.from_user.id}: {message.text}") 
    status = await message.answer("🎬 Создаю видео с голосом и текстом...")
    try:
        path = await generate_video(message.text)
        await bot.send_video(message.chat.id, video=FSInputFile(path), caption="✅ Готово!")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())

