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
TOKEN = "8275988872:AAEUuxKL4fmRPke8U9BvH7p2k6I-M0-yKic" # Убедитесь, что это ваш последний токен
PEXELS_API_KEY = "VjznZIGQWVRr2ot6wxiihpdRMdetxpnxIdAiG9NTP5k6ZLCrnRaqBxmL"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Бот активен!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- ФУНКЦИИ ВИДЕО ---
async def download_random_video():
    queries = ['nature', 'calm', 'dark aesthetic', 'galaxy']
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
    # 1. Озвучка текста (Голос)
    voice = "ru-RU-SvetlanaNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("v.mp3")
    
    # 2. Скачивание видео фона
    bg_path = await download_random_video()
    
    # 3. Обработка видео и аудио
    video = VideoFileClip(bg_path)
    audio = AudioFileClip("v.mp3")
    
    # Зацикливаем видео, если оно короче аудио
    if video.duration < audio.duration:
        from moviepy.video.fx.all import loop
        video = loop(video, duration=audio.duration)
    
    video = video.set_audio(audio).set_duration(audio.duration)

    # 4. Добавление субтитров (Текст на экране)
    # Мы создаем текстовый слой. Если на Render не установлен ImageMagick, текст может не отобразиться.
    try:
        txt_clip = TextClip(text, fontsize=40, color='white', font='Arial-Bold', 
                            method='caption', size=(video.w*0.8, None), stroke_color='black', stroke_width=1)
        txt_clip = txt_clip.set_position('center').set_duration(audio.duration)
        final_video = CompositeVideoClip([video, txt_clip])
    except:
        print("Ошибка ImageMagick: видео будет без текста, только с голосом.")
        final_video = video

    # 5. Сохранение
    final_video.write_videofile("result.mp4", codec="libx264", audio_codec="aac", fps=24)
    
    video.close()
    audio.close()
    return "result.mp4"

# --- ОБРАБОТКА СООБЩЕНИЙ (БЕЗ ПРОВЕРКИ ID) ---
@dp.message()
async def handle_text(message: types.Message):
    # Теперь бот пишет в логи ВСЁ, что получает
    print(f"ПОЛУЧЕНО: {message.text} от {message.from_user.id}")
    
    status = await message.answer("🎬 Начинаю озвучку и создание видео с текстом...")
    
    try:
        path = await generate_video(message.text)
        video_file = FSInputFile(path)
        await bot.send_video(chat_id=message.chat.id, video=video_file, caption="✅ Ваше видео готово!")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Произошла ошибка: {e}")
        print(f"ОШИБКА: {e}")

# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен и готов создавать видео!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())

