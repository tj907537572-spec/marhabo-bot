import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from gradio_client import Client
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 

THEMES = {
    "PSYCHO": {
        "channel": "@tvoia_opora",
        "style": "cinematic film look, shot on 35mm, realistic, calm nature, soft sunlight, highly detailed, 4k, vertical 9:16",
        "name": "Психология",
        "caption": "🌿 Твое мгновение тишины...\n\n#психология #осознанность"
    },
    "MONEY": {
        "channel": "@vash_money_kanal",
        "style": "luxury, futuristic, business, success, golden accents, high-tech, 8k, vertical 9:16",
        "name": "Доход",
        "caption": "💰 Масштабируй свой успех.\n\n#бизнес #доход"
    }
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ РАЗБОРКИ (АНТИ-СОН) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

# --- ЛОГИКА БОТА ---
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🧠 Создать для Психологии")],
    [KeyboardButton(text="💰 Создать для Дохода")]
], resize_keyboard=True)

user_choice = {}

@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer("👋 Привет! Выбери тему для видео:", reply_markup=main_menu)

@dp.message(F.text.in_(["🧠 Создать для Психологии", "💰 Создать для Дохода"]))
async def choose_theme(message: types.Message):
    choice = "PSYCHO" if "Психология" in message.text else "MONEY"
    user_choice[message.from_user.id] = choice
    await message.answer(f"Тема {THEMES[choice]['name']} выбрана. Опиши сюжет видео:")

@dp.message(F.text)
async def handle_prompt(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_choice:
        return

    theme_data = THEMES[user_choice[user_id]]
    status = await message.answer("⏳ ИИ генерирует видео... Пожалуйста, подождите минуту.")

    try:
        client = Client("genmo/mochi-1-preview")
        result = client.predict(
            prompt=f"{message.text}, {theme_data['style']}",
            negative_prompt="horizontal, blur, low quality",
            api_name="/generate-video"
        )

        video = FSInputFile(result)
        await bot.send_video(chat_id=theme_data['channel'], video=video, caption=theme_data['caption'])
        await status.edit_text(f"✅ Готово! Опубликовано в {theme_data['channel']}")
        
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")

async def main():
    # Запускаем сервер и бота одновременно
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

