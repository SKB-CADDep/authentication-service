"""
Модуль конфигурации приложения.

Отвечает за загрузку и валидацию всех настроек микросервиса из переменных окружения 
и файла .env с использованием Pydantic.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Главный класс настроек приложения.
    
    Определяет параметры подключения к инфраструктуре (БД, LDAP, Redis), 
    а также настройки безопасности (JWT, CORS).
    """
    
    # Конфигурация Pydantic для чтения .env файла и игнорирования лишних переменных
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # --- База данных ---
    DATABASE_URL: str = Field(
        ..., 
        description="Строка подключения к основной базе данных (PostgreSQL)"
    )

    # --- LDAP: Интеграция с Active Directory ---
    LDAP_SERVER: str = Field(default="ldap://dc03.utz.local", description="URL сервера LDAP")
    LDAP_PORT: int = Field(default=389, description="Порт подключения к серверу")
    LDAP_BASE_DN: str = Field(default="DC=utz,DC=local", description="Базовый путь для поиска пользователей")
    LDAP_USER_SUFFIX: str = Field(default="@utz.local", description="Суффикс домена для логинов")
    LDAP_BIND_USER: str = Field(default="", description="Имя служебного пользователя для подключения")
    LDAP_BIND_PASSWORD: str = Field(default="", description="Пароль служебного пользователя")

    # --- JWT и Безопасность ---
    SECRET_KEY: str = Field(
        ..., 
        description="Уникальный криптографический ключ для подписи токенов"
    )
    ALGORITHM: str = Field(default="HS256", description="Алгоритм шифрования токена")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Время жизни Access-токена (в минутах)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Время жизни Refresh-токена (в днях)")

    # --- Redis ---
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", 
        description="Строка подключения к Redis (кэш/сессии/blacklists)"
    )

    # --- Общие настройки и Сеть ---
    ALLOWED_ORIGINS: str = Field(
        default="*", 
        description="Разрешенные домены для CORS (указывать через запятую)"
    )
    APP_NAME: str = Field(default="UTZ Auth Service", description="Название микросервиса")
    DEBUG: bool = Field(default=False, description="Включение режима отладки")

    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Преобразует строковое значение ALLOWED_ORIGINS в список строк.
        Это необходимо для корректной настройки CORS middleware в FastAPI.
        
        Returns:
            list[str]: Список разрешенных доменов для кросс-доменных запросов.
            
        Пример:
            В .env: ALLOWED_ORIGINS="http://localhost:3000, https://example.com"
            Возвращает: ["http://localhost:3000", "https://example.com"]
        """
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Глобальный объект настроек, который импортируется в другие модули приложения
settings = Settings()

