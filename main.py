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
from aiohttp import web # Важно для бесплатной работы

try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Этот кусок кода нужен, чтобы Render не отключал бесплатный сервис
async def handle(request):
    return web.Response(text="Бот работает!")

async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=10&orientation=portrait"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())

        comm = Communicate(text, "ru-RU-SvetlanaNeural")
        await comm.save(a_in)

        clip = VideoFileClip(v_in)
        # Исправляем AttributeError: subclip -> subclipped
        if hasattr(clip, "subclipped"):
            clip = clip.subclipped(0, 7)
        else:
            clip = clip.subclip(0, 7)
            
        clip = clip.resize(height=480)
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=15, logger=None, threads=1)
        
        clip.close()
        audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Error: {e}")
        return None
    finally:
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот запущен бесплатно!")

async def main():
    # Запускаем веб-сервер, чтобы Render "видел" порт и не отключал бота
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start() 

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
       
