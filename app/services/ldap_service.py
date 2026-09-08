import logging
from urllib.parse import urlparse

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException, LDAPInvalidCredentialsResult
from ldap3.utils.conv import escape_filter_chars

from app.core.config import settings


logger = logging.getLogger(__name__)


class LDAPServiceUnavailable(RuntimeError):
    """LDAP cannot currently process authentication requests."""


class LDAPService:
    def __init__(self):
        server_url = settings.LDAP_SERVER
        if "://" not in server_url:
            server_url = f"ldap://{server_url}"

        parsed_url = urlparse(server_url)
        if parsed_url.scheme not in {"ldap", "ldaps"} or not parsed_url.hostname:
            raise ValueError("LDAP_SERVER must contain a valid ldap:// or ldaps:// address")

        self.server = Server(
            parsed_url.hostname,
            port=parsed_url.port or settings.LDAP_PORT,
            use_ssl=parsed_url.scheme == "ldaps",
            get_info=ALL,
            connect_timeout=settings.LDAP_TIMEOUT_SECONDS,
        )

    def authenticate(self, username: str, password: str) -> dict | None:
        """
        Аутентификация пользователя через LDAP и получение его данных.

        Returns:
            Dict с данными пользователя или None если аутентификация не удалась
        """
        if not password:
            logger.warning(f"Empty password provided for user {username}")
            return None

        # Формируем user principal name
        user_principal = f"{username}{settings.LDAP_USER_SUFFIX}"

        conn = None
        try:
            # Пытаемся выполнить BIND (это и есть проверка пароля)
            conn = Connection(
                self.server,
                user=user_principal,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
                receive_timeout=settings.LDAP_TIMEOUT_SECONDS,
            )

            logger.info(f"✅ User {username} authenticated successfully")

            # Получаем данные пользователя
            user_data = self._get_user_data(conn, username)

            return user_data

        except LDAPInvalidCredentialsResult:
            logger.warning(f"❌ Invalid credentials for user {username}")
            return None
        except LDAPBindError as e:
            logger.error(f"❌ LDAP bind error for user {username}: {e}")
            raise LDAPServiceUnavailable("LDAP bind failed") from e
        except LDAPException as e:
            logger.error(f"❌ LDAP error: {e}")
            raise LDAPServiceUnavailable("LDAP request failed") from e
        except LDAPServiceUnavailable:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error during authentication: {e}")
            raise LDAPServiceUnavailable("LDAP request failed") from e
        finally:
            if conn is not None:
                conn.unbind()

    def _get_user_data(self, conn: Connection, username: str) -> dict | None:
        """
        Получение данных пользователя из LDAP.
        """
        search_filter = f"(sAMAccountName={escape_filter_chars(username)})"
        attributes = [
            "cn",
            "mail",
            "displayName",
            "sAMAccountName",
            "memberOf",
            "department",
            "title",
            "telephoneNumber",
        ]

        try:
            conn.search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes,
            )

            if not conn.entries:
                logger.warning(f"User {username} not found in LDAP")
                return None

            user_entry = conn.entries[0]

            # Обрабатываем группы
            groups = []
            if hasattr(user_entry, "memberOf"):
                groups = [str(group) for group in user_entry.memberOf]

            user_data = {
                "username": str(user_entry.sAMAccountName),
                "email": str(user_entry.mail) if hasattr(user_entry, "mail") else None,
                "full_name": str(user_entry.displayName)
                if hasattr(user_entry, "displayName")
                else None,
                "cn": str(user_entry.cn) if hasattr(user_entry, "cn") else None,
                "department": str(user_entry.department)
                if hasattr(user_entry, "department")
                else None,
                "title": str(user_entry.title) if hasattr(user_entry, "title") else None,
                "phone": str(user_entry.telephoneNumber)
                if hasattr(user_entry, "telephoneNumber")
                else None,
                "groups": groups,
            }

            logger.info(f"Retrieved data for user {username}: {user_data['full_name']}")
            return user_data

        except LDAPException as e:
            logger.error(f"Error getting user data: {e}")
            raise LDAPServiceUnavailable("LDAP search failed") from e
        except Exception as e:
            logger.error(f"Unexpected error getting user data: {e}")
            raise LDAPServiceUnavailable("LDAP search failed") from e

    def check_group_membership(self, groups: list[str], required_group: str) -> bool:
        """
        Проверка принадлежности к группе.
        """
        return any(required_group.lower() in group.lower() for group in groups)


ldap_service = LDAPService()
