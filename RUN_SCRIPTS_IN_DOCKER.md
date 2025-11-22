# Запуск скриптов внутри Docker контейнера

## Проблема

Скрипты требуют зависимости (psycopg2), которые установлены только в Docker контейнере, а не на хосте.

## Решение: Запуск внутри контейнера

### Вариант 1: Через docker compose exec

```bash
# Сбор MR
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json

# Импорт MR
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json
```

### Вариант 2: Через docker compose run (временный контейнер)

```bash
# Сбор MR
docker compose run --rm api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json

# Копируем файл на хост (если нужно)
docker compose cp api:/tmp/mrs_collected.json ./mrs_collected.json

# Импорт MR
docker compose run --rm api python scripts/import_mrs.py /tmp/mrs_collected.json
```

### Вариант 3: Монтирование файлов

```bash
# Сбор MR (результат сохранится в ./mrs_collected.json на хосте)
docker compose run --rm -v $(pwd)/mrs_collected.json:/tmp/mrs_collected.json api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json

# Импорт MR
docker compose run --rm -v $(pwd)/mrs_collected.json:/tmp/mrs_collected.json api python scripts/import_mrs.py /tmp/mrs_collected.json
```

## Рекомендуемый способ

Используйте автоматический скрипт, который уже настроен:

```bash
# Linux/Mac/WSL
./scripts/setup_mr_database.sh

# Windows PowerShell
.\scripts\setup_mr_database.ps1
```

Он автоматически запустит всё внутри Docker.




