from collections.abc import Iterable
from typing import TYPE_CHECKING
from typing import Union

from .enums import BasePermissionEnum

if TYPE_CHECKING:
    from snap_buy.users.models import User


def permission_required(
    requestor: Union["User", None],
    perms: Iterable[BasePermissionEnum],
) -> bool:
    from snap_buy.users.models import User

    if isinstance(requestor, User):
        return requestor.has_perms(perms)
    return False


def has_one_of_permissions(
    requestor: Union["User", None],
    permissions: Iterable[BasePermissionEnum],
) -> bool:
    if not requestor:
        return False

    return any(permission_required(requestor, (perm,)) for perm in permissions)
