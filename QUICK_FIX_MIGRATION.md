# Быстрое исправление: Применить миграцию

## Проблема
Колонки `mr_type`, `complexity_points`, `stack_tags` не существуют в таблице `merge_requests`.

## Решение

### Вариант 1: Перезапустить API (автоматически применит миграцию)

```bash
# В WSL
docker compose restart api
```

Функция `init_mr_database()` теперь применяет все миграции автоматически при старте API.

### Вариант 2: Применить вручную через скрипт

```bash
# В WSL
docker compose exec api python scripts/apply_migration.py
```

### Вариант 3: Через psql напрямую

```bash
# В WSL
docker compose exec postgres psql -U mr_user -d mr_database

# Затем выполните:
ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS mr_type TEXT;
ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS complexity_points INTEGER DEFAULT 3;
ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS stack_tags TEXT[];
```

## Проверка

После применения проверьте:

```bash
docker compose exec api python scripts/check_mr_stats.py
```

## Что изменилось

Обновлена функция `init_mr_database()` в `api/mr_database.py` - теперь она применяет все миграции:
- `001_create_mr_tables.sql`
- `002_add_mr_classification.sql`




