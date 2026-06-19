"""
Модуль для работы с сервером LDAP (Active Directory).
Обеспечивает проверку учетных данных (BIND) и извлечение профиля пользователя.
"""

import logging
from typing import Any

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException, LDAPInvalidCredentialsResult

from app.core.config import settings

logger = logging.getLogger(__name__)


class LDAPService:
    """
    Сервис для взаимодействия с сервером LDAP (Active Directory).
    
    Предоставляет методы для аутентификации пользователей, извлечения их
    атрибутов и проверки принадлежности к группам.
    """

    def __init__(self) -> None:
        """
        Инициализирует объект сервера LDAP, используя параметры из глобальных настроек.
        """
        self.server = Server(
            settings.LDAP_SERVER,
            port=settings.LDAP_PORT,
            get_info=ALL
        )
    
    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """
        Аутентификация пользователя через LDAP и получение его данных.
        
        Args:
            username (str): Логин пользователя (sAMAccountName).
            password (str): Пароль пользователя.
            
        Returns:
            dict[str, Any] | None: Словарь с данными пользователя, 
                                   или None, если аутентификация не удалась.
        """
        if not password:
            logger.warning(f"Empty password provided for user {username}")
            return None
        
        # Формируем user principal name
        user_principal = f"{username}{settings.LDAP_USER_SUFFIX}"
        
        try:
            # Пытаемся выполнить BIND (это и есть проверка пароля)
            conn = Connection(
                self.server,
                user=user_principal,
                password=password,
                auto_bind=True
            )
            
            logger.info(f"✅ User {username} authenticated successfully")
            
            # Получаем данные пользователя
            user_data = self._get_user_data(conn, username)
            
            conn.unbind()
            return user_data
            
        except LDAPInvalidCredentialsResult:
            logger.warning(f"❌ Invalid credentials for user {username}")
            return None
        except LDAPBindError as e:
            logger.error(f"❌ LDAP bind error for user {username}: {e}")
            return None
        except LDAPException as e:
            logger.error(f"❌ LDAP error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during authentication: {e}")
            return None
    
    def _get_user_data(self, conn: Connection, username: str) -> dict[str, Any] | None:
        """
        Получение атрибутов пользователя из LDAP (Active Directory).
        
        Args:
            conn (Connection): Активное соединение с сервером LDAP.
            username (str): Логин пользователя (sAMAccountName).
            
        Returns:
            dict[str, Any] | None: Нормализованный словарь с атрибутами пользователя
                                   (имя, почта, телефон, группы и т.д.) или None, 
                                   если пользователь не найден или произошла ошибка.
        """
        search_filter = f'(sAMAccountName={username})'
        attributes = [
            'cn', 
            'mail', 
            'displayName', 
            'sAMAccountName',
            'memberOf',
            'department',
            'title',
            'telephoneNumber'
        ]
        
        try:
            conn.search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes
            )
            
            if not conn.entries:
                logger.warning(f"User {username} not found in LDAP")
                return None
            
            user_entry = conn.entries[0]
            
            # Обрабатываем группы
            groups: list[str] = []
            if hasattr(user_entry, 'memberOf'):
                groups = [str(group) for group in user_entry.memberOf]
            
            user_data = {
                'username': str(user_entry.sAMAccountName),
                'email': str(user_entry.mail) if hasattr(user_entry, 'mail') else None,
                'full_name': str(user_entry.displayName) if hasattr(user_entry, 'displayName') else None,
                'cn': str(user_entry.cn) if hasattr(user_entry, 'cn') else None,
                'department': str(user_entry.department) if hasattr(user_entry, 'department') else None,
                'title': str(user_entry.title) if hasattr(user_entry, 'title') else None,
                'phone': str(user_entry.telephoneNumber) if hasattr(user_entry, 'telephoneNumber') else None,
                'groups': groups,
            }
            
            logger.info(f"Retrieved data for user {username}: {user_data.get('full_name')}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    def check_group_membership(self, groups: list[str], required_group: str) -> bool:
        """
        Проверка принадлежности пользователя к целевой группе.
        
        Поиск нечувствителен к регистру и работает по принципу вхождения подстроки 
        (например, поиск 'admin' даст True для группы 'Domain Admins').
        
        Args:
            groups (list[str]): Список групп пользователя (LDAP DNs).
            required_group (str): Имя группы для поиска.
            
        Returns:
            bool: True, если совпадение найдено, иначе False.
        """
        for group in groups:
            if required_group.lower() in group.lower():
                return True
        return False


# Глобальный экземпляр сервиса для импорта в другие модули
ldap_service = LDAPService()

