# Быстрый импорт MR

## Проблема

Скрипт требует `psycopg2`, который установлен только в Docker контейнере.

## Решение: Запуск внутри контейнера

### Шаг 1: Сбор MR

```bash
# В WSL
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json
```

### Шаг 2: Импорт MR

```bash
# В WSL
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json
```

### Шаг 3: Проверка

```bash
curl http://localhost:8000/api/mr/list
```

## Альтернатива: Использовать автоматический скрипт

```bash
# В WSL
chmod +x scripts/setup_mr_database.sh
./scripts/setup_mr_database.sh
```

Он сделает всё автоматически.




