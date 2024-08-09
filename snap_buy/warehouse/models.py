import itertools
import uuid

from django.db import models
from django.db.models import F

from snap_buy.channel.models import Channel
from snap_buy.core.models import ModelWithExternalReference
from snap_buy.core.models import ModelWithMetadata
from snap_buy.core.models import SortableModel
from snap_buy.order.models import OrderLine
from snap_buy.product.models import ProductVariant
from snap_buy.shipping.models import ShippingZone
from snap_buy.users.models import Address

from . import WarehouseClickAndCollectOption


class ChannelWarehouse(SortableModel):
    channel = models.ForeignKey(
        Channel,
        related_name="channelwarehouse",
        on_delete=models.CASCADE,
    )
    warehouse = models.ForeignKey(
        "Warehouse",
        related_name="channelwarehouse",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = (("channel", "warehouse"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.channel.channelwarehouse.all()


class Warehouse(ModelWithMetadata, ModelWithExternalReference):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    channels = models.ManyToManyField(
        Channel,
        related_name="warehouses",
        through=ChannelWarehouse,
    )
    shipping_zones = models.ManyToManyField(
        ShippingZone,
        blank=True,
        related_name="warehouses",
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    email = models.EmailField(blank=True, default="")
    click_and_collect_option = models.CharField(
        max_length=30,
        choices=WarehouseClickAndCollectOption.CHOICES,
        default=WarehouseClickAndCollectOption.DISABLED,
    )
    is_private = models.BooleanField(default=True)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("-slug",)

    def __str__(self):
        return self.name

    @property
    def countries(self) -> set[str]:
        shipping_zones = self.shipping_zones.all()
        return set(itertools.chain(*[zone.countries for zone in shipping_zones]))

    def delete(self, *args, **kwargs):
        address = self.address
        super().delete(*args, **kwargs)
        address.delete()


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        ProductVariant,
        null=False,
        on_delete=models.CASCADE,
        related_name="stocks",
    )
    quantity = models.IntegerField(default=0)
    quantity_allocated = models.IntegerField(default=0)

    class Meta:
        unique_together = [["warehouse", "product_variant"]]
        ordering = ("pk",)

    def __str__(self):
        return f"{self.product_variant} - {self.warehouse}"

    def increase_stock(self, quantity: int, *, commit: bool = True):
        """Return given quantity of product to a stock."""
        self.quantity = F("quantity") + quantity
        if commit:
            self.save(update_fields=["quantity"])

    def decrease_stock(self, quantity: int, *, commit: bool = True):
        self.quantity = F("quantity") - quantity
        if commit:
            self.save(update_fields=["quantity"])


class Allocation(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    stock = models.ForeignKey(
        Stock,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    quantity_allocated = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [["order_line", "stock"]]
        ordering = ("pk",)

    def __str__(self):
        return str(self.id)
