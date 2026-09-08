from __future__ import annotations

from datetime import datetime, timezone

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings


class RefreshTokenStoreError(RuntimeError):
    """Refresh-token state could not be read or persisted."""


class RefreshTokenStore:
    _ROTATE_SCRIPT = """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        redis.call('DEL', KEYS[1])
        redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])
        return 1
    end
    return 0
    """

    def __init__(self) -> None:
        self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    @staticmethod
    def _key(jti: str) -> str:
        return f"auth:refresh:{jti}"

    @staticmethod
    def _ttl(expires_at: int | float) -> int:
        return max(1, int(expires_at - datetime.now(timezone.utc).timestamp()))

    async def register(self, jti: str, username: str, expires_at: int | float) -> None:
        try:
            await self._client.set(self._key(jti), username, ex=self._ttl(expires_at))
        except RedisError as exc:
            raise RefreshTokenStoreError("Refresh token store is unavailable") from exc

    async def rotate(
        self,
        old_jti: str,
        new_jti: str,
        username: str,
        new_expires_at: int | float,
    ) -> bool:
        try:
            result = await self._client.eval(
                self._ROTATE_SCRIPT,
                2,
                self._key(old_jti),
                self._key(new_jti),
                username,
                self._ttl(new_expires_at),
            )
        except RedisError as exc:
            raise RefreshTokenStoreError("Refresh token store is unavailable") from exc
        return bool(result)

    async def revoke(self, jti: str) -> None:
        try:
            await self._client.delete(self._key(jti))
        except RedisError as exc:
            raise RefreshTokenStoreError("Refresh token store is unavailable") from exc

    async def close(self) -> None:
        await self._client.aclose()


refresh_token_store = RefreshTokenStore()
