# Исправление проблемы с модулем mr_database

## Проблема

```
WARNING:main:MR database module not available: No module named 'mr_database'
```

## Решение

Файл `api/mr_database.py` добавлен в Dockerfile, но нужно пересобрать образ **без кэша**:

```bash
# В WSL
docker compose build --no-cache api
docker compose restart api
```

Или если хотите пересобрать только изменённые слои:

```bash
docker compose build api
docker compose restart api
```

## Проверка

После перезапуска проверьте логи:

```bash
docker compose logs api | grep -i "mr database"
```

Должно быть: `MR database module loaded successfully`

## Если всё ещё не работает

Проверьте, что файл существует:

```bash
# В WSL
ls -la api/mr_database.py
```

Если файла нет, он должен быть создан. Проверьте, что он в репозитории.

## Альтернативное решение

Если файл монтируется через volume в docker-compose, он должен быть доступен сразу. Проверьте монтирование:

```yaml
volumes:
  - ./api/mr_database.py:/app/mr_database.py
```

Это уже добавлено в docker-compose.yml, так что после перезапуска должно работать.




