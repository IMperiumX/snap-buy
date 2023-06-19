from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Order(models.Model):
    ...


# Create your models here.
class OrderItem(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sku = models.CharField(max_length=254, null=True, blank=True)

    fullfilled = models.BooleanField(default=False)
    ship_date = models.DateTimeField(null=True, blank=True)
    bill_date = models.DateTimeField(null=True, blank=True)

    order = models.ForeignKey("Order", related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", related_name="order_items", on_delete=models.CASCADE)
    size = models.ForeignKey("Size", null=True, blank=True, on_delete=models.CASCADE)
    color = models.ForeignKey("Color", null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class Size(models.Model):
    size = models.CharField(max_length=254, null=True, blank=True)


class Color(models.Model):
    color = models.CharField(max_length=254, null=True, blank=True)


class Promotion(models.Model):
    code = models.CharField(max_length=24, unique=True)
    description = models.TextField()
    active = models.BooleanField(default=True)

    percent_discount = models.FloatField(default=0)
    discount_amount = models.IntegerField(default=0)

    valid_from = models.DateField()
    valid_to = models.DateField()

    usage_limit = models.IntegerField(default=10000)
    used_times = models.IntegerField(default=0)

    def __str__(self):
        return self.code
