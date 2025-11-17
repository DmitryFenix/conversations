# Настройка интеграции с внешним Gitea

## Ситуация

Gitea уже запущен на хосте на порту 4000 (вне Docker). Docker не может занять порт 4000, так как он уже занят.

## Решение

### 1. Конфигурация уже обновлена

В `docker-compose.yml`:
- Сервис `gitea` закомментирован (не запускается в Docker)
- `GITEA_URL` настроен на `http://host.docker.internal:4000`

Это позволяет контейнеру API обращаться к Gitea, запущенному на хосте.

### 2. Проверка доступности Gitea из контейнера

#### Для Docker Desktop (Windows/Mac)

`host.docker.internal` должен работать автоматически.

#### Для WSL/Linux

Если `host.docker.internal` не работает, нужно использовать IP адрес хоста:

1. **Найдите IP адрес хоста:**
   ```bash
   # В WSL
   ip route show default | awk '/default/ {print $3}'
   # Или
   hostname -I | awk '{print $1}'
   ```

2. **Обновите `.env` файл:**
   ```bash
   GITEA_URL=http://172.x.x.x:4000  # Замените на ваш IP
   GITEA_ADMIN_TOKEN=ваш_токен
   ```

3. **Или обновите `docker-compose.yml`:**
   ```yaml
   environment:
     - GITEA_URL=http://172.x.x.x:4000  # IP адрес хоста
   ```

### 3. Убедитесь, что Gitea доступен

Gitea должен быть доступен на `http://localhost:4000` с хоста.

Если Gitea слушает только на `127.0.0.1`, он может быть недоступен из Docker контейнера. В этом случае:

1. **Настройте Gitea слушать на всех интерфейсах:**
   - В конфигурации Gitea (`app.ini` или через веб-интерфейс)
   - Установите `HTTP_ADDR = 0.0.0.0` вместо `127.0.0.1`

2. **Или используйте IP адрес хоста** (см. выше)

### 4. Установите токен

Создайте файл `.env` в корне проекта:

```bash
GITEA_ADMIN_TOKEN=ваш_токен_из_gitea
```

### 5. Перезапустите контейнеры

```bash
docker compose down
docker compose up -d
```

### 6. Проверьте логи

```bash
docker compose logs api | grep -i gitea
```

Должно появиться:
```
INFO:main:Gitea client initialized: http://host.docker.internal:4000
```

Если видите ошибку подключения, попробуйте использовать IP адрес хоста вместо `host.docker.internal`.

## Альтернатива: Запустить Gitea в Docker на другом порту

Если хотите запустить Gitea в Docker:

1. **Раскомментируйте сервис `gitea` в `docker-compose.yml`**
2. **Измените маппинг порта:**
   ```yaml
   ports:
     - "4001:4000"  # Внешний порт 4001, внутренний 4000
   ```
3. **Обновите `GITEA_URL`:**
   ```yaml
   - GITEA_URL=http://gitea:4000  # Внутри Docker сети
   ```
4. **Обновите `GITEA__server__ROOT_URL` в конфигурации Gitea:**
   ```yaml
   - GITEA__server__ROOT_URL=http://localhost:4001
   ```

Но так как у вас уже есть Gitea на порту 4000, лучше использовать его.

## Проверка интеграции

После настройки:

1. Создайте сессию через `/reviewer`
2. Проверьте, что в ответе есть поле `gitea`
3. Проверьте, что пользователь и репозиторий созданы в Gitea

