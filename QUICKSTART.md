# Быстрый старт - Code Review Platform

## Предварительные требования

- Docker и Docker Compose установлены
- Порты 8000, 3000, 6379, 2222 свободны

## Шаг 1: Клонирование и подготовка

```bash
# Перейдите в директорию проекта
cd conversations

# Убедитесь, что все файлы на месте
ls -la docker-compose.yml
```

## Шаг 2: Запуск приложения

### Вариант A: Production режим (рекомендуется)

```bash
# Запустить все сервисы
docker compose up --build -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f
```

### Вариант B: Development режим (с hot reload)

```bash
# Запустить с dev конфигурацией
docker compose -f docker-compose.dev.yml up --build -d

# Или запустить frontend отдельно на хосте
cd frontend
npm install
npm run dev
```

## Шаг 3: Настройка Gitea (опционально)

Если вы хотите использовать интеграцию с Gitea:

1. **Откройте Gitea в браузере:**
   ```
   http://localhost:3000
   ```

2. **Выполните первоначальную настройку:**
   - Database Type: SQLite3
   - Site Title: Code Review Platform
   - Administrator Username: `admin`
   - Administrator Password: (создайте надёжный пароль)
   - Administrator Email: `admin@code-review.local`

3. **Создайте API токен:**
   - Перейдите: Settings → Applications → Generate New Token
   - Имя: `code-review-platform-admin`
   - Права: **Все права**
   - Скопируйте токен

4. **Установите токен в приложение:**

   **Вариант 1: Через docker-compose.yml**
   
   Отредактируйте `docker-compose.yml`, добавьте в секцию `api`:
   ```yaml
   api:
     environment:
       - PYTHONUNBUFFERED=1
       - GITEA_ADMIN_TOKEN=ваш_токен_здесь
   ```

   **Вариант 2: Через .env файл**
   
   Создайте файл `.env` в корне проекта:
   ```bash
   GITEA_ADMIN_TOKEN=ваш_токен_здесь
   GITEA_URL=http://gitea:3000
   ```
   
   И обновите `docker-compose.yml`:
   ```yaml
   api:
     env_file:
       - .env
   ```

5. **Перезапустите API:**
   ```bash
   docker compose restart api
   ```

6. **Проверьте логи:**
   ```bash
   docker compose logs api | grep Gitea
   ```
   
   Должно появиться: `Gitea client initialized: http://gitea:3000`

## Шаг 4: Проверка работы

### Проверка Backend

```bash
# Проверить здоровье API
curl http://localhost:8000/api/reviewer/sessions

# Должен вернуть: {"sessions": []}
```

### Проверка Frontend

1. **Reviewer Dashboard:**
   ```
   http://localhost:8000/reviewer
   ```

2. **Создание тестовой сессии:**
   - Нажмите "Создать сессию"
   - Введите имя кандидата: `Иван Иванов`
   - Нажмите "Создать"
   - Скопируйте `access_token` из ответа

3. **Интерфейс кандидата:**
   ```
   http://localhost:8000/candidate/{access_token}
   ```

### Проверка Gitea (если настроен)

1. Откройте: `http://localhost:3000`
2. Войдите как администратор
3. Найдите пользователя `candidate_ivan_ivanov`
4. Перейдите в репозиторий `session_1`

## Шаг 5: Тестирование в двух браузерах

### Браузер 1: Reviewer

1. Откройте: `http://localhost:8000/reviewer`
2. Создайте сессию для кандидата
3. Скопируйте токен кандидата

### Браузер 2: Candidate

1. Откройте: `http://localhost:8000/candidate/{token}`
2. Добавьте комментарии к коду
3. Вернитесь в браузер Reviewer и обновите страницу
4. Убедитесь, что комментарии видны

## Полезные команды

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f gitea
```

### Остановка

```bash
# Остановить все сервисы
docker compose down

# Остановить и удалить volumes
docker compose down -v
```

### Перезапуск

```bash
# Перезапустить конкретный сервис
docker compose restart api

# Перезапустить все
docker compose restart
```

### Очистка

```bash
# Удалить неиспользуемые образы
docker image prune

# Удалить всё неиспользуемое
docker system prune -a
```

## Решение проблем

### Проблема: Порт уже занят

```bash
# Проверить, что использует порт
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Изменить порт в docker-compose.yml
ports:
  - "8001:8000"  # Использовать 8001 вместо 8000
```

### Проблема: Gitea не запускается

```bash
# Проверить логи
docker compose logs gitea

# Проверить права доступа
ls -la gitea_data/
```

### Проблема: API не может подключиться к Redis

```bash
# Проверить статус Redis
docker compose ps redis

# Проверить логи Redis
docker compose logs redis

# Перезапустить Redis
docker compose restart redis
```

### Проблема: Worker не обрабатывает задачи

```bash
# Проверить логи worker
docker compose logs worker

# Проверить подключение к Redis
docker compose exec worker python -c "from redis import Redis; r = Redis('redis://redis:6379'); print(r.ping())"
```

## Структура URL

- **Reviewer Dashboard:** `http://localhost:8000/reviewer`
- **Детали сессии:** `http://localhost:8000/reviewer/sessions/{id}`
- **Интерфейс кандидата:** `http://localhost:8000/candidate/{token}`
- **Gitea:** `http://localhost:3000`
- **API:** `http://localhost:8000/api/...`

## Следующие шаги

1. ✅ Приложение запущено
2. ✅ Gitea настроен (опционально)
3. ✅ Создана тестовая сессия
4. ✅ Проверена работа в двух браузерах

Теперь вы можете:
- Создавать сессии для кандидатов
- Кандидаты могут добавлять комментарии
- Reviewer может оценивать работу
- Генерировать отчёты (текст + PDF)

