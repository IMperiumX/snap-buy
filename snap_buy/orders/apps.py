from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "snap_buy.orders"
    verbose_name = _("Orders")

    def ready(self):
        try:
            import snap_buy.users.signals  # noqa: F401
        except ImportError:
            pass
