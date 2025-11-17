# Быстрый старт тестов

## Вариант 1: Локальный запуск (если API на localhost:8000)

```bash
# 1. Установите зависимости
pip install -r tests/requirements.txt

# 2. Запустите тесты один раз
pytest tests/test_api.py -v

# 3. Или запустите в непрерывном режиме (каждые 5 секунд)
python tests/run_tests.py
```

## Вариант 2: Запуск из Docker контейнера

```bash
# 1. Убедитесь, что контейнеры запущены
docker compose up -d

# 2. Установите зависимости в контейнере
docker compose exec api pip install -r tests/requirements.txt

# 3. Запустите тесты
docker compose exec api pytest tests/test_api.py -v
```

## Вариант 3: Непрерывный запуск (watch mode)

### Linux/Mac:
```bash
chmod +x run_tests_continuous.sh
./run_tests_continuous.sh
```

### Windows:
```cmd
run_tests_continuous.bat
```

## Настройка

### Изменить интервал между запусками:
```bash
TEST_INTERVAL=10 python tests/run_tests.py  # каждые 10 секунд
```

### Указать другой API URL:
```bash
API_BASE_URL=http://localhost:8000 pytest tests/test_api.py -v
```

## Что проверяют тесты

✅ Создание сессий ревьюером  
✅ Получение списка сессий  
✅ Получение сессии кандидатом  
✅ Добавление комментариев  
✅ Интеграция с Gitea (если включена)  
✅ Синхронизация комментариев из Gitea  
✅ Управление сессиями (завершение, удаление)  
✅ Сигнал готовности кандидата  
✅ Запуск оценки сессии  
✅ Получение артефактов (diff, отчёты)  

## Устранение проблем

### Ошибка: "API is not available"
- Убедитесь, что API сервер запущен
- Проверьте URL в переменной `API_BASE_URL`

### Ошибка: "ModuleNotFoundError: No module named 'pytest'"
- Установите зависимости: `pip install -r tests/requirements.txt`

### Тесты пропускаются (skipped)
- Это нормально, если условия не выполнены (например, Gitea не настроена)
- Тесты автоматически пропускают зависимости, которые не могут быть выполнены

