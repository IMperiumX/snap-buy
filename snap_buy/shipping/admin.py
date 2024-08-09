from django.contrib import admin

from .models import ShippingMethod
from .models import ShippingZone


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "name",
        "countries",
        "default",
        "description",
    )
    list_filter = ("default",)
    raw_id_fields = ("channels",)
    search_fields = ("name",)


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "name",
        "type",
        "shipping_zone",
        "minimum_order_weight",
        "maximum_order_weight",
        "maximum_delivery_days",
        "minimum_delivery_days",
        "description",
        "tax_class",
    )
    list_filter = ("shipping_zone", "tax_class")
    raw_id_fields = ("excluded_products",)
    search_fields = ("name",)
