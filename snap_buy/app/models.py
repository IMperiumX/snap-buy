from collections.abc import Iterable
from uuid import uuid4

from django.db import models

from snap_buy.core.models import ModelWithMetadata
from snap_buy.permission.enums import AppPermission
from snap_buy.permission.enums import BasePermissionEnum
from snap_buy.permission.models import Permission

from .types import AppType


class App(ModelWithMetadata):
    uuid = models.UUIDField(unique=True, default=uuid4)
    name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    removed_at = models.DateTimeField(blank=True, null=True)
    type = models.CharField(
        choices=AppType.CHOICES,
        default=AppType.LOCAL,
        max_length=60,
    )
    identifier = models.CharField(max_length=256, blank=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text="Specific permissions for this app.",
        related_name="app_set",
        related_query_name="app",
    )
    about_app = models.TextField(blank=True)
    data_privacy = models.TextField(blank=True)
    data_privacy_url = models.URLField(blank=True)
    homepage_url = models.URLField(blank=True)
    support_url = models.URLField(blank=True)
    configuration_url = models.URLField(blank=True)
    app_url = models.URLField(blank=True)
    manifest_url = models.URLField(blank=True)
    version = models.CharField(max_length=60, blank=True)
    audience = models.CharField(blank=True, max_length=256)
    is_installed = models.BooleanField(default=True)
    author = models.CharField(blank=True, max_length=60)
    brand_logo_default = models.ImageField(
        upload_to="app-brand-data",
        blank=True,
        null=True,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("name", "pk")
        permissions = (
            (
                AppPermission.MANAGE_APPS.codename,
                "Manage apps",
            ),
            (
                AppPermission.MANAGE_OBSERVABILITY.codename,
                "Manage observability",
            ),
        )

    def __str__(self):
        return self.name

    def get_permissions(self) -> set[str]:
        """Return the permissions of the app."""
        if not self.is_active:
            return set()
        perm_cache_name = "_app_perm_cache"
        if not hasattr(self, perm_cache_name):
            perms = self.permissions.all()
            perms = perms.values_list("content_type__app_label", "codename").order_by()
            setattr(self, perm_cache_name, {f"{ct}.{name}" for ct, name in perms})
        return getattr(self, perm_cache_name)

    def has_perms(self, perm_list: Iterable[BasePermissionEnum | str]) -> bool:
        """Return True if the app has each of the specified permissions."""
        if not self.is_active:
            return False

        wanted_perms = {
            perm.value if isinstance(perm, BasePermissionEnum) else perm
            for perm in perm_list
        }
        actual_perms = self.get_permissions()

        return (wanted_perms & actual_perms) == wanted_perms

    def has_perm(self, perm: BasePermissionEnum | str) -> bool:
        """Return True if the app has the specified permission."""
        if not self.is_active:
            return False

        perm_value = perm.value if isinstance(perm, BasePermissionEnum) else perm
        return perm_value in self.get_permissions()
