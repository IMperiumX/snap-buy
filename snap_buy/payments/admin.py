from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "payment_option",
        "order",
        "created_at",
        "updated_at",
    )
    list_filter = ("order", "created_at", "updated_at")
    date_hierarchy = "created_at"
