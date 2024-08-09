from django.contrib import admin

from .models import Fulfillment
from .models import FulfillmentLine
from .models import Order
from .models import OrderLine


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "private_metadata",
        "metadata",
        "external_reference",
        "id",
        "number",
        "use_old_id",
        "created_at",
        "updated_at",
        "expired_at",
        "status",
        "authorize_status",
        "charge_status",
        "user",
        "language_code",
        "tracking_client_id",
        "billing_address",
        "shipping_address",
        "user_email",
        "original",
        "origin",
        "currency",
        "shipping_method",
        "collection_point",
        "shipping_method_name",
        "collection_point_name",
        "channel",
        "shipping_price_net_amount",
        "shipping_price_gross_amount",
        "base_shipping_price_amount",
        "undiscounted_base_shipping_price_amount",
        "shipping_tax_rate",
        "shipping_tax_class",
        "shipping_tax_class_name",
        "shipping_tax_class_private_metadata",
        "shipping_tax_class_metadata",
        "checkout_token",
        "total_net_amount",
        "undiscounted_total_net_amount",
        "total_gross_amount",
        "undiscounted_total_gross_amount",
        "total_charged_amount",
        "total_authorized_amount",
        "subtotal_net_amount",
        "subtotal_gross_amount",
        "voucher",
        "voucher_code",
        "display_gross_prices",
        "customer_note",
        "weight",
        "redirect_url",
        "search_document",
        "search_vector",
        "should_refresh_prices",
        "tax_exemption",
        "tax_error",
        "shipping_price_net",
        "shipping_price_gross",
        "shipping_price",
        "base_shipping_price",
        "undiscounted_base_shipping_price",
        "total_net",
        "undiscounted_total_net",
        "total_gross",
        "undiscounted_total_gross",
        "total",
        "undiscounted_total",
        "total_authorized",
        "total_charged",
        "subtotal",
    )
    list_filter = (
        "use_old_id",
        "created_at",
        "updated_at",
        "expired_at",
        "user",
        "billing_address",
        "shipping_address",
        "original",
        "shipping_method",
        "collection_point",
        "channel",
        "shipping_tax_class",
        "voucher",
        "display_gross_prices",
        "should_refresh_prices",
        "tax_exemption",
    )
    raw_id_fields = ("gift_cards",)
    date_hierarchy = "created_at"


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "private_metadata",
        "metadata",
        "id",
        "old_id",
        "created_at",
        "order",
        "variant",
        "product_name",
        "variant_name",
        "translated_product_name",
        "translated_variant_name",
        "product_sku",
        "product_variant_id",
        "is_shipping_required",
        "is_gift_card",
        "quantity",
        "quantity_fulfilled",
        "is_gift",
        "currency",
        "unit_discount_amount",
        "unit_discount_type",
        "unit_discount_reason",
        "unit_price_net_amount",
        "unit_discount_value",
        "unit_price_gross_amount",
        "total_price_net_amount",
        "total_price_gross_amount",
        "undiscounted_unit_price_gross_amount",
        "undiscounted_unit_price_net_amount",
        "undiscounted_total_price_gross_amount",
        "undiscounted_total_price_net_amount",
        "base_unit_price_amount",
        "undiscounted_base_unit_price_amount",
        "tax_rate",
        "tax_class",
        "tax_class_name",
        "tax_class_private_metadata",
        "tax_class_metadata",
        "is_price_overridden",
        "voucher_code",
        "sale_id",
        "unit_discount",
        "unit_price_net",
        "unit_price_gross",
        "unit_price",
        "total_price_net",
        "total_price_gross",
        "total_price",
        "undiscounted_unit_price",
        "undiscounted_total_price",
        "base_unit_price",
        "undiscounted_base_unit_price",
    )
    list_filter = (
        "created_at",
        "order",
        "variant",
        "is_shipping_required",
        "is_gift_card",
        "is_gift",
        "tax_class",
        "is_price_overridden",
    )
    date_hierarchy = "created_at"


@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "fulfillment_order",
        "order",
        "status",
        "tracking_number",
        "created_at",
        "shipping_refund_amount",
        "total_refund_amount",
    )
    list_filter = ("order", "created_at")
    date_hierarchy = "created_at"


@admin.register(FulfillmentLine)
class FulfillmentLineAdmin(admin.ModelAdmin):
    list_display = ("id", "order_line", "fulfillment", "quantity", "stock")
    list_filter = ("order_line", "fulfillment", "stock")
