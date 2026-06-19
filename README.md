# Authentication Service

Сервис аутентификации с использованием LDAP (Active Directory) и JWT токенов. Включает веб-интерфейс для входа в систему и REST API для интеграции с другими сервисами платформы.

## Особенности

- **LDAP аутентификация** через Active Directory
- **JWT токены** (access и refresh токены)
- **Кеширование пользователей** в PostgreSQL
- **Автоматическая синхронизация** данных из LDAP
- **Поддержка групп пользователей** из LDAP
- **Веб-интерфейс** для входа в систему
- **REST API** для интеграции с другими сервисами
- **Docker поддержка** для легкого развертывания

## Структура проекта

> Автоматически сгенерировано: `2026-06-17` | Директорий: **10** | Файлов: **29**

```text
authentication-service/
├── 📁 app/
│   ├── 📁 core/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 config.py              # Конфигурация приложения
│   │   └── 🐍 security.py            # JWT токены и безопасность
│   ├── 📁 database/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 session.py             # Настройка базы данных
│   ├── 📁 models/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 user.py                # SQLAlchemy модель пользователя
│   ├── 📁 routers/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 auth.py                # API endpoints для аутентификации
│   │   └── 🐍 frontend.py            # Frontend роутеры (HTML страницы)
│   ├── 📁 schemas/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 auth.py                # Pydantic схемы для аутентификации
│   │   └── 🐍 user.py                # Pydantic схемы для пользователя
│   ├── 📁 services/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 ldap_service.py        # LDAP аутентификация
│   │   └── 🐍 token_service.py       # Логика работы с токенами
│   ├── 🐍 __init__.py
│   └── 🐍 main.py                    # Точка входа приложения
├── 📁 static/
│   └── 📁 js/
│       └── 📜 auth.js                # JavaScript для авторизации
├── 📁 templates/
│   └── 🌐 login.html                 # Страница входа
├── 📄 .dockerignore
├── 🙈 .gitignore
├── ⚙️ docker-compose.yml             # Docker Compose конфигурация
├── 🐳 Dockerfile                     # Docker образ
├── 📄 env.example                    # Пример конфигурации
├── 🐍 generate_tree.py               # Генератор дерева проекта
├── 🔒 poetry.lock
├── 📦 pyproject.toml                 # Зависимости проекта
└── 📖 README.md
```
<details>
<summary>🚫 Игнорируемые директории</summary>
<code>*.egg-info</code>, <code>.eggs</code>, <code>.env</code>, <code>.git</code>, <code>.idea</code>, <code>.mypy_cache</code>, <code>.pytest_cache</code>, <code>.ruff_cache</code>, <code>.tox</code>, <code>.venv</code>, <code>__pycache__</code>, <code>build</code>, <code>dist</code>, <code>env</code>, <code>migrations</code>, <code>node_modules</code>, <code>venv</code>
</details>

## Требования

- Python 3.12+
- PostgreSQL 15+
- Poetry (для управления зависимостями)
- Docker и Docker Compose (опционально, для контейнеризации)
- Доступ к LDAP/Active Directory серверу

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd authentication-service
```

### 2. Установка зависимостей

```bash
# Установка Poetry (если еще не установлен)
curl -sSL https://install.python-poetry.org | python3 -

# Установка зависимостей проекта
poetry install
```

### 3. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и настройте переменные:

```bash
cp env.example .env
```

Отредактируйте `.env` файл:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/auth_db

# LDAP
LDAP_SERVER=ldap://dc03.utz.local
LDAP_PORT=389
LDAP_BASE_DN=DC=utz,DC=local
LDAP_USER_SUFFIX=@utz.local
LDAP_BIND_USER=
LDAP_BIND_PASSWORD=

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (опционально)
REDIS_URL=redis://localhost:6379/0

# CORS
ALLOWED_ORIGINS=*

# App
APP_NAME=UTZ Auth Service
DEBUG=False
```

** Важно:** Измените `SECRET_KEY` на случайную строку для production!

## 🗄️ Настройка базы данных

### Вариант 1: Использование Docker Compose (рекомендуется)

```bash
# Запустите PostgreSQL
docker-compose up -d auth_db

# Дождитесь, пока база данных будет готова
docker-compose ps
```

### Вариант 2: Локальный PostgreSQL

1. Установите PostgreSQL
2. Создайте базу данных:

```sql
CREATE DATABASE auth_db;
CREATE USER postgres WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE auth_db TO postgres;
```

3. Обновите `DATABASE_URL` в `.env` файле

### Инициализация миграций Alembic

```bash
# Инициализация Alembic (если еще не сделано)
poetry run alembic init alembic

# Настройте alembic/env.py:
# Добавьте в начало файла:
from app.database.session import Base, engine
from app.models.user import User
from app.core.config import settings

# В функции run_migrations_online():
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

### Создание и применение миграций

```bash
# Создание миграции
poetry run alembic revision --autogenerate -m "Initial migration"

# Применение миграций
poetry run alembic upgrade head
```

## Запуск приложения

### Локальный запуск

```bash
# Активация виртуального окружения
poetry shell

# Запуск сервера
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу: `http://localhost:8000`

### Запуск через Docker Compose

```bash
# Запуск всех сервисов (PostgreSQL, Redis, Auth Service)
docker-compose up -d

# Просмотр логов
docker-compose logs -f auth_service

# Остановка сервисов
docker-compose down
```

## API Endpoints

### Frontend (HTML страницы)

- `GET /` - Главная страница (защищенная)
- `GET /login` - Страница входа в систему

### Authentication API

- `POST /auth/login` - Аутентификация через LDAP и получение JWT токенов
  ```json
  {
    "username": "lrshlyogin",
    "password": "password"
  }
  ```
  Ответ:
  ```json
  {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
  ```

- `POST /auth/validate` - Валидация токена (для других сервисов)
  ```json
  {
    "token": "jwt_token_here"
  }
  ```

- `GET /auth/me` - Получение информации о текущем пользователе
  - Требуется: `Authorization: Bearer <access_token>`

- `POST /auth/refresh` - Обновление access токена с помощью refresh токена
  ```json
  {
    "refresh_token": "refresh_token_here"
  }
  ```

- `GET /auth/users/{username}` - Получение информации о пользователе по username
  - Требуется: `Authorization: Bearer <access_token>`

### Health Check

- `GET /health` - Проверка здоровья сервиса и подключения к БД

## Использование API

### Пример авторизации (cURL)

```bash
# Вход в систему
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=lrshlyogin&password=your_password"

# Получение информации о пользователе
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Пример авторизации (JavaScript)

```javascript
// Вход в систему
const formData = new URLSearchParams();
formData.append('username', 'lrshlyogin');
formData.append('password', 'password');

const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: formData
});

const data = await response.json();
localStorage.setItem('access_token', data.access_token);

// Использование токена
const userResponse = await fetch('http://localhost:8000/auth/me', {
  headers: {
    'Authorization': `Bearer ${data.access_token}`
  }
});
```

## Docker

### Сборка образа

```bash
docker build -t auth-service:latest .
```

### Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Остановка с удалением volumes
docker-compose down -v
```

### Переменные окружения для Docker

Все переменные окружения можно настроить в `.env` файле или передать через `docker-compose.yml`.

## Решение проблем

### Ошибка: "Database connection failed"

**Проблема:** База данных недоступна.

**Решение:**
1. Убедитесь, что PostgreSQL запущен:
   ```bash
   # Проверка через Docker
   docker ps | grep postgres
   
   # Или проверка локального PostgreSQL
   pg_isready
   ```

2. Проверьте `DATABASE_URL` в `.env` файле

3. Убедитесь, что база данных создана:
   ```sql
   CREATE DATABASE auth_db;
   ```

4. Примените миграции:
   ```bash
   poetry run alembic upgrade head
   ```

### Ошибка: "email-validator is not installed"

**Решение:**
```bash
poetry add email-validator
poetry install
```

### Ошибка: "Invalid credentials" при LDAP аутентификации

**Проверьте:**
1. Правильность `LDAP_SERVER` в `.env`
2. Доступность LDAP сервера из сети
3. Правильность `LDAP_USER_SUFFIX` (должен быть `@domain.local`)
4. Правильность имени пользователя и пароля

### Ошибка: "ModuleNotFoundError"

**Решение:**
```bash
# Установите все зависимости
poetry install

# Или обновите зависимости
poetry update
```

## Логирование

Приложение логирует все важные события:
- Успешная/неуспешная аутентификация
- Ошибки подключения к БД
- Создание/обновление пользователей

Логи выводятся в консоль в формате:
```
2025-11-06 10:42:38,099 - app.services.ldap_service - INFO - ✅ User lrshlyogin authenticated successfully
```

## Безопасность

- **JWT токены** с настраиваемым временем жизни
- **HTTPS** рекомендуется для production
- **CORS** настраивается через переменные окружения
- **Пароли** не хранятся в БД (проверка через LDAP)
- **Secret Key** должен быть уникальным и секретным

## Дополнительная информация

### Структура JWT токена

Access токен содержит:
- `sub` - username пользователя
- `email` - email пользователя
- `exp` - время истечения
- `type` - тип токена ("access")

Refresh токен содержит:
- `sub` - username пользователя
- `exp` - время истечения
- `type` - тип токена ("refresh")

### Хранение пользователей

Пользователи кешируются в PostgreSQL для быстрого доступа. Данные автоматически синхронизируются из LDAP при каждом входе.

### Группы пользователей

Группы из LDAP (`memberOf`) сохраняются в БД и доступны через API для проверки прав доступа в других сервисах.

## Вклад в проект

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## Лицензия

Этот проект создан для внутреннего использования УТЗ.

## Авторы

- **lrshlyogin** - *Initial work*

## Поддержка

При возникновении проблем создайте Issue в репозитории проекта.

