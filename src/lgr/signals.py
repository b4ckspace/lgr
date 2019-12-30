from itertools import chain
from django.conf import settings
from django.db.models import signals
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission, User
from django_auth_ldap.backend import populate_user

from lgr import models
from lgr.helpers import logger


@receiver(populate_user)
def fix_backspace_ldap(sender, user, ldap_user, **kwargs):
    """Add backspace user from ldap and work around attrs."""

    # map attributes
    for attr, func in settings.INVENTORY_LDAP_ATTR_FILTER_MAP.items():
        setattr(user, attr, func(ldap_user))
    user.save()

    # map groups
    group_map = settings.INVENTORY_LDAP_ATTR_FILTER_TO_GROUPS
    if group_map:
        groups = chain.from_iterable(func(ldap_user) for func in group_map)
        local_groups = list()
        for group in groups:
            local_group = Group.objects.filter(name=group).first()
            if local_group:
                local_groups.append(local_group)
            else:
                logger.warning('No local group found %s.', group)
        user.groups.set(local_groups)

    person, _ = models.Person.objects.get_or_create(
        nickname=ldap_user.attrs['uid'][0]
    )
    person.email = ldap_user.attrs['mladdress'][0]
    person.save()
