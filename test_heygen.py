#!/usr/bin/env python3
"""
Простой тест HeyGen API - создание короткого видео
"""
import os
from dotenv import load_dotenv
from heygen_video import HeyGenVideoCreator

load_dotenv()

def test_heygen():
    """Тестовый запуск создания видео"""
    
    # Проверка API ключа
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        print("❌ HEYGEN_API_KEY не найден в .env файле!")
        print("\n📝 Добавьте в .env файл:")
        print("HEYGEN_API_KEY=ваш_ключ_здесь")
        print("\n🔗 Получить ключ: https://www.heygen.com/")
        return
    
    print("=" * 60)
    print("🎬 ТЕСТ СОЗДАНИЯ ВИДЕО С HEYGEN")
    print("=" * 60)
    
    # Создаем экземпляр
    creator = HeyGenVideoCreator(api_key)
    
    # Короткий тестовый скрипт
    test_scripts = {
        "ru": "Привет! Это тестовое видео. Я AI-аватар от HeyGen.",
        "uz": "Salom! Bu test video. Men HeyGen AI-avatariman.",
        "en": "Hello! This is a test video. I am an AI avatar from HeyGen."
    }
    
    print("\n📝 Выберите язык для теста:")
    print("1. Русский")
    print("2. O'zbek")
    print("3. English")
    
    choice = input("\nВыбор (1-3, Enter = 1): ").strip() or "1"
    
    lang_map = {"1": "ru", "2": "uz", "3": "en"}
    lang = lang_map.get(choice, "ru")
    script = test_scripts[lang]
    
    print(f"\n✅ Выбран язык: {lang}")
    print(f"📝 Текст: {script}")
    
    # Настройки по умолчанию
    avatar_id = "Angela-inblackskirt-20220820"
    voice_id = "1bd001e7e50f421d891986aad5158bc8"
    
    print(f"\n👤 Аватар: Angela")
    print(f"🎙️ Голос: Female (English)")
    print(f"🎨 Фон: Белый")
    
    confirm = input("\n▶️ Начать создание видео? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Отменено")
        return
    
    print("\n⏳ Создаю видео...")
    print("=" * 60)
    
    # Создаем видео
    result = creator.create_video(
        script_text=script,
        avatar_id=avatar_id,
        voice_id=voice_id,
        background_color="#FFFFFF"
    )
    
    if not result or not result.get('data'):
        print("❌ Ошибка при создании видео")
        print("💡 Проверьте:")
        print("   - Правильность API ключа")
        print("   - Наличие кредитов на аккаунте")
        print("   - Доступность API HeyGen")
        return
    
    video_id = result['data'].get('video_id')
    print(f"✅ Видео создается!")
    print(f"🆔 Video ID: {video_id}")
    print("\n⏳ Ожидание завершения (это может занять 2-5 минут)...")
    print("=" * 60)
    
    # Ожидаем завершения
    final_status = creator.wait_for_video(video_id, max_wait_time=600, check_interval=15)
    
    print("\n" + "=" * 60)
    
    if final_status and final_status.get('data', {}).get('status') == 'completed':
        video_url = final_status['data'].get('video_url', '')
        thumbnail_url = final_status['data'].get('thumbnail_url', '')
        
        print("🎉 ВИДЕО ГОТОВО!")
        print("=" * 60)
        print(f"📥 Скачать видео:")
        print(f"   {video_url}")
        if thumbnail_url:
            print(f"\n🖼️ Превью:")
            print(f"   {thumbnail_url}")
        print("\n💡 Совет: Скачайте видео сразу, ссылка может истечь через некоторое время")
        print("=" * 60)
    else:
        print("❌ Не удалось создать видео")
        if final_status:
            status = final_status.get('data', {}).get('status', 'unknown')
            error = final_status.get('data', {}).get('error', 'No error message')
            print(f"📊 Статус: {status}")
            print(f"❗ Ошибка: {error}")
        print("=" * 60)

def test_avatars():
    """Тест получения аватаров"""
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        print("❌ HEYGEN_API_KEY не найден!")
        return

    print("=" * 60)
    print("👤 ТЕСТ ПОЛУЧЕНИЯ АВАТАРОВ")
    print("=" * 60)
    
    creator = HeyGenVideoCreator(api_key)
    avatars = creator.get_avatars()
    
    if avatars:
        print(f"✅ Получено {len(avatars)} аватаров")
        print("\nПервые 5 аватаров:")
        for i, av in enumerate(avatars[:5]):
            print(f"{i+1}. {av.get('name')} (ID: {av.get('avatar_id')})")
    else:
        print("❌ Не удалось получить список аватаров")
    print("=" * 60)

import sys

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "avatars":
            test_avatars()
        else:
            print("1. Тест создания видео")
            print("2. Тест получения аватаров")
            choice = input("Выбор (1/2): ").strip()
            
            if choice == "2":
                test_avatars()
            else:
                test_heygen()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
