from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    cn: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    groups: List[str] = []


class UserUpdate(UserCreate):
    last_sync_from_ldap: datetime


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    cn: Optional[str] = None
    groups: List[str] = []
    is_active: bool
    is_superuser: bool
    first_login: datetime
    last_login: datetime
    last_sync_from_ldap: datetime


class UserPublic(BaseModel):
    """Публичная информация о пользователе для других сервисов."""
    model_config = ConfigDict(from_attributes=True)
    
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    cn: Optional[str] = None
    groups: List[str] = []
    is_active: bool

