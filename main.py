import asyncio
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- 1. ТАНЗИМОТИ ВЕБ-СЕРВЕР (БАРОИ ОН КИ БОТ ХОБ НАРАВАД) ---
app = Flask('')

@app.route('/')
def home():
    return "Ман зиндаам ва 24/7 кор мекунам!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. МАЪЛУМОТИ АСОСИИ БОТ ---
TOKEN = "8275988872:AAGsVaY4FqTaGCyIbhO5jiX-EsHfs4_kA1s"
ADMIN_ID = 6341390660  # ID-и шумо
GROUP_ID = -1002446755497  # Ин ҷо ID-и гурӯҳи Марҳаборо гузоред
CARD_NUMBER = "9999 9999 9999 9999"  # Картаи Марҳабо Ҳасанова

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатураи асосӣ
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Харидани курс", callback_data="buy")],
        [InlineKeyboardButton(text="👩🏻‍🏫 Дар бораи муаллиф", callback_data="about")],
        [InlineKeyboardButton(text="🆘 Дастгирӣ", callback_data="support")]
    ])

# Фармони /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        f"Ассалому алайкум, {message.from_user.first_name}! ✨\n\n"
        "Хуш омадед ба боти расмии Марҳабо Ҳасанова. "
        "Дар ин ҷо шумо метавонед курсҳои психологиро харидорӣ кунед.",
        reply_markup=main_kb()
    )

# Қисми харид
@dp.callback_query(F.data == "buy")
async def buy(call: types.CallbackQuery):
    await call.message.answer(
        f"💳 Барои харидани курс маблағро ба ин карта гузаронед:\n\n"
        f"`{CARD_NUMBER}`\n\n"
        "Пас аз пардохт, **РАСМИ ЧЕК-РО** (скриншот) ба ҳамин ҷо фиристед. 👇"
    )
    await call.answer()

# Қабули чек ва огоҳинома ба шумо (Админ)
@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ТАСДИҚ (Ссылка фиристодан)", callback_data=f"confirm_{message.from_user.id}")]
    ])
    
    # Ба шумо хабар меояд
    await bot.send_photo(
        ADMIN_ID, 
        photo=message.photo[-1].file_id, 
        caption=f"💰 **ЧЕКИ НАВ ОМАД!**\n👤 Муштарӣ: @{message.from_user.username or 'бе ном'}\n🆔 ID: {message.from_user.id}",
        reply_markup=admin_kb
    )
    
    # Ба муштарӣ ҷавоб меравад
    await message.answer("Раҳмат! Чеки шумо қабул шуд. Администратор онро месанҷад ва ба шумо истиноди чатро мефиристад. ⏳")

# Тасдиқи пардохт ва фиристодани ссылкаи автоматикӣ
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm(call: types.CallbackQuery):
    user_id = int(call.data.split("_")[1])
    
    try:
        # Сохтани ссылкаи яквақтаина барои гурӯҳ
        invite = await bot.create_chat_invite_link(chat_id=GROUP_ID, member_limit=1)
        
        await bot.send_message(
            user_id, 
            f"✅ Пардохти шумо тасдиқ шуд!\n\nИнак истиноди шумо барои дохил шудан ба чати пӯшида:\n{invite.invite_link}"
        )
        await call.message.edit_caption(caption="✅ ТАСДИҚ ШУД ВА ССЫЛКА ФИРИСТОДА ШУД!")
    
    except Exception as e:
        await call.message.answer(f"Хатогӣ ҳангоми сохтани ссылка: {e}\n(Шояд бот дар гурӯҳ админ нест?)")

# --- 3. БА КОР ДАРОВАРДАНИ БОТ ---
async def main():
    keep_alive() # Веб-серверро бедор мекунад
    print("Бот ба кор даромад...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот боздошт шуд.")
