from django.contrib import admin

from .models import Promotion
from .models import PromotionRule
from .models import PromotionRule_Variants
from .models import Voucher
from .models import VoucherCode
from .models import VoucherCustomer


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "private_metadata",
        "metadata",
        "id",
        "name",
        "type",
        "description",
        "old_sale_id",
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
        "last_notification_scheduled_at",
    )
    list_filter = (
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
        "last_notification_scheduled_at",
    )
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(PromotionRule)
class PromotionRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "promotion",
        "catalogue_predicate",
        "order_predicate",
        "reward_value_type",
        "reward_value",
        "reward_type",
        "old_channel_listing_id",
        "variants_dirty",
    )
    list_filter = ("promotion", "variants_dirty")
    raw_id_fields = ("channels", "variants", "gifts")
    search_fields = ("name",)


@admin.register(PromotionRule_Variants)
class PromotionRuleVariantsAdmin(admin.ModelAdmin):
    list_display = ("id", "promotionrule", "productvariant")
    list_filter = ("promotionrule", "productvariant")


@admin.register(VoucherCode)
class VoucherCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "used",
        "is_active",
        "voucher",
        "created_at",
    )
    list_filter = ("is_active", "voucher", "created_at")
    date_hierarchy = "created_at"


@admin.register(VoucherCustomer)
class VoucherCustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "voucher_code", "customer_email")
    list_filter = ("voucher_code",)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "type",
        "name",
        "usage_limit",
        "start_date",
        "end_date",
        "apply_once_per_order",
        "apply_once_per_customer",
        "single_use",
        "only_for_staff",
        "discount_value_type",
        "countries",
        "min_checkout_items_quantity",
    )
    list_filter = (
        "start_date",
        "end_date",
        "apply_once_per_order",
        "apply_once_per_customer",
        "single_use",
        "only_for_staff",
    )
    raw_id_fields = ("products", "variants", "collections", "categories")
    search_fields = ("name",)
