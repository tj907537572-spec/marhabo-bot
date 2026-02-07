import os
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp
import aiofiles
from moviepy.editor import VideoFileClip, AudioFileClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def create_video_logic(text, chat_id):
    # Уникальные имена файлов, чтобы они не путались
    v_in = f"video_{chat_id}.mp4"
    a_in = f"audio_{chat_id}.mp3"
    v_out = f"final_{chat_id}.mp4"
    
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=15&orientation=portrait"

    try:
        # 1. Загрузка фона
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        # 2. Создание озвучки
        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        # 3. Легкий монтаж (только видео и звук, без наложения текста — это спасет память)
        clip = VideoFileClip(v_in).subclip(0, 7).resize(height=720) # Уменьшил качество до 720p для скорости
        audio = AudioFileClip(a_in)
        
        final = clip.set_audio(audio)
        # Параметр threads=1 и fps=20 снизит нагрузку на Render
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=20, logger=None, threads=1)
        
        clip.close()
        audio.close()
        
        return v_out
    except Exception as e:
        logging.error(f"ОШИБКА: {e}")
        return None
    finally:
        # Удаляем исходники сразу, чтобы освободить место
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Пришли мне текст, и я сделаю видео!")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith('/'): return
    
    msg = await message.answer("⏳ Начинаю работу... Это займет около 40-60 секунд.")
    path = await create_video_logic(message.text, message.chat.id)
    
    if path:
        await bot.send_video(message.chat.id, FSInputFile(path), caption="Готово!")
        os.remove(path) # Удаляем готовый файл
        await msg.delete()
    else:
        await message.answer("❌ Сервер перегружен. Попробуй текст покороче или подожди минуту.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
