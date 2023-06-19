from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class CategoryQuerySet(models.QuerySet):
    ...


class ProductsQueryset(models.QuerySet):
    def prefetched_for_webhook(self, single_object=True):
        common_fields = (
            "attributes__values",
            "attributes__assignment__attribute",
            "media",
            "variants__attributes__values",
            "variants__attributes__assignment__attribute",
            "variants__variant_medica__media",
            "variants__stocks__allocations",
            "variants__channel_listings__channel",
            "channel_listings__channel",
        )
        if single_object:
            return self.prefetch_related(*common_fields)
        return self.prefetch_related("collections", "category", *common_fields)


class ProductVariantQueryset(models.QuerySet):
    def annotate_quantities(self):
        return self.annotate(
            quantity=Coalesce(Sum("stocks__quantity"), 0),
            quantity_allocated=Coalesce(Sum("stocks__allocations__quantity_allocated"), 0),
        )

    def available_in_channel(self, channel_slug):
        return self.filter(
            channel_listings__price_amount__isnull=False,
            channel_listings__channel__slug=str(channel_slug),
        )

    def prefetched_for_webhook(self):
        return self.prefetch_related(
            "attributes__values",
            "attributes__assignment__attribute",
            "variant_media__media",
        )


class ProductVariantChannelListingQuerySet(models.QuerySet):
    def annotate_preorder_quantity_allocated(self):
        return self.annotate(
            preorder_quantity_allocated=Coalesce(Sum("preorder_allocations__quantity"), 0),
        )


class CollectionQuerySet(models.QuerySet):
    ...


CategoryManager = models.Manager.from_queryset(CategoryQuerySet)
ProductManager = models.Manager.from_queryset(ProductsQueryset)
ProductVariantManager = models.Manager.from_queryset(ProductVariantQueryset)
ProductVariantChannelListingManager = models.Manager.from_queryset(ProductVariantChannelListingQuerySet)
CollectionManager = models.Manager.from_queryset(CollectionQuerySet)
