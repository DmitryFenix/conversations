#!/bin/bash
# Скрипт для развертывания на VPS (Ubuntu/Debian)

set -e

echo "🚀 Развертывание Code Review Platform на VPS..."

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Запустите скрипт с sudo"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Установка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Установка Docker Compose..."
    apt install docker-compose -y
fi

# Добавление пользователя в группу docker
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker $SUDO_USER
    echo "✅ Пользователь $SUDO_USER добавлен в группу docker"
fi

# Клонирование репозитория (если нужно)
if [ ! -d "/opt/code-review-platform" ]; then
    echo "📥 Клонирование репозитория..."
    mkdir -p /opt
    cd /opt
    # Замените на ваш репозиторий
    # git clone <your-repo-url> code-review-platform
    echo "⚠️  Не забудьте клонировать репозиторий в /opt/code-review-platform"
fi

cd /opt/code-review-platform

# Создание .env файла
if [ ! -f ".env" ]; then
    echo "📝 Создание .env файла..."
    cat > .env << EOF
GITEA_URL=http://gitea:4000
GITEA_WEB_URL=http://$(hostname -I | awk '{print $1}'):4001
GITEA_ADMIN_TOKEN=
EOF
    echo "⚠️  Не забудьте настроить GITEA_ADMIN_TOKEN в .env файле!"
fi

# Запуск приложения
echo "🚀 Запуск приложения..."
docker compose up -d

# Проверка статуса
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка
if docker compose ps | grep -q "Up"; then
    echo "✅ Приложение успешно запущено!"
    echo "🌐 Доступно по адресу: http://$(hostname -I | awk '{print $1}'):8000"
    echo "🌐 Gitea доступна по адресу: http://$(hostname -I | awk '{print $1}'):4001"
else
    echo "❌ Ошибка при запуске. Проверьте логи: docker compose logs"
    exit 1
fi

echo "✅ Развертывание завершено!"

