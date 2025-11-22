# Исправление: Применение миграции для классификации MR

## Проблема

Ошибка: `column "mr_type" does not exist`

Миграция `002_add_mr_classification.sql` не была применена к базе данных.

## Решение

### Вариант 1: Через скрипт (рекомендуется)

```bash
# В WSL
docker compose exec api python scripts/apply_migration.py
```

### Вариант 2: Через API (автоматически)

Миграция должна применяться автоматически при запуске API через `init_mr_database()`. 

Если не применяется, перезапустите API:

```bash
docker compose restart api
```

### Вариант 3: Вручную через psql

```bash
# В WSL
docker compose exec postgres psql -U mr_user -d mr_database

# Затем выполните SQL:
ALTER TABLE merge_requests 
ADD COLUMN IF NOT EXISTS mr_type TEXT,
ADD COLUMN IF NOT EXISTS complexity_points INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS stack_tags TEXT[];

CREATE INDEX IF NOT EXISTS idx_mr_type ON merge_requests(mr_type);
CREATE INDEX IF NOT EXISTS idx_mr_complexity ON merge_requests(complexity_points);
CREATE INDEX IF NOT EXISTS idx_mr_stack_tags ON merge_requests USING GIN(stack_tags);

UPDATE merge_requests 
SET 
    mr_type = COALESCE(mr_type, 'feature'),
    complexity_points = COALESCE(complexity_points, 3),
    stack_tags = COALESCE(stack_tags, ARRAY[]::TEXT[])
WHERE mr_type IS NULL OR complexity_points IS NULL OR stack_tags IS NULL;
```

## Проверка

После применения миграции проверьте:

```bash
docker compose exec api python scripts/check_mr_stats.py
```

Или через SQL:

```bash
docker compose exec postgres psql -U mr_user -d mr_database -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'merge_requests' AND column_name IN ('mr_type', 'complexity_points', 'stack_tags');"
```

## Почему это произошло

Функция `init_mr_database()` в `api/mr_database.py` должна применять миграции автоматически, но возможно:
1. API не был перезапущен после добавления миграции
2. Миграция не была найдена
3. Ошибка при применении была проигнорирована

## После исправления

После применения миграции:
1. Пересоберите MR с классификацией (если они уже есть в БД без классификации)
2. Или просто соберите новые MR - они будут автоматически классифицированы




