import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# --- НАСТРОЙКИ ---
# ЗАМЕНИТЕ ЭТОТ ТОКЕН НА НОВЫЙ ИЗ @BotFather!
TOKEN = "8275988872:AAHpernZv9mZScnQz2nBCkK-yiNfiZLGQhM"
# Узнайте свой ID у бота @userinfobot
ADMIN_ID = 6341390660

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# --- СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ ПАДАЛ) ---
@app.route('/')
def home():
    return "Бот активен и готов создавать видео!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА ВИДЕО ---
async def create_video(text, output_name="result.mp4"):
    # Озвучка
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    audio = AudioFileClip("voice.mp3")
    
    # Фон (файл background.mp4 должен быть в GitHub!)
    if not os.path.exists("background.mp4"):
        raise FileNotFoundError("Ошибка: загрузите файл background.mp4 в свой репозиторий!")
    
    video = VideoFileClip("background.mp4").subclip(0, audio.duration)
    
    # Субтитры
    txt_clip = TextClip(text, fontsize=45, color='white', font='Arial', 
                        method='caption', size=(video.w*0.8, None))
    txt_clip = txt_clip.set_duration(audio.duration).set_position('center')
    
    # Сборка видео
    final = CompositeVideoClip([video, txt_clip]).set_audio(audio)
    final.write_videofile(output_name, fps=24, codec="libx264")
    return output_name

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет, Админ! Пришли текст для видео.")

@dp.message(F.text)
async def handle_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return # Игнорируем не админов
    
    msg = await message.answer("⏳ Создаю видео с голосом и субтитрами...")
    try:
        path = await create_video(message.text)
        await message.answer_video(FSInputFile(path))
        await msg.delete()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# --- ЗАПУСК ---
async def main_loop():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем Flask в фоне
    Thread(target=run_web_server, daemon=True).start()
    # Запускаем бота
    asyncio.run(main_loop())

