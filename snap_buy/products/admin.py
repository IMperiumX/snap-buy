# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import (
    Category,
    ProductType,
    Product,
    ProductChannelListing,
    ProductVariant,
    ProductVariantChannelListing,
    ProductMedia,
    VariantMedia,
    Shipper,
    CollectionProduct,
    Tag,
    Collection,
    CollectionChannelListing,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "seo_title",
        "seo_description",
        "background_image",
        "background_image_alt",
        "description",
        "description_plaintext",
        "name",
        "slug",
        "parent",
        "lft",
        "rght",
        "tree_id",
        "level",
    )
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "kind",
        "has_variants",
        "is_shipping_required",
        "is_digital",
        "weight",
        "tax_class",
    )
    list_filter = (
        "has_variants",
        "is_shipping_required",
        "is_digital",
        "tax_class",
    )
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "external_reference",
        "seo_title",
        "seo_description",
        "available",
        "created",
        "description",
        "image",
        "name",
        "price",
        "rating",
        "slug",
        "updated",
        "category",
        "default_variant",
        "product_type",
        "tax_class",
        "weight",
    )
    list_filter = (
        "available",
        "created",
        "updated",
        "category",
        "default_variant",
        "product_type",
        "tax_class",
    )
    raw_id_fields = ("tags",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(ProductChannelListing)
class ProductChannelListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "published_at",
        "is_published",
        "available_for_purchase_at",
        "currency",
        "discounted_price_amount",
        "visible_in_listings",
        "channel",
        "product",
        "discounted_price",
    )
    list_filter = (
        "published_at",
        "is_published",
        "available_for_purchase_at",
        "visible_in_listings",
        "channel",
        "product",
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "external_reference",
        "created_at",
        "is_preorder",
        "name",
        "preorder_end_date",
        "preorder_global_threshold",
        "quantity_limit_per_customer",
        "sku",
        "track_inventory",
        "updated_at",
        "product",
        "weight",
    )
    list_filter = (
        "created_at",
        "is_preorder",
        "preorder_end_date",
        "track_inventory",
        "updated_at",
        "product",
    )
    raw_id_fields = ("media",)
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(ProductVariantChannelListing)
class ProductVariantChannelListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cost_price_amount",
        "currency",
        "preorder_quantity_threshold",
        "price_amount",
        "channel",
        "variant",
        "cost_price",
        "price",
    )
    list_filter = ("channel", "variant")


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "alt",
        "external_url",
        "image",
        "oembed_data",
        "type",
        "product",
    )
    list_filter = ("product",)


@admin.register(VariantMedia)
class VariantMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "media")
    list_filter = ("variant", "media")


@admin.register(Shipper)
class ShipperAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "phone")


@admin.register(CollectionProduct)
class CollectionProductAdmin(admin.ModelAdmin):
    list_display = ("id", "sort_order", "collection", "product")
    list_filter = ("collection", "product")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "seo_title",
        "seo_description",
        "background_image",
        "background_image_alt",
        "description",
        "name",
        "slug",
    )
    raw_id_fields = ("products",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(CollectionChannelListing)
class CollectionChannelListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "published_at",
        "is_published",
        "collection",
        "channel",
    )
    list_filter = ("published_at", "is_published", "collection", "channel")
