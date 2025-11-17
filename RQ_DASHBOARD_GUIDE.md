# Руководство по RQ Dashboard

## Что такое RQ Dashboard?

**RQ Dashboard** - это официальный веб-интерфейс для мониторинга Redis Queue (RQ) задач. Он предоставляет удобный графический интерфейс для отслеживания состояния очередей, задач и воркеров.

## Доступ к Dashboard

После запуска внешнего сервиса мониторинга:

```
http://localhost:9181
```

⚠️ **Важно**: RQ Dashboard запускается как **внешний сервис**, отдельно от основного приложения. Это позволяет легко включать/отключать мониторинг без изменения основного docker-compose.yml.

## Основные возможности

### 1. Обзор очередей

На главной странице отображаются:
- **Все очереди** - список всех доступных очередей RQ
- **Статистика по каждой очереди**:
  - Queued (в очереди)
  - Started (выполняются)
  - Finished (завершены)
  - Failed (ошибки)
  - Deferred (отложены)
  - Scheduled (запланированы)

### 2. Просмотр задач

Для каждой очереди можно:
- Просмотреть все задачи
- Отфильтровать по статусу
- Увидеть детали каждой задачи:
  - ID задачи
  - Статус
  - Время создания
  - Время начала выполнения
  - Время завершения
  - Длительность выполнения
  - Результат или ошибка

### 3. Детали задачи

При клике на задачу отображается:
- Полная информация о задаче
- Аргументы функции
- Результат выполнения
- Трассировка ошибки (если есть)
- Логи выполнения

### 4. Управление задачами

Возможности:
- **Перезапуск** - перезапустить неудачную задачу
- **Удаление** - удалить задачу из очереди
- **Отмена** - отменить выполняющуюся задачу

### 5. Мониторинг воркеров

Dashboard показывает:
- Активные воркеры
- Задачи, которые они выполняют
- Время работы воркеров

## Использование

### Запуск Dashboard как внешнего сервиса

RQ Dashboard запускается через отдельный `docker-compose.monitoring.yml`:

```bash
# 1. Сначала убедитесь, что основное приложение запущено
docker compose up -d

# 2. Запустите мониторинг как внешний сервис
docker compose -f docker-compose.monitoring.yml up -d

# Или запустите в foreground для просмотра логов
docker compose -f docker-compose.monitoring.yml up
```

### Остановка Dashboard

```bash
# Остановить мониторинг
docker compose -f docker-compose.monitoring.yml down

# Остановить с удалением контейнера
docker compose -f docker-compose.monitoring.yml down --remove-orphans
```

### Запуск БЕЗ Dashboard (продакшен)

```bash
# Просто запустите основное приложение
docker compose up -d

# Мониторинг не будет запущен, так как он в отдельном файле
```

### Проверка статуса

```bash
# Проверить, что RQ Dashboard запущен
docker compose -f docker-compose.monitoring.yml ps

# Посмотреть логи
docker compose -f docker-compose.monitoring.yml logs -f rq-dashboard
```

### Остановка

```bash
# Остановить только мониторинг
docker compose -f docker-compose.monitoring.yml down

# Остановить основное приложение (мониторинг продолжит работать)
docker compose down
```

## Интерфейс

### Главная страница

```
┌─────────────────────────────────────┐
│  RQ Dashboard                      │
├─────────────────────────────────────┤
│  Queue: default                    │
│  ┌───────────────────────────────┐ │
│  │ Queued:    5                 │ │
│  │ Started:   2                 │ │
│  │ Finished:  150               │ │
│  │ Failed:    3                 │ │
│  └───────────────────────────────┘ │
│                                    │
│  [View Jobs] [View Workers]        │
└─────────────────────────────────────┘
```

### Страница задач

- Фильтры по статусу
- Поиск по ID задачи
- Сортировка по времени создания
- Автообновление (каждые 5 секунд)

## Интеграция с API

RQ Dashboard работает независимо от нашего API, но использует тот же Redis. Это означает:

- ✅ Все задачи, созданные через API, видны в Dashboard
- ✅ Все метрики синхронизированы
- ✅ Можно управлять задачами как через API, так и через Dashboard

## Безопасность

⚠️ **Важно**: RQ Dashboard по умолчанию не имеет аутентификации. В production окружении рекомендуется:

1. Использовать reverse proxy с аутентификацией (nginx + basic auth)
2. Ограничить доступ по IP
3. Использовать VPN или внутреннюю сеть

### Пример настройки nginx с basic auth

```nginx
server {
    listen 80;
    server_name rq-dashboard.example.com;

    location / {
        auth_basic "RQ Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://localhost:9181;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Dashboard не открывается

1. Проверьте, что контейнер запущен:
   ```bash
   docker compose -f docker-compose.monitoring.yml ps
   ```

2. Проверьте логи:
   ```bash
   docker compose -f docker-compose.monitoring.yml logs rq-dashboard
   ```

3. Проверьте, что основное приложение запущено и Redis доступен:
   ```bash
   docker compose ps redis
   ```

4. Проверьте, что мониторинг подключён к правильной Docker сети:
   ```bash
   docker network ls
   docker network inspect conversations_default
   ```

### Нет задач в Dashboard

1. Убедитесь, что задачи создаются через API
2. Проверьте, что воркер запущен:
   ```bash
   docker compose ps worker
   ```

3. Проверьте подключение к Redis:
   ```bash
   docker compose exec redis redis-cli ping
   ```

### Dashboard показывает старые данные

- Dashboard обновляется автоматически каждые 5 секунд
- Если данные не обновляются, перезагрузите страницу
- Проверьте, что Redis работает корректно

## Дополнительные возможности

### Настройка через переменные окружения

В `docker-compose.monitoring.yml` можно настроить:

```yaml
rq-dashboard:
  environment:
    - RQ_DASHBOARD_REDIS_URL=redis://redis:6379
    - RQ_DASHBOARD_POLL_INTERVAL=5  # Интервал обновления (секунды)
    - RQ_DASHBOARD_WEB_BACKGROUND=white  # Цвет фона
```

Или при запуске:

```bash
RQ_DASHBOARD_POLL_INTERVAL=5 docker compose -f docker-compose.monitoring.yml up -d
```

### Подключение к нескольким Redis

RQ Dashboard может подключаться только к одному Redis. Если нужно мониторить несколько Redis, запустите несколько экземпляров Dashboard на разных портах, изменив порт в `docker-compose.monitoring.yml`.

## Сравнение с API мониторингом

| Функция | RQ Dashboard | API Endpoints |
|---------|-------------|---------------|
| Веб-интерфейс | ✅ Да | ❌ Нет |
| Визуализация | ✅ Да | ❌ Нет |
| Управление задачами | ✅ Да | ❌ Нет |
| Программный доступ | ❌ Нет | ✅ Да |
| Метрики эффективности | ❌ Нет | ✅ Да |
| Тренды | ❌ Нет | ✅ Да |
| Сравнение периодов | ❌ Нет | ✅ Да |

**Рекомендация**: Используйте RQ Dashboard для визуального мониторинга и быстрого управления задачами, а API endpoints - для программного доступа к метрикам и автоматизации.

