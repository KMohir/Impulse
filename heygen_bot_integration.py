"""
Интеграция HeyGen в Telegram бота для создания видео с аватаром
Добавьте этот код в bot.py
"""

# Добавьте в импорты:
# from heygen_video import HeyGenVideoCreator

# Добавьте новое состояние для создания видео:
class VideoCreationStates(StatesGroup):
    script = State()
    avatar = State()
    voice = State()


@dp.message(Command("createvideo"))
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


@dp.message(VideoCreationStates.script)
async def process_video_script(message: Message, state: FSMContext):
    """Обработка скрипта для видео"""
    await state.update_data(script=message.text)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👩 Angela (ayol)")],
            [KeyboardButton(text="👨 Josh (erkak)")],
            [KeyboardButton(text="👩 Anna")],
            [KeyboardButton(text="🎭 Boshqa avatar")]
        ] if UZ else [
            [KeyboardButton(text="👩 Angela (женщина)")],
            [KeyboardButton(text="👨 Josh (мужчина)")],
            [KeyboardButton(text="👩 Anna")],
            [KeyboardButton(text="🎭 Другой аватар")]
        ],
        resize_keyboard=True
    )
    
    text = (
        "👤 Avatarni tanlang:"
        if UZ else
        "👤 Выберите аватар:"
    )
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(VideoCreationStates.avatar)


@dp.message(VideoCreationStates.avatar)
async def process_video_avatar(message: Message, state: FSMContext):
    """Обработка выбора аватара"""
    avatar_map = {
        "Angela": "Angela-inblackskirt-20220820",
        "Josh": "josh-lite3-20230714",
        "Anna": "Anna_public_3_20240108"
    }
    
    # Определяем ID аватара
    avatar_id = "Angela-inblackskirt-20220820"  # По умолчанию
    for name, aid in avatar_map.items():
        if name.lower() in message.text.lower():
            avatar_id = aid
            break
    
    await state.update_data(avatar_id=avatar_id)
    
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


@dp.message(VideoCreationStates.voice)
async def process_video_voice(message: Message, state: FSMContext):
    """Обработка выбора голоса и создание видео"""
    
    # Карта голосов (замените на реальные ID из HeyGen)
    voice_map = {
        "женский": "1bd001e7e50f421d891986aad5158bc8",
        "мужской": "2d5b0e6c4f3a4b8c9d1e2f3a4b5c6d7e",
        "русский": "3e6c1f7d5a4b3c2d1e0f9a8b7c6d5e4f",
        "узбекский": "4f7d2e8c6b5a4d3c2e1f0a9b8c7d6e5f"
    }
    
    voice_id = "1bd001e7e50f421d891986aad5158bc8"  # По умолчанию
    for key, vid in voice_map.items():
        if key in message.text.lower():
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
    await bot.send_chat_action(message.chat.id, "upload_video")
    
    try:
        # Создаем видео через HeyGen API
        heygen_api_key = os.getenv('HEYGEN_API_KEY')
        
        if not heygen_api_key:
            error_text = (
                "❌ HeyGen API kaliti topilmadi!"
                if UZ else
                "❌ HeyGen API ключ не найден!"
            )
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
