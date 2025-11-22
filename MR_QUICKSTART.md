# Быстрый старт: Система Merge Requests

> 📖 **Для подробной инструкции см. [MR_SETUP_GUIDE.md](MR_SETUP_GUIDE.md)**

## 🚀 Быстрая настройка (5 минут)

### 1. Запуск PostgreSQL
```bash
docker compose up -d postgres
docker compose ps postgres  # Проверка статуса
```

### 2. Сбор MR из существующих данных
```bash
python scripts/collect_mrs.py --artifacts ./artifacts --output mrs_collected.json
```

### 3. Импорт в БД
```bash
# Проверка (dry-run)
python scripts/import_mrs.py mrs_collected.json --dry-run

# Импорт
python scripts/import_mrs.py mrs_collected.json
```

### 4. Проверка
```bash
curl http://localhost:8000/api/mr/list
```

### 5. Использование
```bash
curl -X POST http://localhost:8000/api/reviewer/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "Иван Иванов",
    "mr_package": "demo_package",
    "reviewer_name": "Reviewer",
    "mr_id": 1
  }'
```

## 📚 Дополнительная информация

- **Подробная инструкция**: [MR_SETUP_GUIDE.md](MR_SETUP_GUIDE.md)
- **Описание метрик**: [MR_METRICS.md](MR_METRICS.md)
- **План реализации**: [MR_SYSTEM_PLAN.md](MR_SYSTEM_PLAN.md)

## Структура файлов

```
api/
  ├── mr_database.py          # Модуль для работы с PostgreSQL
  ├── migrations/
  │   └── 001_create_mr_tables.sql  # SQL миграция
  └── main.py                 # API endpoints для MR

scripts/
  ├── collect_mrs.py          # Сбор MR из источников
  └── import_mrs.py           # Импорт в БД

MR_SYSTEM_PLAN.md             # План реализации
MR_METRICS.md                 # Описание метрик
MR_IMPLEMENTATION_SUMMARY.md  # Резюме реализации
```

## Переменные окружения

```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mr_database
POSTGRES_USER=mr_user
POSTGRES_PASSWORD=mr_password
```

## Troubleshooting

### PostgreSQL не запускается
```bash
docker compose logs postgres
```

### Ошибка подключения к БД
Проверьте переменные окружения и убедитесь, что PostgreSQL запущен.

### MR не импортируются
Проверьте логи:
```bash
python scripts/import_mrs.py mrs_collected.json --dry-run
```


