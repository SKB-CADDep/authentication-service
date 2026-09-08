# Multi-stage build для оптимизации размера образа

# Стадия 1: Сборка зависимостей
FROM python:3.12-slim AS builder

# Устанавливаем poetry
RUN pip install --no-cache-dir poetry==2.4.2

# Рабочая директория
WORKDIR /app

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем только production-зависимости в переносимое виртуальное окружение
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Стадия 2: Production образ
FROM python:3.12-slim

# Метаданные
LABEL maintainer="lrshlyogin@utz.ru"
LABEL description="UTZ Auth Service with LDAP integration"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH"

# Создаем пользователя для запуска приложения (безопасность)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Рабочая директория
WORKDIR /app

# Копируем готовое окружение без dev-зависимостей и Poetry
COPY --from=builder /app/.venv /app/.venv

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

