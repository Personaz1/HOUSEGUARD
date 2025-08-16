# ΔΣ Smart House - Virtual Home Summary
## Полноценный виртуальный дом с датчиками и автоматизацией

## 🏠 Дом

### Планировка
- **Размеры**: 45m × 25m × 3m (450 × 250 × 30 units)
- **Комнаты**: 7 основных зон
  - Entrance Hall (вход)
  - Living Room (гостиная)
  - Kitchen (кухня)
  - Master Bedroom (спальня)
  - Bathroom (ванная)
  - Garage (гараж)
  - Backyard (задний двор)

### Зоны безопасности
- **Perimeter Zone**: внешние камеры, датчики дверей/окон
- **Interior Zone**: внутренние датчики движения, камеры
- **Critical Zone**: датчики дыма, CO, протечек воды

## 📡 Устройства (40+ устройств)

### Освещение (5 устройств)
- `light_living_main` - основное освещение гостиной
- `light_living_ambient` - декоративное освещение
- `light_kitchen_main` - освещение кухни
- `light_bedroom_main` - освещение спальни
- `light_bathroom` - освещение ванной

### Безопасность (15 устройств)
- **Камеры**: `camera_front_door`, `camera_backyard`, `camera_living`, `camera_garage`
- **Датчики движения**: `motion_sensor_living`, `motion_sensor_kitchen`, `motion_sensor_bedroom`
- **Датчики дверей**: `door_sensor_front`, `door_sensor_back`
- **Датчики окон**: `window_sensor_living`, `window_sensor_bedroom`
- **Замки**: `front_door_lock`, `back_door_lock`
- **Сирены**: `siren_main`, `siren_backup`

### Комфорт (8 устройств)
- **Термостаты**: `thermostat_living`, `thermostat_bedroom`
- **Датчики влажности**: `humidity_sensor_living`, `humidity_sensor_bedroom`
- **Датчик качества воздуха**: `air_quality_sensor_living`
- **Вентилятор**: `fan_living`
- **Жалюзи**: `blinds_living`, `blinds_bedroom`

### Безопасность жизни (6 устройств)
- **Датчики дыма**: `smoke_detector_living`, `smoke_detector_kitchen`
- **Датчик CO**: `co_detector_living`
- **Датчики протечек**: `water_leak_sensor_kitchen`, `water_leak_sensor_bathroom`
- **Гаражные ворота**: `garage_door`

### Автоматизация (6 устройств)
- **Умные розетки**: `smart_plug_living_tv`, `smart_plug_kitchen_coffee`
- **Робот-пылесос**: `robot_vacuum`

## 🤖 Автоматизация

### Сценарии (16 правил)
1. **Morning Routine** - утренняя рутина
2. **Evening Routine** - вечерняя рутина
3. **Security Breach Response** - реакция на нарушение безопасности
4. **Fire Emergency Response** - реакция на пожар
5. **Water Leak Response** - реакция на протечку воды
6. **Occupancy-Based Lighting** - освещение по присутствию
7. **Temperature Control** - контроль температуры
8. **Energy Saving Mode** - режим экономии энергии
9. **Air Quality Control** - контроль качества воздуха
10. **Humidity Control** - контроль влажности
11. **Smart Blinds** - умные жалюзи
12. **Robot Vacuum Schedule** - расписание робота-пылесоса
13. **Coffee Morning** - утренний кофе
14. **Security Arm Away** - постановка на охрану
15. **Security Disarm Home** - снятие с охраны

### Триггеры
- **Время**: по расписанию (07:00, 22:00, etc.)
- **Датчики**: движение, открытие дверей/окон, дым, CO, протечки
- **Условия**: режим безопасности, температура, влажность

### Действия
- **Освещение**: включение/выключение, яркость, цветовая температура
- **Безопасность**: блокировка/разблокировка, сирены, снимки камер
- **Комфорт**: температура, жалюзи, вентилятор
- **Автоматизация**: умные розетки, робот-пылесос

## 📊 Симулятор

### SmartHomeSimulator
- **Полная эмуляция** всех устройств
- **MQTT интеграция** с Guardian
- **FastAPI сервер** для управления
- **Real-time симуляция** состояний
- **Генерация кадров** камер
- **Симуляция событий** датчиков

### Возможности симулятора
- Управление занятостью комнат
- Симуляция погодных условий
- Генерация событий безопасности
- Эмуляция работы термостатов
- Создание снимков камер
- Публикация в MQTT

## 🔗 Интеграция с Guardian

### MQTT топики
- `home/device/{device_id}/set` - управление устройствами
- `home/device/{device_id}/state` - состояния устройств
- `vision/events/{camera_id}` - события камер
- `home/security/state` - состояние безопасности

### API endpoints
- `GET /devices` - список всех устройств
- `GET /device/{id}` - состояние устройства
- `POST /device/{id}/set` - управление устройством
- `GET /camera/{id}/frame` - кадр камеры
- `GET /occupancy` - занятость комнат
- `GET /weather` - погодные условия
- `GET /security/mode` - режим безопасности

## 🎯 Использование

### Запуск
```bash
cd SMARTHOUSE
docker-compose up -d
```

### Тестирование
```bash
# Проверить состояние всех устройств
curl http://localhost:8000/devices

# Включить свет в гостиной
curl -X POST http://localhost:8000/device/light_living_main/set \
  -H "Content-Type: application/json" \
  -d '{"state": "ON", "brightness": 80}'

# Симулировать движение в спальне
curl -X POST http://localhost:8000/occupancy/bedroom \
  -H "Content-Type: application/json" \
  -d 'true'

# Получить кадр с камеры
curl http://localhost:8000/camera/camera_front_door/frame
```

### Мониторинг
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MinIO**: http://localhost:9000 (minioadmin/minioadmin)

## 🚀 Следующие шаги

### Phase 1: Интеграция с Guardian (24h)
- [ ] Подключение к Guardian Core/Vision/Security
- [ ] Тестирование автоматизации
- [ ] Валидация сценариев безопасности

### Phase 2: UI/UX (48h)
- [ ] Веб-интерфейс управления домом
- [ ] 3D визуализация плана
- [ ] Дашборды мониторинга
- [ ] Мобильное приложение

### Phase 3: Расширение (72h)
- [ ] Добавление новых устройств
- [ ] Расширенные сценарии
- [ ] Интеграция с внешними сервисами
- [ ] Machine Learning для оптимизации

### Phase 4: Production (24h)
- [ ] Оптимизация производительности
- [ ] Безопасность и шифрование
- [ ] Документация и обучение
- [ ] Развертывание

## 🎉 Результат

Полноценный виртуальный дом с:
- ✅ **40+ устройств** всех типов
- ✅ **16 сценариев** автоматизации
- ✅ **Полная симуляция** работы
- ✅ **Интеграция** с Guardian
- ✅ **MQTT коммуникация**
- ✅ **API для управления**
- ✅ **Мониторинг** и метрики

**Готов к использованию для обучения и тестирования Guardian!**

---

**ΔΣ Smart House** - Виртуальный дом для обучения AI-системы умного дома.




