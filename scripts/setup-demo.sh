#!/bin/bash
# Скрипт для настройки демо-версии

set -e

echo "🎯 Настройка демо-версии Code Review Platform..."

# Создание демо-конфигурации
cat > docker-compose.demo.yml << 'EOF'
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DEMO_MODE=true
      - MAX_SESSIONS=5
      - SESSION_DURATION=30
      - AUTO_CLEANUP=true
      - CLEANUP_INTERVAL=3600
    volumes:
      - ./artifacts:/artifacts
      - ./mr_packages:/mr_packages
      - ./api/reviews.db:/app/reviews.db
    depends_on:
      - redis
      - gitea

  worker:
    build:
      context: .
      dockerfile: api/Dockerfile
    command: rq worker default
    environment:
      - DEMO_MODE=true
    volumes:
      - ./artifacts:/artifacts
      - ./mr_packages:/mr_packages
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  gitea:
    image: gitea/gitea:latest
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=sqlite3
    ports:
      - "4001:4000"
      - "2222:22"
    volumes:
      - gitea_data:/data
    restart: unless-stopped

volumes:
  gitea_data:
EOF

echo "✅ Демо-конфигурация создана: docker-compose.demo.yml"
echo ""
echo "Для запуска демо-версии используйте:"
echo "  docker compose -f docker-compose.demo.yml up -d"
echo ""
echo "Особенности демо-режима:"
echo "  - Максимум 5 активных сессий"
echo "  - Длительность сессии: 30 минут"
echo "  - Автоматическая очистка старых данных"
echo "  - Водяной знак 'DEMO' на интерфейсе"

