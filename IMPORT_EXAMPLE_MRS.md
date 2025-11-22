# Импорт примеров MR в базу данных

## 📋 Что создано

Создан файл `example_mrs.json` с 10 примерами MR разных типов:

1. **Bugfix** (2 балла) - исправление null pointer exception
2. **Feature** (3 балла) - добавление редактирования профиля пользователя
3. **Refactoring** (4 балла) - рефакторинг с dependency injection
4. **Tests** (3 балла) - добавление unit тестов
5. **Performance** (3 балла) - оптимизация запросов к БД
6. **Security** (3 балла) - исправление SQL injection
7. **Feature** (4 балла) - React компонент для dashboard (JavaScript)
8. **Refactoring** (5 баллов) - микросервисная архитектура (Senior level)

## 🚀 Как импортировать

### Вариант 1: Через WSL (если Docker доступен)

```bash
# В WSL
cd /mnt/c/Users/Дмитрий/Downloads/conversations-main/conversations-main/conversations

# Скопировать файл в контейнер
docker compose cp example_mrs.json api:/tmp/example_mrs.json

# Импортировать
docker compose exec api python scripts/import_mrs.py /tmp/example_mrs.json
```

### Вариант 2: Через PowerShell (если Docker Desktop работает)

```powershell
# Скопировать файл в контейнер
docker compose cp example_mrs.json api:/tmp/example_mrs.json

# Импортировать
docker compose exec api python scripts/import_mrs.py /tmp/example_mrs.json
```

### Вариант 3: Создать файл внутри контейнера

```bash
# Войти в контейнер
docker compose exec api bash

# Создать файл (можно скопировать содержимое example_mrs.json)
# Или использовать wget/curl если файл доступен по URL

# Импортировать
python scripts/import_mrs.py /tmp/example_mrs.json
```

## ✅ Проверка импорта

После импорта проверьте статистику:

```bash
docker compose exec api python scripts/check_mr_stats.py
```

Или через API:

```bash
curl http://localhost:8000/api/mr/list
```

## 📊 Что вы увидите

После импорта в базе будет:
- **8 типов MR**: bugfix, feature, refactoring, tests, performance, security
- **Разные уровни сложности**: от 2 до 5 баллов
- **Разные языки**: Python, JavaScript/TypeScript
- **Разные теги стека**: backend, frontend, database, devops

Теперь можно протестировать:
- Фильтрацию по типу
- Рекомендации по грейду
- Поиск по тегам стека
- Выбор MR для сессий

