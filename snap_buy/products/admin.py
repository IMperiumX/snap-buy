from django.contrib import admin

from .models import (
    Category,
    Collection,
    CollectionChannelListing,
    CollectionProduct,
    Product,
    ProductChannelListing,
    ProductMedia,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
    Shipper,
    Tag,
    VariantMedia,
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
        "default_variant",
        "description",
        "image",
        "name",
        "price",
        "rating",
        "slug",
        "updated",
        "weight",
        "category",
        "product_type",
        "tax_class",
    )
    list_filter = (
        "available",
        "created",
        "default_variant",
        "updated",
        "category",
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
        "product",
        "channel",
        "visible_in_listings",
        "available_for_purchase_at",
        "currency",
        "discounted_price_amount",
        "discounted_price",
    )
    list_filter = (
        "published_at",
        "is_published",
        "product",
        "channel",
        "visible_in_listings",
        "available_for_purchase_at",
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "external_reference",
        "sku",
        "name",
        "track_inventory",
        "is_preorder",
        "preorder_end_date",
        "preorder_global_threshold",
        "quantity_limit_per_customer",
        "created_at",
        "updated_at",
        "weight",
        "product",
    )
    list_filter = (
        "track_inventory",
        "is_preorder",
        "preorder_end_date",
        "created_at",
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
        "variant",
        "channel",
        "currency",
        "price_amount",
        "cost_price_amount",
        "preorder_quantity_threshold",
        "price",
        "cost_price",
    )
    list_filter = ("variant", "channel")


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "product",
        "image",
        "alt",
        "type",
        "external_url",
        "oembed_data",
        "to_remove",
    )
    list_filter = ("product", "to_remove")


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
        "slug",
        "background_image",
        "background_image_alt",
        "name",
        "description",
    )
    raw_id_fields = ("products",)
    search_fields = ("slug", "name")
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
