# Anti-Drone Defense Simulation
## ΔΣ Guardian Training Environment

Полноценный тренировочный полигон для обучения Guardian в симуляции перед развертыванием на реальном оборудовании.

## 🎯 Цель

Создать безопасную среду для обучения AI-системы антидронной защиты с возможностью sim2real переноса. Симулятор включает:

- **3D физику** дронов, птиц, погодных условий
- **Сенсорную симуляцию** (камеры, радар, лидар)
- **Турельные системы** с пан/тилт контролем
- **Интеграцию с Guardian** (Core, Vision, Security, Comfort)
- **Метрики и мониторинг** производительности
- **Curriculum обучения** от базового до продвинутого

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Simulation    │    │    Guardian     │    │   Monitoring    │
│   Environment   │    │   Services      │    │   & Analytics   │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • AntiDroneWorld│    │ • Core (8005)   │    │ • Grafana       │
│ • Scenarios     │    │ • Vision (8002) │    │ • Prometheus    │
│ • Agents (UAVs) │    │ • Security(8003)│    │ • MinIO         │
│ • Sensors       │    │ • Comfort(8004) │    │ • PostgreSQL    │
│ • Weather       │    │ • MQTT Bridge   │    │ • ChromaDB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MQTT Broker   │
                    │   (Mosquitto)   │
                    └─────────────────┘
```

## 🚀 Быстрый старт

### 1. Запуск симулятора

```bash
# Клонировать репозиторий (если еще не сделано)
cd GUARDIAN/sim

# Запустить симулятор
make run

# Проверить статус
make status
```

### 2. Доступ к интерфейсам

- **Simulation UI**: http://localhost:8082
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9091
- **MinIO Console**: http://localhost:9002 (minioadmin/minioadmin)

### 3. Запуск тестового сценария

```bash
# Быстрый тест
make quick-test

# Полный тест
make test

# Конкретный сценарий
make scenario SCENARIO=basic_uav_detection
```

## 📚 Curriculum обучения

### Phase A: Basic Detection
```bash
make curriculum PHASE=phase_a_basic
```
- Обнаружение одиночных UAV
- Базовое сопровождение целей
- Понимание ограничений сенсоров

### Phase B: False Target Discrimination
```bash
make curriculum PHASE=phase_b_false_targets
```
- Различение UAV и птиц
- Снижение ложных срабатываний
- Поддержание точности обнаружения

### Phase C: Complex Scenarios
```bash
make curriculum PHASE=phase_c_complex
```
- Множественные одновременные угрозы
- Поддержание ситуационной осведомленности
- Оптимизация распределения ресурсов

### Phase D: Adverse Conditions
```bash
make curriculum PHASE=phase_d_adverse
```
- Работа в плохих погодных условиях
- Обнаружение скрытных подходов
- Поддержание производительности под нагрузкой

### Phase E: Advanced Tactics
```bash
make curriculum PHASE=phase_e_advanced
```
- Смешанные среды
- Правильная приоритизация угроз
- Поддержание оперативной эффективности

## 🔧 Конфигурация

### Сценарии

Сценарии определяются в `scenarios/anti_drone_scenarios.yaml`:

```yaml
scenarios:
  basic_uav_detection:
    name: "Basic UAV Detection"
    duration: 60
    weather:
      wind_speed: 2.0
      fog_density: 0.0
    spawns:
      - time: 5.0
        agent_type: "uav"
        position: [100, 0, 30]
        velocity: [-3, 0, 0]
```

### Интеграция с Guardian

Настройки интеграции в `guardian_integration.py`:

```python
config = GuardianConfig(
    core_url="http://localhost:8005",
    vision_url="http://localhost:8002",
    security_url="http://localhost:8003",
    comfort_url="http://localhost:8004",
    mqtt_host="localhost",
    mqtt_port=1883
)
```

## 📊 Метрики и мониторинг

### Ключевые метрики

- **Detection Performance**: время обнаружения, точность, ложные срабатывания
- **Tracking Performance**: непрерывность сопровождения, точность трекинга
- **System Performance**: CPU, память, латентность сети
- **Guardian Integration**: успешность интеграции, время отклика

### Дашборды

1. **Simulation Overview** - общий обзор симуляции
2. **Detection Analytics** - анализ обнаружения
3. **Guardian Integration** - статус интеграции
4. **Performance Metrics** - системные метрики

## 🛠️ Разработка

### Структура кода

```
sim/
├── emulator/
│   ├── anti_drone_world.py    # Основной мир симуляции
│   └── world.py               # Базовый мир (legacy)
├── scenarios/
│   └── anti_drone_scenarios.yaml  # Конфигурация сценариев
├── anti_drone_runner.py       # Запуск сценариев
├── guardian_integration.py    # Интеграция с Guardian
├── docker-compose.sim.yml     # Docker конфигурация
├── Dockerfile.sim             # Docker образ
└── Makefile                   # Управление
```

### Добавление новых сценариев

1. Создать конфигурацию в `scenarios/anti_drone_scenarios.yaml`
2. Определить spawn points, weather conditions, objectives
3. Добавить в curriculum если нужно
4. Протестировать: `make scenario SCENARIO=your_scenario`

### Расширение мира симуляции

1. Добавить новые типы агентов в `AntiDroneWorld`
2. Реализовать физику в `_update_agents()`
3. Добавить новые сенсоры в `_setup_default_scene()`
4. Обновить метрики в `_calculate_metrics()`

## 🔍 Отладка

### Логи

```bash
# Логи симулятора
make logs

# Все логи
make logs-all

# Логи конкретного сервиса
docker-compose -f docker-compose.sim.yml logs -f guardian-sim
```

### Тестирование

```bash
# Быстрый тест
make quick-test

# Бенчмарк производительности
make benchmark

# Проверка здоровья сервисов
make status
```

### Отладка интеграции

```bash
# Проверить MQTT сообщения
docker exec -it guardian-mosquitto mosquitto_sub -t "vision/#" -v

# Проверить API endpoints
curl http://localhost:8005/health
curl http://localhost:8002/health
```

## 📈 Производительность

### Оптимизация

- **GPU acceleration**: для YOLO детекции
- **Batch processing**: группировка кадров
- **Async processing**: неблокирующие операции
- **Caching**: кэширование результатов

### Мониторинг

```bash
# Проверить использование ресурсов
docker stats

# Метрики производительности
make benchmark

# Экспорт телеметрии
make export-telemetry
```

## 🔒 Безопасность

### Этические принципы

- **Только оборонительные** сценарии
- **Символические флаги** для активных средств
- **Безопасные зоны** и no-fire zones
- **Аудит всех действий**

### Безопасность данных

- **Шифрование** телеметрии
- **Access control** к данным
- **Audit trails** всех операций
- **Data retention** политики

## 🚀 Sim2Real

### Подготовка к переносу

1. **Domain Randomization**: вариация текстур, погоды, шумов
2. **Sensor Models**: реалистичные модели сенсоров
3. **Calibration**: калибровка под реальные устройства
4. **A/B Testing**: сравнение симуляции и реальности

### Контракты API

Одинаковые API между симуляцией и реальностью:
- MQTT топики
- REST endpoints
- Data formats
- Error handling

## 📝 Примеры использования

### Запуск полного обучения

```bash
# Запустить все фазы curriculum
for phase in phase_a_basic phase_b_false_targets phase_c_complex phase_d_adverse phase_e_advanced; do
    make curriculum PHASE=$phase
done

# Сгенерировать отчет
make report
```

### Интеграция с существующим Guardian

```bash
# Запустить Guardian сервисы
cd .. && docker-compose up -d

# Запустить симулятор с интеграцией
cd sim && make run

# Проверить интеграцию
make status
```

### Кастомный сценарий

```bash
# Создать кастомный сценарий
cat > custom_scenario.yaml << EOF
scenarios:
  my_scenario:
    name: "Custom Scenario"
    duration: 120
    weather:
      wind_speed: 10.0
      fog_density: 0.3
    spawns:
      - time: 10.0
        agent_type: "uav"
        position: [200, 0, 50]
        velocity: [-5, 0, 0]
EOF

# Запустить кастомный сценарий
python -m sim.anti_drone_runner --scenario my_scenario --scenarios custom_scenario.yaml
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создать feature branch
3. Добавить тесты для новых функций
4. Обновить документацию
5. Создать Pull Request

## 📄 Лицензия

Проект лицензирован под MIT License. См. LICENSE файл для деталей.

## 🆘 Поддержка

- **Issues**: GitHub Issues
- **Documentation**: Этот README и inline комментарии
- **Community**: Guardian Discord/Telegram

---

**ΔΣ Guardian Anti-Drone Simulation** - Безопасное обучение AI для защиты от дронов.
