from django.db import models


class Webhook(models.Model):
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=255, blank=True)
    subscription_query = models.TextField(blank=True)

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return self.name
