from datetime import datetime
from decimal import ROUND_HALF_UP
from functools import partial
from typing import TYPE_CHECKING
from typing import Optional
from uuid import uuid4

import pytz
from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex
from django.db import models
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from django.utils import timezone
from django_countries.fields import CountryField
from prices import Money
from prices import fixed_discount
from prices import percentage_discount

from snap_buy.channel.models import Channel
from snap_buy.core.db.fields import SanitizedJSONField
from snap_buy.core.models import ModelWithMetadata
from snap_buy.core.utils.editorjs import clean_editor_js
from snap_buy.core.utils.json_serializer import CustomJsonEncoder
from snap_buy.permission.enums import DiscountPermissions

from . import DiscountValueType
from . import PromotionType
from . import RewardType
from . import RewardValueType
from . import VoucherType

if TYPE_CHECKING:
    from snap_buy.users.models import User


class NotApplicableError(ValueError):
    """Exception raised when a discount is not applicable to a checkout.

    The error is raised if the order value is below the minimum required
    price or the order quantity is below the minimum quantity of items.
    Minimum price will be available as the `min_spent` attribute.
    Minimum quantity will be available as the `min_checkout_items_quantity` attribute.
    """

    def __init__(self, msg, min_spent=None, min_checkout_items_quantity=None):
        super().__init__(msg)
        self.min_spent = min_spent
        self.min_checkout_items_quantity = min_checkout_items_quantity


class PromotionQueryset(models.QuerySet["Promotion"]):
    def active(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date),
            start_date__lte=date,
        )

    def expired(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(end_date__lt=date, start_date__lt=date)


PromotionManager = models.Manager.from_queryset(PromotionQueryset)


class Promotion(ModelWithMetadata):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=255,
        choices=PromotionType.CHOICES,
        default=PromotionType.CATALOGUE,
    )
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    old_sale_id = models.IntegerField(blank=True, null=True, unique=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    last_notification_scheduled_at = models.DateTimeField(null=True, blank=True)
    objects = PromotionManager()

    class Meta:
        ordering = ("name", "pk")
        permissions = (
            (
                DiscountPermissions.MANAGE_DISCOUNTS.codename,
                "Manage promotions and vouchers.",
            ),
        )
        indexes = [
            BTreeIndex(fields=["start_date"], name="start_date_idx"),
            BTreeIndex(fields=["end_date"], name="end_date_idx"),
        ]

    def is_active(self, date=None):
        if date is None:
            date = datetime.now(pytz.utc)
        return (not self.end_date or self.end_date >= date) and self.start_date <= date


class PromotionRule_Variants(models.Model):  # noqa: N801
    id = models.BigAutoField(primary_key=True, editable=False, unique=True)
    promotionrule = models.ForeignKey(
        "discount.PromotionRule",
        on_delete=models.CASCADE,
    )
    productvariant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.promotionrule} (Promotion Rule Variants)"


class PromotionRule(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = models.CharField(max_length=255, blank=True)
    description = SanitizedJSONField(blank=True, sanitizer=clean_editor_js)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    channels = models.ManyToManyField(Channel)
    catalogue_predicate = models.JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    order_predicate = models.JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    variants = models.ManyToManyField(  # type: ignore[var-annotated]
        "product.ProductVariant",
        blank=True,
        through="PromotionRule_Variants",
    )
    reward_value_type = models.CharField(
        max_length=255,
        choices=RewardValueType.CHOICES,
        blank=True,
    )
    reward_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    reward_type = models.CharField(
        max_length=255,
        choices=RewardType.CHOICES,
        blank=True,
    )
    gifts = models.ManyToManyField(
        "product.ProductVariant",
        blank=True,
        related_name="+",
    )
    old_channel_listing_id = models.IntegerField(blank=True, null=True, unique=True)
    variants_dirty = models.BooleanField(default=False)

    class Meta:
        ordering = ("name", "pk")

    def __str__(self):
        return f"{self.name} (Promotion Rule)"

    def get_discount(self, currency):
        if self.reward_value_type == RewardValueType.FIXED:
            discount_amount = Money(self.reward_value, currency)
            return partial(fixed_discount, discount=discount_amount)
        if self.reward_value_type == RewardValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=self.reward_value,
                rounding=ROUND_HALF_UP,
            )
        msg = "Unknown discount type"
        raise NotImplementedError(msg)


class VoucherCode(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    code = models.CharField(max_length=255, unique=True, db_index=True)
    used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    voucher = models.ForeignKey(
        "discount.Voucher",
        related_name="codes",
        on_delete=models.CASCADE,
        db_index=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [BTreeIndex(fields=["voucher"], name="vouchercode_voucher_idx")]
        ordering = ("-created_at", "code")

    def __str__(self):
        return f"{self.code} (Voucher Code)"


class VoucherCustomer(models.Model):
    voucher_code = models.ForeignKey(
        VoucherCode,
        related_name="customers",
        on_delete=models.CASCADE,
        db_index=False,
    )
    customer_email = models.EmailField()

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["voucher_code"],
                name="vouchercustomer_voucher_code_idx",
            ),
        ]
        ordering = ("voucher_code", "customer_email", "pk")
        unique_together = (("voucher_code", "customer_email"),)

    def __str__(self):
        return f"{self.customer_email} (Voucher Customer)"


class Voucher(ModelWithMetadata):
    type = models.CharField(
        max_length=20,
        choices=VoucherType.CHOICES,
        default=VoucherType.ENTIRE_ORDER,
    )
    name = models.CharField(max_length=255, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # this field indicates if discount should be applied per order or
    # individually to every item
    apply_once_per_order = models.BooleanField(default=False)
    apply_once_per_customer = models.BooleanField(default=False)
    single_use = models.BooleanField(default=False)

    only_for_staff = models.BooleanField(default=False)

    discount_value_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )

    # not mandatory fields, usage depends on type
    countries = CountryField(multiple=True, blank=True)
    min_checkout_items_quantity = models.PositiveIntegerField(null=True, blank=True)
    products = models.ManyToManyField("product.Product", blank=True)
    variants = models.ManyToManyField("product.ProductVariant", blank=True)
    collections = models.ManyToManyField("product.Collection", blank=True)
    categories = models.ManyToManyField("product.Category", blank=True)

    class Meta:
        ordering = ("name", "pk")

    @property
    def code(self):
        # this function should be removed after field `code` will be deprecated
        code_instance = self.codes.last()
        return code_instance.code if code_instance else None

    @property
    def promo_codes(self):
        return list(self.codes.values_list("code", flat=True))

    def get_discount(self, channel: Channel):
        """Return proper discount amount for given channel.

        It operates over all channel listings as assuming that we have prefetched them.
        """
        voucher_channel_listing = None

        for channel_listing in self.channel_listings.all():
            if channel.id == channel_listing.channel_id:
                voucher_channel_listing = channel_listing
                break

        if not voucher_channel_listing:
            msg = "This voucher is not assigned to this channel"
            raise NotApplicableError(msg)
        if self.discount_value_type == DiscountValueType.FIXED:
            discount_amount = Money(
                voucher_channel_listing.discount_value,
                voucher_channel_listing.currency,
            )
            return partial(fixed_discount, discount=discount_amount)
        if self.discount_value_type == DiscountValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=voucher_channel_listing.discount_value,
                rounding=ROUND_HALF_UP,
            )
        msg = "Unknown discount type"
        raise NotImplementedError(msg)

    def get_discount_amount_for(self, price: Money, channel: Channel) -> Money:
        discount = self.get_discount(channel)
        after_discount = discount(price)
        if after_discount.amount < 0:
            return price
        return price - after_discount

    def validate_min_spent(self, value: Money, channel: Channel):
        voucher_channel_listing = self.channel_listings.filter(channel=channel).first()
        if not voucher_channel_listing:
            msg = "This voucher is not assigned to this channel"
            raise NotApplicableError(msg)
        min_spent = voucher_channel_listing.min_spent
        if min_spent and value < min_spent:
            msg = f"This offer is only valid for orders over {min_spent}."
            raise NotApplicableError(msg, min_spent=min_spent)

    def validate_min_checkout_items_quantity(self, quantity):
        min_checkout_items_quantity = self.min_checkout_items_quantity
        if min_checkout_items_quantity and min_checkout_items_quantity > quantity:
            msg = (
                "This offer is only valid for orders with a minimum of "
                f"{min_checkout_items_quantity} quantity."
            )
            raise NotApplicableError(
                msg,
                min_checkout_items_quantity=min_checkout_items_quantity,
            )

    def validate_once_per_customer(self, customer_email):
        voucher_codes = self.codes.all()
        voucher_customer = VoucherCustomer.objects.filter(
            Exists(voucher_codes.filter(id=OuterRef("voucher_code_id"))),
            customer_email=customer_email,
        )
        if voucher_customer:
            msg = "This offer is valid only once per customer."
            raise NotApplicableError(msg)

    def validate_only_for_staff(self, customer: Optional["User"]):
        if not self.only_for_staff:
            return

        if not customer or not customer.is_staff:
            msg = "This offer is valid only for staff customers."
            raise NotApplicableError(msg)
