import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from typing import List, Optional

import requests

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

import config
import time
import random
import string
import re
from heygen_bot_integration import router as heygen_router
from heygen_video import HeyGenVideoCreator

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
    waiting_for_selection = State()
    waiting_for_scenario_number = State()
    waiting_for_audio = State()
    waiting_for_avatar = State()

# Initialize bot with FSM storage
storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
dp.include_router(heygen_router)

# OpenAI client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIO_STORAGE_DIR = os.path.join(PROJECT_ROOT, "audio_storage")  # Папка для постоянного хранения
CHUNK_DURATION = 48  # секунд
MAX_FILE_SIZE_MB = 20  # Telegram API limit for getFile

# Создаем папку для хранения аудио и текстов при запуске
os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)


def _get_audio_duration(file_path: str) -> float:
    """Получает длительность аудио файла в секундах"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error: {result.stderr}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Не удалось определить длительность: {result.stdout}")


def _run_ffmpeg_to_wav(src_path: str, dst_path: str) -> None:
    """Конвертирует аудио в WAV формат (16кГц, моно)"""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", src_path,
        "-ac", "1",
        "-ar", "16000",
        dst_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode(errors='ignore')}")


def _split_audio_to_chunks(wav_path: str, temp_dir: str) -> List[str]:
    """Разрезает аудио на куски по 48 секунд. Возвращает список путей к кускам"""
    duration = _get_audio_duration(wav_path)
    chunk_paths = []
    
    if duration <= CHUNK_DURATION:
        # Аудио короче 48 секунд - возвращаем как есть
        chunk_path = os.path.join(temp_dir, "chunk_0.wav")
        shutil.copy2(wav_path, chunk_path)
        chunk_paths.append(chunk_path)
        return chunk_paths
    
    # Разрезаем на куски по 48 секунд
    chunk_index = 0
    start_time = 0.0
    
    while start_time < duration:
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}.wav")
        chunk_duration = min(CHUNK_DURATION, duration - start_time)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", wav_path,
            "-ss", str(start_time),
            "-t", str(chunk_duration),
            "-ac", "1",
            "-ar", "16000",
            chunk_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg split error: {result.stderr.decode(errors='ignore')}")
        
        chunk_paths.append(chunk_path)
        chunk_index += 1
        start_time += CHUNK_DURATION
    
    return chunk_paths


def _post_to_stt(wav_path: str, filename_for_form: str) -> str:
    """Отправляет аудио файл в STT API и возвращает распознанный текст"""
    headers = {"x-api-key": config.MUXLISA_API_KEY}
    try:
        with open(wav_path, "rb") as f:
            files = [("audio", (filename_for_form, f, "audio/wav"))]
            # Таймаут: 30 секунд на подключение, 120 секунд на чтение
            resp = requests.post(
                config.MUXLISA_STT_URL,
                headers=headers,
                files=files,
                data={},
                timeout=(30, 120)
            )
        resp.raise_for_status()
        try:
            js = resp.json()
            for key in ("text", "result", "transcript"):
                if key in js and isinstance(js[key], str):
                    return js[key]
            return str(js)
        except Exception:
            return resp.text.strip() or ""
    except requests.exceptions.Timeout:
        logger.error(f"Timeout при запросе к STT для файла {filename_for_form}")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к STT: {e}")
        return ""


def _split_text_by_scenarios(text: str, max_length: int = 4000) -> List[str]:
    """
    Splits text by '🎥 Kontent' delimiter to keep scenarios intact.
    """
    # Split by the scenario marker, keeping the delimiter
    parts = re.split(r'(?=🎥 Kontent \d)', text)
    
    # Remove empty strings
    parts = [p for p in parts if p.strip()]
    
    final_chunks = []
    current_chunk = ""
    
    for part in parts:
        if len(current_chunk) + len(part) <= max_length:
            current_chunk += part
        else:
            if current_chunk:
                final_chunks.append(current_chunk)
            current_chunk = part
            
    if current_chunk:
        final_chunks.append(current_chunk)
        
    # If regex didn't find anything (e.g. error message), fallback to simple split
    if not final_chunks:
        return _split_text_for_telegram(text, max_length)
        
    return final_chunks


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
            if current_chunk := current_part: # Fixed variable name bug in original code if copied
                parts.append(current_chunk + ".")
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


def _extract_scenario(text: str, number: int) -> Optional[str]:
    """Extracts the content of a specific scenario number."""
    pattern = rf"(🎥 Kontent {number}\s*.*?)(?=\n🎥 Kontent \d|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


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
        "Yuqoridagi barcha ma'lumotlardan kelib chiqib, Instagram Reels uchun ROPPA-ROSA 15 TA (kam ham emas, ko'p ham emas) viral mavzu va HeyGen avatari gapirishi uchun tayyor matn (skript) yozing.\n\n"
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
    response_parts = _split_text_by_scenarios(response_text)
    for i, part in enumerate(response_parts):
        try:
            await message.answer(part)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending part {i+1}: {e}")
            continue

    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Hammasi yoqdi", callback_data="finish_generation")]
    ])

    await state.set_state(UserStates.waiting_for_selection)
    await message.answer(
        "\n♻️ <b>Qaysi mavzular sizga yoqdi?</b>\n\n"
        "Agar biror mavzu yoqqan bo'lsa va uni yozib bermoqchi bo'lsangiz, quyidagi tugmani bosing:\n"
        "👇 <b>Hammasi yoqdi</b>\n\n"
        "Yoki o'zgartirmoqchi bo'lgan mavzular raqamini yozing (masalan: 1, 5, 10).\n"
        "Men ularni saqlab qolaman va qolganlarini yangisiga almashtirib beraman.\n\n"
        "Yoki yangi soha tanlash uchun /start ni bosing.",
        reply_markup=keyboard
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
        "3. Jami yana ROPPA-ROSA 15 TA kontent bo'lishi kerak (eski saqlanganlar + yangilar = 15 ta).\n\n"
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
    response_parts = _split_text_by_scenarios(response_text)
    for i, part in enumerate(response_parts):
        try:
            await message.answer(part)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending part {i+1}: {e}")
            continue
            
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Hammasi yoqdi", callback_data="finish_generation")]
    ])

    await message.answer(
        "\n♻️ <b>Yana o'zgartiramizmi?</b>\n"
        "Yoqqanlarini raqamini yozing (masalan: 1, 2, 3) yoki yangi soha uchun /start ni bosing."
    )


@dp.message(F.voice | F.audio)
async def handle_audio_message(message: Message, state: FSMContext):
    await bot.send_chat_action(message.chat.id, "typing")

    file_id: Optional[str] = None
    file_size: Optional[int] = None
    
    if message.voice:
        file_id = message.voice.file_id
        file_size = message.voice.file_size
    elif message.audio:
        file_id = message.audio.file_id
        file_size = message.audio.file_size

    if not file_id:
        await message.answer("Faylni olishning imkoni bo'lmadi. Iltimos, yana urinib ko'ring.")
        return

    # Check file size before attempting to download
    if file_size:
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            await message.answer(
                f"❌ Audio fayl juda katta ({file_size_mb:.1f} MB).\n"
                f"Telegram API cheklovi: {MAX_FILE_SIZE_MB} MB.\n"
                f"Iltimos, qisqaroq yoki kichikroq fayl yuboring."
            )
            logger.warning(f"File too large: {file_size_mb:.1f} MB (limit: {MAX_FILE_SIZE_MB} MB)")
            return

    # Создаем временную папку для этого аудио
    temp_dir = None
    src_path = None
    
    try:
        tg_file = await bot.get_file(file_id)
        src_ext = os.path.splitext(tg_file.file_path or "")[1] or ".ogg"
        rnd = uuid.uuid4().hex
        
        # Создаем уникальную папку для каждого аудио в постоянном хранилище
        temp_dir = os.path.join(AUDIO_STORAGE_DIR, f"audio_{rnd}")
        os.makedirs(temp_dir, exist_ok=True)
        
        src_path = os.path.join(temp_dir, f"original{src_ext}")
        wav_path = os.path.join(temp_dir, "full.wav")

        # Скачиваем оригинал
        await bot.download_file(tg_file.file_path, destination=src_path)

        # Конвертируем в WAV 16кГц моно
        _run_ffmpeg_to_wav(src_path, wav_path)

        # Разрезаем на куски по 48 секунд (если нужно)
        chunk_paths = _split_audio_to_chunks(wav_path, temp_dir)
        
        # Обрабатываем каждый кусок через STT
        all_texts = []
        for i, chunk_path in enumerate(chunk_paths):
            try:
                form_filename = f"{uuid.uuid4().hex}.wav"
                text_result = _post_to_stt(chunk_path, form_filename)
                if text_result and text_result.strip():
                    all_texts.append(text_result.strip())
                    logger.info(f"Chunk {i+1}/{len(chunk_paths)} processed: {len(text_result)} chars")
                else:
                    logger.warning(f"Chunk {i+1}/{len(chunk_paths)} вернул пустой результат")
            except Exception as chunk_error:
                logger.error(f"Ошибка при обработке куска {i+1}/{len(chunk_paths)}: {chunk_error}")
                # Продолжаем обработку следующих кусков
                continue

        # Объединяем все тексты
        combined_text = " ".join(all_texts)
        
        if not combined_text:
            await message.answer("Tanish natijasi bo'sh. Yana urinib ko'ring.")
        else:
            # Сохраняем распознанный текст в файл
            text_file_path = os.path.join(temp_dir, "stt_text.txt")
            try:
                with open(text_file_path, "w", encoding="utf-8") as text_file:
                    text_file.write(combined_text)
                logger.info(f"STT текст сохранен в: {text_file_path}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении текста: {e}")
            
            # Отправляем распознанный текст пользователю
            await message.answer("📝 Tanish natijalari:\n" + "="*30)
            text_parts = _split_text_for_telegram(combined_text)
            for i, part in enumerate(text_parts):
                try:
                    if i == 0:
                        await message.answer(part)
                    else:
                        await message.answer(f"[{i+1}/{len(text_parts)}] {part}")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при отправке части текста {i+1}: {e}")
                    continue
            
            # Отправляем в ChatGPT с промптом
            await message.answer("\n🤖 ChatGPT bilan kontent plan tayyorlanmoqda...")
            await bot.send_chat_action(message.chat.id, "typing")
            
            prompt = (
                f"Mijozning audio xabari matni: {combined_text}\n\n"
                "🎯 TOPSHIRIQ:\n"
                "Yuqoridagi audio matnidan kelib chiqib, Instagram Reels uchun 15 ta viral mavzu yozing.\n\n"
                "Javobingiz qat'iy quyidagi formatda bo'lsin (har bir mavzu uchun):\n\n"
                "🎥 Kontent {raqam}\n"
                "<b>Hook:</b> [Videoni boshlash uchun 3 soniyalik kuchli ilmoq/gap]\n"
                "<b>Kontent:</b> [Video nima haqida bo'lishi, vizual tavsif va g'oya]\n\n"
                "Barcha javoblar O'zbek tilida bo'lsin."
            )
            
            response_text = await _send_to_chatgpt(prompt)
            
            # Save for refinement
            await state.update_data(last_response=response_text)
            
            # Split and send response
            response_parts = _split_text_for_telegram(response_text)
            for i, part in enumerate(response_parts):
                try:
                    await message.answer(part)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при отправке ответа ChatGPT {i+1}: {e}")
                    continue
            
            await state.set_state(UserStates.waiting_for_selection)
            await message.answer(
                "\n♻️ <b>Qaysi mavzular sizga yoqdi?</b>\n\n"
                "Yoqqan mavzular raqamini yozing (masalan: 1, 5, 10).\n"
                "Men ularni saqlab qolaman va qolganlarini yangisiga almashtirib beraman.\n\n"
                "Yoki yangi soha tanlash uchun /start ni bosing."
            )
            
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        await message.answer("Audio qayta ishlashda xatolik yuz berdi.")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            logger.info(f"Аудио и текст сохранены в: {temp_dir}")



@dp.callback_query(F.data == "finish_generation", UserStates.waiting_for_selection)
async def process_finish_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Qaysi ssenariyni yozmoqchisiz? Raqamini yozing (masalan: 1).")
    await state.set_state(UserStates.waiting_for_scenario_number)
    await callback.answer()


@dp.message(UserStates.waiting_for_scenario_number)
async def process_scenario_number(message: Message, state: FSMContext):
    try:
        selection = int(message.text)
        await state.update_data(selected_scenario=selection)
        
        # Extract scenario text
        data = await state.get_data()
        last_response = data.get('last_response', '')
        scenario_text = _extract_scenario(last_response, selection)
        
        msg_text = f"✅ {selection}-mavzu tanlandi.\n\n"
        if scenario_text:
            msg_text += f"{scenario_text}\n\n"
        
        msg_text += "Endi ushbu mavzu uchun audio yozib yuboring (ovozli xabar yoki audio fayl)."
        
        await state.set_state(UserStates.waiting_for_audio)
        
        await message.answer(msg_text)
    except ValueError:
        await message.answer("Iltimos, faqat raqam yozing. Masalan: 1")


@dp.message(UserStates.waiting_for_audio, F.voice | F.audio)
async def process_audio(message: Message, state: FSMContext):
    user_id = message.from_user.id
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    # Determine file extension and file id
    if message.voice:
        file_id = message.voice.file_id
        file_ext = "ogg"
    else:
        file_id = message.audio.file_id
        file_ext = "mp3"  # Default to mp3 for audio files, or extract from file_name if needed
        if message.audio.file_name:
            ext = message.audio.file_name.split('.')[-1]
            if ext:
                file_ext = ext

    filename = f"{user_id}_{timestamp}_{random_suffix}.{file_ext}"
    
    # Ensure storage directory exists
    os.makedirs("audio_storage", exist_ok=True)
    file_path = os.path.join("audio_storage", filename)
    
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)
        
        # Save audio file path in state
        await state.update_data(audio_file_path=file_path)
        
        await message.answer(
            f"✅ Audio qabul qilindi va saqlandi!\n"
            f"Fayl nomi: {filename}\n\n"
            "⏳ Avatarlar yuklanmoqda..."
        )
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Fetch avatars from HeyGen
        heygen_api_key = config.HEYGEN_API_KEY
        
        if not heygen_api_key:
            await message.answer("❌ HeyGen API kaliti topilmadi! Iltimos, admin bilan bog'laning.")
            await state.set_state(UserStates.waiting_for_scenario_number)
            return
        
        creator = HeyGenVideoCreator(heygen_api_key)
        avatars = creator.get_avatars()
        
        if not avatars:
            await message.answer("❌ Avatarlarni yuklashda xatolik. Iltimos, qaytadan urinib ko'ring.")
            await state.set_state(UserStates.waiting_for_scenario_number)
            return
        
        # Filter avatars with valid names and limit to first 50
        valid_avatars = [av for av in avatars if av.get('name')][:50]
        
        if not valid_avatars:
            await message.answer("❌ Hech qanday avatar topilmadi.")
            await state.set_state(UserStates.waiting_for_scenario_number)
            return
        
        # Create avatar mapping
        avatar_map = {}
        keyboard_buttons = []
        
        for av in valid_avatars:
            name = av.get('name', 'Unknown')
            avatar_id = av.get('avatar_id')
            avatar_map[name] = avatar_id
            keyboard_buttons.append([KeyboardButton(text=name)])
        
        # Store avatar map in state
        await state.update_data(avatar_map=avatar_map)
        
        # Create keyboard
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
        
        await message.answer(
            "👤 Avatarni tanlang:",
            reply_markup=keyboard
        )
        await state.set_state(UserStates.waiting_for_avatar)
        
    except Exception as e:
        logger.error(f"Error saving audio: {e}")
        await message.answer("❌ Audio saqlashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@dp.message(UserStates.waiting_for_avatar)
async def process_avatar_selection(message: Message, state: FSMContext):
    """Handle avatar selection after audio upload"""
    data = await state.get_data()
    avatar_map = data.get('avatar_map', {})
    
    selected_name = message.text
    avatar_id = avatar_map.get(selected_name)
    
    if not avatar_id:
        await message.answer("❌ Iltimos, ro'yxatdan avatarni tanlang.")
        return
    
    # Save selected avatar
    await state.update_data(selected_avatar_id=avatar_id, selected_avatar_name=selected_name)
    
    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        f"✅ Avatar tanlandi: {selected_name}\n\n"
        "Video yaratish uchun barcha ma'lumotlar tayyor!\n"
        "Yana boshqa mavzu tanlash uchun raqamini yozing yoki "
        "yangi soha uchun /start ni bosing.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Return to scenario selection
    await state.set_state(UserStates.waiting_for_scenario_number)


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
