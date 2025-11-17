# Запуск тестов в Docker

## Быстрый старт

### Вариант 1: Одноразовый запуск

```bash
# Запустить все сервисы и тесты
docker compose up -d api redis worker
docker compose run --rm tests
```

### Вариант 2: Используя скрипт

```bash
# Простой запуск
./run_tests.sh

# Непрерывный запуск (watch mode)
./run_tests_continuous.sh
```

### Вариант 3: С отдельным compose файлом

```bash
# Запустить сервисы
docker compose up -d

# Запустить тесты
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm tests
```

## Непрерывный запуск (watch mode)

```bash
# Запускать тесты каждые 10 секунд
TEST_INTERVAL=10 ./run_tests_continuous.sh
```

## Запуск конкретных тестов

```bash
# Только тесты создания сессий
docker compose run --rm tests pytest test_api.py::TestSessionCreation -v

# Только тесты Gitea
docker compose run --rm tests pytest test_api.py::TestGiteaIntegration -v

# С фильтром по имени
docker compose run --rm tests pytest test_api.py -k "session" -v
```

## Преимущества Docker подхода

✅ **Изолированная среда** - тесты запускаются в чистом окружении  
✅ **Доступ к API** - тесты имеют прямой доступ к API через Docker сеть  
✅ **Воспроизводимость** - одинаковые результаты на любой машине  
✅ **CI/CD готовность** - легко интегрировать в CI/CD pipeline  
✅ **Независимость от хоста** - не нужно устанавливать зависимости на хост-машине  

## Структура

- `tests/Dockerfile` - образ для тестов
- `docker-compose.test.yml` - конфигурация для тестов
- `run_tests.sh` - скрипт для запуска
- `run_tests_continuous.sh` - скрипт для непрерывного запуска

## Переменные окружения

- `API_BASE_URL` - URL API (по умолчанию `http://api:8000` внутри Docker сети)
- `TEST_INTERVAL` - интервал между запусками в watch mode (по умолчанию 10 секунд)

