import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from gradio_client import Client
from aiohttp import web

# ТОКЕН ВСТАВЛЯЕМ СЮДА (в кавычках)
TOKEN = "8275988872:AAH8dKL778aKWqs6-WBsussjXuxZP1NXPTA"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки с темами
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🧠 Психология", callback_data="theme_psy")
    kb.button(text="💰 Доход", callback_data="theme_money")
    kb.adjust(1)
    await message.answer("Выберите тему для создания видео:", reply_markup=kb.as_markup())

# Обработка нажатия кнопок
@dp.callback_query(F.data.startswith("theme_"))
async def theme_selected(callback: types.CallbackQuery):
    theme = "Психология" if callback.data == "theme_psy" else "Доход"
    await callback.answer()
    await callback.message.answer(f"Вы выбрали тему: {theme}. Готовлю видео...")

# Веб-сервер для Render (чтобы не засыпал)
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
