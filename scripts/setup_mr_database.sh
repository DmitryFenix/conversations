#!/bin/bash
# Скрипт для автоматической настройки базы данных Merge Requests

set -e

echo "🚀 Настройка базы данных Merge Requests..."

# Проверяем, что PostgreSQL запущен
echo "📦 Проверка PostgreSQL..."
if ! docker compose ps postgres | grep -q "Up"; then
    echo "⚠️  PostgreSQL не запущен. Запускаю..."
    docker compose up -d postgres
    echo "⏳ Ожидание готовности PostgreSQL..."
    sleep 5
fi

# Проверяем, что API запущен (для инициализации БД)
echo "📦 Проверка API..."
if ! docker compose ps api | grep -q "Up"; then
    echo "⚠️  API не запущен. Запускаю..."
    docker compose up -d api
    echo "⏳ Ожидание готовности API..."
    sleep 3
fi

# Проверяем наличие artifacts
ARTIFACTS_DIR="./artifacts"
if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "⚠️  Директория artifacts не найдена. Создаю..."
    mkdir -p "$ARTIFACTS_DIR"
fi

# Проверяем, есть ли уже собранные MR
MR_FILE="mrs_collected.json"
if [ -f "$MR_FILE" ]; then
    echo "✅ Найден файл $MR_FILE"
    read -p "Пересобрать MR? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "📋 Используем существующий файл $MR_FILE"
    else
        echo "🔄 Собираю MR из artifacts..."
        python scripts/collect_mrs.py --artifacts "$ARTIFACTS_DIR" --output "$MR_FILE"
    fi
else
    echo "🔄 Собираю MR из artifacts..."
    python scripts/collect_mrs.py --artifacts "$ARTIFACTS_DIR" --output "$MR_FILE"
fi

# Проверяем, что файл создан и не пустой
if [ ! -f "$MR_FILE" ] || [ ! -s "$MR_FILE" ]; then
    echo "❌ Ошибка: файл $MR_FILE не создан или пуст"
    echo "💡 Убедитесь, что в директории artifacts есть diff файлы (*_diff.patch)"
    exit 1
fi

# Проверяем количество MR в файле
MR_COUNT=$(python -c "import json; print(len(json.load(open('$MR_FILE'))))" 2>/dev/null || echo "0")
echo "📊 Найдено MR: $MR_COUNT"

if [ "$MR_COUNT" -eq 0 ]; then
    echo "⚠️  В файле нет MR. Пропускаю импорт."
    exit 0
fi

# Проверяем, есть ли уже данные в БД
echo "🔍 Проверка существующих данных в БД..."
EXISTING_COUNT=$(docker compose exec -T postgres psql -U mr_user -d mr_database -t -c "SELECT COUNT(*) FROM merge_requests;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$EXISTING_COUNT" -gt 0 ]; then
    echo "📋 В БД уже есть $EXISTING_COUNT MR"
    read -p "Добавить новые MR? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Пропускаю импорт. Используем существующие данные."
        exit 0
    fi
fi

# Импортируем
echo "📥 Импорт MR в базу данных..."
python scripts/import_mrs.py "$MR_FILE"

echo ""
echo "✅ Готово! База данных Merge Requests настроена."
echo ""
echo "📊 Проверка:"
echo "   curl http://localhost:8000/api/mr/list"
echo ""




