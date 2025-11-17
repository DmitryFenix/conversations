# Настройка Gitea для Code Review Platform

## Первоначальная настройка Gitea

После первого запуска `docker compose up`, Gitea будет доступен по адресу `http://localhost:4000`.

### 1. Первоначальная установка

1. Откройте браузер: `http://localhost:4000`
2. Заполните форму первоначальной настройки:
   - **Database Type**: SQLite3 (по умолчанию)
   - **General Settings**:
     - **Site Title**: Code Review Platform
     - **Repository Root Path**: `/data/git/repositories`
     - **Git LFS Root Path**: `/data/git/lfs`
     - **Run As**: `git`
     - **SSH Server Domain**: `localhost`
     - **SSH Port**: `2222`
     - **HTTP Port**: `4000`
     - **Gitea Base URL**: `http://localhost:4000`
   - **Administrator Account Settings**:
     - **Username**: `admin`
     - **Password**: (создайте надежный пароль)
     - **Email**: `admin@code-review.local`

### 2. Создание API токена администратора

После входа в Gitea:

1. Перейдите в **Settings** → **Applications** → **Generate New Token**
2. Задайте имя токена: `code-review-platform-admin`
3. Выберите права доступа: **Все права**
4. Нажмите **Generate Token**
5. **Скопируйте токен** (он будет показан только один раз!)

### 3. Установка токена в приложение

Установите переменную окружения `GITEA_ADMIN_TOKEN`:

#### Вариант A: Через docker-compose.yml

Добавьте в секцию `api` в `docker-compose.yml`:

```yaml
api:
  environment:
    - PYTHONUNBUFFERED=1
    - GITEA_ADMIN_TOKEN=ваш_токен_здесь
```

#### Вариант B: Через .env файл

Создайте файл `.env` в корне проекта:

```bash
GITEA_ADMIN_TOKEN=ваш_токен_здесь
GITEA_URL=http://gitea:4000
```

И обновите `docker-compose.yml`:

```yaml
api:
  env_file:
    - .env
```

### 4. Перезапуск приложения

После установки токена:

```bash
docker compose restart api
```

Проверьте логи:

```bash
docker compose logs api | grep Gitea
```

Должно появиться: `Gitea client initialized: http://gitea:4000`

## Проверка интеграции

### Создание тестовой сессии

1. Откройте `http://localhost:8000/reviewer`
2. Создайте новую сессию для кандидата
3. Проверьте, что в ответе есть поле `gitea`:
   ```json
   {
     "session_id": 1,
     "access_token": "...",
     "gitea": {
       "enabled": true,
       "user": "candidate_ivan_ivanov",
       "repo": "session_1",
       "clone_url": "http://gitea:4000/candidate_ivan_ivanov/session_1.git",
       "web_url": "http://localhost:4000/candidate_ivan_ivanov/session_1"
     }
   }
   ```

### Проверка репозитория в Gitea

1. Откройте `http://localhost:4000`
2. Войдите как администратор
3. Найдите пользователя `candidate_...` в списке пользователей
4. Перейдите в репозиторий `session_...`
5. Убедитесь, что файл `main.py` создан

## Использование

После настройки, при создании новой сессии через `/api/reviewer/sessions`:

1. Автоматически создаётся пользователь в Gitea для кандидата
2. Создаётся приватный репозиторий для сессии
3. Инициализируется стартовый код (`main.py`)
4. Кандидат может клонировать репозиторий и работать с кодом

### Клонирование репозитория кандидатом

```bash
git clone http://localhost:4000/candidate_ivan_ivanov/session_1.git
cd session_1
# Работа с кодом
git add .
git commit -m "My changes"
git push origin main
```

## Отключение Gitea

Если нужно временно отключить интеграцию с Gitea:

1. Удалите или закомментируйте `GITEA_ADMIN_TOKEN` в `docker-compose.yml`
2. Перезапустите API: `docker compose restart api`

Приложение будет работать в режиме без Gitea (используя старый workflow с .zip файлами).

