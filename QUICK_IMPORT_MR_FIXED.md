# Исправленный способ импорта MR

## Проблема решена!

Добавлено монтирование директории `scripts` в docker-compose.yml.

## Теперь выполните:

### Шаг 1: Перезапустите API (чтобы применить изменения)

```bash
# В WSL
docker compose restart api
```

### Шаг 2: Сбор MR

```bash
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json
```

### Шаг 3: Импорт MR

```bash
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json
```

### Шаг 4: Проверка

```bash
curl http://localhost:8000/api/mr/list
```

## Альтернатива: Использовать автоматический скрипт

```bash
# В WSL
chmod +x scripts/setup_mr_database.sh
./scripts/setup_mr_database.sh
```

Он автоматически запустит всё внутри Docker.




