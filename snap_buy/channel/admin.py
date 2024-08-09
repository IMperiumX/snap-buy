from django.contrib import admin

from .models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "name",
        "is_active",
        "slug",
        "currency_code",
        "default_country",
        "allocation_strategy",
        "order_mark_as_paid_strategy",
        "default_transaction_flow_strategy",
        "automatically_confirm_all_new_orders",
        "allow_unpaid_orders",
        "automatically_fulfill_non_shippable_gift_card",
        "expire_orders_after",
        "delete_expired_orders_after",
        "include_draft_order_in_voucher_usage",
        "use_legacy_error_flow_for_checkout",
    )
    list_filter = (
        "is_active",
        "automatically_confirm_all_new_orders",
        "allow_unpaid_orders",
        "automatically_fulfill_non_shippable_gift_card",
        "include_draft_order_in_voucher_usage",
        "use_legacy_error_flow_for_checkout",
    )
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}
