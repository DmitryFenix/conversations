# Исправление проблемы с RQ Dashboard

## Проблема
Ошибка: `No module named 'rq_dashboard'`

## Причина
Контейнер был запущен до создания файла `rq_dashboard.py`, поэтому файл не был подхвачен.

## Решение

### Вариант 1: Перезапуск контейнера (быстро)
```bash
docker compose restart api
```

### Вариант 2: Полный перезапуск (если первый не помог)
```bash
docker compose down
docker compose up -d api redis worker
```

### Вариант 3: Проверка файла в контейнере
```bash
# Проверить, что файл есть
docker compose exec api ls -la /app/rq_dashboard.py

# Проверить импорт
docker compose exec api python -c "import rq_dashboard; print('OK')"
```

## После перезапуска

Проверьте логи:
```bash
docker compose logs api | grep -i "rq\|dashboard"
```

Должно быть:
```
INFO:main:Attempting to import rq_dashboard...
INFO:main:Router imported: prefix=/api/rq, routes count=3
INFO:main:RQ monitoring dashboard enabled at /api/rq/*
INFO:main:RQ routes registered: ['/api/rq/stats', '/api/rq/jobs/recent', '/api/rq/jobs/{job_id}']
```

Затем проверьте endpoint:
```bash
curl http://localhost:8000/api/rq/stats
```


