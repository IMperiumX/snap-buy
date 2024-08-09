from django.contrib import admin

from .models import GiftCard
from .models import GiftCardTag


@admin.register(GiftCardTag)
class GiftCardTagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "code",
        "is_active",
        "created_by",
        "used_by",
        "created_by_email",
        "used_by_email",
        "app",
        "expiry_date",
        "created_at",
        "last_used_on",
        "product",
        "fulfillment_line",
        "currency",
        "initial_balance_amount",
        "current_balance_amount",
        "search_vector",
        "search_index_dirty",
        "initial_balance",
        "current_balance",
    )
    list_filter = (
        "is_active",
        "created_by",
        "used_by",
        "app",
        "expiry_date",
        "created_at",
        "last_used_on",
        "product",
        "fulfillment_line",
        "search_index_dirty",
    )
    raw_id_fields = ("tags",)
    date_hierarchy = "created_at"
