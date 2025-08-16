# ΔΣ Guardian: Vision API Guide

## Архитектура Vision API

Guardian использует многоуровневую архитектуру анализа изображений с автоматическим fallback:

### Доступные стратегии анализа:

1. **`basic_only`** - Только базовые метрики OpenCV
   - Размеры изображения
   - Яркость, контраст, резкость
   - Анализ цвета
   - Быстро и надежно

2. **`google_vision`** - Google Cloud Vision API + базовые метрики
   - Детекция объектов и меток
   - Распознавание текста (OCR)
   - Детекция лиц
   - Требует API ключ

3. **`gemini_only`** - Только Gemini Vision
   - LLM-анализ изображений
   - Контекстуальное понимание
   - Требует Gemini API ключ

4. **`full_stack`** - Все доступные методы
   - Максимальная детализация
   - Высокое потребление ресурсов

5. **`auto`** - Автоматический выбор (рекомендуется)
   - Google Vision + Gemini fallback
   - Оптимальная производительность

## Настройка Google Cloud Vision API

### 1. Получение API ключа

```bash
# Создайте проект в Google Cloud Console
# Включите Vision API
# Создайте API ключ или Service Account
```

### 2. Настройка переменных окружения

```bash
# В файле .env
GOOGLE_CLOUD_VISION_API_KEY=your_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 3. Установка зависимостей

```bash
pip install google-cloud-vision
```

## Использование в коде

### Базовое использование

```python
from ai_client.tools.vision_tools import VisionTools

vision = VisionTools()

# Автоматический выбор стратегии
result = vision.analyze_image("path/to/image.jpg")

# Явное указание стратегии
result = vision.analyze_image("path/to/image.jpg", strategy="google_vision")
```

### Получение информации о стратегиях

```python
strategies = vision.get_analysis_strategies()
print(f"Google Vision enabled: {strategies['google_vision_enabled']}")
print(f"Recommended strategy: {strategies['recommended']}")
```

### Примеры использования

```python
# Быстрый анализ для мониторинга
result = vision.analyze_image("camera.jpg", strategy="basic_only")

# Глубокий анализ для безопасности
result = vision.analyze_image("security.jpg", strategy="full_stack")

# Анализ документов
result = vision.analyze_image("document.jpg", strategy="google_vision")
```

## Fallback стратегия

При использовании стратегии `auto`:

1. **Проверяется доступность Google Cloud Vision API**
   - Если API ключ настроен → используется Google Vision
   - Если нет → переход к Gemini

2. **Gemini Vision как fallback**
   - Всегда доступен (если настроен Gemini API)
   - Обеспечивает базовый анализ

3. **Базовые метрики OpenCV**
   - Всегда доступны
   - Минимальный fallback

## Мониторинг и логирование

```python
# Логи показывают используемую стратегию
logger.info("🔍 Vision Tools: Глубокий анализ изображения завершен")

# В результатах указывается использованный API
{
    "google_vision": {
        "api_used": "google_cloud_vision_rest",
        "labels": [...],
        "objects": [...]
    }
}
```

## Производительность

| Стратегия | Скорость | Точность | Ресурсы |
|-----------|----------|----------|---------|
| `basic_only` | ⚡⚡⚡ | ⚡ | ⚡ |
| `google_vision` | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ |
| `gemini_only` | ⚡ | ⚡⚡ | ⚡⚡⚡ |
| `full_stack` | ⚡ | ⚡⚡⚡ | ⚡⚡⚡ |
| `auto` | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ |

## Troubleshooting

### Google Vision API недоступен

```bash
# Проверьте API ключ
echo $GOOGLE_CLOUD_VISION_API_KEY

# Проверьте квоты
# В Google Cloud Console → APIs & Services → Quotas
```

### Gemini Vision недоступен

```bash
# Проверьте Gemini API ключ
echo $GEMINI_API_KEY

# Проверьте модель
# gemini-1.5-pro должна быть доступна
```

### Рекомендации

1. **Для production**: Используйте `auto` стратегию
2. **Для разработки**: `basic_only` для быстрого тестирования
3. **Для безопасности**: `full_stack` для максимальной детализации
4. **Для экономии**: `google_vision` или `gemini_only` в зависимости от потребностей
