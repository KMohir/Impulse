import asyncio
import logging
import os
import subprocess
import uuid
from typing import Optional

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


def _run_ffmpeg_to_wav(src_path: str, dst_path: str) -> None:
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


def _post_to_stt(wav_path: str, filename_for_form: str) -> str:
    headers = {"x-api-key": config.MUXLISA_API_KEY}
    with open(wav_path, "rb") as f:
        files = [("audio", (filename_for_form, f, "audio/wav"))]
        resp = requests.post(config.MUXLISA_STT_URL, headers=headers, files=files, data={})
    try:
        js = resp.json()
        for key in ("text", "result", "transcript"):
            if key in js and isinstance(js[key], str):
                return js[key]
        return str(js)
    except Exception:
        return resp.text.strip() or ""


@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Отправьте голосовое или аудио-файл — верну текст.")


@dp.message(F.voice | F.audio)
async def handle_audio_message(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")

    file_id: Optional[str] = None
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id

    if not file_id:
        await message.answer("Не удалось получить файл. Попробуйте еще раз.")
        return

    try:
        tg_file = await bot.get_file(file_id)
        src_ext = os.path.splitext(tg_file.file_path or "")[1] or ".ogg"
        rnd = uuid.uuid4().hex
        src_path = os.path.join(PROJECT_ROOT, f"{rnd}{src_ext}")
        wav_name = f"{uuid.uuid4().hex}.wav"
        wav_path = os.path.join(PROJECT_ROOT, wav_name)

        # Скачиваем оригинал
        await bot.download_file(tg_file.file_path, destination=src_path)

        # Конвертируем в WAV 16кГц моно
        _run_ffmpeg_to_wav(src_path, wav_path)

        # Имя файла в multipart также случайное
        form_filename = f"{uuid.uuid4().hex}.wav"
        text_result = _post_to_stt(wav_path, form_filename)

        if not text_result:
            await message.answer("Пустой ответ распознавания. Попробуйте снова.")
        else:
            await message.answer(text_result)
    except Exception as e:
        logger.error(f"STT error: {e}")
        await message.answer("Произошла ошибка при обработке аудио. Убедитесь, что установлен ffmpeg.")
    finally:
        try:
            if 'src_path' in locals() and os.path.exists(src_path):
                os.remove(src_path)
        except Exception:
            pass
        try:
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception:
            pass


@dp.message()
async def default_message(message: Message):
    await message.answer("Отправьте голосовое сообщение или аудио-файл. Я конвертирую его в текст.")


async def main():
    logging.info("STT бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
