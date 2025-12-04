from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    Token, 
    LoginRequest, 
    TokenValidationRequest,
    TokenValidationResponse,
    RefreshTokenRequest
)
from app.schemas.user import UserPublic
from app.services.ldap_service import ldap_service
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя из токена.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_or_create_user(db: AsyncSession, ldap_data: dict) -> User:
    """
    Получить пользователя из БД или создать нового на основе LDAP данных.
    """
    try:
        # Ищем пользователя
        result = await db.execute(
            select(User).where(User.username == ldap_data['username'])
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Обновляем данные из LDAP
            user.email = ldap_data.get('email')
            user.full_name = ldap_data.get('full_name')
            user.cn = ldap_data.get('cn')
            user.groups = ldap_data.get('groups', [])
            user.last_login = datetime.utcnow()
            user.last_sync_from_ldap = datetime.utcnow()
            
            logger.info(f"Updated user {user.username} from LDAP")
        else:
            # Создаем нового пользователя
            user = User(
                username=ldap_data['username'],
                email=ldap_data.get('email'),
                full_name=ldap_data.get('full_name'),
                cn=ldap_data.get('cn'),
                groups=ldap_data.get('groups', []),
                is_active=True,
                is_superuser=False
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
    Аутентификация пользователя через LDAP и выдача JWT токенов.
    """
    # 1. Аутентификация в LDAP
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
    
    # 2. Создаем/обновляем пользователя в БД
    try:
        user = await get_or_create_user(db, ldap_data)
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка при сохранении данных пользователя. Проверьте подключение к базе данных."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован"
        )
    
    # 3. Создаем токены
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
    Валидация токена (для других сервисов).
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
    Получение информации о текущем пользователе.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление access токена с помощью refresh токена.
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
    
    # Создаем новые токены
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
    Получение информации о пользователе по username (для других сервисов).
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

