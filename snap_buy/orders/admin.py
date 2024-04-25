from django.contrib import admin

from .models import Order
from .models import OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "buyer",
        "status",
        "shipping_address",
        "billing_address",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "buyer",
        "shipping_address",
        "billing_address",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "quantity",
        "created_at",
        "updated_at",
    )
    list_filter = ("order", "product", "created_at", "updated_at")
    date_hierarchy = "created_at"
