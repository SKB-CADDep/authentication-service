from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime

from app.database.session import Base


class User(Base):
    """
    Кеш пользователей из LDAP.
    Хранит только базовую информацию для быстрого доступа.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # sAMAccountName
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)  # displayName
    cn = Column(String, nullable=True)  # Common Name
    
    # LDAP Groups
    groups = Column(JSON, default=list)  # Список групп из memberOf
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Метаданные
    first_login = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_from_ldap = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.username}>"

