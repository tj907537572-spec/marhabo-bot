import os, random, asyncio, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp, aiofiles
from aiohttp import web
from moviepy.editor import VideoFileClip, AudioFileClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
MY_ID = os.getenv("MY_ID")
CHANNEL_PSY = os.getenv("CHANNEL_PSY")
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ")

bot = Bot(token=TOKEN)
dp = Dispatcher()

texts_psy = ["Твоё спокойствие — твоя сила.", "Счастье внутри тебя.", "Верь в свой путь."]
texts_biz = ["Бизнес-идея: ИИ-сервисы.", "Стратегия 80/20 для роста.", "Инвестируй в навыки."]

async def create_video_logic(text, chat_id):
    v_in, a_in, v_out = f"v_{chat_id}.mp4", f"a_{chat_id}.mp3", f"res_{chat_id}.mp4"
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search?query=nature&per_page=15&orientation=portrait"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                v_link = random.choice(data['videos'])['video_files'][0]['link']
                async with session.get(v_link) as vr:
                    async with aiofiles.open(v_in, mode='wb') as f:
                        await f.write(await vr.read())
        await Communicate(text, "ru-RU-SvetlanaNeural").save(a_in)
        
        # УПРОЩЕННЫЙ МОНТАЖ (БЕЗ RESIZE)
        clip = VideoFileClip(v_in).subclip(0, 7).without_audio()
        audio = AudioFileClip(a_in)
        final = clip.set_audio(audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        clip.close(); audio.close()
        return v_out
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None
    finally:
        for f in [v_in, a_in]:
            if os.path.exists(f): os.remove(f)

async def send_auto_posts():
    v1 = await create_video_logic(random.choice(texts_psy), "auto_psy")
    if v1:
        await bot.send_video(CHANNEL_PSY, FSInputFile(v1), caption="🧠 Психология")
        os.remove(v1)
    v2 = await create_video_logic(random.choice(texts_biz), "auto_biz")
    if v2:
        await bot.send_video(CHANNEL_BIZ, FSInputFile(v2), caption="🚀 Идея и доход")
        os.remove(v2)

async def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in ["09:00", "18:00"]:
            await send_auto_posts()
            await asyncio.sleep(60)
        await asyncio.sleep(30)

@dp.message()
async def handle_msg(message: types.Message):
    if str(message.from_user.id) == str(MY_ID) and message.text.lower().startswith("сделай"):
        clean_text = message.text.lower().replace("сделай", "").strip()
        msg = await message.answer("🛠 Собираю видео...")
        video = await create_video_logic(clean_text, message.from_user.id)
        if video:
            await message.answer_video(FSInputFile(video))
            os.remove(video)
        else:
            await message.answer("❌ Ошибка монтажа.")
        await msg.delete()

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()
    
    await bot.delete_webhook(drop_pending_updates=True) 
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
