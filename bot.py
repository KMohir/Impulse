import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from typing import List, Optional

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

PROJECT_ROOT = "/home/mohirbek/Projects/Impulse"
CHUNK_DURATION = 48  # секунд


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


@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Ovozli xabar yoki audio fayl yuboring — men matnni qaytaraman.")


@dp.message(F.voice | F.audio)
async def handle_audio_message(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")

    file_id: Optional[str] = None
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id

    if not file_id:
        await message.answer("Faylni olishning imkoni bo‘lmadi. Iltimos, yana urinib ko‘ring.")
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
            await message.answer("Tanish natijasi bo‘sh. Yana urinib ko‘ring.")
        else:
            # Разбиваем длинный текст на части и отправляем отдельными сообщениями
            text_parts = _split_text_for_telegram(combined_text)
            for i, part in enumerate(text_parts):
                try:
                    if i == 0:
                        await message.answer(part)
                    else:
                        # Добавляем заголовок для продолжения
                        await message.answer(f"[{i+1}/{len(text_parts)}] {part}")
                    # Небольшая задержка между сообщениями, чтобы избежать rate limit
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при отправке части текста {i+1}: {e}")
                    # Пробуем отправить следующую часть
                    continue
            
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        try:
            await message.answer("Audio qayta ishlashda xatolik yuz berdi. Tizimda ffmpeg va ffprobe o‘rnatilganini tekshiring.")
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
async def default_message(message: Message):
    await message.answer("Ovozli xabar yoki audio fayl yuboring. Men uni matnga aylantirib beraman.")


async def main():
    logging.info("STT бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
