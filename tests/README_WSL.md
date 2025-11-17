# Запуск тестов через WSL

## Быстрый старт

```bash
# В WSL терминале
./run_tests_wsl.sh
```

## Что делает скрипт

1. Проверяет доступность Docker
2. Запускает необходимые сервисы (api, redis, worker)
3. Запускает все тесты в Docker контейнере
4. Выводит результаты

## Ручной запуск

```bash
# 1. Убедитесь, что сервисы запущены
docker compose up -d api redis worker

# 2. Запустите тесты
docker compose run --rm -e API_BASE_URL=http://api:8000 tests
```

## Запуск конкретных тестов

```bash
# Только основные тесты
docker compose run --rm -e API_BASE_URL=http://api:8000 tests pytest test_api.py -v

# Только расширенные тесты
docker compose run --rm -e API_BASE_URL=http://api:8000 tests pytest test_api_extended.py -v

# Только тесты RQ мониторинга
docker compose run --rm -e API_BASE_URL=http://api:8000 tests pytest test_rq_monitoring.py -v

# Все тесты
docker compose run --rm -e API_BASE_URL=http://api:8000 tests pytest test_api.py test_api_extended.py test_rq_monitoring.py -v
```

## Преимущества WSL

✅ Нативная поддержка Linux команд  
✅ Прямой доступ к Docker  
✅ Нет проблем с кодировкой  
✅ Быстрая работа с файловой системой  

## Устранение проблем

### Docker не доступен
```bash
# Проверьте, что Docker запущен
sudo service docker start

# Или через systemd
sudo systemctl start docker
```

### Контейнеры не запускаются
```bash
# Проверьте логи
docker compose logs api

# Пересоберите образы
docker compose build
```

### Тесты не находят API
```bash
# Убедитесь, что API доступен
curl http://localhost:8000/api/reviewer/sessions

# Проверьте переменную окружения
docker compose run --rm -e API_BASE_URL=http://api:8000 tests env | grep API_BASE_URL
```


