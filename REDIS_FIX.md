# Исправление проблемы Redis

## Проблема

Redis 7.2 не может загрузить старый RDB файл с версией формата 12:
```
Can't handle RDB format version 12
Error reading the RDB base file appendonly.aof.1.base.rdb, AOF loading aborted
```

## Решение

### Вариант 1: Автоматическая очистка (уже применено)

Конфигурация Redis теперь автоматически удаляет старые файлы при запуске:
```yaml
command: >
  sh -c "
  echo 1 > /proc/sys/vm/overcommit_memory 2>/dev/null || true &&
  rm -f /data/appendonly.aof* /data/dump.rdb 2>/dev/null || true &&
  redis-server --appendonly no --save '' --maxmemory-policy noeviction
  "
```

### Вариант 2: Ручная очистка volumes

Если проблема сохраняется, удалите volumes вручную:

**В WSL:**
```bash
wsl docker compose down -v
wsl docker compose up -d
```

**В PowerShell:**
```powershell
docker compose down -v
docker compose up -d
```

### Вариант 3: Удаление только Redis volume

Если нужно сохранить другие данные:

```bash
# Найти volume Redis
docker volume ls | grep redis

# Удалить конкретный volume
docker volume rm <volume_name>
```

## Проверка

После исправления Redis должен запуститься без ошибок:

```bash
docker compose logs redis
```

Должно быть:
```
Redis is starting
Server initialized
Ready to accept connections
```

## Примечание

- AOF отключен (`--appendonly no`) - данные Redis не сохраняются между перезапусками
- Это нормально для очереди задач (RQ) - задачи можно перезапустить
- Если нужна персистентность, можно включить AOF после очистки старых файлов

