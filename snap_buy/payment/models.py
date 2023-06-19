from django.db import models


# Create your models here.
class Payment(models.Model):
    payment_type = models.CharField(max_length=255)
    allowed = models.BooleanField(default=True)
