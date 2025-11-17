# Архитектура Code Review Platform

## Общая схема системы

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Code Review Platform                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼───────┐              ┌───────▼───────┐
            │   Frontend    │              │   Backend      │
            │  (React/Vite) │              │   (FastAPI)    │
            └───────┬───────┘              └───────┬───────┘
                    │                               │
                    │  HTTP/REST API                │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼───────┐              ┌───────▼───────┐
            │   SQLite DB   │              │     Redis     │
            │  (reviews.db) │              │   (Task Queue) │
            └───────────────┘              └───────┬───────┘
                                                    │
                                            ┌───────▼───────┐
                                            │   RQ Worker   │
                                            │  (Eval Worker)│
                                            └───────┬───────┘
                                                    │
                                            ┌───────▼───────┐
                                            │   Gitea       │
                                            │  (Git Server)  │
                                            └───────────────┘
```

## Компоненты системы

### 1. Frontend (React + Vite)

**Технологии:**
- React 19.1.1
- Vite 7.1.7
- React Router 6.31.1
- Monaco Editor (для отображения diff)
- Lucide Icons

**Роуты:**
- `/reviewer` - Dashboard для проверяющего
- `/reviewer/sessions/:id` - Детали сессии
- `/candidate/:token` - Интерфейс кандидата
- `/` - Старый интерфейс (для обратной совместимости)

**Основные компоненты:**
- `ReviewerDashboard.jsx` - Дашборд со списком сессий
- `CandidateView.jsx` - Интерфейс кандидата
- `App.jsx` - Старый интерфейс (legacy)

### 2. Backend (FastAPI)

**Технологии:**
- FastAPI 0.119.1
- Python 3.11.10
- Uvicorn 0.38.0
- WeasyPrint 62.3 (для генерации PDF)

**API Endpoints:**

#### Reviewer API (`/api/reviewer/*`)
- `POST /api/reviewer/sessions` - Создать сессию
- `GET /api/reviewer/sessions` - Список сессий
- `GET /api/reviewer/sessions/{id}` - Детали сессии
- `POST /api/reviewer/sessions/{id}/evaluate` - Запустить оценку
- `POST /api/reviewer/sessions/{id}/extend` - Продлить сессию
- `GET /api/reviewer/sessions/{id}/report` - Текстовый отчёт
- `GET /api/reviewer/sessions/{id}/report/pdf` - PDF отчёт

#### Candidate API (`/api/candidate/*`)
- `GET /api/candidate/sessions/{token}` - Получить сессию по токену
- `GET /api/candidate/sessions/{token}/diff` - Получить diff
- `GET /api/candidate/sessions/{token}/comments` - Получить комментарии
- `POST /api/candidate/sessions/{token}/comments` - Добавить комментарий

#### Legacy API (`/api/sessions/*`)
- Старые endpoints для обратной совместимости

### 3. База данных (SQLite)

**Файл:** `api/reviews.db`

**Таблица `sessions`:**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT,
    candidate_name TEXT,
    reviewer_name TEXT,
    mr_package TEXT,
    comments TEXT,  -- JSON массив комментариев
    created_at TEXT,  -- ISO 8601 с 'Z'
    expires_at TEXT,  -- ISO 8601 с 'Z'
    access_token TEXT UNIQUE,  -- Токен для кандидата
    reviewer_token TEXT,  -- Токен для проверяющего
    status TEXT DEFAULT 'active',
    -- Gitea интеграция
    gitea_user TEXT,
    gitea_repo TEXT,
    gitea_pr_id INTEGER,
    gitea_enabled INTEGER DEFAULT 0
)
```

### 4. Redis + RQ (Task Queue)

**Назначение:**
- Асинхронная обработка задач оценки кода
- Очередь задач для worker'а

**Использование:**
- `queue.enqueue("eval_worker.evaluate", session_id)` - Добавить задачу оценки
- Worker обрабатывает задачи в фоне

### 5. RQ Worker (Eval Worker)

**Файл:** `api/eval_worker.py`

**Функции:**
- `evaluate(session_id)` - Оценка кода кандидата
- Сравнение комментариев с golden truth
- Генерация отчёта (TP, FP, FN, Score, Grade)
- Сохранение отчёта в `/artifacts/{session_id}_report.txt`

### 6. Gitea (Git Server)

**Назначение:**
- Хранение репозиториев для каждой сессии
- Управление пользователями кандидатов
- Pull Requests для code review
- Git workflow

**Интеграция:**
- `GiteaClient` - класс для работы с Gitea REST API
- Автоматическое создание пользователя и репозитория при создании сессии
- Инициализация стартового кода

## Потоки данных

### Создание сессии (Reviewer)

```
Reviewer → POST /api/reviewer/sessions
    ↓
Backend создаёт запись в SQLite
    ↓
Генерирует access_token и reviewer_token
    ↓
Если Gitea включен:
    ├─ Создаёт пользователя candidate_XXX
    ├─ Создаёт репозиторий session_YYY
    └─ Инициализирует стартовый код
    ↓
Возвращает session_id, токены, Gitea URL
```

### Работа кандидата

```
Candidate → GET /api/candidate/sessions/{token}
    ↓
Backend проверяет токен в SQLite
    ↓
Возвращает данные сессии
    ↓
Candidate → GET /api/candidate/sessions/{token}/diff
    ↓
Backend возвращает diff из файла
    ↓
Candidate → POST /api/candidate/sessions/{token}/comments
    ↓
Backend сохраняет комментарий в SQLite
```

### Оценка сессии (Reviewer)

```
Reviewer → POST /api/reviewer/sessions/{id}/evaluate
    ↓
Backend добавляет задачу в Redis Queue
    ↓
RQ Worker обрабатывает задачу:
    ├─ Загружает комментарии из SQLite
    ├─ Загружает golden_truth.json
    ├─ Сравнивает комментарии
    ├─ Вычисляет метрики (TP, FP, FN)
    ├─ Генерирует Score и Grade
    └─ Сохраняет отчёт в файл
    ↓
Reviewer → GET /api/reviewer/sessions/{id}/report
    ↓
Backend возвращает отчёт
```

## Разделение ролей

### Reviewer (Проверяющий)
- ✅ Создаёт сессии
- ✅ Видит список всех сессий
- ✅ Просматривает комментарии кандидата
- ✅ Запускает оценку
- ✅ Просматривает отчёты (текст + PDF)
- ✅ Продлевает сессии
- ✅ Доступ к Gitea репозиториям

### Candidate (Кандидат)
- ✅ Получает доступ по токену
- ✅ Просматривает diff кода
- ✅ Добавляет комментарии
- ✅ Видит таймер сессии
- ❌ НЕ видит отчёты
- ❌ НЕ может продлевать сессию
- ❌ НЕ может создавать сессии

## Безопасность

1. **Токены доступа:**
   - `access_token` - уникальный токен для кандидата (32 байта)
   - `reviewer_token` - токен для проверяющего (24 байта)
   - Генерируются через `secrets.token_urlsafe()`

2. **Проверка доступа:**
   - Candidate API требует валидный `access_token`
   - Reviewer API доступен по `session_id` (без дополнительной авторизации в MVP)

3. **Gitea:**
   - Приватные репозитории
   - Отдельные пользователи для каждого кандидата

## Файловая структура

```
conversations/
├── api/
│   ├── main.py              # FastAPI приложение
│   ├── eval_worker.py       # RQ Worker для оценки
│   ├── gitea_client.py      # Gitea API клиент
│   ├── requirements.txt     # Python зависимости
│   ├── Dockerfile           # Docker образ для API/Worker
│   └── reviews.db           # SQLite база данных
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Legacy компонент
│   │   ├── ReviewerDashboard.jsx
│   │   ├── CandidateView.jsx
│   │   ├── router.jsx       # React Router
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile.dev       # Dev Dockerfile
├── artifacts/               # Генерируемые файлы
│   ├── {session_id}_diff.patch
│   ├── {session_id}_report.txt
│   └── {session_id}_report.pdf
├── mr_packages/             # MR пакеты
├── gitea_data/              # Данные Gitea (volume)
├── gitea_config/            # Конфигурация Gitea (volume)
├── docker-compose.yml       # Production конфигурация
├── docker-compose.dev.yml   # Development конфигурация
└── GITEA_SETUP.md          # Инструкция по настройке Gitea
```

## Порты

- **8000** - FastAPI Backend
- **3000** - Gitea Web UI
- **2222** - Gitea SSH
- **6379** - Redis
- **5173** - Vite Dev Server (только в dev режиме)

## Переменные окружения

### Backend
- `PYTHONUNBUFFERED=1` - Небуферизованный вывод Python
- `GITEA_URL` - URL Gitea (по умолчанию: `http://gitea:3000`)
- `GITEA_ADMIN_TOKEN` - API токен администратора Gitea

### Worker
- `RQ_REDIS_URL` - URL Redis для RQ (по умолчанию: `redis://redis:6379`)

### Frontend (Dev)
- `VITE_API_URL` - URL API (по умолчанию: `http://localhost:8000`)

