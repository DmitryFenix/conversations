# Устранение проблем с RQ Dashboard

Если Dashboard не открывается (ERR_EMPTY_RESPONSE), выполните следующие шаги:

## ⚠️ Важно: Проблемы совместимости версий

### Ошибка 1: `ImportError: cannot import name 'pop_connection' from 'rq'`

Это означает, что `rq-dashboard==0.6.1` несовместим с `rq==2.6.0`. 

**Решение**: В `docker-compose.monitoring.yml` используется старая версия RQ (1.15.1) для совместимости.

### Ошибка 2: `AttributeError: 'Blueprint' object has no attribute 'before_app_first_request'`

Это означает, что `rq-dashboard==0.6.1` несовместим с Flask 3.x.

**Решение**: В конфигурации уже установлена совместимая версия Flask (`Flask<3.0`). Если проблема сохраняется, используйте API endpoints мониторинга (см. ниже).

## Проблема: Контейнер завершается с кодом 0

Если контейнер постоянно перезапускается (`exited with code 0`):

1. **Проверьте логи**:
   ```bash
   docker compose -f docker-compose.monitoring.yml logs rq-dashboard
   ```

2. **Попробуйте альтернативную конфигурацию**:
   ```bash
   docker compose -f docker-compose.monitoring.yml down
   docker compose -f docker-compose.monitoring-fallback.yml up -d
   ```

3. **Или используйте API endpoints** (рекомендуется):
   ```bash
   # API endpoints работают всегда
   curl http://localhost:8000/api/rq/stats
   ```

## Шаг 1: Проверка основного приложения

Убедитесь, что основное приложение запущено:

```bash
docker compose ps
```

Должны быть запущены:
- `api`
- `redis`
- `worker`

Если не запущены:
```bash
docker compose up -d
```

## Шаг 2: Проверка имени сети

Узнайте имя сети основного приложения:

```bash
# PowerShell
docker network ls | Select-String "conversations"

# Или через WSL
wsl docker network ls | grep conversations
```

Обычно это `conversations_default` или `<имя_папки>_default`.

## Шаг 3: Обновление docker-compose.monitoring.yml

Если имя сети отличается от `conversations_default`, откройте `docker-compose.monitoring.yml` и измените:

```yaml
networks:
  main_network:
    name: ваше_реальное_имя_сети_default  # Измените здесь
    external: true
```

## Шаг 4: Запуск RQ Dashboard

```bash
# Запустить Dashboard
docker compose -f docker-compose.monitoring.yml up -d

# Проверить статус
docker compose -f docker-compose.monitoring.yml ps
```

## Шаг 5: Проверка логов

Если контейнер не запускается, проверьте логи:

```bash
docker compose -f docker-compose.monitoring.yml logs rq-dashboard
```

### Типичные ошибки:

**Ошибка: Network not found**
```
ERROR: Network conversations_default declared as external, but could not be found
```

**Решение**: Убедитесь, что основное приложение запущено:
```bash
docker compose up -d
```

**Ошибка: Cannot connect to Redis**
```
ConnectionError: Error connecting to Redis
```

**Решение**: Проверьте, что Redis доступен:
```bash
docker compose ps redis
docker compose exec redis redis-cli ping
```

## Шаг 6: Альтернативный способ запуска

Если проблемы с сетью продолжаются, можно использовать прямой доступ к Redis через localhost:

### Вариант A: Изменить docker-compose.monitoring.yml

Измените команду запуска:

```yaml
services:
  rq-dashboard:
    image: python:3.11.10-slim
    container_name: rq-dashboard
    network_mode: "host"  # Использовать host сеть
    command: >
      sh -c "
      pip install --no-cache-dir rq-dashboard==0.6.1 &&
      rq-dashboard --redis-url redis://localhost:6379 --host 0.0.0.0 --port 9181
      "
    environment:
      - PYTHONUNBUFFERED=1
```

⚠️ **Внимание**: Host network mode работает только на Linux. В Windows/Mac используйте вариант B.

### Вариант B: Использовать host.docker.internal (Windows/Mac)

```yaml
services:
  rq-dashboard:
    image: python:3.11.10-slim
    container_name: rq-dashboard
    command: >
      sh -c "
      pip install --no-cache-dir rq-dashboard==0.6.1 &&
      rq-dashboard --redis-url redis://host.docker.internal:6379 --host 0.0.0.0 --port 9181
      "
    ports:
      - "9181:9181"
    environment:
      - PYTHONUNBUFFERED=1
```

## Шаг 7: Проверка порта

Убедитесь, что порт 9181 не занят:

```bash
# Windows PowerShell
netstat -ano | findstr :9181

# WSL/Linux
netstat -tuln | grep 9181
```

Если порт занят, измените в `docker-compose.monitoring.yml`:

```yaml
ports:
  - "9182:9181"  # Используйте другой порт
```

## Шаг 8: Полная переустановка

Если ничего не помогает:

```bash
# Остановить и удалить контейнер
docker compose -f docker-compose.monitoring.yml down

# Удалить образ (если нужно)
docker rmi python:3.11.10-slim

# Запустить заново
docker compose -f docker-compose.monitoring.yml up -d

# Проверить логи
docker compose -f docker-compose.monitoring.yml logs -f rq-dashboard
```

## Быстрая диагностика (PowerShell скрипт)

Запустите `check_monitoring.ps1`:

```powershell
.\check_monitoring.ps1
```

Скрипт покажет:
- Статус основного приложения
- Статус RQ Dashboard
- Доступные сети
- Логи Dashboard
- Информацию о контейнере

## Проверка работоспособности

После успешного запуска:

1. **Проверьте контейнер**:
   ```bash
   docker ps | Select-String "rq-dashboard"
   ```

2. **Проверьте логи** (должны быть без ошибок):
   ```bash
   docker compose -f docker-compose.monitoring.yml logs rq-dashboard | Select-String -Pattern "error|Error|ERROR" -NotMatch
   ```

3. **Откройте в браузере**:
   ```
   http://localhost:9181
   ```

## Если Dashboard всё равно не работает

### Используйте API endpoints мониторинга (рекомендуется)

API endpoints работают всегда и не требуют отдельного сервиса:

```bash
# Статистика очереди
curl http://localhost:8000/api/rq/stats

# Метрики производительности
curl http://localhost:8000/api/rq/performance?hours=1

# Тренды
curl http://localhost:8000/api/rq/performance/trends

# Сравнение периодов
curl http://localhost:8000/api/rq/performance/compare
```

Или откройте в браузере:
- http://localhost:8000/api/rq/stats
- http://localhost:8000/api/rq/performance?hours=24

### Альтернатива: Использовать старую версию RQ для Dashboard

Если нужен именно веб-интерфейс Dashboard, можно использовать отдельную версию RQ:

```yaml
command: >
  sh -c "
  pip install --no-cache-dir 'rq==1.15.1' 'rq-dashboard==0.6.1' &&
  rq-dashboard --redis-url redis://redis:6379 --host 0.0.0.0 --port 9181
  "
```

⚠️ **Внимание**: Это создаст несовместимость версий RQ между основным приложением и Dashboard, но Dashboard будет работать.

