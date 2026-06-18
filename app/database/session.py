"""
Модуль настройки подключения к базе данных.
Отвечает за создание асинхронного движка SQLAlchemy, фабрики сессий
и базового класса для ORM-моделей. Также предоставляет зависимость (Dependency)
для получения сессии БД в эндпоинтах FastAPI.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Асинхронный движок SQLAlchemy. Управляет пулом асинхронных соединений с БД.
# Если в настройках включен режим DEBUG, echo=True будет выводить все SQL-запросы в консоль.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG
)

# Фабрика для создания новых асинхронных сессий БД.
# expire_on_commit=False гарантирует, что объекты не будут "устаревать" после коммита,
# что позволяет безопасно обращаться к их атрибутам после закрытия транзакции.
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для всех ORM-моделей приложения.
# Все таблицы (например, User в app/models/user.py) должны наследоваться от этого класса.
Base = declarative_base()


async def get_db():
    """
    Dependency (зависимость) для FastAPI.
    
    Создает новую асинхронную сессию базы данных для каждого входящего запроса 
    и гарантированно закрывает её (возвращает соединение в пул) после завершения 
    обработки запроса, даже если во время выполнения произошла ошибка.
    
    Yields:
        AsyncSession: Объект асинхронной сессии для выполнения SQL-запросов.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

