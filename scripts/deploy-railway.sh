#!/bin/bash
# Скрипт для развертывания на Railway.app

set -e

echo "🚀 Развертывание Code Review Platform на Railway..."

# Проверка установки Railway CLI
if ! command -v railway &> /dev/null; then
    echo "📦 Установка Railway CLI..."
    npm install -g @railway/cli || {
        echo "❌ Ошибка: npm не установлен. Установите Node.js сначала."
        exit 1
    }
fi

# Проверка логина
if ! railway whoami &> /dev/null; then
    echo "🔐 Вход в Railway..."
    railway login
fi

# Инициализация проекта (если еще не инициализирован)
if [ ! -f "railway.json" ]; then
    echo "📝 Инициализация Railway проекта..."
    railway init
fi

# Развертывание
echo "🚀 Запуск развертывания..."
railway up

echo "✅ Развертывание завершено!"
echo "🌐 Проверьте статус на https://railway.app"

