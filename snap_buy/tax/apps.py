from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "snap_buy.tax"
    verbose_name = _("Taxes")

    def ready(self):
        try:
            import snap_buy.tax.signals  # noqa: F401
        except ImportError:
            pass
