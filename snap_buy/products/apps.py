from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "snap_buy.products"
    verbose_name = _("Products")

    def ready(self):
        try:
            import snap_buy.products.signals  # noqa: F401
        except ImportError:
            pass
