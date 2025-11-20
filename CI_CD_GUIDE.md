# CI/CD Guide - Local Deployment

## GitHub Actions Workflow

Проект использует GitHub Actions для автоматической проверки кода, тестирования и проверки локального развёртывания.

### Workflow файл

Расположен в `.github/workflows/ci.yml`

### Jobs

1. **lint-backend** - Проверка кода Python (flake8, black, isort, bandit, safety)
2. **lint-frontend** - Проверка кода JavaScript (ESLint, npm audit)
3. **backend-tests** - Запуск тестов бэкенда в Docker (матрица: Python 3.10, 3.11)
4. **frontend-build** - Сборка фронтенда (матрица: Node 18, 20, с сохранением артефактов)
5. **docker-build-production** - Сборка production Docker образа с публикацией в GHCR
6. **local-deployment-test** - Проверка локального развёртывания через docker-compose
7. **docker-compose-validation** - Валидация всех docker-compose файлов
8. **code-quality** - Проверка качества кода (pylint, radon для анализа сложности)
9. **notify-on-failure** - Уведомления при провале jobs

### Триггеры

- Push в ветки `main` или `dev`
- Pull Request в ветки `main` или `dev`
- Ручной запуск через `workflow_dispatch`
- Ежедневный запуск в 2:00 UTC для проверки зависимостей (schedule)

### Что проверяется

#### Линтинг и безопасность
- **Python:**
  - flake8 - проверка стиля кода
  - black - проверка форматирования
  - isort - проверка сортировки импортов
  - bandit - проверка безопасности кода
  - safety - проверка уязвимостей в зависимостях
- **JavaScript:**
  - ESLint - проверка стиля кода
  - npm audit - проверка уязвимостей в зависимостях

#### Тестирование
- Backend тесты запускаются в Docker окружении
- **Матричное тестирование:** Python 3.10 и 3.11
- Проверяется работоспособность API endpoints
- Результаты тестов сохраняются как артефакты

#### Сборка
- Frontend собирается с **матричным тестированием** (Node 18 и 20)
- Артефакты сохраняются для каждого варианта
- Production Docker образ собирается для проверки
- **Публикация в GHCR:** Docker образы публикуются в GitHub Container Registry
- **Multi-platform:** Поддержка linux/amd64 и linux/arm64

#### Локальное развёртывание
- Проверяется, что `docker-compose.yml` корректно поднимает все сервисы
- Тестируются основные API endpoints после запуска
- **Производительность:** Простые нагрузочные тесты (10 запросов)
- Проверяются логи сервисов
- **Мониторинг ресурсов:** Проверка использования CPU и памяти

#### Валидация конфигураций
- Проверяется синтаксис всех docker-compose файлов:
  - `docker-compose.yml` (production)
  - `docker-compose.dev.yml` (development)
  - `docker-compose.test.yml` (testing)
- Проверка на типичные проблемы в конфигурации

#### Качество кода
- **pylint** - детальный анализ Python кода
- **radon** - анализ сложности кода (cyclomatic complexity)
- Отчёты сохраняются как артефакты

#### Уведомления
- Автоматические уведомления при провале любого job
- Ссылки на детали провала в GitHub Actions

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

### Локальное развёртывание

#### Production режим

```bash
# Сборка и запуск
docker compose build
docker compose up -d

# Проверка работоспособности
curl http://localhost:8000/health

# Остановка
docker compose down
```

#### Development режим (с hot reload)

```bash
# Запуск с hot reload
docker compose -f docker-compose.dev.yml up

# Или обычный docker-compose.yml (тоже с hot reload для API)
docker compose up
```

#### Проверка конфигураций

```bash
# Проверка синтаксиса
docker compose -f docker-compose.yml config
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.test.yml config
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

### Локальное развёртывание

После локального запуска проверьте:

```bash
# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f api

# Статус сервисов
docker compose ps

# Проверка health endpoint
curl http://localhost:8000/health
```

## Troubleshooting

### Тесты не проходят

1. Проверьте логи в GitHub Actions
2. Убедитесь, что все зависимости установлены
3. Проверьте, что Docker контейнеры запускаются корректно

### Локальное развёртывание не работает

1. Проверьте логи: `docker compose logs`
2. Убедитесь, что порты не заняты (8000, 6379)
3. Проверьте, что Docker и Docker Compose установлены
4. Попробуйте пересобрать образы: `docker compose build --no-cache`

### Очистка сессий не работает

1. Проверьте логи приложения: `docker compose logs api | grep cleanup`
2. Убедитесь, что переменные окружения настроены правильно
3. Используйте ручной endpoint для тестирования: `POST /api/admin/cleanup-sessions`

### Docker Compose валидация не проходит

1. Проверьте синтаксис YAML файлов
2. Убедитесь, что все сервисы правильно определены
3. Проверьте, что все используемые образы доступны

## Артефакты

### Сохраняемые артефакты

1. **Frontend Build** - собранный фронтенд для разных версий Node
   - Хранится 1 день
   - Доступен для скачивания

2. **Security Reports** - отчёты безопасности
   - bandit-report.json (Python)
   - npm-audit.json (JavaScript)
   - Хранятся 7 дней

3. **Test Results** - результаты тестов
   - XML/HTML отчёты
   - Coverage отчёты
   - Хранятся 7 дней

4. **Code Quality Reports** - отчёты качества кода
   - pylint-report.json
   - complexity-report.json
   - Хранятся 7 дней

### Доступ к артефактам

1. Перейдите в репозиторий → вкладка "Actions"
2. Выберите нужный workflow run
3. Прокрутите вниз до раздела "Artifacts"
4. Скачайте нужный артефакт

## Кэширование

Workflow использует агрессивное кэширование для ускорения:

- **Python пакеты** - кэшируются через pip cache
- **npm пакеты** - кэшируются через npm cache
- **Docker слои** - кэшируются через GitHub Actions cache (GHA)
- **Docker Buildx** - использует cache-from и cache-to для оптимизации

## Матричное тестирование

### Backend
- Тестируется на Python 3.10 и 3.11
- Гарантирует совместимость с разными версиями

### Frontend
- Собирается на Node 18 и 20
- Проверяет совместимость с разными версиями Node

## Публикация Docker образов

### GitHub Container Registry (GHCR)

Docker образы автоматически публикуются в GHCR:
- **Для push в main/dev:** `ghcr.io/owner/repo/api:branch-name`
- **Для PR:** образы собираются, но не публикуются
- **Multi-platform:** Поддержка AMD64 и ARM64

### Использование опубликованных образов

```bash
# Pull образа
docker pull ghcr.io/DmitryFenix/conversations/api:main

# Использование в docker-compose
# Обновите docker-compose.yml:
# image: ghcr.io/DmitryFenix/conversations/api:main
```

## Ежедневные проверки

Workflow автоматически запускается каждую ночь в 2:00 UTC для:
- Проверки уязвимостей в зависимостях
- Обновления security reports
- Проверки работоспособности после обновлений зависимостей

## Оптимизация производительности

### Параллельность
- Jobs запускаются параллельно где возможно
- `fail-fast: false` позволяет всем матричным вариантам завершиться

### Кэширование
- Все зависимости кэшируются
- Docker слои кэшируются между запусками
- Ускоряет последующие запуски на 50-70%

### Timeouts
- Backend tests: 30 минут
- Local deployment: 10 минут
- Предотвращает зависшие jobs
