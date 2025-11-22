# Проверка статистики MR

Миграция применена успешно! Видно в логах:
```
INFO:mr_database:Migration 002_add_mr_classification.sql applied successfully
INFO:mr_database:MR database initialized successfully
```

Теперь можно проверить статистику:

```bash
# В WSL
docker compose exec api python scripts/check_mr_stats.py
```

Если база пуста, нужно собрать MR:

```bash
# 1. Собрать MR из артефактов
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json

# 2. Импортировать в БД
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json

# 3. Проверить статистику
docker compose exec api python scripts/check_mr_stats.py
```




