# Скрипт для настройки GitHub репозитория и первого коммита

Write-Host "🚀 Настройка GitHub репозитория" -ForegroundColor Green
Write-Host ""

# Проверка git
try {
    $gitVersion = git --version
    Write-Host "✅ Git установлен: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git не установлен!" -ForegroundColor Red
    Write-Host "Установите Git с https://git-scm.com/" -ForegroundColor Yellow
    exit 1
}

# Проверка, инициализирован ли репозиторий
if (-not (Test-Path ".git")) {
    Write-Host "📝 Инициализация git репозитория..." -ForegroundColor Yellow
    git init
    Write-Host "✅ Репозиторий инициализирован" -ForegroundColor Green
} else {
    Write-Host "✅ Git репозиторий уже инициализирован" -ForegroundColor Green
}

# Добавление всех файлов
Write-Host ""
Write-Host "📦 Добавление файлов..." -ForegroundColor Yellow
git add .

# Проверка статуса
Write-Host ""
Write-Host "📊 Статус репозитория:" -ForegroundColor Cyan
git status --short

# Создание коммита
Write-Host ""
$commitMessage = "Initial commit: Code Review Platform with Gitea integration"
Write-Host "💾 Создание коммита..." -ForegroundColor Yellow
git commit -m $commitMessage

Write-Host ""
Write-Host "✅ Коммит создан!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Создайте репозиторий на GitHub:" -ForegroundColor Yellow
Write-Host "   - Зайдите на https://github.com/new" -ForegroundColor White
Write-Host "   - Введите название репозитория (например: code-review-platform)" -ForegroundColor White
Write-Host "   - НЕ добавляйте README, .gitignore или лицензию (они уже есть)" -ForegroundColor White
Write-Host "   - Нажмите 'Create repository'" -ForegroundColor White
Write-Host ""
Write-Host "2. Подключите remote и запушьте код:" -ForegroundColor Yellow
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "3. После пуша разверните на Railway:" -ForegroundColor Yellow
Write-Host "   - Зайдите на https://railway.app" -ForegroundColor White
Write-Host "   - New Project → Deploy from GitHub repo" -ForegroundColor White
Write-Host "   - Выберите ваш репозиторий" -ForegroundColor White
Write-Host ""

