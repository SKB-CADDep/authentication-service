"""
Модуль Pydantic-схем для аутентификации.
Содержит модели данных для запросов и ответов, связанных с токенами (JWT) и логином.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Схема ответа при успешной генерации токенов."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Схема полезной нагрузки (payload), извлекаемой из токена."""
    username: str | None = None


class LoginRequest(BaseModel):
    """Схема запроса на авторизацию (JSON)."""
    username: str
    password: str


class TokenValidationRequest(BaseModel):
    """Схема запроса для межсервисной валидации токена."""
    token: str


class TokenValidationResponse(BaseModel):
    """Схема ответа при межсервисной валидации токена."""
    valid: bool
    username: str | None = None
    message: str | None = None


class RefreshTokenRequest(BaseModel):
    """Схема запроса на обновление (ротацию) токенов."""
    refresh_token: str

