"""
Главный модуль приложения (Entrypoint).
Инициализирует FastAPI, настраивает CORS, подключает роутеры и статику,
а также управляет жизненным циклом приложения (подключение к БД).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.database.session import Base, engine
from app.models.user import User  # Импорт обязателен для регистрации таблиц в Base.metadata
from app.routers import auth, frontend

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения (Lifespan).
    Заменяет устаревший декоратор @app.on_event("startup") и "shutdown".
    Создает таблицы и проверяет БД при запуске, закрывает соединения при остановке.
    
    Args:
        app (FastAPI): Экземпляр приложения FastAPI.
        
    Yields:
        None: Передает управление работающему приложению.
    """
    # --- Выполняется ПРИ СТАРТЕ приложения ---
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")

    try:
        # Пытаемся подключиться к БД
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("⚠️  Please ensure:")
        logger.error("   1. PostgreSQL is running")
        logger.error("   2. DATABASE_URL is correctly configured in .env file")
        logger.error("   3. Database exists and migrations are applied")
        logger.error(f"   Current DATABASE_URL: {settings.DATABASE_URL}")
        
    yield  # 🚀 Здесь приложение запускается и обрабатывает запросы пользователей
    
    # --- Выполняется ПРИ ОСТАНОВКЕ приложения ---
    await engine.dispose()
    logger.info("🛑 Database connection closed")


# Инициализация приложения с новым механизмом lifespan
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Подключаем статические файлы
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(frontend.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint с проверкой подключения к БД.
    Используется для мониторинга состояния приложения.
    
    Returns:
        dict[str, str]: Словарь со статусом приложения и базы данных.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
