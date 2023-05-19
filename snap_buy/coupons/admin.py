# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "valid_from",
        "valid_to",
        "discount",
        "active",
    )
    list_filter = ("valid_from", "valid_to", "active")
