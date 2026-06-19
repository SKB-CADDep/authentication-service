"""
Модуль Pydantic-схем для пользователей.
Содержит модели для валидации данных пользователя при создании, обновлении,
а также для сериализации данных из БД (ORM) в ответы API.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Базовые атрибуты пользователя."""
    username: str
    email: EmailStr | None = None
    full_name: str | None = None


class UserCreate(UserBase):
    """Схема для создания нового пользователя (данные, приходящие из LDAP)."""
    cn: str | None = None
    department: str | None = None
    title: str | None = None
    phone: str | None = None
    groups: list[str] = []


class UserUpdate(UserCreate):
    """Схема для обновления профиля существующего пользователя."""
    last_sync_from_ldap: datetime


class UserInDB(UserBase):
    """Полная схема пользователя из базы данных (для внутреннего использования)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    cn: str | None = None
    groups: list[str] = []
    is_active: bool
    is_superuser: bool
    first_login: datetime
    last_login: datetime
    last_sync_from_ldap: datetime


class UserPublic(BaseModel):
    """Публичная информация о пользователе для отдачи на фронтенд или в другие сервисы."""
    model_config = ConfigDict(from_attributes=True)
    
    username: str
    email: str | None = None
    full_name: str | None = None
    cn: str | None = None
    groups: list[str] = []
    is_active: bool

