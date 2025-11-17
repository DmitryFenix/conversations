# Исправление ошибки: большой файл gitea

## Проблема
Файл `gitea` размером 108.84 MB превышает лимит GitHub (100 MB).

## Решение

Выполните эти команды в WSL (где вы запушили код):

```bash
# 1. Удалить файл из git (но оставить на диске)
git rm --cached gitea

# 2. Добавить изменения в .gitignore (уже добавлен)
git add .gitignore

# 3. Создать новый коммит
git commit -m "Remove large gitea binary file"

# 4. Запушить снова
git push -u origin main
```

## Если файл уже в истории коммитов

Если файл уже был закоммичен ранее, нужно удалить его из истории:

```bash
# 1. Удалить из индекса
git rm --cached gitea

# 2. Добавить в .gitignore (уже сделано)
git add .gitignore

# 3. Создать коммит
git commit -m "Remove large gitea binary file"

# 4. Если нужно удалить из всей истории (опционально, если файл был в предыдущих коммитах)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch gitea" \
  --prune-empty --tag-name-filter cat -- --all

# 5. Принудительный пуш (ОСТОРОЖНО: перезаписывает историю)
git push origin --force --all
```

## Простое решение (рекомендуется)

Если файл только в последнем коммите:

```bash
# 1. Удалить файл из git
git rm --cached gitea

# 2. Добавить .gitignore
git add .gitignore

# 3. Изменить последний коммит (amend)
git commit --amend --no-edit

# 4. Принудительный пуш
git push -u origin main --force
```

---

**Важно:** Файл `gitea` - это бинарный файл Gitea, который не должен быть в репозитории. Он будет скачиваться при сборке Docker образа.

