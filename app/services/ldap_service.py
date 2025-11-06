from ldap3 import Server, Connection, SUBTREE, ALL
from ldap3.core.exceptions import (
    LDAPBindError, 
    LDAPInvalidCredentialsResult,
    LDAPException
)
from typing import Optional, Dict, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class LDAPService:
    def __init__(self):
        self.server = Server(
            settings.LDAP_SERVER,
            port=settings.LDAP_PORT,
            get_info=ALL
        )
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
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
    
    def _get_user_data(self, conn: Connection, username: str) -> Optional[Dict]:
        """
        Получение данных пользователя из LDAP.
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
            groups = []
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
            
            logger.info(f"Retrieved data for user {username}: {user_data['full_name']}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    def check_group_membership(self, groups: List[str], required_group: str) -> bool:
        """
        Проверка принадлежности к группе.
        """
        for group in groups:
            if required_group.lower() in group.lower():
                return True
        return False


ldap_service = LDAPService()

