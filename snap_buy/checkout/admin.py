from django.contrib import admin

from .models import Checkout
from .models import CheckoutLine
from .models import CheckoutMetadata


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "last_change",
        "completing_started_at",
        "last_transaction_modified_at",
        "automatically_refundable",
        "user",
        "email",
        "token",
        "channel",
        "billing_address",
        "shipping_address",
        "shipping_method",
        "collection_point",
        "note",
        "currency",
        "country",
        "total_net_amount",
        "total_gross_amount",
        "base_total_amount",
        "subtotal_net_amount",
        "subtotal_gross_amount",
        "base_subtotal_amount",
        "shipping_price_net_amount",
        "shipping_price_gross_amount",
        "shipping_tax_rate",
        "authorize_status",
        "charge_status",
        "price_expiration",
        "discount_amount",
        "discount_name",
        "translated_discount_name",
        "voucher_code",
        "is_voucher_usage_increased",
        "redirect_url",
        "tracking_code",
        "language_code",
        "tax_exemption",
        "tax_error",
        "total",
        "base_total",
        "subtotal",
        "base_subtotal",
        "shipping_price",
        "discount",
    )
    list_filter = (
        "created_at",
        "last_change",
        "completing_started_at",
        "last_transaction_modified_at",
        "automatically_refundable",
        "user",
        "channel",
        "billing_address",
        "shipping_address",
        "shipping_method",
        "collection_point",
        "price_expiration",
        "is_voucher_usage_increased",
        "tax_exemption",
    )
    date_hierarchy = "created_at"


@admin.register(CheckoutLine)
class CheckoutLineAdmin(admin.ModelAdmin):
    list_display = (
        "private_metadata",
        "metadata",
        "id",
        "old_id",
        "created_at",
        "checkout",
        "variant",
        "quantity",
        "is_gift",
        "price_override",
        "currency",
        "total_price_net_amount",
        "total_price_gross_amount",
        "tax_rate",
        "total_price",
    )
    list_filter = ("created_at", "checkout", "variant", "is_gift")
    date_hierarchy = "created_at"


@admin.register(CheckoutMetadata)
class CheckoutMetadataAdmin(admin.ModelAdmin):
    list_display = ("id", "private_metadata", "metadata", "checkout")
    list_filter = ("checkout",)
