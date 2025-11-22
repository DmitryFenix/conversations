# Исправление проблемы PostgreSQL в WSL

## Проблема

PostgreSQL не может изменить права доступа к директории:
```
initdb: error: could not change permissions of directory "/var/lib/postgresql/data/pgdata": Operation not permitted
```

## Причина

В WSL/Windows при монтировании директорий через bind mount (`./postgres_data:/var/lib/postgresql/data`) возникают проблемы с правами доступа.

## Решение

Используем **именованный том Docker** вместо bind mount. Это уже исправлено в `docker-compose.yml`.

### Шаг 1: Остановите PostgreSQL

```bash
docker compose down postgres
```

### Шаг 2: Удалите старую директорию (если есть)

```bash
# В WSL
rm -rf postgres_data/

# Или в PowerShell
Remove-Item -Recurse -Force postgres_data
```

### Шаг 3: Запустите PostgreSQL заново

```bash
docker compose up -d postgres
```

Теперь PostgreSQL использует именованный том `postgres_data`, который Docker управляет автоматически.

### Шаг 4: Проверьте статус

```bash
docker compose ps postgres
```

Должно быть: `Up (healthy)`

## Проверка тома

Посмотреть, где хранятся данные:

```bash
docker volume inspect conversations_postgres_data
```

## Если нужно сохранить данные

Если у вас уже были данные в `./postgres_data/`, их можно перенести:

```bash
# 1. Создайте резервную копию
docker compose exec postgres pg_dump -U mr_user mr_database > backup.sql

# 2. После пересоздания тома восстановите
docker compose exec -T postgres psql -U mr_user mr_database < backup.sql
```

Но обычно при первой настройке данных ещё нет, поэтому просто удалите директорию.




