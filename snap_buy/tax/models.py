from django.db import models


class TaxClass(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ("name", "pk")

    def __str__(self):
        return self.name
