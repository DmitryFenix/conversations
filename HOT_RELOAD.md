# Hot Reload - Автоматическое обновление без перезапуска

## Настройка Hot Reload

### Бэкенд (FastAPI)

Hot reload уже настроен в `docker-compose.yml`:
- Исходники монтируются через volumes
- Uvicorn запускается с флагом `--reload`
- Изменения в `api/main.py` и `api/eval_worker.py` применяются автоматически

### Фронтенд (React/Vite)

Есть два варианта:

#### Вариант 1: Использовать dev-сервер Vite отдельно (рекомендуется)

Запустите на хосте (вне Docker):

```bash
cd frontend
npm install
npm run dev
```

Фронтенд будет доступен на `http://localhost:5173` с hot reload.

#### Вариант 2: Использовать Docker для фронтенда

```bash
docker compose -f docker-compose.dev.yml up
```

Это запустит все сервисы, включая dev-сервер фронтенда в Docker.

## Использование

### Текущая конфигурация (только бэкенд с hot reload)

```bash
docker compose up
```

**Что работает:**
- ✅ Изменения в `api/main.py` → автоматическая перезагрузка API
- ✅ Изменения в `api/eval_worker.py` → перезагрузка worker (нужен рестарт worker)
- ❌ Изменения во фронтенде → нужна пересборка

### Полный hot reload (бэкенд + фронтенд)

**Вариант A: Фронтенд на хосте**

1. Запустите Docker:
```bash
docker compose up
```

2. В отдельном терминале запустите фронтенд:
```bash
cd frontend
npm run dev
```

**Вариант B: Фронтенд в Docker**

```bash
docker compose -f docker-compose.dev.yml up
```

## Что обновляется автоматически

### Бэкенд (FastAPI)
- ✅ `api/main.py` - изменения применяются сразу
- ✅ `api/eval_worker.py` - изменения видны после перезапуска worker

### Фронтенд (React)
- ✅ Все файлы в `frontend/src/` - обновляются через Vite HMR
- ✅ `frontend/index.html` - обновляется автоматически
- ✅ CSS файлы - обновляются автоматически

## Примечания

1. **Worker перезагрузка**: Worker не перезагружается автоматически при изменении `eval_worker.py`. Для применения изменений:
   ```bash
   docker compose restart worker
   ```

2. **База данных**: Изменения в структуре БД требуют миграций или пересоздания контейнера.

3. **Зависимости**: При добавлении новых Python-пакетов или npm-пакетов нужно пересобрать образ:
   ```bash
   docker compose build
   docker compose up
   ```

4. **Порты**:
   - API: `http://localhost:8000`
   - Frontend dev: `http://localhost:5173` (если запущен отдельно)

## Отладка

Если hot reload не работает:

1. Проверьте, что volumes правильно смонтированы:
   ```bash
   docker compose exec api ls -la /app/main.py
   ```

2. Проверьте логи:
   ```bash
   docker compose logs -f api
   ```

3. Убедитесь, что файлы изменяются на хосте (не только в контейнере)




