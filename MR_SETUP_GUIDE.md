# Подробная инструкция по настройке системы Merge Requests

> ⚡ **Быстрый старт:** Используйте автоматический скрипт `scripts/setup_mr_database.sh` (Linux/Mac) или `scripts/setup_mr_database.ps1` (Windows). См. [MR_AUTO_SETUP.md](MR_AUTO_SETUP.md)

## 📋 Содержание
1. [Автоматическая настройка (рекомендуется)](#автоматическая-настройка-рекомендуется)
2. [Предварительные требования](#предварительные-требования)
3. [Шаг 1: Запуск PostgreSQL](#шаг-1-запуск-postgresql)
4. [Шаг 2: Проверка подключения](#шаг-2-проверка-подключения)
5. [Шаг 3: Сбор Merge Requests](#шаг-3-сбор-merge-requests)
6. [Шаг 4: Импорт в базу данных](#шаг-4-импорт-в-базу-данных)
7. [Шаг 5: Проверка данных](#шаг-5-проверка-данных)
8. [Шаг 6: Использование в сессиях](#шаг-6-использование-в-сессиях)
9. [Решение проблем](#решение-проблем)

## Автоматическая настройка (рекомендуется)

**Просто запустите один скрипт:**

```bash
# Linux/Mac/WSL
chmod +x scripts/setup_mr_database.sh
./scripts/setup_mr_database.sh

# Windows PowerShell
.\scripts\setup_mr_database.ps1
```

Скрипт автоматически:
- ✅ Проверит и запустит PostgreSQL (если нужно)
- ✅ Соберёт MR из ваших `./artifacts/*_diff.patch`
- ✅ Импортирует их в базу данных
- ✅ Покажет статистику

**Время:** ~2-3 минуты

Подробнее: [MR_AUTO_SETUP.md](MR_AUTO_SETUP.md)

---

## Предварительные требования

Убедитесь, что у вас установлено:
- ✅ Docker и Docker Compose
- ✅ Python 3.10+ (для скриптов)
- ✅ Git (для сбора из репозиториев)

---

## Шаг 1: Запуск PostgreSQL

### 1.1. Запустите PostgreSQL контейнер

```bash
docker compose up -d postgres
```

Эта команда:
- Создаст контейнер PostgreSQL
- Настроит базу данных `mr_database`
- Создаст пользователя `mr_user` с паролем `mr_password`
- Сохранит данные в `./postgres_data/` (не коммитится в Git)

### 1.2. Проверьте статус

```bash
docker compose ps postgres
```

Должно быть:
```
NAME              STATUS          PORTS
postgres_mr       Up (healthy)    0.0.0.0:5432->5432/tcp
```

### 1.3. Проверьте логи (если есть проблемы)

```bash
docker compose logs postgres
```

---

## Шаг 2: Проверка подключения

### 2.1. Запустите API сервер

```bash
docker compose up -d api
```

Или если уже запущен:
```bash
docker compose restart api
```

### 2.2. Проверьте логи API

```bash
docker compose logs api | grep -i "mr database"
```

Должно быть сообщение:
```
MR database module loaded successfully
```

Если видите предупреждение:
```
MR database module not available: ...
```

Проверьте:
1. PostgreSQL запущен и здоров
2. Переменные окружения установлены правильно

### 2.3. Проверьте переменные окружения

В `docker-compose.yml` должны быть:
```yaml
environment:
  - POSTGRES_HOST=postgres
  - POSTGRES_PORT=5432
  - POSTGRES_DB=mr_database
  - POSTGRES_USER=mr_user
  - POSTGRES_PASSWORD=mr_password
```

---

## Шаг 3: Сбор Merge Requests

### 3.1. Сбор из существующих artifacts

У вас уже есть diff файлы в папке `./artifacts/`. Соберём из них MR:

```bash
python scripts/collect_mrs.py --artifacts ./artifacts --output mrs_collected.json
```

**Что делает скрипт:**
- Находит все файлы `*_diff.patch` в `./artifacts/`
- Анализирует каждый diff:
  - Подсчитывает изменённые файлы
  - Подсчитывает добавленные/удалённые строки
  - Определяет язык программирования
  - Вычисляет сложность
  - Классифицирует по уровню (beginner/intermediate/advanced)
- Сохраняет результат в `mrs_collected.json`

**Пример вывода:**
```
INFO: Collected MR from artifact: 1_diff.patch (complexity: 25.5)
INFO: Collected MR from artifact: 2_diff.patch (complexity: 45.2)
...
INFO: Total collected: 15 MRs
INFO: Languages: {'python': 10, 'javascript': 3, 'unknown': 2}
INFO: Difficulty levels: {'beginner': 5, 'intermediate': 7, 'advanced': 3}
```

### 3.2. Сбор из локального Git репозитория (опционально)

Если у вас есть локальный репозиторий с интересными коммитами:

```bash
python scripts/collect_mrs.py --repo /path/to/your/repo --limit 20 --output mrs_from_repo.json
```

**Параметры:**
- `--repo` - путь к репозиторию
- `--limit` - максимальное количество коммитов (по умолчанию 10)
- `--output` - файл для сохранения

### 3.3. Объединение нескольких источников

Можно собрать из нескольких источников и объединить:

```bash
# Собираем из artifacts
python scripts/collect_mrs.py --artifacts ./artifacts --output mrs_artifacts.json

# Собираем из репозитория
python scripts/collect_mrs.py --repo ./some-repo --output mrs_repo.json

# Объединяем (вручную или скриптом)
python -c "
import json
with open('mrs_artifacts.json') as f1, open('mrs_repo.json') as f2:
    all_mrs = json.load(f1) + json.load(f2)
    with open('mrs_all.json', 'w') as out:
        json.dump(all_mrs, out, indent=2, ensure_ascii=False)
"
```

---

## Шаг 4: Импорт в базу данных

### 4.1. Проверка данных (dry-run)

Перед импортом проверьте данные:

```bash
python scripts/import_mrs.py mrs_collected.json --dry-run
```

**Что делает:**
- Проверяет подключение к PostgreSQL
- Валидирует структуру данных
- Показывает, сколько MR будет импортировано
- **НЕ импортирует** данные (безопасно)

**Пример вывода:**
```
INFO: Loaded 15 MRs from mrs_collected.json
INFO: [DRY RUN] Would import MR 1/15: Code Review Session #1...
INFO: [DRY RUN] Would import MR 2/15: Code Review Session #2...
...
INFO: Import complete: 15 imported, 0 skipped, 0 errors
```

### 4.2. Реальный импорт

Если всё хорошо, импортируйте:

```bash
python scripts/import_mrs.py mrs_collected.json
```

**Что делает:**
- Подключается к PostgreSQL
- Создаёт таблицы (если ещё не созданы)
- Импортирует каждый MR
- Сохраняет diff в БД
- Выводит статистику

**Пример вывода:**
```
INFO: Loaded 15 MRs from mrs_collected.json
INFO: Imported MR 1/15: ID=1, Code Review Session #1...
INFO: Imported MR 2/15: ID=2, Code Review Session #2...
...
INFO: Import complete: 15 imported, 0 skipped, 0 errors
```

### 4.3. Если есть ошибки

Если некоторые MR не импортировались:
- Проверьте логи на ошибки
- Убедитесь, что PostgreSQL запущен
- Проверьте формат JSON файла

---

## Шаг 5: Проверка данных

### 5.1. Проверка через API

#### Получить список всех MR:
```bash
curl http://localhost:8000/api/mr/list
```

**Ответ:**
```json
{
  "merge_requests": [
    {
      "id": 1,
      "title": "Code Review Session #1",
      "language": "python",
      "difficulty_level": "beginner",
      "complexity_score": 25.5,
      ...
    },
    ...
  ],
  "total": 15
}
```

#### Фильтрация по языку:
```bash
curl "http://localhost:8000/api/mr/list?language=python"
```

#### Фильтрация по уровню сложности:
```bash
curl "http://localhost:8000/api/mr/list?difficulty_level=intermediate"
```

#### Комбинированная фильтрация:
```bash
curl "http://localhost:8000/api/mr/list?language=python&difficulty_level=intermediate&min_complexity=30&max_complexity=70"
```

#### Получить детали конкретного MR:
```bash
curl http://localhost:8000/api/mr/1
```

#### Получить diff:
```bash
curl http://localhost:8000/api/mr/1/diff
```

#### Полнотекстовый поиск:
```bash
curl "http://localhost:8000/api/mr/search?q=security"
```

### 5.2. Проверка через PostgreSQL (опционально)

Если хотите проверить напрямую в БД:

```bash
docker compose exec postgres psql -U mr_user -d mr_database
```

В psql:
```sql
-- Количество MR
SELECT COUNT(*) FROM merge_requests;

-- Список MR с метриками
SELECT id, title, language, difficulty_level, complexity_score 
FROM merge_requests 
ORDER BY complexity_score DESC;

-- Статистика по языкам
SELECT language, COUNT(*) 
FROM merge_requests 
GROUP BY language;

-- Статистика по уровням сложности
SELECT difficulty_level, COUNT(*) 
FROM merge_requests 
GROUP BY difficulty_level;

-- Выход
\q
```

---

## Шаг 6: Использование в сессиях

### 6.1. Создание сессии с MR через API

При создании сессии можно указать `mr_id`:

```bash
curl -X POST http://localhost:8000/api/reviewer/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "Иван Иванов",
    "mr_package": "demo_package",
    "reviewer_name": "Reviewer",
    "mr_id": 1
  }'
```

**Что произойдёт:**
1. Создастся сессия с привязкой к MR #1
2. Автоматически загрузится diff из MR в `./artifacts/{session_id}_diff.patch`
3. Кандидат увидит этот diff вместо демо-версии

**Ответ:**
```json
{
  "session_id": 100,
  "access_token": "abc123...",
  "reviewer_token": "xyz789...",
  "candidate_url": "/candidate/abc123...",
  "reviewer_url": "/reviewer/sessions/100"
}
```

### 6.2. Проверка сессии с MR

Получите информацию о сессии:

```bash
curl http://localhost:8000/api/reviewer/sessions/100
```

В ответе будет информация о MR:
```json
{
  "id": 100,
  "candidate_name": "Иван Иванов",
  "mr_id": 1,
  "merge_request": {
    "id": 1,
    "title": "Code Review Session #1",
    "language": "python",
    "difficulty_level": "beginner",
    "change_type": "feature",
    "complexity_score": 25.5
  },
  ...
}
```

### 6.3. Использование в UI (будущее)

В будущем можно добавить в UI:
- Выбор MR при создании сессии
- Фильтры по языку, сложности, типу
- Предпросмотр diff перед созданием сессии

---

## Решение проблем

### Проблема 1: PostgreSQL не запускается

**Симптомы:**
```
Error: failed to start container postgres_mr
```

**Решение:**
1. Проверьте, не занят ли порт 5432:
   ```bash
   netstat -an | grep 5432
   # или на Windows:
   netstat -an | findstr 5432
   ```

2. Остановите другие PostgreSQL инстансы

3. Проверьте логи:
   ```bash
   docker compose logs postgres
   ```

4. Удалите старые данные (если нужно):
   ```bash
   docker compose down postgres
   rm -rf postgres_data/
   docker compose up -d postgres
   ```

### Проблема 2: Ошибка подключения к БД

**Симптомы:**
```
MR database module not available: ...
```

**Решение:**
1. Убедитесь, что PostgreSQL запущен:
   ```bash
   docker compose ps postgres
   ```

2. Проверьте переменные окружения в `docker-compose.yml`

3. Перезапустите API:
   ```bash
   docker compose restart api
   ```

4. Проверьте логи API:
   ```bash
   docker compose logs api | tail -50
   ```

### Проблема 3: Скрипт collect_mrs.py не работает

**Симптомы:**
```
ModuleNotFoundError: No module named '...'
```

**Решение:**
1. Убедитесь, что используете правильный Python:
   ```bash
   python --version  # Должно быть 3.10+
   ```

2. Установите зависимости (если нужно):
   ```bash
   pip install -r api/requirements.txt
   ```

3. Запускайте из корня проекта:
   ```bash
   cd /path/to/conversations
   python scripts/collect_mrs.py ...
   ```

### Проблема 4: Импорт не работает

**Симптомы:**
```
Failed to import MR: ...
```

**Решение:**
1. Проверьте формат JSON:
   ```bash
   python -m json.tool mrs_collected.json | head -20
   ```

2. Проверьте подключение к PostgreSQL:
   ```bash
   docker compose exec postgres psql -U mr_user -d mr_database -c "SELECT 1;"
   ```

3. Проверьте, что таблицы созданы:
   ```bash
   docker compose exec postgres psql -U mr_user -d mr_database -c "\dt"
   ```

4. Если таблиц нет, создайте вручную:
   ```bash
   docker compose exec -T postgres psql -U mr_user -d mr_database < api/migrations/001_create_mr_tables.sql
   ```

### Проблема 5: API не возвращает MR

**Симптомы:**
```
{"merge_requests": [], "total": 0}
```

**Решение:**
1. Проверьте, что данные импортированы:
   ```bash
   curl http://localhost:8000/api/mr/list
   ```

2. Проверьте напрямую в БД:
   ```bash
   docker compose exec postgres psql -U mr_user -d mr_database -c "SELECT COUNT(*) FROM merge_requests;"
   ```

3. Если данных нет, повторите импорт

---

## 📊 Следующие шаги

После успешной настройки:

1. ✅ **Соберите больше MR** из разных источников
2. ✅ **Протестируйте API** endpoints
3. ✅ **Создайте несколько сессий** с разными MR
4. ✅ **Обновите UI** для выбора MR (опционально)
5. ✅ **Настройте автоматический сбор** MR из GitHub/GitLab (опционально)

---

## 💡 Полезные команды

### Просмотр всех MR в БД:
```bash
curl http://localhost:8000/api/mr/list | python -m json.tool
```

### Поиск MR по ключевому слову:
```bash
curl "http://localhost:8000/api/mr/search?q=bug" | python -m json.tool
```

### Получить статистику:
```bash
# В PostgreSQL
docker compose exec postgres psql -U mr_user -d mr_database -c "
SELECT 
  language, 
  difficulty_level, 
  COUNT(*) as count,
  AVG(complexity_score) as avg_complexity
FROM merge_requests 
GROUP BY language, difficulty_level
ORDER BY language, difficulty_level;
"
```

### Очистка данных (если нужно начать заново):
```bash
docker compose down postgres
rm -rf postgres_data/
docker compose up -d postgres
# Затем повторите импорт
```

---

## 📝 Примечания

- **Данные PostgreSQL** хранятся в `./postgres_data/` (не коммитится)
- **Собранные MR** в JSON можно хранить в Git (если не слишком большие)
- **Diff файлы** могут быть большими, учитывайте это при импорте
- **API endpoints** работают только если PostgreSQL доступен

---

Если возникнут вопросы или проблемы - проверьте логи и используйте команды из раздела "Решение проблем".

