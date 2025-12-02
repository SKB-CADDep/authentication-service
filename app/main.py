from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
from sqlalchemy import text

from app.core.config import settings
from app.routers import auth, frontend
from app.database.session import engine, Base
from app.models.user import User

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).parent.parent

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
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


@app.on_event("startup")
async def startup_event():
    """
    Проверка подключения к базе данных при старте приложения.
    """
    logger = logging.getLogger(__name__)
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


@app.get("/health")
async def health_check():
    """
    Health check endpoint с проверкой подключения к БД.
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
