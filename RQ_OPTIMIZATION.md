# Оптимизация RQ задач

## Что реализовано

### 1. Мониторинг RQ (`api/rq_monitor.py`)

**Класс `RQMonitor`:**
- ✅ Статистика очереди (queued, started, finished, failed, deferred, scheduled)
- ✅ Детальная информация о задачах (статус, время выполнения, результат)
- ✅ Список недавних задач
- ✅ Логирование событий (enqueued, started, finished, failed)

**Методы:**
- `get_queue_stats()` - статистика очереди
- `get_job_info(job_id)` - детали задачи
- `get_recent_jobs(limit)` - недавние задачи
- `log_job_*()` - логирование событий

### 2. Оптимизированная очередь (`api/rq_monitor.py`)

**Класс `OptimizedQueue`:**
- ✅ Настраиваемые таймауты (в зависимости от приоритета)
- ✅ Автоматические retry (по умолчанию 2 попытки)
- ✅ Приоритеты задач (high, normal, low)
- ✅ TTL для результатов и ошибок
- ✅ Интеграция с мониторингом

**Метод `enqueue_evaluation()`:**
```python
job = opt_queue.enqueue_evaluation(
    session_id,
    timeout=300,  # 5 минут
    retry=2,      # 2 попытки
    priority="normal"  # normal, high, low
)
```

### 3. Dashboard API (`api/rq_dashboard.py`)

**Endpoints:**
- `GET /api/rq/stats` - статистика очереди
- `GET /api/rq/jobs/recent?limit=10` - недавние задачи
- `GET /api/rq/jobs/{job_id}` - детали задачи

### 4. Интеграция в main.py

Автоматически используется оптимизированная очередь для всех задач оценки:
- `POST /api/reviewer/sessions/{session_id}/evaluate`
- `GET /api/sessions/{session_id}/evaluate` (legacy)

## Использование

### Мониторинг через API

```bash
# Статистика очереди
curl http://localhost:8000/api/rq/stats

# Недавние задачи
curl http://localhost:8000/api/rq/jobs/recent?limit=10

# Детали задачи
curl http://localhost:8000/api/rq/jobs/{job_id}
```

### Логирование

Все события автоматически логируются:
```
INFO: Job enqueued: id=abc123, session_id=42, queue=default, timeout=300
INFO: Job started: id=abc123, queued_for=0.5s
INFO: Job finished: id=abc123, duration=12.34s
ERROR: Job failed: id=abc123, error=...
```

## Оптимизации

### 1. Таймауты
- **High priority**: максимум 10 минут
- **Normal priority**: 5 минут (по умолчанию)
- **Low priority**: минимум 3 минуты

### 2. Retry
- По умолчанию 2 попытки
- Автоматический retry при ошибках
- Логирование всех попыток

### 3. TTL
- Результаты хранятся 1 час
- Ошибки хранятся 24 часа
- Экономия памяти Redis

### 4. Мониторинг
- Отслеживание времени в очереди
- Отслеживание времени выполнения
- Статистика успешных/неудачных задач

## Тесты

Созданы тесты в `tests/test_rq_monitoring.py`:
- Получение статистики
- Получение списка задач
- Получение деталей задачи

## Следующие шаги

1. ✅ Мониторинг - реализовано
2. ✅ Оптимизация - реализовано
3. ⏳ Приоритетные очереди (high/normal/low)
4. ⏳ Rate limiting
5. ⏳ Batch processing
6. ⏳ Web UI для мониторинга


