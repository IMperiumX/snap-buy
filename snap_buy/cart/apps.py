from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "snap_buy.cart"
    verbose_name = _("Cart")

    def ready(self):
        try:
            import snap_buy.users.signals  # noqa: F401
        except ImportError:
            pass
