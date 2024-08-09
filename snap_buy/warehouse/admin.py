from django.contrib import admin

from .models import Allocation
from .models import ChannelWarehouse
from .models import Stock
from .models import Warehouse


@admin.register(ChannelWarehouse)
class ChannelWarehouseAdmin(admin.ModelAdmin):
    list_display = ("id", "sort_order", "channel", "warehouse")
    list_filter = ("channel", "warehouse")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "private_metadata",
        "metadata",
        "external_reference",
        "id",
        "name",
        "slug",
        "address",
        "email",
        "click_and_collect_option",
        "is_private",
    )
    list_filter = ("address", "is_private")
    raw_id_fields = ("channels",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "warehouse",
        "product_variant",
        "quantity",
        "quantity_allocated",
    )
    list_filter = ("warehouse", "product_variant")


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ("id", "order_line", "stock", "quantity_allocated")
    list_filter = ("order_line", "stock")
