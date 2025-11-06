from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    DATABASE_URL: str

    # LDAP
    LDAP_SERVER: str = "ldap://dc03.utz.local"
    LDAP_PORT: int = 389
    LDAP_BASE_DN: str = "DC=utz,DC=local"
    LDAP_USER_SUFFIX: str = "@utz.local"
    LDAP_BIND_USER: str = ""
    LDAP_BIND_PASSWORD: str = ""

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # App
    APP_NAME: str = "UTZ Auth Service"
    DEBUG: bool = False

    @property
    def allowed_origins_list(self) -> List[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()

