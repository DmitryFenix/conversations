# Dockerfile для тестов
FROM python:3.11.10-slim

WORKDIR /app

# Копируем зависимости для тестов
COPY tests/requirements.txt /app/tests/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r tests/requirements.txt

# Копируем тесты (будут перемонтированы через volume, но нужны для сборки)
COPY tests/ /app/tests/

# Рабочая директория для тестов
WORKDIR /app/tests

# По умолчанию запускаем все тесты
CMD ["pytest", "test_api.py", "-v", "--tb=short", "--color=yes"]

