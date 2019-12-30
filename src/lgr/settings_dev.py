"""Custom settings for dev."""

import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

## general ldap settings
#

AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_LDAP_SERVER_URI = 'ldap://ldap.core.bckspc.de'
AUTH_LDAP_BIND_DN = "cn=reader,ou=ldapuser,dc=backspace"
AUTH_LDAP_BIND_PASSWORD = "8S4FSyDxDz1Q7vlQGTU7"
AUTH_LDAP_USER_SEARCH = LDAPSearch("ou=member,dc=backspace",
                                   ldap.SCOPE_SUBTREE, "(uid=%(user)s)")

AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'uid',
    'last_name': 'uid',
    'email': 'mlAddress',
}


## ldap backspace settings
#

INVENTORY_LDAP_ATTR_FILTER_MAP = {
    'is_staff': lambda ldap_user: 'door' in ldap_user.attrs['serviceEnabled'],
    'is_admin': lambda ldap_user: 'door' in ldap_user.attrs['serviceEnabled'],
}
INVENTORY_LDAP_ATTR_FILTER_TO_GROUPS = [
    lambda ldap_user: ['member'] if 'door' in ldap_user.attrs['serviceEnabled'] else [],
]
