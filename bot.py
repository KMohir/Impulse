import asyncio
import logging
import os
from typing import List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FSM States
class UserStates(StatesGroup):
    # New states for questionnaire
    waiting_for_soha = State()
    waiting_for_auditoriya = State()
    waiting_for_maqsad = State()
    waiting_for_muammolar = State()
    waiting_for_tasir = State()
    waiting_for_tajriba = State()
    waiting_for_mavzular = State()
    waiting_for_unique = State()
    waiting_for_selection = State()

# Initialize bot with FSM storage
storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# OpenAI client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def _split_text_for_telegram(text: str, max_length: int = 4000) -> List[str]:
    """Разбивает длинный текст на части для отправки в Telegram (лимит ~4096 символов)"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по предложениям для лучшей читаемости
    sentences = text.split('. ')
    
    for sentence in sentences:
        if len(current_part) + len(sentence) + 2 <= max_length:
            if current_part:
                current_part += ". " + sentence
            else:
                current_part = sentence
        else:
            if current_part:
                parts.append(current_part + ".")
                current_part = sentence
            else:
                # Если одно предложение длиннее лимита, разбиваем по словам
                words = sentence.split()
                for word in words:
                    if len(current_part) + len(word) + 1 <= max_length:
                        if current_part:
                            current_part += " " + word
                        else:
                            current_part = word
                    else:
                        if current_part:
                            parts.append(current_part)
                            current_part = word
                        else:
                            parts.append(word)
    
    if current_part:
        parts.append(current_part)
    
    return parts


async def _send_to_chatgpt(user_prompt: str) -> str:
    """Отправляет текст в ChatGPT с заданным промптом"""
    messages = [
        {
            "role": "system", 
            "content": "Siz Instagram algoritmini chuqur tahlil qilgan, 100.000+ prosmotr olgan kontentlarni analiz qilgan kontent strateg mutaxassissiz."
        },
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"ChatGPT API xatoligi: {e}")
        return f"❌ ChatGPT bilan bog'lanishda xatolik: {str(e)}"


@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_for_soha)
    await message.answer(
        "👋 Assalomu alaykum! Men sizning shaxsiy kontent strategingizman.\n\n"
        "Keling, siz uchun millionlab ko'rishlar olib keladigan kontent rejasi tuzamiz.\n\n"
        "1️⃣ <b>Sohangiz nima?</b> (Masalan: SMM, Psixologiya, Ingliz tili...)"
    )


@dp.message(UserStates.waiting_for_soha)
async def process_soha(message: Message, state: FSMContext):
    await state.update_data(soha=message.text)
    await state.set_state(UserStates.waiting_for_auditoriya)
    await message.answer(
        "2️⃣ <b>Auditoriyangiz kim?</b>\n"
        "(Masalan: Tadbirkorlar, talabalar, yosh onalar...)"
    )


@dp.message(UserStates.waiting_for_auditoriya)
async def process_auditoriya(message: Message, state: FSMContext):
    await state.update_data(auditoriya=message.text)
    await state.set_state(UserStates.waiting_for_maqsad)
    await message.answer(
        "3️⃣ <b>Maqsadingiz nima?</b>\n"
        "(Masalan: Xizmat sotish, obunachi yig'ish, ekspertlikni oshirish...)"
    )


@dp.message(UserStates.waiting_for_maqsad)
async def process_maqsad(message: Message, state: FSMContext):
    await state.update_data(maqsad=message.text)
    await state.set_state(UserStates.waiting_for_muammolar)
    await message.answer(
        "4️⃣ <b>Siz hozirda sohangizda qanday muammolarni hal qilayapsiz?</b>"
    )


@dp.message(UserStates.waiting_for_muammolar)
async def process_muammolar(message: Message, state: FSMContext):
    await state.update_data(muammolar=message.text)
    await state.set_state(UserStates.waiting_for_tasir)
    await message.answer(
        "5️⃣ <b>Sohangiz odamlar hayotiga qanday ta’sir o’tkazayapti?</b>\n"
        "(Hayotini qaysi tomonlarini yaxshilanishiga sabab bo’lmoqda)"
    )


@dp.message(UserStates.waiting_for_tasir)
async def process_tasir(message: Message, state: FSMContext):
    await state.update_data(tasir=message.text)
    await state.set_state(UserStates.waiting_for_tajriba)
    await message.answer(
        "6️⃣ <b>Shaxsiy biror tajribangizni gapirib bersangiz sohangiz bo'yicha?</b>\n"
        "(Umumiy sohangiz bo'yicha keyslaringiz ulardan olgan xulosangiz)"
    )


@dp.message(UserStates.waiting_for_tajriba)
async def process_tajriba(message: Message, state: FSMContext):
    await state.update_data(tajriba=message.text)
    await state.set_state(UserStates.waiting_for_mavzular)
    await message.answer(
        "7️⃣ <b>Siz qanday mavzularda kontent chiqarishni hoxlayapsiz?</b>\n"
        "(Imkoni bo'lsa batafsil yozing)"
    )


@dp.message(UserStates.waiting_for_mavzular)
async def process_mavzular(message: Message, state: FSMContext):
    await state.update_data(mavzular=message.text)
    await state.set_state(UserStates.waiting_for_unique)
    await message.answer(
        "8️⃣ <b>Sizni boshqalardan nima ajratib turadi?</b>\n"
        "(Yani sohangizdagi kuchli tomoningiz)"
    )


@dp.message(UserStates.waiting_for_unique)
async def process_unique(message: Message, state: FSMContext):
    await state.update_data(unique=message.text)
    data = await state.get_data()
    
    soha = data.get('soha')
    auditoriya = data.get('auditoriya')
    maqsad = data.get('maqsad')
    muammolar = data.get('muammolar')
    tasir = data.get('tasir')
    tajriba = data.get('tajriba')
    mavzular = data.get('mavzular')
    unique = message.text

    await message.answer("⏳ <b>Tahlil qilyapman...</b>\nInstagram algoritmlarini o'rganib, eng trenddagi mavzularni tayyorlayapman.")
    await bot.send_chat_action(message.chat.id, "typing")

    prompt = (
        f"Soha: {soha}\n"
        f"Auditoriya: {auditoriya}\n"
        f"Maqsad: {maqsad}\n"
        f"Hal qilayotgan muammolar: {muammolar}\n"
        f"Ta'siri: {tasir}\n"
        f"Shaxsiy tajriba/Keyslar: {tajriba}\n"
        f"Istalgan mavzular: {mavzular}\n"
        f"O'ziga xoslik (USP): {unique}\n\n"
        "🎯 TOPSHIRIQ:\n"
        "Yuqoridagi barcha ma'lumotlardan kelib chiqib, Instagram Reels uchun 15 ta viral mavzu va HeyGen avatari gapirishi uchun tayyor matn (skript) yozing.\n\n"
        "Talablar:\n"
        "- Har bir ssenariy turlicha bo'lsin (turli formatlar va yondashuvlar).\n"
        "- Foydalanuvchining shaxsiy tajribasi va o'ziga xosligini inobatga oling.\n\n"
        "Javobingiz qat'iy quyidagi formatda bo'lsin (har bir mavzu uchun):\n\n"
        "🎥 Kontent {raqam}\n"
        "<b>Hook:</b> [Videoni boshlash uchun 3 soniyalik kuchli ilmoq/gap]\n"
        "<b>Kontent:</b> [Video nima haqida bo'lishi, vizual tavsif va g'oya]\n\n"
        "Barcha javoblar O'zbek tilida bo'lsin."
    )

    response_text = await _send_to_chatgpt(prompt)
    
    # Save the response for refinement
    await state.update_data(last_response=response_text)
    
    # Split and send response
    response_parts = _split_text_for_telegram(response_text)
    for i, part in enumerate(response_parts):
        try:
            await message.answer(part)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending part {i+1}: {e}")
            continue

    await state.set_state(UserStates.waiting_for_selection)
    await message.answer(
        "\n♻️ <b>Qaysi mavzular sizga yoqdi?</b>\n\n"
        "Yoqqan mavzular raqamini yozing (masalan: 1, 5, 10).\n"
        "Men ularni saqlab qolaman va qolganlarini yangisiga almashtirib beraman.\n\n"
        "Yoki yangi soha tanlash uchun /start ni bosing."
    )


@dp.message(UserStates.waiting_for_selection)
async def process_selection(message: Message, state: FSMContext):
    selected_numbers = message.text
    data = await state.get_data()
    
    # Retrieve context
    soha = data.get('soha')
    auditoriya = data.get('auditoriya')
    maqsad = data.get('maqsad')
    muammolar = data.get('muammolar')
    tasir = data.get('tasir')
    tajriba = data.get('tajriba')
    mavzular = data.get('mavzular')
    unique = data.get('unique')
    last_response = data.get('last_response')

    await message.answer("⏳ <b>Qayta ishlayapman...</b>\nTanlangan mavzularni saqlab, qolganlarini yangilayapman.")
    await bot.send_chat_action(message.chat.id, "typing")

    prompt = (
        f"Soha: {soha}\n"
        f"Auditoriya: {auditoriya}\n"
        f"Maqsad: {maqsad}\n"
        f"Hal qilayotgan muammolar: {muammolar}\n"
        f"Ta'siri: {tasir}\n"
        f"Shaxsiy tajriba/Keyslar: {tajriba}\n"
        f"Istalgan mavzular: {mavzular}\n"
        f"O'ziga xoslik (USP): {unique}\n\n"
        "--------------------------------------------------\n"
        f"OLDINGI GENERATSIYA:\n{last_response}\n"
        "--------------------------------------------------\n"
        f"FOYDALANUVCHI TANLAGAN RAQAMLAR: {selected_numbers}\n\n"
        "🎯 TOPSHIRIQ:\n"
        "1. Foydalanuvchi tanlagan raqamdagi mavzularni (Hook va Kontent) XUDDI O'ZIDEK saqlab qoling.\n"
        "2. Tanlanmagan mavzular o'rniga YANGI, viral va qiziqarli g'oyalar yozing.\n"
        "3. Jami yana 15 ta kontent bo'lishi kerak.\n\n"
        "Javobingiz qat'iy quyidagi formatda bo'lsin (har bir mavzu uchun):\n\n"
        "🎥 Kontent {raqam}\n"
        "<b>Hook:</b> [Videoni boshlash uchun 3 soniyalik kuchli ilmoq/gap]\n"
        "<b>Kontent:</b> [Video nima haqida bo'lishi, vizual tavsif va g'oya]\n\n"
        "Barcha javoblar O'zbek tilida bo'lsin."
    )

    response_text = await _send_to_chatgpt(prompt)
    
    # Update last response
    await state.update_data(last_response=response_text)

    # Split and send response
    response_parts = _split_text_for_telegram(response_text)
    for i, part in enumerate(response_parts):
        try:
            await message.answer(part)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending part {i+1}: {e}")
            continue
            
    await message.answer(
        "\n♻️ <b>Yana o'zgartiramizmi?</b>\n"
        "Yoqqanlarini raqamini yozing (masalan: 1, 2, 3) yoki yangi soha uchun /start ni bosing."
    )


@dp.message()
async def default_message(message: Message, state: FSMContext):
    await message.answer(
        "Iltimos, /start buyrug'ini bosing va so'rovnomani to'ldiring."
    )


async def main():
    logging.info("Bot ishga tushmoqda...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
