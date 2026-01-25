import asyncio
import os
import random
import logging
import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

# --- НАСТРОЙКИ ---
TOKEN = "8275988872:AAHpernZv9mZScnQz2nBCkK-yiNfiZLGQhM" #
PEXELS_API_KEY = "VjznZIGQwVRr2ot6wxiiHpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxml" #
ADMIN_ID = 6341390660# Ваш ID

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home(): return "Бот работает!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Функция для создания картинки с текстом (замена ImageMagick)
def create_text_image(text, size):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Используем стандартный шрифт
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Рисуем текст по центру с обводкой
    w, h = size
    draw.text((w/2, h/2), text, font=font, fill="white", anchor="mm", stroke_width=2, stroke_fill="black")
    img.save("text_overlay.png")
    return "text_overlay.png"

async def create_video_logic(text):
    # 1. Голос
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    audio = AudioFileClip("voice.mp3")

    # 2. Видео с Pexels
    headers = {"Authorization": PEXELS_API_KEY}
    res = requests.get(f"https://api.pexels.com/videos/search?query=nature&orientation=portrait&per_page=1", headers=headers).json()
    video_url = res['videos'][0]['video_files'][0]['link']
    
    with requests.get(video_url) as r:
        with open("bg.mp4", 'wb') as f: f.write(r.content)

    # 3. Сборка
    video = VideoFileClip("bg.mp4").subclip(0, audio.duration)
    text_img_path = create_text_image(text, video.size)
    txt_clip = ImageClip(text_img_path).set_duration(audio.duration).set_position('center')
    
    final = CompositeVideoClip([video, txt_clip]).set_audio(audio)
    final.write_videofile("result.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "result.mp4"

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("Бот готов! Пришлите текст для видео.")

@dp.message(F.text)
async def handle_text(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    status = await m.answer("⏳ Создаю видео (скачиваю фон и озвучиваю)...")
    try:
        path = await create_video_logic(m.text)
        await m.answer_video(FSInputFile(path))
        await status.delete()
    except Exception as e:
        await m.answer(f"Ошибка: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


