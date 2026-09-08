from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, create_refresh_token
from app.routers import auth
from app.schemas.auth import RefreshTokenRequest, TokenValidationRequest
from app.services.ldap_service import LDAPServiceUnavailable


def _user(active: bool = True):
    return SimpleNamespace(
        username="engineer",
        email="engineer@utz.local",
        full_name="Test Engineer",
        groups=["CN=BalanceUsers,OU=Groups,DC=utz,DC=local"],
        is_active=active,
    )


@pytest.mark.asyncio
async def test_login_returns_service_unavailable_when_ldap_is_down(monkeypatch) -> None:
    def raise_ldap_unavailable(*_args, **_kwargs):
        raise LDAPServiceUnavailable("LDAP request failed")

    monkeypatch.setattr(auth.ldap_service, "authenticate", raise_ldap_unavailable)
    form_data = SimpleNamespace(username="engineer", password="secret")

    with pytest.raises(HTTPException) as exc_info:
        await auth.login(form_data, db=AsyncMock())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Сервис LDAP временно недоступен"


@pytest.mark.asyncio
async def test_login_returns_service_unavailable_when_ldap_times_out(monkeypatch) -> None:
    monkeypatch.setattr(auth.asyncio, "to_thread", AsyncMock(side_effect=TimeoutError))
    form_data = SimpleNamespace(username="engineer", password="secret")

    with pytest.raises(HTTPException) as exc_info:
        await auth.login(form_data, db=AsyncMock())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Сервис LDAP временно недоступен"


@pytest.mark.asyncio
async def test_validate_accepts_active_user_access_token(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_find_user", AsyncMock(return_value=_user()))
    token = create_access_token({"sub": "engineer"})

    result = await auth.validate_token(TokenValidationRequest(token=token), db=AsyncMock())

    assert result.valid is True
    assert result.username == "engineer"
    assert result.full_name == "Test Engineer"


@pytest.mark.asyncio
async def test_validate_rejects_refresh_token_without_database_lookup(monkeypatch) -> None:
    find_user = AsyncMock()
    monkeypatch.setattr(auth, "_find_user", find_user)
    token = create_refresh_token({"sub": "engineer"})

    result = await auth.validate_token(TokenValidationRequest(token=token), db=AsyncMock())

    assert result.valid is False
    find_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_rejects_inactive_user(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_find_user", AsyncMock(return_value=_user(active=False)))
    token = create_access_token({"sub": "engineer"})

    result = await auth.validate_token(TokenValidationRequest(token=token), db=AsyncMock())

    assert result.valid is False


@pytest.mark.asyncio
async def test_protected_auth_route_rejects_refresh_token(monkeypatch) -> None:
    find_user = AsyncMock()
    monkeypatch.setattr(auth, "_find_user", find_user)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(create_refresh_token({"sub": "engineer"}), AsyncMock())

    assert exc_info.value.status_code == 401
    find_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rotates_registered_token_and_preserves_email(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_find_user", AsyncMock(return_value=_user()))
    rotate = AsyncMock(return_value=True)
    monkeypatch.setattr(auth.refresh_token_store, "rotate", rotate)
    old_refresh = create_refresh_token({"sub": "engineer"})

    result = await auth.refresh_token(
        RefreshTokenRequest(refresh_token=old_refresh),
        db=AsyncMock(),
    )

    assert result["access_token"] != old_refresh
    assert result["refresh_token"] != old_refresh
    rotate.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_replayed_token(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_find_user", AsyncMock(return_value=_user()))
    monkeypatch.setattr(auth.refresh_token_store, "rotate", AsyncMock(return_value=False))
    old_refresh = create_refresh_token({"sub": "engineer"})

    with pytest.raises(HTTPException) as exc_info:
        await auth.refresh_token(
            RefreshTokenRequest(refresh_token=old_refresh),
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 401
