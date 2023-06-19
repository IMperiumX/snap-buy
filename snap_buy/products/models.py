import uuid
from functools import partial

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_measurement.models import MeasurementField
from django_prices.models import MoneyField
from measurement.measures import Weight
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

from snap_buy import file_upload
from snap_buy.channel.models import Channel
from snap_buy.core.models import ModelWithExternalReference, PublishableModel, SortableModel
from snap_buy.core.units import WeightUnits
from snap_buy.core.weight import zero_weight
from snap_buy.seo.models import SeoModel
from snap_buy.tax.models import TaxClass

from . import ProductMediaTypes, ProductTypeKind
from .managers import (
    CategoryManager,
    CollectionManager,
    ProductManager,
    ProductVariantChannelListingManager,
    ProductVariantManager,
)
from .mixins import (
    CollectionProductMixin,
    ProductChannelListingMixin,
    ProductMediaMixin,
    ProductMixin,
    ProductVariantMixin,
)


class Category(MPTTModel, SeoModel):
    background_image = models.ImageField(
        max_length=250,
        upload_to=partial(file_upload, "category"),
    )
    background_image_alt = models.CharField(max_length=128, blank=True)
    description = models.JSONField(blank=True, null=True)
    description_plaintext = models.TextField(blank=True)
    name = models.CharField(max_length=250)
    slug = models.SlugField(
        _("Slug"),
        allow_unicode=True,
        default=uuid.uuid4,
        max_length=255,
        unique=True,
    )

    parent = TreeForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    object = CategoryManager()
    tree = TreeManager()  # type: ignore[django-manager-missing]

    class Meta:
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class ProductType(models.Model):
    name = models.CharField(max_length=250)
    slug = models.SlugField(
        allow_unicode=True,
        max_length=255,
        unique=True,
    )
    kind = models.CharField(
        choices=ProductTypeKind.CHOICES,
        max_length=32,
    )
    has_variants = models.BooleanField(default=True)
    is_shipping_required = models.BooleanField(default=True)
    is_digital = models.BooleanField(default=False)
    weight = MeasurementField(
        default=zero_weight,
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
    )

    # relations
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="product_types",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("slug",)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        class_ = type(self)
        return "<{}.{}(pk={!r}, name={!r})>".format(
            class_.__module__,
            class_.__name__,
            self.pk,
            self.name,
        )


class Product(ProductMixin, SeoModel, ModelWithExternalReference):
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=partial(file_upload, "products"),
        blank=True,
    )
    name = models.CharField(max_length=250)
    price = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # DecimalField instead of FloatField to avoid rounding issues.
    rating = models.FloatField(null=True, blank=True)
    slug = models.SlugField(max_length=255)
    updated = models.DateTimeField(auto_now=True)

    # relations
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    product_type = models.ForeignKey(
        ProductType,
        related_name="products",
        on_delete=models.CASCADE,
    )
    tags = models.ManyToManyField("Tag", blank=True)
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="products",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    objects = ProductManager()

    class Meta:
        ordering = ("slug",)
        index_together = (("id", "slug"),)  # plan to query products by both id and slug

    def __str__(self):
        return self.name


class ProductChannelListing(ProductChannelListingMixin, PublishableModel):
    product = models.ForeignKey(
        Product,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="product_listings",
        on_delete=models.CASCADE,
    )
    visible_in_listings = models.BooleanField(default=False)
    available_for_purchase_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    discounted_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    discounted_price = MoneyField(amount_field="discounted_price_amount", currency_field="currency")

    class Meta:
        unique_together = [["product", "channel"]]
        ordering = ("pk",)
        indexes = [
            models.Index(fields=["published_at"]),
            BTreeIndex(fields=["discounted_price_amount"]),
        ]


class ProductVariant(ProductVariantMixin, SortableModel, ModelWithExternalReference):
    sku = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)

    track_inventory = models.BooleanField(default=True)
    is_preorder = models.BooleanField(default=False)
    preorder_end_date = models.DateTimeField(null=True, blank=True)
    preorder_global_threshold = models.IntegerField(blank=True, null=True)
    quantity_limit_per_customer = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )

    product = models.ForeignKey(
        "Product",
        related_name="variants",
        on_delete=models.CASCADE,
    )
    media = models.ManyToManyField("ProductMedia", through="VariantMedia")

    objects = ProductVariantManager()

    class Meta:
        ordering = ("sort_order", "sku")

    def __str__(self) -> str:
        return self.name or self.sku or f"ID:{self.pk}"


class ProductVariantChannelListing(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="variant_listings",
        on_delete=models.CASCADE,
    )
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    price = MoneyField(amount_field="price_amount", currency_field="currency")

    cost_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    cost_price = MoneyField(amount_field="cost_price_amount", currency_field="currency")

    preorder_quantity_threshold = models.IntegerField(blank=True, null=True)

    objects = ProductVariantChannelListingManager()

    class Meta:
        unique_together = [["variant", "channel"]]
        ordering = ("pk",)


class ProductMedia(ProductMediaMixin, SortableModel):
    product = models.ForeignKey(
        Product,
        related_name="media",
        on_delete=models.CASCADE,
        # DEPRECATED
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="products", blank=True, null=True)
    alt = models.CharField(max_length=128, blank=True)
    type = models.CharField(
        max_length=32,
        choices=ProductMediaTypes.CHOICES,
        default=ProductMediaTypes.IMAGE,
    )
    external_url = models.CharField(max_length=256, blank=True, null=True)
    oembed_data = models.JSONField(blank=True, default=dict)

    # DEPRECATED
    to_remove = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort_order", "pk")


class VariantMedia(models.Model):
    variant = models.ForeignKey(
        "ProductVariant",
        related_name="variant_media",
        on_delete=models.CASCADE,
    )
    media = models.ForeignKey(
        ProductMedia,
        related_name="variant_media",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("variant", "media")


class Shipper(models.Model):
    company_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)

    class Meta:
        ordering = ("company_name",)
        verbose_name = "shipper"
        verbose_name_plural = "shippers"


class CollectionProduct(CollectionProductMixin, SortableModel):
    collection = models.ForeignKey(
        "Collection",
        related_name="collectionproduct",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name="collectionproduct",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = (("collection", "product"),)


class Tag(models.Model):
    name = models.CharField(max_length=250, unique=True)

    def __str__(self):
        return f"{self.name}"


class Collection(SeoModel):
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )
    background_image = models.ImageField(
        blank=True,
        null=True,
        upload_to=partial(file_upload, "collection-backgrounds"),
    )
    background_image_alt = models.CharField(max_length=128, blank=True)
    name = models.CharField(max_length=250)
    description = models.JSONField(blank=True, null=True)

    products = models.ManyToManyField(
        "Product",
        blank=True,
        related_name="collections",
        through_fields=("collection", "product"),
        through=CollectionProduct,
    )

    objects = CollectionManager()

    class Meta:
        ordering = ("slug",)

    def __str__(self) -> str:
        return self.name


class CollectionChannelListing(PublishableModel):
    collection = models.ForeignKey(
        Collection,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="collection_listings",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = [["collection", "channel"]]
        ordering = ("pk",)
