import asyncio
import os
import random
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# --- НАСТРОЙКИ ---
# ВАЖНО: Если этот токен не работает, возьмите новый у @BotFather!
TOKEN =" 8275988872:AAFO_SAYsfWD_PywJ6RRk8wzmCOwZ41wWGQ"
# Замените на ваш реальный ID (можно узнать в боте @userinfobot)
ADMIN_ID = 6341390660

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(name)

logging.basicConfig(level=logging.INFO)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
@app.route('/')
def home():
    return "Бот-видеомейкер активен!"

def run_web_server():
    # Порт должен браться из переменной окружения Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА СОЗДАНИЯ ВИДЕО ---
async def create_video(text, output_name="result.mp4"):
    # 1. Генерируем голос
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save("voice.mp3")
    
    # 2. Подготовка аудио и видео
    audio = AudioFileClip("voice.mp3")
    
    # ВАЖНО: Файл background.mp4 ДОЛЖЕН быть в вашем GitHub!
    if not os.path.exists("background.mp4"):
        raise FileNotFoundError("Загрузите файл background.mp4 в GitHub!")

    video = VideoFileClip("background.mp4").subclip(0, audio.duration)
    
    # 3. Субтитры
    txt_clip = TextClip(text, fontsize=50, color='white', font='Arial', 
                        method='caption', size=(video.w*0.8, None))
    txt_clip = txt_clip.set_duration(audio.duration).set_position('center')
    
    # Сборка
    final_video = CompositeVideoClip([video, txt_clip])
    final_video = final_video.set_audio(audio)
    final_video.write_videofile(output_name, fps=24, codec="libx264", audio_codec="aac")
    
    return output_name

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Пришлите текст, и я сделаю видео с озвучкой и субтитрами!")

@dp.message(F.text)
async def handle_text(message: types.Message):
    # Проверка на админа (если нужно ограничить доступ)
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к созданию видео.")
        return

    status_msg = await message.answer("⏳ Начинаю создание видео...")
    try:
        video_path = await create_video(message.text)
        await message.answer_video(FSInputFile(video_path), caption="Ваше видео готово!")
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logging.error(f"Ошибка создания видео: {e}")

async def main():
    # Удаляем вебхук для работы в режиме polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if name == "main":
    # Запуск сервера для предотвращения остановки Render
    Thread(target=run_web_server, daemon=True).start()
    asyncio.run(main())

