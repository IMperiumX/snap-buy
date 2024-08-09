from django.contrib import admin

from .models import Webhook


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_active",
        "secret_key",
        "subscription_query",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
