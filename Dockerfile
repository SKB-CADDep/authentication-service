# Multi-stage build для оптимизации размера образа

# Стадия 1: Сборка зависимостей
FROM python:3.12-slim as builder

# Устанавливаем poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Рабочая директория
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Экспортируем зависимости в requirements.txt
RUN poetry config virtualenvs.create false && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes --with dev || \
    (poetry install --no-interaction --no-ansi && poetry export -f requirements.txt --output requirements.txt --without-hashes)

# Стадия 2: Production образ
FROM python:3.12-slim

# Метаданные
LABEL maintainer="lrshlyogin@utz.ru"
LABEL description="UTZ Auth Service with LDAP integration"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создаем пользователя для запуска приложения (безопасность)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Рабочая директория
WORKDIR /app

# Копируем requirements.txt из builder stage
COPY --from=builder /app/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY --chown=appuser:appuser . .

# Даем права на выполнение скриптов
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# Переключаемся на непривилегированного пользователя
USER appuser

# Expose порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

