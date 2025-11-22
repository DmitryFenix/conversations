# Проверка статистики MR

## Как проверить статистику MR

### Вариант 1: Через скрипт (в Docker)

```bash
# В WSL или Linux
docker compose exec api python scripts/check_mr_stats.py

# Или через PowerShell (если Docker доступен)
wsl docker compose exec api python scripts/check_mr_stats.py
```

### Вариант 2: Через API

```bash
# Общее количество
curl "http://localhost:8000/api/mr/list?limit=1" | jq '.total'

# По типам (через фильтры)
curl "http://localhost:8000/api/mr/list?mr_type=bugfix" | jq '.total'
curl "http://localhost:8000/api/mr/list?mr_type=feature" | jq '.total'
curl "http://localhost:8000/api/mr/list?mr_type=security" | jq '.total'
# и т.д.
```

### Вариант 3: Прямой SQL запрос

```bash
docker compose exec postgres psql -U mr_user -d mr_database -c "
SELECT 
    mr_type,
    COUNT(*) as count,
    AVG(complexity_points) as avg_points
FROM merge_requests
GROUP BY mr_type
ORDER BY count DESC;
"
```

## Откуда берутся MR

MR собираются из двух источников:

1. **Локальные Git репозитории** (`scripts/collect_mrs.py`):
   - Анализирует коммиты в указанных репозиториях
   - Извлекает diff и метаданные
   - Автоматически классифицирует по типу, баллам и тегам

2. **Артефакты сессий** (`/artifacts/*_diff.patch`):
   - Использует существующие diff файлы из предыдущих сессий
   - Классифицирует их как отдельные MR

## Принцип классификации

1. **Тип MR** определяется по ключевым словам в title, description, diff:
   - `bugfix` - bug, fix, error, null, exception
   - `feature` - feature, new, add, implement
   - `refactoring` - refactor, architecture, design pattern
   - `tests` - test, spec, coverage, mock
   - `performance` - performance, optimization, slow
   - `security` - security, vulnerability, injection
   - `infrastructure` - docker, kubernetes, ci/cd
   - `code_style` - style, format, lint, readability

2. **Баллы сложности** (1-5) вычисляются на основе:
   - Размера (файлы, строки)
   - Типа MR
   - Сложности кода

3. **Теги стека** определяются по:
   - Языку программирования
   - Ключевым словам (backend, frontend, devops)

## Если база пуста

Если статистика показывает 0 MR, выполните сбор:

```bash
# 1. Собрать MR
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json

# 2. Импортировать в БД
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json

# 3. Проверить статистику
docker compose exec api python scripts/check_mr_stats.py
```




