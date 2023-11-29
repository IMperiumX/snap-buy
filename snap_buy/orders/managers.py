from django.db import  models
from django.db.models import F
from django.db.models.expressions import Exists, OuterRef

from . import (
    OrderStatus,
)

class OrderQueryset(models.QuerySet):
    def get_by_checkout_token(self, token):
        """Return non-draft order with matched checkout token."""
        return self.non_draft().filter(checkout_token=token).first()

    def confirmed(self):
        """Return orders that aren't draft or unconfirmed."""
        return self.exclude(status__in=[OrderStatus.DRAFT, OrderStatus.UNCONFIRMED])

    def non_draft(self):
        """Return orders that aren't draft."""
        return self.exclude(status=OrderStatus.DRAFT)

    def drafts(self):
        """Return draft orders."""
        return self.filter(status=OrderStatus.DRAFT)

    # def ready_to_fulfill(self):
    #     """Return orders that can be fulfilled.

    #     Orders ready to fulfill are fully paid but unfulfilled (or partially
    #     fulfilled).
    #     """
    #     statuses = {OrderStatus.UNFULFILLED, OrderStatus.PARTIALLY_FULFILLED}
    #     payments = Payment.objects.filter(is_active=True).values("id")
    #     return self.filter(
    #         Exists(payments.filter(order_id=OuterRef("id"))),
    #         status__in=statuses,
    #         total_gross_amount__lte=F("total_charged_amount"),
    #     )

    # def ready_to_capture(self):
    #     """Return orders with payments to capture.

    #     Orders ready to capture are those which are not draft or canceled and
    #     have a preauthorized payment. The preauthorized payment can not
    #     already be partially or fully captured.
    #     """
    #     payments = Payment.objects.filter(
    #         is_active=True, charge_status=ChargeStatus.NOT_CHARGED
    #     ).values("id")
    #     qs = self.filter(Exists(payments.filter(order_id=OuterRef("id"))))
    #     return qs.exclude(
    #         status={OrderStatus.DRAFT, OrderStatus.CANCELED, OrderStatus.EXPIRED}
    #     )

    def ready_to_confirm(self):
        """Return unconfirmed orders."""
        return self.filter(status=OrderStatus.UNCONFIRMED)

