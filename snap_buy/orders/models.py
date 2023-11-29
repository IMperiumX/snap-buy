from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from typing import TYPE_CHECKING, List, Optional, cast


if TYPE_CHECKING:
    from snap_buy.users.models import User


class OrderMinin:
    def is_fully_paid(self):
        return self.total_charged >= self.total.gross

    def is_partly_paid(self):
        return self.total_charged_amount > 0

    def get_customer_email(self):
        if self.user_id:
            # when user_id is set, user is set as well
            return cast("User", self.user).email
        return self.user_email

    def __repr__(self):
        return "<Order #%r>" % (self.id,)

    def __str__(self):
        return f"#{self.id}"

    # def get_last_payment(self) -> Optional[Payment]:
    #     # Skipping a partial payment is a temporary workaround for storing a basic data
    #     # about partial payment from Adyen plugin. This is something that will removed
    #     # in 3.1 by introducing a partial payments feature.
    #     payments: List[Payment] = [payment for payment in self.payments.all() if not payment.partial]
    #     return max(payments, default=None, key=attrgetter("pk"))

    # def is_pre_authorized(self):
    #     return (
    #         self.payments.filter(
    #             is_active=True,
    #             transactions__kind=TransactionKind.AUTH,
    #             transactions__action_required=False,
    #         )
    #         .filter(transactions__is_success=True)
    #         .exists()
    #     )

    # def is_captured(self):
    #     return (
    #         self.payments.filter(
    #             is_active=True,
    #             transactions__kind=TransactionKind.CAPTURE,
    #             transactions__action_required=False,
    #         )
    #         .filter(transactions__is_success=True)
    #         .exists()
    #     )

    # def is_shipping_required(self):
    #     return any(line.is_shipping_required for line in self.lines.all())

    # def get_subtotal(self):
    #     return get_subtotal(self.lines.all(), self.currency)

    # def get_total_quantity(self):
    #     return sum([line.quantity for line in self.lines.all()])

    # def is_draft(self):
    #     return self.status == OrderStatus.DRAFT

    # def is_unconfirmed(self):
    #     return self.status == OrderStatus.UNCONFIRMED

    # def is_expired(self):
    #     return self.status == OrderStatus.EXPIRED

    # def is_open(self):
    #     statuses = {OrderStatus.UNFULFILLED, OrderStatus.PARTIALLY_FULFILLED}
    #     return self.status in statuses

    # def can_cancel(self):
    #     statuses_allowed_to_cancel = [
    #         FulfillmentStatus.CANCELED,
    #         FulfillmentStatus.REFUNDED,
    #         FulfillmentStatus.REPLACED,
    #         FulfillmentStatus.REFUNDED_AND_RETURNED,
    #         FulfillmentStatus.RETURNED,
    #     ]
    #     return (not self.fulfillments.exclude(status__in=statuses_allowed_to_cancel).exists()) and self.status not in {
    #         OrderStatus.CANCELED,
    #         OrderStatus.DRAFT,
    #         OrderStatus.EXPIRED,
    #     }

    # def can_capture(self, payment=None):
    #     if not payment:
    #         payment = self.get_last_payment()
    #     if not payment:
    #         return False
    #     order_status_ok = self.status not in {
    #         OrderStatus.DRAFT,
    #         OrderStatus.CANCELED,
    #         OrderStatus.EXPIRED,
    #     }
    #     return payment.can_capture() and order_status_ok

    # def can_void(self, payment=None):
    #     if not payment:
    #         payment = self.get_last_payment()
    #     if not payment:
    #         return False
    #     return payment.can_void()

    # def can_refund(self, payment=None):
    #     if not payment:
    #         payment = self.get_last_payment()
    #     if not payment:
    #         return False
    #     return payment.can_refund()

    # def can_mark_as_paid(self, payments=None):
    #     if not payments:
    #         payments = self.payments.all()
    #     return len(payments) == 0

    # @property
    # def total_balance(self):
    #     return self.total_charged - self.total.gross

    # def get_total_weight(self, _lines=None):
    #     return self.weight


class Order(OrderMinin, models.Model):
    ...


# Create your models here.
class OrderItem(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sku = models.CharField(max_length=254, null=True, blank=True)

    fullfilled = models.BooleanField(default=False)
    ship_date = models.DateTimeField(null=True, blank=True)
    bill_date = models.DateTimeField(null=True, blank=True)

    order = models.ForeignKey("Order", related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", related_name="order_items", on_delete=models.CASCADE)
    size = models.ForeignKey("Size", null=True, blank=True, on_delete=models.CASCADE)
    color = models.ForeignKey("Color", null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class Size(models.Model):
    size = models.CharField(max_length=254, null=True, blank=True)


class Color(models.Model):
    color = models.CharField(max_length=254, null=True, blank=True)


class Promotion(models.Model):
    code = models.CharField(max_length=24, unique=True)
    description = models.TextField()
    active = models.BooleanField(default=True)

    percent_discount = models.FloatField(default=0)
    discount_amount = models.IntegerField(default=0)

    valid_from = models.DateField()
    valid_to = models.DateField()

    usage_limit = models.IntegerField(default=10000)
    used_times = models.IntegerField(default=0)

    def __str__(self):
        return self.code
