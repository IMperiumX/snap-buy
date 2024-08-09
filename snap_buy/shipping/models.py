from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django_countries.fields import CountryField
from django_measurement.models import MeasurementField
from measurement.measures import Weight

from snap_buy.channel.models import Channel
from snap_buy.core.db.fields import SanitizedJSONField
from snap_buy.core.models import ModelWithMetadata
from snap_buy.core.units import WeightUnits
from snap_buy.core.utils.editorjs import clean_editor_js
from snap_buy.core.weight import convert_weight
from snap_buy.core.weight import get_default_weight_unit
from snap_buy.core.weight import zero_weight
from snap_buy.permission.enums import ShippingPermissions
from snap_buy.product.models import Product
from snap_buy.tax.models import TaxClass

from . import ShippingMethodType


def _get_weight_type_display(min_weight, max_weight):
    default_unit = get_default_weight_unit()

    if min_weight.unit != default_unit:
        min_weight = convert_weight(min_weight, default_unit)
    if max_weight and max_weight.unit != default_unit:
        max_weight = convert_weight(max_weight, default_unit)

    if max_weight is None:
        return f"{min_weight} and up"
    return f"{min_weight} to {max_weight}"


class ShippingZone(ModelWithMetadata):
    name = models.CharField(max_length=100)
    countries = CountryField(multiple=True, default=[], blank=True)
    default = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    channels = models.ManyToManyField(Channel, related_name="shipping_zones")

    def __str__(self):
        return self.name

    class Meta(ModelWithMetadata.Meta):
        permissions = (
            (ShippingPermissions.MANAGE_SHIPPING.codename, "Manage shipping."),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                fields=["countries"],
                name="s_z_countries_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]


class ShippingMethod(ModelWithMetadata):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, choices=ShippingMethodType.CHOICES)
    shipping_zone = models.ForeignKey(
        ShippingZone,
        related_name="shipping_methods",
        on_delete=models.CASCADE,
    )
    minimum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
        blank=True,
        null=True,
    )
    maximum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )
    excluded_products = models.ManyToManyField(Product, blank=True)
    maximum_delivery_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_delivery_days = models.PositiveIntegerField(null=True, blank=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="shipping_methods",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)

    def __str__(self):
        return self.name

    def __repr__(self):
        if self.type == ShippingMethodType.PRICE_BASED:
            return f"ShippingMethod(type={self.type})"
        weight_type_display = _get_weight_type_display(
            self.minimum_order_weight,
            self.maximum_order_weight,
        )
        return f"ShippingMethod(type={self.type} weight_range=({weight_type_display})"
