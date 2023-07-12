import datetime

import pytz
from django.db import transaction
from django.utils import timezone
from prices import Money

from snap_buy.core.models import SortableModel
from snap_buy.products import models as products_models
from snap_buy.products.enums import ProductTypeKind


class ProductMixin:
    def get_first_image(self):
        all_media = self.media.all()
        images = [media for media in all_media if media.type == products_models.ProductMediaTypes.IMAGE]
        return images[0] if images else None

    @staticmethod
    def sort_by_attribute_fields() -> list:
        return ["concatenated_values_order", "concatenated_values", "name"]


class ProductVariantMixin:
    def get_base_price(
        self,
        channel_listing,
        price_override=None,
    ):
        return channel_listing.price if price_override is None else Money(price_override, channel_listing.currency)

    # def get_price(
    #     self,
    #     product,
    #     collections,
    #     channel,
    #     channel_listing,
    #     discounts=None,
    #     price_override=None,
    # ):
    #     price = self.get_base_price(channel_listing, price_override)
    #     return calculate_discounted_price(
    #         product=product,
    #         price=price,
    #         discounts=discounts,
    #         collections=collections,
    #         channel=channel,
    #         variant_id=self.id,
    #     )

    def get_weight(self):
        return self.weight or self.product.weight or self.product.product_type.weight

    def is_shipping_required(self) -> bool:
        return self.product.product_type.is_shipping_required

    def is_gift_card(self) -> bool:
        return self.product.product_type.kind == ProductTypeKind.GIFT_CARD

    def is_digital(self) -> bool:
        is_digital = self.product.product_type.is_digital
        return not self.is_shipping_required() and is_digital

    def display_product(self, translated: bool = False) -> str:
        if translated:
            product = self.product.translated
            variant_display = str(self.translated)
        else:
            variant_display = str(self)
            product = self.product
        product_display = f"{product} ({variant_display})" if variant_display else str(product)
        return product_display

    def get_ordering_queryset(self):
        return self.product.variants.all()

    def is_preorder_active(self):
        return self.is_preorder and (self.preorder_end_date is None or timezone.now() <= self.preorder_end_date)


class ProductMediaMixin:
    def get_ordering_queryset(self):
        if not self.product:
            return products_models.ProductMedia.objects.none()
        return self.product.media.all()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super(SortableModel, self).delete(*args, **kwargs)


class ProductChannelListingMixin:
    def is_available_for_purchase(self):
        return (
            self.available_for_purchase_at is not None
            and datetime.datetime.now(pytz.UTC) >= self.available_for_purchase_at
        )


class CollectionProductMixin:
    def get_ordering_queryset(self):
        return self.product.collectionproduct.all()
