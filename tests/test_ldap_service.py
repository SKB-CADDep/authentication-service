from app.services.ldap_service import LDAPService


def test_ldap_service_parses_ldap_url(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ldap_service.settings.LDAP_SERVER", "ldap://dc03.utz.local")
    monkeypatch.setattr("app.services.ldap_service.settings.LDAP_PORT", 389)

    service = LDAPService()

    assert service.server.host == "dc03.utz.local"
    assert service.server.port == 389
    assert service.server.ssl is False


def test_ldap_service_enables_ssl_for_ldaps_url(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ldap_service.settings.LDAP_SERVER", "ldaps://ldap.utz.local:636")

    service = LDAPService()

    assert service.server.host == "ldap.utz.local"
    assert service.server.port == 636
    assert service.server.ssl is True
