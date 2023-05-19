# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Order, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "address",
        "postal_code",
        "city",
        "created",
        "updated",
        "paid",
        "braintree_id",
        "coupon",
        "discount",
    )
    list_filter = ("created", "updated", "paid", "coupon")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "price", "quantity")
    list_filter = ("order", "product")
