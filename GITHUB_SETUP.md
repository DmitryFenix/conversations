# Настройка GitHub интеграции

## Требования

1. **GitHub Personal Access Token (PAT)**
   - Перейдите в GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Создайте новый токен с правами:
     - `repo` (полный доступ к репозиториям)
     - `workflow` (если нужна интеграция с GitHub Actions)

2. **Организация (опционально)**
   - Если вы хотите создавать репозитории в организации, укажите её название
   - Токен должен иметь права на создание репозиториев в организации

## Настройка переменных окружения

### Docker Compose

Добавьте в `.env` файл или экспортируйте переменные:

```bash
export GITHUB_TOKEN=your_github_token_here
export GITHUB_ORGANIZATION=your_org_name  # Опционально
```

Или в `docker-compose.yml`:

```yaml
environment:
  - GITHUB_TOKEN=${GITHUB_TOKEN:-}
  - GITHUB_ORGANIZATION=${GITHUB_ORGANIZATION:-}
```

### Локальный запуск

```bash
export GITHUB_TOKEN=your_github_token_here
export GITHUB_ORGANIZATION=your_org_name  # Опционально
python api/main.py
```

## Отличия от Gitea

1. **Пользователи**: В GitHub нельзя создавать пользователей через API. Репозитории создаются от имени пользователя, владеющего токеном, или в организации.

2. **Репозитории**: Каждая сессия создаёт отдельный репозиторий с именем `code-review-session-{session_id}`.

3. **Доступ**: Кандидаты получают доступ к репозиторию через GitHub (нужно настроить коллаборацию или использовать GitHub App для автоматического управления доступом).

## Ограничения

- GitHub API имеет rate limits (5000 запросов в час для аутентифицированных пользователей)
- Создание репозиториев ограничено (100 в час для бесплатных аккаунтов)
- Для production рекомендуется использовать GitHub App вместо Personal Access Token

## Миграция с Gitea

Если у вас были сессии с Gitea, они продолжат работать, но новые сессии будут использовать GitHub. Поля в базе данных (`gitea_user`, `gitea_repo`, `gitea_pr_id`) используются для обратной совместимости.

