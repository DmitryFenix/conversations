# PowerShell скрипт для автоматической настройки базы данных Merge Requests

Write-Host "🚀 Настройка базы данных Merge Requests..." -ForegroundColor Cyan

# Проверяем, что PostgreSQL запущен
Write-Host "📦 Проверка PostgreSQL..." -ForegroundColor Yellow
$postgresStatus = docker compose ps postgres 2>$null | Select-String "Up"
if (-not $postgresStatus) {
    Write-Host "⚠️  PostgreSQL не запущен. Запускаю..." -ForegroundColor Yellow
    docker compose up -d postgres
    Write-Host "⏳ Ожидание готовности PostgreSQL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Проверяем, что API запущен
Write-Host "📦 Проверка API..." -ForegroundColor Yellow
$apiStatus = docker compose ps api 2>$null | Select-String "Up"
if (-not $apiStatus) {
    Write-Host "⚠️  API не запущен. Запускаю..." -ForegroundColor Yellow
    docker compose up -d api
    Write-Host "⏳ Ожидание готовности API..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

# Проверяем наличие artifacts
$artifactsDir = "./artifacts"
if (-not (Test-Path $artifactsDir)) {
    Write-Host "⚠️  Директория artifacts не найдена. Создаю..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}

# Проверяем, есть ли уже собранные MR
$mrFile = "mrs_collected.json"
if (Test-Path $mrFile) {
    Write-Host "✅ Найден файл $mrFile" -ForegroundColor Green
    $response = Read-Host "Пересобрать MR? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "📋 Используем существующий файл $mrFile" -ForegroundColor Cyan
    } else {
        Write-Host "🔄 Собираю MR из artifacts..." -ForegroundColor Yellow
        python scripts/collect_mrs.py --artifacts $artifactsDir --output $mrFile
    }
} else {
    Write-Host "🔄 Собираю MR из artifacts..." -ForegroundColor Yellow
    python scripts/collect_mrs.py --artifacts $artifactsDir --output $mrFile
}

# Проверяем, что файл создан и не пустой
if (-not (Test-Path $mrFile) -or (Get-Item $mrFile).Length -eq 0) {
    Write-Host "❌ Ошибка: файл $mrFile не создан или пуст" -ForegroundColor Red
    Write-Host "💡 Убедитесь, что в директории artifacts есть diff файлы (*_diff.patch)" -ForegroundColor Yellow
    exit 1
}

# Проверяем количество MR в файле
try {
    $mrContent = Get-Content $mrFile -Raw | ConvertFrom-Json
    $mrCount = $mrContent.Count
    Write-Host "📊 Найдено MR: $mrCount" -ForegroundColor Cyan
} catch {
    Write-Host "⚠️  Не удалось прочитать файл $mrFile" -ForegroundColor Yellow
    $mrCount = 0
}

if ($mrCount -eq 0) {
    Write-Host "⚠️  В файле нет MR. Пропускаю импорт." -ForegroundColor Yellow
    exit 0
}

# Проверяем, есть ли уже данные в БД
Write-Host "🔍 Проверка существующих данных в БД..." -ForegroundColor Yellow
try {
    $existingCount = docker compose exec -T postgres psql -U mr_user -d mr_database -t -c "SELECT COUNT(*) FROM merge_requests;" 2>$null
    $existingCount = $existingCount.Trim()
    if ($existingCount -match '^\d+$') {
        Write-Host "📋 В БД уже есть $existingCount MR" -ForegroundColor Cyan
        $response = Read-Host "Добавить новые MR? (y/n)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "✅ Пропускаю импорт. Используем существующие данные." -ForegroundColor Green
            exit 0
        }
    }
} catch {
    Write-Host "⚠️  Не удалось проверить БД (возможно, таблицы ещё не созданы)" -ForegroundColor Yellow
}

# Импортируем
Write-Host "📥 Импорт MR в базу данных..." -ForegroundColor Yellow
python scripts/import_mrs.py $mrFile

Write-Host ""
Write-Host "✅ Готово! База данных Merge Requests настроена." -ForegroundColor Green
Write-Host ""
Write-Host "📊 Проверка:" -ForegroundColor Cyan
Write-Host "   curl http://localhost:8000/api/mr/list" -ForegroundColor Gray
Write-Host ""




