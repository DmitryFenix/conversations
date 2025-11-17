# Скрипт для запуска тестов через WSL
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running API Tests via WSL" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем WSL
$wslPath = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslPath) {
    Write-Host "WSL is not available. Trying Docker directly..." -ForegroundColor Yellow
    docker compose run --rm -e API_BASE_URL=http://api:8000 tests
    exit $LASTEXITCODE
}

Write-Host "Using WSL..." -ForegroundColor Green
Write-Host ""

# Получаем текущий путь в формате WSL
$currentPath = (Get-Location).Path
$wslPath = $currentPath -replace 'C:\\', '/mnt/c/' -replace '\\', '/'

Write-Host "Current path: $currentPath" -ForegroundColor Gray
Write-Host "WSL path: $wslPath" -ForegroundColor Gray
Write-Host ""

# Запускаем тесты через WSL
Write-Host "Running tests..." -ForegroundColor Yellow
wsl bash -c "cd '$wslPath' && docker compose run --rm -e API_BASE_URL=http://api:8000 tests"

exit $LASTEXITCODE


