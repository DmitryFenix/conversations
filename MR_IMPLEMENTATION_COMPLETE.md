# Реализация системы классификации и подбора MR - ЗАВЕРШЕНО

## ✅ Что реализовано

### 1. Классификация MR

#### Типы MR (8 категорий):
1. **bugfix** - Bugfix / корректность логики
2. **feature** - Feature / добавление функционала
3. **refactoring** - Refactoring / архитектурный MR
4. **tests** - Tests / покрытие и качество тестов
5. **performance** - Performance / ресурсоёмкость
6. **security** - Security / надёжность
7. **infrastructure** - Infrastructure / конфигурация / DevOps
8. **code_style** - Code style / читаемость / code smells

#### Баллы сложности (1-5):
- **1 балл** - очень простой, "разогрев"
- **2 балла** - простой, однозадачный MR
- **3 балла** - средний, типичный рабочий MR
- **4 балла** - сложный, с несколькими аспектами
- **5 баллов** - очень сложный, почти "lead-level"

#### Теги стека:
- Языки: python, javascript, java, go
- Направления: backend, frontend, devops
- Технологии: database

### 2. База данных

✅ Миграция `002_add_mr_classification.sql`:
- Поле `mr_type` - тип MR
- Поле `complexity_points` - баллы сложности (1-5)
- Поле `stack_tags` - массив тегов стека
- Индексы для быстрого поиска

### 3. Автоматическая классификация

✅ Модуль `api/mr_classifier.py`:
- `detect_mr_type()` - определение типа на основе ключевых слов
- `calculate_complexity_points()` - вычисление баллов (размер, тип, сложность)
- `detect_stack_tags()` - определение тегов стека
- `classify_mr()` - полная классификация

✅ Интеграция в `scripts/collect_mrs.py`:
- Автоматическая классификация при сборе MR
- Логирование типа и баллов

### 4. API Endpoints

✅ Обновлён `GET /api/mr/list`:
- Фильтрация по `mr_type`
- Фильтрация по `min_complexity_points` / `max_complexity_points`
- Фильтрация по `stack_tag`

✅ Новый `GET /api/mr/recommend`:
- Рекомендации на основе грейда (junior/middle/senior)
- Подбор MR для достижения целевого диапазона баллов
- Фильтрация по стеку и типам

✅ Обновлён `POST /api/reviewer/sessions`:
- Поддержка `mr_ids` (список MR)
- Объединение diff из нескольких MR
- Отображение типа и баллов каждого MR в diff

### 5. Структура данных

```json
{
  "id": 1,
  "title": "Fix security vulnerability",
  "mr_type": "security",
  "complexity_points": 4,
  "stack_tags": ["python", "backend"],
  "language": "python",
  "files_changed": 3,
  "lines_added": 150,
  "complexity_score": 65.5
}
```

## 📋 Что осталось сделать

### Frontend (UI)

1. **Компонент выбора MR** (`MRSelector.jsx`):
   - Выбор грейда (junior/middle/senior)
   - Выбор стека (теги)
   - Кнопка "Получить рекомендации"
   - Список MR с чекбоксами
   - Прогресс-бар выбранных баллов
   - Фильтры по типу и баллам

2. **Интеграция в форму создания сессии**:
   - Добавить секцию выбора MR
   - Отправлять `mr_ids` при создании сессии

3. **Отображение информации о MR**:
   - В списке сессий показывать типы и баллы
   - В деталях сессии показывать информацию о выбранных MR

## 🚀 Как использовать сейчас

### 1. Собрать и классифицировать MR

```bash
# В Docker контейнере
docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json
```

MR автоматически классифицируются по типу, баллам и тегам.

### 2. Импортировать в БД

```bash
docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json
```

### 3. Получить рекомендации через API

```bash
# Для Middle уровня, Python Backend
curl "http://localhost:8000/api/mr/recommend?target_grade=middle&stack_tags=python,backend"

# Ответ:
{
  "recommended_mrs": [
    {"id": 1, "title": "...", "mr_type": "bugfix", "complexity_points": 2},
    {"id": 3, "title": "...", "mr_type": "feature", "complexity_points": 3}
  ],
  "total_points": 5,
  "target_range": "5-7",
  "grade": "middle"
}
```

### 4. Создать сессию с несколькими MR

```bash
curl -X POST http://localhost:8000/api/reviewer/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "Иван Иванов",
    "mr_package": "demo_package",
    "reviewer_name": "Reviewer",
    "mr_ids": [1, 3, 5]
  }'
```

Diff из всех выбранных MR будет объединён в один файл.

## 📊 Примеры наборов MR

### Junior Backend (3-4 балла):
```json
{
  "mr_ids": [1, 2],
  "total_points": 3,
  "mrs": [
    {"id": 1, "type": "bugfix", "points": 2},
    {"id": 2, "type": "code_style", "points": 1}
  ]
}
```

### Middle Backend (5-7 баллов):
```json
{
  "mr_ids": [3, 4],
  "total_points": 5,
  "mrs": [
    {"id": 3, "type": "feature", "points": 3},
    {"id": 4, "type": "tests", "points": 2}
  ]
}
```

### Senior (8-10 баллов):
```json
{
  "mr_ids": [5, 6, 7],
  "total_points": 8,
  "mrs": [
    {"id": 5, "type": "refactoring", "points": 4},
    {"id": 6, "type": "security", "points": 3},
    {"id": 7, "type": "tests", "points": 1}
  ]
}
```

## 📝 Файлы

### Созданные:
- `api/mr_classifier.py` - модуль классификации
- `api/migrations/002_add_mr_classification.sql` - миграция БД
- `MR_CLASSIFICATION_SYSTEM.md` - описание системы
- `MR_SELECTION_UI_PLAN.md` - план UI

### Обновлённые:
- `api/mr_database.py` - добавлена поддержка новых полей
- `api/main.py` - добавлены endpoints и поддержка `mr_ids`
- `scripts/collect_mrs.py` - автоматическая классификация
- `api/Dockerfile` - добавлен `mr_classifier.py`
- `docker-compose.yml` - монтирование `mr_classifier.py`

## 🔄 Следующие шаги

1. **Перезапустить API** для применения миграций:
   ```bash
   docker compose restart api
   ```

2. **Пересобрать MR** с классификацией:
   ```bash
   docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json
   docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json
   ```

3. **Протестировать API**:
   ```bash
   curl "http://localhost:8000/api/mr/list?mr_type=bugfix&min_complexity_points=2"
   curl "http://localhost:8000/api/mr/recommend?target_grade=middle&stack_tags=python"
   ```

4. **Обновить UI** (см. `MR_SELECTION_UI_PLAN.md`)




