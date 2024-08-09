from django.contrib import admin

from .models import EventDelivery
from .models import EventDeliveryAttempt
from .models import EventPayload


@admin.register(EventPayload)
class EventPayloadAdmin(admin.ModelAdmin):
    list_display = ("id", "payload", "created_at")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(EventDelivery)
class EventDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "status",
        "event_type",
        "payload",
        "webhook",
    )
    list_filter = ("created_at", "payload", "webhook")
    date_hierarchy = "created_at"


@admin.register(EventDeliveryAttempt)
class EventDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "delivery",
        "created_at",
        "task_id",
        "duration",
        "response",
        "response_headers",
        "response_status_code",
        "request_headers",
        "status",
    )
    list_filter = ("delivery", "created_at")
    date_hierarchy = "created_at"
