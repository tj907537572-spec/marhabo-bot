import os, random, asyncio, logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from edge_tts import Communicate
import aiohttp, aiofiles
from aiohttp import web
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

TOKEN = os.getenv("BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
MY_ID = os.getenv("MY_ID")
CHANNEL_PSY = os.getenv("CHANNEL_PSY")
CHANNEL_BIZ = os.getenv("CHANNEL_BIZ")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция для поиска картинки и отправки поста
async def send_image_post(text, channel_id):
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/v1/search?query=minimalism+success&per_page=10"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                img_url = random.choice(data['photos'])['src']['large']
                await bot.send_photo(channel_id, photo=img_url, caption=text)
                return True
    except Exception as e:
        logging.error(f"Ошибка поста: {e}")
        return False

# Твоя функция видео (обновленная под системный шрифт)
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
        await Communicate(text, "ru-RU-SvetlanaNeural").save(a_in)
        clip = VideoFileClip(v_in).subclip(0, 7).without_audio()
        audio = AudioFileClip(a_in)
        # Используем стандартный шрифт, который точно есть в системе
        txt = TextClip(text.upper(), fontsize=40, color='white', font='DejaVu-Sans', 
                       method='caption', size=(clip.w*0.8, None)).set_duration(audio.duration).set_position('center')
        final = CompositeVideoClip([clip, txt]).set_audio(audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=24, logger=None)
        return v_out
    except Exception as e:
        logging.error(f"Ошибка видео: {e}")
        return None

@dp.message()
async def handle_msg(message: types.Message):
    if str(message.from_user.id) != str(MY_ID): return

    # Команда для ПОСТА С КАРТИНКОЙ
    if message.text.lower().startswith("пост"):
        content = message.text[4:].strip()
        target_channel = CHANNEL_PSY if "психо" in content.lower() else CHANNEL_BIZ
        await message.answer("📸 Ищу подходящую картинку и отправляю пост...")
        success = await send_image_post(content, target_channel)
        if success: await message.answer("✅ Пост опубликован в канале!")
        else: await message.answer("❌ Ошибка при создании поста.")

    # Команда для ВИДЕО
    elif message.text.lower().startswith("сделай"):
        content = message.text[6:].strip()
        msg = await message.answer("🎬 Создаю видео с субтитрами...")
        video = await create_video_logic(content, message.from_user.id)
        if video:
            await message.answer_video(FSInputFile(video))
            os.remove(video)
        else: await message.answer("❌ Ошибка монтажа.")
        await msg.delete()

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()
    await bot.delete_webhook(drop_pending_updates=True) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
