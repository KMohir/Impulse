import logging
import os
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from heygen_video import HeyGenVideoCreator

# Initialize router
router = Router()
logger = logging.getLogger(__name__)

# States
class VideoCreationStates(StatesGroup):
    script = State()
    avatar = State()
    voice = State()

# Constants
UZ = True  # Assuming Uzbek based on bot.py context, or we can make it dynamic if needed. 
# For now, I'll keep the logic from the snippet but clean it up.

@router.message(Command("createvideo"))
async def cmd_create_video(message: Message, state: FSMContext):
    """Начало создания видео с аватаром"""
    text = (
        "🎬 Keling, avatar bilan video yaratamiz!\n\n"
        "📝 Video uchun matnni yuboring (skript):"
        if UZ else
        "🎬 Давайте создадим видео с аватаром!\n\n"
        "📝 Отправьте текст для видео (скрипт):"
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await state.set_state(VideoCreationStates.script)


@router.message(VideoCreationStates.script)
async def process_video_script(message: Message, state: FSMContext):
    """Обработка скрипта для видео и получение списка аватаров"""
    await state.update_data(script=message.text)
    
    await message.answer("⏳ Avatarlar yuklanmoqda..." if UZ else "⏳ Загрузка аватаров...")
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Fetch avatars
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        await message.answer("❌ API key not found")
        return

    creator = HeyGenVideoCreator(api_key)
    avatars = creator.get_avatars()
    
    if not avatars:
        await message.answer("❌ Avatarlarni yuklashda xatolik" if UZ else "❌ Ошибка загрузки аватаров")
        return

    # Store avatars in state to use later
    # We'll store a simplified list or dict
    # avatars is a list of dicts
    
    # Filter or just take top N? Or show all?
    # Let's show first 10-15 or use pagination if needed. 
    # For now, let's just list names.
    
    # Create buttons
    keyboard_builder = []
    
    # Save mapping of Name -> ID in state
    avatar_map = {}
    
    for av in avatars:
        name = av.get('name', 'Unknown')
        aid = av.get('avatar_id')
        preview = av.get('preview_image_url') # Optional: could send preview
        
        # Make name unique if needed, but usually names are distinct enough or we use ID
        # Let's use Name in button
        avatar_map[name] = aid
        keyboard_builder.append([KeyboardButton(text=name)])
        
    await state.update_data(avatar_map=avatar_map)
    
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_builder, resize_keyboard=True)
    
    text = (
        "👤 Avatarni tanlang:"
        if UZ else
        "👤 Выберите аватар:"
    )
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(VideoCreationStates.avatar)


@router.message(VideoCreationStates.avatar)
async def process_video_avatar(message: Message, state: FSMContext):
    """Обработка выбора аватара"""
    data = await state.get_data()
    avatar_map = data.get('avatar_map', {})
    
    selected_name = message.text
    avatar_id = avatar_map.get(selected_name)
    
    if not avatar_id:
        # Try fuzzy match or just error
        # Let's try to find if user typed something close or just error
        await message.answer("❌ Iltimos, ro'yxatdan tanlang" if UZ else "❌ Пожалуйста, выберите из списка")
        return
    
    await state.update_data(avatar_id=avatar_id)
    
    # Voice selection
    # For now hardcoded voices as in original snippet, or we could fetch voices too.
    # User request specifically mentioned "user must select avatar".
    # I'll keep voices static for now to minimize scope creep, unless requested.
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎤 Ayol ovozi (ingliz)")],
            [KeyboardButton(text="🎤 Erkak ovozi (ingliz)")],
            [KeyboardButton(text="🎤 Rus tili ovozi")],
            [KeyboardButton(text="🎤 O'zbek tili ovozi")]
        ] if UZ else [
            [KeyboardButton(text="🎤 Женский голос (англ)")],
            [KeyboardButton(text="🎤 Мужской голос (англ)")],
            [KeyboardButton(text="🎤 Русский голос")],
            [KeyboardButton(text="🎤 Узбекский голос")]
        ],
        resize_keyboard=True
    )
    
    text = (
        "🎙️ Ovozni tanlang:"
        if UZ else
        "🎙️ Выберите голос:"
    )
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(VideoCreationStates.voice)


@router.message(VideoCreationStates.voice)
async def process_video_voice(message: Message, state: FSMContext):
    """Обработка выбора голоса и создание видео"""
    
    # Карта голосов (замените на реальные ID из HeyGen)
    voice_map = {
        "женский": "1bd001e7e50f421d891986aad5158bc8",
        "мужской": "2d5b0e6c4f3a4b8c9d1e2f3a4b5c6d7e",
        "русский": "3e6c1f7d5a4b3c2d1e0f9a8b7c6d5e4f",
        "узбекский": "4f7d2e8c6b5a4d3c2e1f0a9b8c7d6e5f",
        "ayol": "1bd001e7e50f421d891986aad5158bc8",
        "erkak": "2d5b0e6c4f3a4b8c9d1e2f3a4b5c6d7e",
        "rus": "3e6c1f7d5a4b3c2d1e0f9a8b7c6d5e4f",
        "o'zbek": "4f7d2e8c6b5a4d3c2e1f0a9b8c7d6e5f"
    }
    
    voice_id = "1bd001e7e50f421d891986aad5158bc8"  # Default
    text_lower = message.text.lower()
    
    for key, vid in voice_map.items():
        if key in text_lower:
            voice_id = vid
            break
    
    await state.update_data(voice_id=voice_id)
    
    # Получаем все данные
    data = await state.get_data()
    
    text = (
        "⏳ Video yaratilmoqda...\n"
        "Bu bir necha daqiqa davom etishi mumkin."
        if UZ else
        "⏳ Создаю видео...\n"
        "Это может занять несколько минут."
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await message.bot.send_chat_action(message.chat.id, "upload_video")
    
    try:
        # Создаем видео через HeyGen API
        heygen_api_key = os.getenv('HEYGEN_API_KEY')
        
        if not heygen_api_key:
            error_text = "❌ HeyGen API kaliti topilmadi!"
            await message.answer(error_text)
            await state.clear()
            return
        
        creator = HeyGenVideoCreator(heygen_api_key)
        
        # Создаем видео
        result = creator.create_video(
            script_text=data['script'],
            avatar_id=data['avatar_id'],
            voice_id=data['voice_id']
        )
        
        if result and result.get('data'):
            video_id = result['data'].get('video_id')
            
            progress_text = (
                f"✅ Video yaratilmoqda!\n"
                f"🆔 Video ID: {video_id}\n\n"
                f"⏳ Iltimos, kuting..."
                if UZ else
                f"✅ Видео создается!\n"
                f"🆔 Video ID: {video_id}\n\n"
                f"⏳ Пожалуйста, подождите..."
            )
            await message.answer(progress_text)
            
            # Ожидаем завершения
            final_status = creator.wait_for_video(video_id, max_wait_time=300)
            
            if final_status and final_status.get('data', {}).get('status') == 'completed':
                video_url = final_status['data'].get('video_url', '')
                
                success_text = (
                    f"🎉 Video tayyor!\n\n"
                    f"📥 Yuklab olish: {video_url}"
                    if UZ else
                    f"🎉 Видео готово!\n\n"
                    f"📥 Скачать: {video_url}"
                )
                await message.answer(success_text)
            else:
                error_text = (
                    "❌ Video yaratishda xatolik yuz berdi."
                    if UZ else
                    "❌ Ошибка при создании видео."
                )
                await message.answer(error_text)
        else:
            error_text = (
                "❌ Video yaratish boshlanmadi."
                if UZ else
                "❌ Не удалось начать создание видео."
            )
            await message.answer(error_text)
            
    except Exception as e:
        logger.error(f"Ошибка при создании видео: {e}")
        error_text = (
            "❌ Video yaratishda xatolik yuz berdi."
            if UZ else
            "❌ Произошла ошибка при создании видео."
        )
        await message.answer(error_text)
    
    await state.clear()
