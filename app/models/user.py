"""
Модуль ORM-моделей базы данных для пользователей.
Определяет структуру таблицы 'users' с использованием SQLAlchemy.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from app.database.session import Base


def get_utcnow() -> datetime:
    """
    Возвращает текущее время в UTC. 
    Используется вместо устаревшего в Python 3.12 метода datetime.utcnow().
    """
    return datetime.now(timezone.utc)


class User(Base):
    """
    Кеш пользователей из LDAP.
    Хранит только базовую информацию для быстрого доступа, чтобы не делать 
    запросы к LDAP-серверу при каждой проверке токена или прав пользователя.
    
    Атрибуты сопоставляются с полями Active Directory (sAMAccountName, displayName и т.д.).
    """
    __tablename__ = "users"

    # Основные идентификаторы
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # Логин в AD (sAMAccountName)
    email = Column(String, unique=True, index=True, nullable=True)      # Почта из AD
    full_name = Column(String, nullable=True)                           # Отображаемое имя (displayName)
    cn = Column(String, nullable=True)                                  # Common Name
    
    # LDAP Groups
    # Хранит список групп (memberOf) в виде JSON-массива. 
    # Позволяет реализовать RBAC (Role-Based Access Control) без дополнительных таблиц.
    groups = Column(JSON, default=list)
    
    # Статус пользователя в системе
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Метаданные для аудита
    first_login = Column(DateTime, default=get_utcnow)
    last_login = Column(DateTime, default=get_utcnow, onupdate=get_utcnow)
    last_sync_from_ldap = Column(DateTime, default=get_utcnow, onupdate=get_utcnow)
    
    # -----------------------------------------------------------------------
    # ДОКУМЕНТАЦИЯ ПО СВЯЗЯМ (Relationships)
    # -----------------------------------------------------------------------
    # На данный момент таблица `users` является плоской (flat) и выступает
    # в роли изолированного кэша данных из LDAP. Строгих связей (Foreign Keys) 
    # с другими таблицами в данном микросервисе нет.
    #
    # ПРИМЕРЫ возможных связей на будущее (для выполнения архитектурных требований):
    #
    # 1. One-to-Many (Один ко многим): 
    #    Связь с таблицей сессий (UserSession). Один пользователь — много сессий.
    #    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    #
    # 2. Many-to-Many (Многие ко многим): 
    #    Связь с таблицей ролей или материалов (в зависимости от домена) через промежуточную таблицу.
    #    roles = relationship("Role", secondary="user_roles", back_populates="users")
    # -----------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Строковое представление объекта (удобно для отладки и логов).
        """
        return f"<User {self.username}>"

