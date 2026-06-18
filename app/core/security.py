"""
Модуль криптографии и безопасности.
Обеспечивает создание и валидацию JWT-токенов (Access и Refresh), 
а также безопасное хеширование и проверку паролей с использованием bcrypt.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Контекст для работы с паролями: используем надежный алгоритм хеширования bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Создание Access Token (короткоживущий).
    
    Используется для аутентификации пользователя при каждом запросе к защищенным API.
    
    Args:
        data (dict): Данные (payload), которые будут зашифрованы в токене (например, {"sub": username}).
        expires_delta (timedelta | None): Опциональное время жизни токена. Если не передано, 
                                          используется ACCESS_TOKEN_EXPIRE_MINUTES из настроек.
                                             
    Returns:
        str: Сгенерированная строка JWT-токена.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Добавляем время истечения и тип токена в payload
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Создание Refresh Token (долгоживущий).
    
    Используется для безопасного получения новой пары (Access/Refresh) 
    без необходимости повторного ввода логина и пароля пользователем.
    
    Args:
        data (dict): Данные (payload), которые будут зашифрованы в токене.
        
    Returns:
        str: Сгенерированная строка JWT-токена.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Декодирование и валидация токена.
    
    Проверяет корректность подписи токена с использованием SECRET_KEY 
    и проверяет, не истекло ли время его жизни (поле "exp").
    
    Args:
        token (str): JWT-токен, переданный клиентом.
        
    Returns:
        dict | None: Словарь с данными (payload), если токен валиден. 
                     Если токен недействителен, истек или поврежден, возвращает None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля (для локальных пользователей, если будут).
    
    Сравнивает переданный открытый пароль с захешированным паролем из БД.
    
    Args:
        plain_password (str): Пароль в открытом виде (введенный пользователем).
        hashed_password (str): Хеш пароля, сохраненный в базе данных.
        
    Returns:
        bool: True, если пароли совпадают, иначе False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля.
    
    Превращает открытый пароль в безопасный хеш для сохранения в базе данных.
    
    Args:
        password (str): Пароль в открытом виде.
        
    Returns:
        str: Сгенерированный хеш пароля.
    """
    return pwd_context.hash(password)

