from django.contrib import admin

from .models import App


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "uuid",
        "name",
        "created_at",
        "is_active",
        "removed_at",
        "type",
        "identifier",
        "about_app",
        "data_privacy",
        "data_privacy_url",
        "homepage_url",
        "support_url",
        "configuration_url",
        "app_url",
        "manifest_url",
        "version",
        "audience",
        "is_installed",
        "author",
        "brand_logo_default",
    )
    list_filter = ("created_at", "is_active", "removed_at", "is_installed")
    raw_id_fields = ("permissions",)
    search_fields = ("name",)
    date_hierarchy = "created_at"
