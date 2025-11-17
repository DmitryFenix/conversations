#!/bin/bash
# Скрипт для непрерывного запуска тестов в Docker

set -e

INTERVAL=${TEST_INTERVAL:-10}

echo "=========================================="
echo "Continuous Test Runner (Docker)"
echo "=========================================="
echo "Interval: $INTERVAL seconds"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Проверяем, что контейнеры запущены
if ! docker compose ps api | grep -q "Up"; then
    echo "Starting services..."
    docker compose up -d api redis worker
    echo "Waiting for services to be ready..."
    sleep 10
fi

# Запускаем тесты в цикле
while true; do
    echo "----------------------------------------"
    echo "Running tests at $(date '+%Y-%m-%d %H:%M:%S')"
    echo "----------------------------------------"
    
    docker compose run --rm \
        -e API_BASE_URL=http://api:8000 \
        tests || true
    
    echo ""
    echo "Waiting $INTERVAL seconds before next run..."
    echo ""
    sleep "$INTERVAL"
done
