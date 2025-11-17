# Настройка внешнего мониторинга RQ

RQ Dashboard запускается как **внешний сервис**, отдельно от основного приложения. Это позволяет легко включать/отключать мониторинг без изменения основного `docker-compose.yml`.

## Быстрый старт

```bash
# 1. Запустите основное приложение
docker compose up -d

# 2. Запустите мониторинг
docker compose -f docker-compose.monitoring.yml up -d

# 3. Откройте в браузере
# http://localhost:9181
```

## Определение имени сети

Docker Compose автоматически создаёт сеть с именем `<имя_проекта>_default`. 

### Автоматическое определение

Если ваш проект находится в папке `conversations`, имя проекта обычно `conversations`, и сеть будет `conversations_default`.

### Ручное указание имени проекта

Если нужно указать имя проекта явно:

```bash
docker compose -p conversations -f docker-compose.monitoring.yml up -d
```

### Проверка имени сети

```bash
# Посмотреть все сети
docker network ls

# Найти сеть основного приложения
docker compose ps
# Или
docker network inspect $(docker compose config | grep -A 5 networks | grep name | head -1 | awk '{print $2}')
```

### Изменение имени сети в docker-compose.monitoring.yml

Если имя сети отличается от `conversations_default`, откройте `docker-compose.monitoring.yml` и измените:

```yaml
networks:
  main_network:
    name: ваше_имя_сети_default  # Измените здесь
    external: true
```

## Альтернативный способ: использование host сети

Если возникают проблемы с подключением к сети, можно использовать host сеть (только для Linux):

```yaml
services:
  rq-dashboard:
    network_mode: host
    # И измените redis URL на localhost:6379
    command: >
      sh -c "
      pip install --no-cache-dir rq-dashboard==0.6.1 &&
      rq-dashboard --redis-url redis://localhost:6379 --host 0.0.0.0 --port 9181
      "
```

⚠️ **Внимание**: Host network mode не работает в Docker Desktop для Windows/Mac.

## Проверка подключения

```bash
# Проверить, что контейнер запущен
docker compose -f docker-compose.monitoring.yml ps

# Проверить логи
docker compose -f docker-compose.monitoring.yml logs rq-dashboard

# Проверить подключение к Redis из контейнера мониторинга
docker compose -f docker-compose.monitoring.yml exec rq-dashboard ping -c 1 redis
```

## Остановка

```bash
# Остановить только мониторинг
docker compose -f docker-compose.monitoring.yml down

# Остановить всё (включая основное приложение)
docker compose down
docker compose -f docker-compose.monitoring.yml down
```

## Troubleshooting

### Ошибка: network not found

```
ERROR: Network conversations_default declared as external, but could not be found
```

**Решение**: Убедитесь, что основное приложение запущено:
```bash
docker compose up -d
```

Или измените имя сети в `docker-compose.monitoring.yml` на правильное.

### Dashboard не подключается к Redis

**Решение**: Проверьте, что Redis доступен в сети:
```bash
# Проверить, что Redis запущен
docker compose ps redis

# Проверить сеть
docker network inspect conversations_default | grep redis
```

### Порт 9181 уже занят

**Решение**: Измените порт в `docker-compose.monitoring.yml`:
```yaml
ports:
  - "9182:9181"  # Используйте другой внешний порт
```

