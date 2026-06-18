"""
Модуль маршрутизации аутентификации (API Endpoints).
Обеспечивает точки входа для авторизации пользователей (взаимодействие с LDAP),
генерации, обновления и межсервисной валидации JWT-токенов, 
а также получения профиля пользователя.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,  # Оставлено, если используется в других местах/документации
    RefreshTokenRequest,
    Token,
    TokenValidationRequest,
    TokenValidationResponse,
)
from app.schemas.user import UserPublic
from app.services.ldap_service import ldap_service

logger = logging.getLogger(__name__)

# Роутер FastAPI для группировки эндпоинтов с префиксом /auth
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Схема безопасности для Swagger UI и извлечения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI Dependency (зависимость) для получения текущего пользователя из токена.
    Извлекает JWT из заголовка, валидирует его и возвращает объект пользователя из БД.
    
    Args:
        token (str): JWT Access токен (передается автоматически).
        db (AsyncSession): Сессия базы данных.
        
    Returns:
        User: ORM-модель текущего пользователя.
        
    Raises:
        HTTPException: 401 Unauthorized, если токен невалиден или пользователь удален из БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_or_create_user(db: AsyncSession, ldap_data: dict[str, Any]) -> User:
    """
    Получить пользователя из БД или создать нового на основе LDAP данных (Upsert).
    Выступает в роли синхронизатора локального кэша и AD.
    
    Args:
        db (AsyncSession): Сессия базы данных.
        ldap_data (dict): Словарь с атрибутами пользователя, полученный от LDAP.
        
    Returns:
        User: Обновленный или созданный объект пользователя.
        
    Raises:
        HTTPException: 503 или 500 при проблемах с подключением к БД.
    """
    try:
        # Ищем пользователя
        result = await db.execute(
            select(User).where(User.username == ldap_data['username'])
        )
        user = result.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        
        if user:
            # Обновляем данные из LDAP (если они изменились в AD с прошлого входа)
            user.email = ldap_data.get('email')
            user.full_name = ldap_data.get('full_name')
            user.cn = ldap_data.get('cn')
            user.groups = ldap_data.get('groups', [])
            user.last_login = now
            user.last_sync_from_ldap = now
            
            logger.info(f"Updated user {user.username} from LDAP")
        else:
            # Создаем нового пользователя при первом входе
            user = User(
                username=ldap_data['username'],
                email=ldap_data.get('email'),
                full_name=ldap_data.get('full_name'),
                cn=ldap_data.get('cn'),
                groups=ldap_data.get('groups', []),
                is_active=True,
                is_superuser=False,
                first_login=now,
                last_login=now,
                last_sync_from_ldap=now
            )
            db.add(user)
            logger.info(f"Created new user {user.username} from LDAP")
        
        await db.commit()
        await db.refresh(user)
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_or_create_user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="База данных недоступна. Пожалуйста, убедитесь, что PostgreSQL запущен и миграции выполнены."
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_or_create_user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при работе с базой данных"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Эндпоинт аутентификации пользователя через LDAP и выдачи JWT токенов.
    Ожидает данные формы (application/x-www-form-urlencoded).
    """
    # 1. Аутентификация в LDAP: проверяем связку логин/пароль в AD
    ldap_data = ldap_service.authenticate(
        form_data.username,
        form_data.password
    )
    
    if not ldap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Создаем/обновляем пользователя в локальной БД (кэшируем профиль)
    try:
        user = await get_or_create_user(db, ldap_data)
    except HTTPException:
        # Пробрасываем HTTPException дальше (например, ошибку БД)
        raise
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка при сохранении данных пользователя. Проверьте подключение к базе данных."
        )
    
    # Проверка статуса учетной записи в локальной базе
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован"
        )
    
    # 3. Создаем JWT токены для авторизации в микросервисах
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(request: TokenValidationRequest):
    """
    Межсервисная валидация токена.
    Используется другими микросервисами для проверки валидности токена
    без необходимости дублировать логику парсинга и секретный ключ JWT.
    """
    payload = decode_token(request.token)
    
    if not payload:
        return TokenValidationResponse(
            valid=False,
            message="Invalid or expired token"
        )
    
    username = payload.get("sub")
    if not username:
        return TokenValidationResponse(
            valid=False,
            message="Invalid token payload"
        )
    
    return TokenValidationResponse(
        valid=True,
        username=username
    )


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о текущем (авторизованном) пользователе.
    Возвращает данные профиля на основе переданного Bearer токена.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Обновление пары токенов (access и refresh).
    Позволяет пользователю оставаться авторизованным без повторного ввода пароля.
    Ожидает валидный (не протухший) refresh токен.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise credentials_exception
    
    username = payload.get("sub")
    if not username:
        raise credentials_exception
    
    # Создаем новые токены (ротация)
    access_token = create_access_token(data={"sub": username})
    new_refresh_token = create_refresh_token(data={"sub": username})
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/users/{username}", response_model=UserPublic)
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о пользователе по его username.
    Защищенный эндпоинт (требует авторизации). Используется другими сервисами,
    которым нужны метаданные или список групп конкретного пользователя.
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

