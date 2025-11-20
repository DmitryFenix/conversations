# CI/CD Guide

## GitHub Actions Workflow

Проект использует GitHub Actions для автоматической проверки кода, тестирования и деплоя.

### Workflow файл

Расположен в `.github/workflows/ci.yml`

### Jobs

1. **lint-backend** - Проверка кода Python (flake8, black)
2. **lint-frontend** - Проверка кода JavaScript (ESLint)
3. **backend-tests** - Запуск тестов бэкенда в Docker
4. **frontend-build** - Сборка фронтенда
5. **docker-build** - Тестовая сборка Docker образа
6. **deploy** - Автоматический деплой на Railway (только для ветки `main`)

### Триггеры

- Push в ветки `main` или `dev`
- Pull Request в ветки `main` или `dev`
- Ручной запуск через `workflow_dispatch`

### Secrets

Для работы деплоя необходимо настроить следующие secrets в GitHub:

1. **RAILWAY_TOKEN** - Токен для доступа к Railway API
   - Получить можно в Railway Dashboard → Settings → Tokens
   
2. **RAILWAY_SERVICE** (опционально) - ID сервиса для деплоя
   - Если не указан, деплой будет в дефолтный сервис проекта

### Настройка Secrets

1. Перейдите в репозиторий на GitHub
2. Settings → Secrets and variables → Actions
3. Добавьте необходимые secrets

### Локальный запуск

Для локального запуска тестов используйте:

```bash
# Backend тесты
docker compose --profile testing up -d redis api worker
docker compose --profile testing run --rm tests

# Frontend сборка
cd frontend
npm ci
npm run build
```

## Автоматическая очистка сессий

### Настройка

Очистка сессий настроена через переменные окружения:

- `SESSION_RETENTION_DAYS` - Количество дней хранения сессий (по умолчанию: 2)
- `SESSION_CLEANUP_INTERVAL_SECONDS` - Интервал проверки в секундах (по умолчанию: 3600 = 1 час)

### Как это работает

1. При старте приложения автоматически запускается фоновый поток очистки
2. Каждый час (или по настройке) проверяются все активные сессии
3. Сессии старше `SESSION_RETENTION_DAYS` дней помечаются как удалённые (`deleted_at`)
4. Артефакты сессий (файлы в `/artifacts`) также удаляются

### API Endpoints для управления очисткой

#### Ручной запуск очистки

```bash
POST /api/admin/cleanup-sessions
```

Ответ:
```json
{
  "status": "success",
  "deleted_sessions": 5,
  "retention_days": 2,
  "message": "Cleaned up 5 sessions older than 2 days"
}
```

#### Статистика сессий

```bash
GET /api/admin/sessions-stats
```

Ответ:
```json
{
  "active_sessions": 10,
  "deleted_sessions": 25,
  "expiring_soon": 2,
  "old_uncleaned": 0,
  "retention_days": 2,
  "cleanup_interval_seconds": 3600
}
```

### Логирование

Все операции очистки логируются:
- Успешная очистка: `INFO` уровень
- Ошибки: `ERROR` уровень с полным traceback

Пример лога:
```
INFO: Auto-cleaned 5 sessions older than 2 days
```

## Мониторинг

### GitHub Actions

Проверьте статус последних запусков:
- Перейдите в репозиторий → вкладка "Actions"
- Посмотрите статус последнего workflow

### Railway Deployment

После деплоя проверьте:
- Railway Dashboard → ваш проект → Deployments
- Логи сервиса для проверки ошибок

## Troubleshooting

### Тесты не проходят

1. Проверьте логи в GitHub Actions
2. Убедитесь, что все зависимости установлены
3. Проверьте, что Docker контейнеры запускаются корректно

### Деплой не работает

1. Проверьте, что `RAILWAY_TOKEN` настроен правильно
2. Убедитесь, что вы в ветке `main`
3. Проверьте логи деплоя в GitHub Actions

### Очистка сессий не работает

1. Проверьте логи приложения
2. Убедитесь, что переменные окружения настроены правильно
3. Используйте ручной endpoint для тестирования: `POST /api/admin/cleanup-sessions`

