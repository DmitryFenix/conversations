# Руководство по настройке мониторинга

Мониторинг RQ состоит из двух компонентов:

1. **API Endpoints мониторинга** - встроены в основное приложение (`/api/rq/*`)
2. **RQ Dashboard** - внешний веб-интерфейс (запускается отдельно)

## Быстрый старт

### 1. Запуск основного приложения (с API мониторингом)

```bash
# Запустить основное приложение
docker compose up -d

# API endpoints мониторинга уже доступны:
# - http://localhost:8000/api/rq/stats
# - http://localhost:8000/api/rq/performance
# - http://localhost:8000/api/rq/performance/trends
# - http://localhost:8000/api/rq/performance/compare
```

### 2. Запуск RQ Dashboard (опционально)

```bash
# Запустить внешний веб-интерфейс мониторинга
docker compose -f docker-compose.monitoring.yml up -d

# Открыть в браузере
# http://localhost:9181
```

## Компоненты мониторинга

### API Endpoints (встроены в приложение)

**Файлы**: `api/rq_monitor.py`, `api/rq_dashboard.py`

**Доступны автоматически** после запуска основного приложения.

**Endpoints**:
- `GET /api/rq/stats` - статистика очереди
- `GET /api/rq/jobs/recent?limit=10` - недавние задачи
- `GET /api/rq/jobs/{job_id}` - детали задачи
- `GET /api/rq/performance?hours=24` - метрики производительности
- `GET /api/rq/performance/trends?periods=6&hours_per_period=4` - тренды
- `GET /api/rq/performance/compare?current_hours=1&previous_hours=1` - сравнение периодов

**Использование**:
```bash
# Получить статистику
curl http://localhost:8000/api/rq/stats

# Получить метрики за последний час
curl http://localhost:8000/api/rq/performance?hours=1

# Получить тренды
curl http://localhost:8000/api/rq/performance/trends
```

### RQ Dashboard (внешний сервис)

**Файл**: `docker-compose.monitoring.yml`

**Веб-интерфейс** для визуального мониторинга задач.

**Запуск**:
```bash
# Запустить Dashboard
docker compose -f docker-compose.monitoring.yml up -d

# Остановить Dashboard
docker compose -f docker-compose.monitoring.yml down
```

**Доступ**: http://localhost:9181

## Настройка для разных окружений

### Разработка

```bash
# 1. Запустить основное приложение
docker compose up -d

# 2. (Опционально) Запустить Dashboard для визуального мониторинга
docker compose -f docker-compose.monitoring.yml up -d
```

### Продакшен

```bash
# Запустить только основное приложение
docker compose up -d

# Dashboard НЕ запускается автоматически
# Используйте API endpoints для мониторинга:
# - /api/rq/performance
# - /api/rq/performance/trends
# - /api/rq/performance/compare
```

## Обновление кода мониторинга

⚠️ **Важно**: Файлы `rq_monitor.py` и `rq_dashboard.py` **не монтируются** как volumes, поэтому изменения требуют пересборки образа.

### Изменение кода мониторинга

1. **Отредактировать файлы**:
   - `api/rq_monitor.py`
   - `api/rq_dashboard.py`

2. **Пересобрать образ**:
   ```bash
   docker compose build api
   docker compose up -d api
   ```

3. **Проверить изменения**:
   ```bash
   # Проверить логи
   docker compose logs api | grep -i "rq\|monitoring"
   
   # Проверить API endpoints
   curl http://localhost:8000/api/rq/stats
   ```

### Быстрая проверка без пересборки (только для разработки)

Если нужно быстро протестировать изменения, можно временно добавить volumes в `docker-compose.yml`:

```yaml
volumes:
  - ./api/rq_monitor.py:/app/rq_monitor.py
  - ./api/rq_dashboard.py:/app/rq_dashboard.py
```

После тестирования **обязательно уберите** volumes и пересоберите образ для продакшена.

## Настройка RQ Dashboard

### Изменение порта

Отредактируйте `docker-compose.monitoring.yml`:

```yaml
ports:
  - "9182:9181"  # Внешний порт 9182, внутренний 9181
```

### Изменение интервала обновления

Создайте файл `.env.monitoring`:

```env
RQ_DASHBOARD_POLL_INTERVAL=10
```

И используйте при запуске:

```bash
docker compose --env-file .env.monitoring -f docker-compose.monitoring.yml up -d
```

### Подключение к другому Redis

Отредактируйте `docker-compose.monitoring.yml`:

```yaml
command: >
  sh -c "
  pip install --no-cache-dir rq-dashboard==0.6.1 &&
  rq-dashboard --redis-url redis://your-redis-host:6379 --host 0.0.0.0 --port 9181
  "
```

## Проверка работы мониторинга

### Проверка API endpoints

```bash
# Статистика очереди
curl http://localhost:8000/api/rq/stats

# Метрики производительности
curl http://localhost:8000/api/rq/performance?hours=1

# Тренды
curl http://localhost:8000/api/rq/performance/trends?periods=6&hours_per_period=4

# Сравнение периодов
curl http://localhost:8000/api/rq/performance/compare?current_hours=1&previous_hours=1
```

### Проверка RQ Dashboard

```bash
# Проверить статус
docker compose -f docker-compose.monitoring.yml ps

# Проверить логи
docker compose -f docker-compose.monitoring.yml logs rq-dashboard

# Открыть в браузере
# http://localhost:9181
```

### Проверка подключения к Redis

```bash
# Из контейнера мониторинга
docker compose -f docker-compose.monitoring.yml exec rq-dashboard ping -c 1 redis

# Проверить сеть
docker network inspect conversations_default | grep redis
```

## Troubleshooting

### API endpoints не работают

1. Проверьте, что приложение запущено:
   ```bash
   docker compose ps api
   ```

2. Проверьте логи:
   ```bash
   docker compose logs api | grep -i "rq\|monitoring"
   ```

3. Проверьте, что файлы мониторинга в образе:
   ```bash
   docker compose exec api ls -la /app/rq_*.py
   ```

### RQ Dashboard не подключается к Redis

1. Убедитесь, что основное приложение запущено:
   ```bash
   docker compose up -d
   ```

2. Проверьте имя сети:
   ```bash
   docker network ls
   # Найдите сеть вида: conversations_default
   ```

3. Обновите имя сети в `docker-compose.monitoring.yml` если нужно

### Изменения в коде не применяются

Помните: файлы мониторинга не монтируются как volumes, поэтому:

1. **Пересоберите образ**:
   ```bash
   docker compose build api
   docker compose up -d api
   ```

2. Или временно добавьте volumes для разработки (см. выше)

## Рекомендации

### Для разработки

- Используйте API endpoints для программного доступа
- Запускайте RQ Dashboard для визуального мониторинга
- При изменении кода мониторинга - пересобирайте образ

### Для продакшена

- Используйте только API endpoints
- Не запускайте RQ Dashboard (безопасность, ресурсы)
- Настройте мониторинг через внешние системы (Prometheus, Grafana) используя API endpoints
- Настройте алерты на основе метрик из `/api/rq/performance`

## Интеграция с внешними системами мониторинга

API endpoints можно использовать для интеграции с Prometheus, Grafana и другими системами:

```bash
# Пример экспорта метрик для Prometheus
curl http://localhost:8000/api/rq/performance?hours=1 | \
  jq '.metrics | to_entries | map("rq_\(.key) \(.value)") | .[]'
```

## Дополнительная документация

- `RQ_PERFORMANCE_MONITORING.md` - подробное описание API endpoints
- `RQ_DASHBOARD_GUIDE.md` - руководство по RQ Dashboard
- `MONITORING_SETUP.md` - настройка внешнего мониторинга

