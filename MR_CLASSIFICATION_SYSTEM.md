# Система классификации и подбора Merge Requests

## Обзор

Система позволяет ревьюеру выбирать MR для кандидата на основе:
- **Типа MR** (8 категорий)
- **Баллов сложности** (1-5)
- **Тегов стека** (python, backend, frontend, devops и т.д.)
- **Целевого грейда** (junior, middle, senior)

## Типы Merge Requests

### 1. Bugfix / корректность логики
- **Что проверяет**: Внимание к деталям, умение мысленно "прогнать" код
- **Обычно**: 1-3 балла сложности
- **Ключевые слова**: bug, fix, error, null, exception

### 2. Feature / добавление функционала
- **Что проверяет**: Оценка соответствия требованиям, понимание связей между модулями
- **Обычно**: 2-4 балла сложности
- **Ключевые слова**: feature, new, add, implement

### 3. Refactoring / архитектурный MR
- **Что проверяет**: Архитектурное мышление, понимание SOLID, DRY, KISS
- **Обычно**: 3-5 баллов сложности
- **Ключевые слова**: refactor, architecture, design pattern, solid

### 4. Tests / покрытие и качество тестов
- **Что проверяет**: Тестовое мышление, понимание границ ответственности тестов
- **Обычно**: 1-3 балла сложности
- **Ключевые слова**: test, spec, coverage, mock, assert

### 5. Performance / ресурсоёмкость
- **Что проверяет**: Умение думать о сложности алгоритмов, понимание узких мест
- **Обычно**: 3-5 баллов сложности
- **Ключевые слова**: performance, optimization, slow, bottleneck, cache

### 6. Security / надёжность
- **Что проверяет**: Базовую безопасность, умение отличать критичные проблемы
- **Обычно**: 3-5 баллов сложности
- **Ключевые слова**: security, vulnerability, injection, xss, csrf, auth

### 7. Infrastructure / конфигурация / DevOps
- **Что проверяет**: Понимание среды исполнения, умение видеть опасные настройки
- **Обычно**: 2-4 балла сложности
- **Ключевые слова**: docker, kubernetes, ci/cd, deploy, config

### 8. Code style / читаемость / code smells
- **Что проверяет**: Чувство стиля, готовность улучшать код
- **Обычно**: 1-2 балла сложности
- **Ключевые слова**: style, format, lint, readability, naming

## Баллы сложности (1-5)

### Факторы оценки:

1. **Размер и разброс**
   - 1-2 файла, до 30 строк → 1-2 балла
   - Несколько файлов, 50-150 строк → 3 балла
   - Много файлов, 150+ строк → 4-5 баллов

2. **Тип MR**
   - bugfix / code_style → обычно проще (1-3)
   - architecture / perf / security → обычно сложнее (3-5)

3. **Сложность кода**
   - Низкая сложность → +0
   - Высокая сложность → +1

### Рекомендации по грейдам:

- **Junior**: 3-4 балла
- **Middle**: 5-7 баллов
- **Senior**: 8-10 баллов

## API Endpoints

### Получить список MR с фильтрацией

```
GET /api/mr/list?mr_type=bugfix&min_complexity_points=2&max_complexity_points=4&stack_tag=python
```

Параметры:
- `mr_type`: Тип MR (bugfix, feature, refactoring, tests, performance, security, infrastructure, code_style)
- `min_complexity_points`: Минимальные баллы (1-5)
- `max_complexity_points`: Максимальные баллы (1-5)
- `stack_tag`: Тег стека (python, backend, frontend, devops и т.д.)

### Рекомендации MR для кандидата

```
GET /api/mr/recommend?target_grade=middle&stack_tags=python,backend&target_points=6
```

Параметры:
- `target_grade`: junior, middle, senior
- `stack_tags`: Теги стека через запятую
- `target_points`: Целевое количество баллов (опционально)
- `mr_types`: Типы MR через запятую (опционально)

Ответ:
```json
{
  "recommended_mrs": [...],
  "total_points": 6,
  "target_range": "5-7",
  "grade": "middle"
}
```

### Создание сессии с несколькими MR

```
POST /api/reviewer/sessions
{
  "candidate_name": "Иван Иванов",
  "mr_package": "demo_package",
  "reviewer_name": "Reviewer",
  "mr_ids": [1, 3, 5]  // Список ID MR
}
```

Diff из всех выбранных MR будет объединён в один файл.

## Автоматическая классификация

При сборе MR через `scripts/collect_mrs.py` автоматически определяются:
- Тип MR (на основе ключевых слов в title, description, diff)
- Баллы сложности (на основе размера, типа, сложности кода)
- Теги стека (на основе языка, ключевых слов)

## Примеры наборов MR

### Для Junior Backend:
- Bugfix (2 балла)
- Code style (1 балл)
- **Итого: 3 балла**

### Для Middle Backend:
- Feature (3 балла)
- Tests (2 балла)
- **Итого: 5 баллов**

### Для Senior:
- Refactoring (4 балла)
- Security (3 балла)
- Tests (1 балл)
- **Итого: 8 баллов**

## Следующие шаги

1. ✅ Классификация MR реализована
2. ✅ API для фильтрации и рекомендаций готов
3. ⏳ Обновить UI для выбора MR при создании сессии
4. ⏳ Добавить отображение типов и баллов в интерфейсе
5. ⏳ Реализовать подбор MR на основе грейда




