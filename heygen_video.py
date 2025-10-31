#!/usr/bin/env python3
"""
Скрипт для создания видео через HeyGen API с аватаром
"""
import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# HeyGen API настройки
HEYGEN_API_KEY = os.getenv('HEYGEN_API_KEY', '')
HEYGEN_API_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"

class HeyGenVideoCreator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def create_video(self, script_text, avatar_id="default", voice_id="default", background_color="#FFFFFF"):
        """
        Создать видео с аватаром
        
        Args:
            script_text (str): Текст для озвучки аватаром
            avatar_id (str): ID аватара (например: "Angela-inblackskirt-20220820")
            voice_id (str): ID голоса (например: "1bd001e7e50f421d891986aad5158bc8")
            background_color (str): Цвет фона в HEX формате
        
        Returns:
            dict: Ответ от API с video_id
        """
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script_text,
                        "voice_id": voice_id
                    },
                    "background": {
                        "type": "color",
                        "value": background_color
                    }
                }
            ],
            "dimension": {
                "width": 1920,
                "height": 1080
            },
            "aspect_ratio": "16:9",
            "test": False  # False для реального создания, True для теста
        }
        
        try:
            response = requests.post(
                HEYGEN_API_URL,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при создании видео: {e}")
            if hasattr(e.response, 'text'):
                print(f"Детали ошибки: {e.response.text}")
            return None
    
    def check_video_status(self, video_id):
        """
        Проверить статус создания видео
        
        Args:
            video_id (str): ID видео
        
        Returns:
            dict: Статус видео
        """
        params = {"video_id": video_id}
        
        try:
            response = requests.get(
                HEYGEN_STATUS_URL,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при проверке статуса: {e}")
            return None
    
    def wait_for_video(self, video_id, max_wait_time=600, check_interval=10):
        """
        Ожидать завершения создания видео
        
        Args:
            video_id (str): ID видео
            max_wait_time (int): Максимальное время ожидания в секундах
            check_interval (int): Интервал проверки в секундах
        
        Returns:
            dict: Финальный статус видео
        """
        elapsed_time = 0
        print(f"⏳ Ожидание создания видео (ID: {video_id})...")
        
        while elapsed_time < max_wait_time:
            status = self.check_video_status(video_id)
            
            if status:
                video_status = status.get('data', {}).get('status', 'unknown')
                print(f"📊 Статус: {video_status} (прошло {elapsed_time}с)")
                
                if video_status == "completed":
                    video_url = status.get('data', {}).get('video_url', '')
                    print(f"✅ Видео готово! URL: {video_url}")
                    return status
                elif video_status == "failed":
                    print(f"❌ Создание видео не удалось")
                    return status
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        print(f"⏰ Превышено время ожидания ({max_wait_time}с)")
        return None


def main():
    """Пример использования"""
    
    # Проверка API ключа
    if not HEYGEN_API_KEY:
        print("❌ HEYGEN_API_KEY не найден в .env файле!")
        print("Добавьте в .env файл: HEYGEN_API_KEY=ваш_ключ")
        return
    
    # Создание экземпляра
    creator = HeyGenVideoCreator(HEYGEN_API_KEY)
    
    # Пример скрипта для видео
    script = """
    Привет! Я представляю наш бренд.
    Мы предлагаем инновационные решения для вашего бизнеса.
    Присоединяйтесь к нам и развивайте свой бренд вместе с нами!
    """
    
    # Популярные аватары HeyGen (замените на свои):
    # "Angela-inblackskirt-20220820" - женщина в черной юбке
    # "josh-lite3-20230714" - мужчина
    # "Anna_public_3_20240108" - женщина Анна
    
    avatar_id = "Angela-inblackskirt-20220820"  # Замените на нужный
    voice_id = "1bd001e7e50f421d891986aad5158bc8"  # Замените на нужный голос
    
    print("🎬 Создание видео с аватаром...")
    print(f"📝 Скрипт: {script[:50]}...")
    print(f"👤 Аватар ID: {avatar_id}")
    
    # Создать видео
    result = creator.create_video(
        script_text=script,
        avatar_id=avatar_id,
        voice_id=voice_id,
        background_color="#FFFFFF"
    )
    
    if result and result.get('data'):
        video_id = result['data'].get('video_id')
        print(f"✅ Видео создается! ID: {video_id}")
        
        # Ожидать завершения
        final_status = creator.wait_for_video(video_id)
        
        if final_status:
            video_url = final_status.get('data', {}).get('video_url', '')
            if video_url:
                print(f"\n🎉 Готово! Скачайте видео: {video_url}")
    else:
        print("❌ Не удалось создать видео")


if __name__ == "__main__":
    main()
