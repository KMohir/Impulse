import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from typing import List, Optional

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
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
    waiting_for_audio = State()
    processing_audio = State()
    waiting_for_chatgpt = State()

# Initialize bot with FSM storage
storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=storage)

# OpenAI client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

PROJECT_ROOT = "/app"
CHUNK_DURATION = 48  # секунд
MAX_FILE_SIZE_MB = 20  # Telegram API limit for getFile


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


async def _send_to_chatgpt(stt_text: str, user_prompt: str) -> str:
    """Отправляет STT текст в ChatGPT с заданным промптом"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Sen tajribali brend-strateg, professional ssenarist va motivatsion kontent prodyusersan. "
                               "O'zbek tilida ajoyib video skriptlar yozasan. Har doim aniq strukturaga rioya qilasan va "
                               "mijoz talablarini to'liq bajarasan. Faqat so'ralgan formatda javob berasan."
                },
                {"role": "user", "content": f"{user_prompt}\n\nMana mijoz matni (audio dan olingan):\n\n{stt_text}"}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"ChatGPT API xatoligi: {e}")
        return f"❌ ChatGPT bilan bog'lanishda xatolik: {str(e)}"


@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_audio)
    await message.answer(
        "👋 Ovozli xabar yoki audio fayl yuboring — men:\n"
        "1. Matnni qaytaraman\n"
        "2. ChatGPT yordamida kontent plan tayyorlayman\n"
        "3. HeyGen uchun tayyor skript formatida 15 ta video skriptini taqdim etaman"
    )


@dp.message(F.voice | F.audio)
async def handle_audio_message(message: Message, state: FSMContext):
    await state.set_state(UserStates.processing_audio)
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
        
        # Создаем уникальную временную папку для каждого аудио
        temp_dir = os.path.join(PROJECT_ROOT, f"temp_audio_{rnd}")
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
            await state.set_state(UserStates.waiting_for_audio)
        else:
            # Сохраняем текст в FSM
            await state.update_data(stt_text=combined_text)
            await state.set_state(UserStates.waiting_for_chatgpt)
            
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
            
            user_prompt = (
                "Sen — tajribali brend-strateg, ssenarist va motivatsion kontent prodyusersan. "
                "Yuqoridagi mijozning matni asosida 15 ta qisqa motivatsion video skript tayyorla. "
                "Har bir skript quyidagi qat'iy tuzilma bo'yicha bo'lsin va aniq ajratib yozilsin:\n\n"
                "Sarlavha: (motivatsion, esda qoladigan nom — 3–6 so'z)\n"
                "🎯 Hook: (birinchi 3 soniyada e'tibor tortadigan 1–2 jumla; kuchli boshlanish)\n"
                "💡 Kontent g'oyasi: (video nimani o'rgatadi yoki qanday hissiyot uyg'otadi — 1–2 jumla)\n"
                "🗣 Skript (100–120 so'z): (samimiy \"sen\" murojaatida, motivatsion va tabiiy ovozda; "
                "kamera qarshisida aytilishga mos; har bir skript 100–120 so'z orasida bo'lsin)\n\n"
                "Qo'shimcha talablar:\n"
                "- Til: o'zbekcha (lotin alifbosida)\n"
                "- Ohang: motivatsion, ishonchli, tabiiy (sun'iy \"trainer\" ohangsiz)\n"
                "- Format: javobda faqat 15 ta blok bo'lsin — hech qanday qo'shimcha izoh yoki tushuntirishsiz\n"
                "- Har bir skript lichniy brend videoga mos (Reels / TikTok / Shorts: 40–60 soniya)\n"
                "- Har bir hook qisqa, aniq va darhol e'tiborni tortadigan bo'lsin"
            )
            
            chatgpt_response = await _send_to_chatgpt(combined_text, user_prompt)
            
            # Отправляем ответ ChatGPT
            await message.answer("\n" + "="*30 + "\n📋 KONTENT PLAN - HEYGEN SKRIPTLAR\n" + "="*30)
            response_parts = _split_text_for_telegram(chatgpt_response)
            for i, part in enumerate(response_parts):
                try:
                    await message.answer(part)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при отправке ответа ChatGPT {i+1}: {e}")
                    continue
            
            await state.set_state(UserStates.waiting_for_audio)
            await message.answer("\n✅ Tayyor! Yangi audio yuboring yoki /start bosing.")
            
    except TelegramBadRequest as e:
        if "file is too big" in str(e):
            logger.error(f"STT error: {e}")
            try:
                await message.answer(
                    f"❌ Audio fayl juda katta.\n"
                    f"Telegram API cheklovi: {MAX_FILE_SIZE_MB} MB.\n"
                    f"Iltimos, qisqaroq yoki kichikroq fayl yuboring."
                )
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {send_error}")
        else:
            logger.error(f"Telegram API error: {e}", exc_info=True)
            try:
                await message.answer("Telegram API xatoligi yuz berdi. Iltimos, yana urinib ko'ring.")
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {send_error}")
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        try:
            await message.answer("Audio qayta ishlashda xatolik yuz berdi. Tizimda ffmpeg va ffprobe o'rnatilganini tekshiring.")
        except Exception as send_error:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {send_error}")
    finally:
        # Удаляем временную папку и все файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Удалена временная папка: {temp_dir}")
            except Exception as e:
                logger.error(f"Ошибка при удалении папки {temp_dir}: {e}")


@dp.message()
async def default_message(message: Message, state: FSMContext):
    await message.answer(
        "Ovozli xabar yoki audio fayl yuboring. Men uni matnga aylantirib, "
        "ChatGPT yordamida kontent plan tayyorlayman."
    )


async def main():
    logging.info("STT бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
