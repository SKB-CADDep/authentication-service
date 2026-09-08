import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    Token,
    TokenValidationRequest,
    TokenValidationResponse,
)
from app.schemas.user import UserPublic
from app.services.ldap_service import LDAPServiceUnavailable, ldap_service
from app.services.refresh_token_store import (
    RefreshTokenStoreError,
    refresh_token_store,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _credentials_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _find_user(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


def _token_store_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Refresh token store is unavailable",
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя из токена.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise _credentials_exception()

    username: str = payload.get("sub")
    if not username:
        raise _credentials_exception()

    try:
        user = await _find_user(db, username)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User store is unavailable",
        ) from exc

    if user is None or not user.is_active:
        raise _credentials_exception()

    return user


async def get_or_create_user(db: AsyncSession, ldap_data: dict) -> User:
    """
    Получить пользователя из БД или создать нового на основе LDAP данных.
    """
    try:
        # Ищем пользователя
        result = await db.execute(select(User).where(User.username == ldap_data["username"]))
        user = result.scalar_one_or_none()

        if user:
            # Обновляем данные из LDAP
            user.email = ldap_data.get("email")
            user.full_name = ldap_data.get("full_name")
            user.cn = ldap_data.get("cn")
            user.groups = ldap_data.get("groups", [])
            user.last_login = datetime.utcnow()
            user.last_sync_from_ldap = datetime.utcnow()

            logger.info(f"Updated user {user.username} from LDAP")
        else:
            # Создаем нового пользователя
            user = User(
                username=ldap_data["username"],
                email=ldap_data.get("email"),
                full_name=ldap_data.get("full_name"),
                cn=ldap_data.get("cn"),
                groups=ldap_data.get("groups", []),
                is_active=True,
                is_superuser=False,
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
            detail="База данных недоступна. Пожалуйста, убедитесь, что PostgreSQL запущен и миграции выполнены.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_or_create_user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при работе с базой данных",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация пользователя через LDAP и выдача JWT токенов.
    """
    # 1. Аутентификация в LDAP
    try:
        ldap_data = await asyncio.wait_for(
            asyncio.to_thread(
                ldap_service.authenticate,
                form_data.username,
                form_data.password,
            ),
            timeout=settings.LDAP_TIMEOUT_SECONDS,
        )
    except (TimeoutError, LDAPServiceUnavailable) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис LDAP временно недоступен",
        ) from exc

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
            detail="Ошибка при сохранении данных пользователя. Проверьте подключение к базе данных.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь заблокирован"
        )

    # 3. Создаем токены
    access_token = create_access_token(data={"sub": user.username, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.username})

    refresh_payload = decode_token(refresh_token)
    try:
        await refresh_token_store.register(
            refresh_payload["jti"],
            user.username,
            refresh_payload["exp"],
        )
    except RefreshTokenStoreError as exc:
        logger.error("Failed to persist refresh token for %s", user.username)
        raise _token_store_unavailable() from exc

    logger.info(f"User {user.username} logged in successfully")

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(
    request: TokenValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Валидация токена (для других сервисов).
    """
    payload = decode_token(request.token)

    if not payload or payload.get("type") != "access":
        return TokenValidationResponse(valid=False, message="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        return TokenValidationResponse(valid=False, message="Invalid token payload")

    try:
        user = await _find_user(db, username)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User store is unavailable",
        ) from exc

    if user is None or not user.is_active:
        return TokenValidationResponse(valid=False, message="User is inactive or missing")

    return TokenValidationResponse(
        valid=True,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        groups=user.groups or [],
    )


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Обновление access токена с помощью refresh токена.
    """
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise _credentials_exception("Invalid refresh token")

    username = payload.get("sub")
    old_jti = payload.get("jti")
    if not username or not old_jti:
        raise _credentials_exception("Invalid refresh token")

    try:
        user = await _find_user(db, username)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User store is unavailable",
        ) from exc

    if user is None or not user.is_active:
        raise _credentials_exception("Invalid refresh token")

    # Создаем новые токены
    access_token = create_access_token(data={"sub": username, "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": username})

    new_refresh_payload = decode_token(new_refresh_token)
    try:
        rotated = await refresh_token_store.rotate(
            old_jti,
            new_refresh_payload["jti"],
            username,
            new_refresh_payload["exp"],
        )
    except RefreshTokenStoreError as exc:
        raise _token_store_unavailable() from exc

    if not rotated:
        raise _credentials_exception("Invalid or already used refresh token")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: RefreshTokenRequest) -> Response:
    payload = decode_token(request.refresh_token)
    if payload and payload.get("type") == "refresh" and payload.get("jti"):
        try:
            await refresh_token_store.revoke(payload["jti"])
        except RefreshTokenStoreError as exc:
            raise _token_store_unavailable() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/{username}", response_model=UserPublic)
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получение информации о пользователе по username (для других сервисов).
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
