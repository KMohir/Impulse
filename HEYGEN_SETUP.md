# 🎬 Настройка HeyGen для создания видео с аватаром

## 📋 Что такое HeyGen?

HeyGen - это платформа для создания AI-видео с реалистичными аватарами. Вы можете создавать видео, где аватар говорит ваш текст.

## 🔑 Получение API ключа

1. Зарегистрируйтесь на [HeyGen](https://www.heygen.com/)
2. Перейдите в раздел **API** в настройках аккаунта
3. Создайте новый API ключ
4. Скопируйте ключ

## ⚙️ Установка

### 1. Добавьте API ключ в `.env`:

```env
HEYGEN_API_KEY=ваш_heygen_api_ключ
```

### 2. Установите зависимость (уже установлена):

```bash
pip install requests
```

## 🚀 Использование

### Вариант 1: Через скрипт напрямую

```bash
python heygen_video.py
```

Отредактируйте скрипт `heygen_video.py` для изменения:
- Текста (script)
- ID аватара (avatar_id)
- ID голоса (voice_id)
- Цвета фона (background_color)

### Вариант 2: Через Telegram бота

1. Добавьте код из `heygen_bot_integration.py` в `bot.py`
2. Перезапустите бота
3. Используйте команду `/createvideo` в Telegram

## 👤 Доступные аватары

Популярные аватары HeyGen:

| Имя | ID | Описание |
|-----|-------|----------|
| Angela | `Angela-inblackskirt-20220820` | Женщина в черной юбке |
| Josh | `josh-lite3-20230714` | Мужчина |
| Anna | `Anna_public_3_20240108` | Женщина Анна |

**Полный список аватаров**: https://docs.heygen.com/reference/list-avatars-v2

## 🎙️ Доступные голоса

Получить список голосов через API:
```bash
curl -X GET "https://api.heygen.com/v1/voice.list" \
  -H "X-Api-Key: ваш_ключ"
```

Или посмотрите в документации: https://docs.heygen.com/reference/list-voices-v2

## 📝 Пример использования в коде

```python
from heygen_video import HeyGenVideoCreator

# Создать экземпляр
creator = HeyGenVideoCreator("ваш_api_ключ")

# Создать видео
result = creator.create_video(
    script_text="Привет! Это тестовое видео.",
    avatar_id="Angela-inblackskirt-20220820",
    voice_id="1bd001e7e50f421d891986aad5158bc8",
    background_color="#FFFFFF"
)

# Получить video_id
video_id = result['data']['video_id']

# Ожидать завершения
final_status = creator.wait_for_video(video_id)

# Получить URL видео
video_url = final_status['data']['video_url']
print(f"Видео готово: {video_url}")
```

## 💰 Цены

HeyGen работает на кредитной основе:
- 1 минута видео ≈ 1 кредит
- Бесплатный план: ограниченное количество кредитов
- Платные планы: от $24/месяц

Подробнее: https://www.heygen.com/pricing

## 🔗 Полезные ссылки

- [Документация API](https://docs.heygen.com/)
- [Список аватаров](https://docs.heygen.com/reference/list-avatars-v2)
- [Список голосов](https://docs.heygen.com/reference/list-voices-v2)
- [Примеры](https://docs.heygen.com/docs/examples)

## ⚠️ Важные замечания

1. **Лимиты API**: Проверьте лимиты вашего плана
2. **Время создания**: Видео создается 2-5 минут
3. **Формат**: Видео создается в формате MP4
4. **Размер**: Стандартное разрешение 1920x1080 (Full HD)

## 🐛 Решение проблем

### Ошибка "API key not found"
- Проверьте, что `HEYGEN_API_KEY` добавлен в `.env`
- Перезапустите скрипт/бота

### Ошибка "Invalid avatar_id"
- Используйте правильный ID аватара из документации
- Проверьте доступность аватара в вашем плане

### Ошибка "Insufficient credits"
- Пополните баланс кредитов на HeyGen
- Проверьте лимиты вашего плана

### Видео не создается
- Проверьте статус через `check_video_status(video_id)`
- Увеличьте `max_wait_time` если видео долго создается
