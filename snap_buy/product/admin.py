from django.contrib import admin

from .models import Category
from .models import CategoryTranslation
from .models import Collection
from .models import CollectionChannelListing
from .models import CollectionProduct
from .models import CollectionTranslation
from .models import DigitalContent
from .models import DigitalContentUrl
from .models import Product
from .models import ProductChannelListing
from .models import ProductMedia
from .models import ProductTranslation
from .models import ProductType
from .models import ProductVariant
from .models import ProductVariantChannelListing
from .models import ProductVariantTranslation
from .models import VariantChannelListingPromotionRule
from .models import VariantMedia


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "seo_title",
        "seo_description",
        "name",
        "slug",
        "description",
        "description_plaintext",
        "updated_at",
        "parent",
        "background_image",
        "background_image_alt",
        "lft",
        "rght",
        "tree_id",
        "level",
    )
    list_filter = ("updated_at", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}
    date_hierarchy = "updated_at"


@admin.register(CategoryTranslation)
class CategoryTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "language_code",
        "seo_title",
        "seo_description",
        "category",
        "name",
        "description",
    )
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
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
        "private_metadata",
        "metadata",
        "external_reference",
        "seo_title",
        "seo_description",
        "product_type",
        "name",
        "slug",
        "description",
        "description_plaintext",
        "search_document",
        "search_vector",
        "search_index_dirty",
        "category",
        "created_at",
        "updated_at",
        "weight",
        "default_variant",
        "rating",
        "tax_class",
    )
    list_filter = (
        "product_type",
        "search_index_dirty",
        "category",
        "created_at",
        "updated_at",
        "default_variant",
        "tax_class",
    )
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}
    date_hierarchy = "created_at"


@admin.register(ProductTranslation)
class ProductTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "language_code",
        "seo_title",
        "seo_description",
        "product",
        "name",
        "description",
    )
    list_filter = ("product",)
    search_fields = ("name",)


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
        "discounted_price_dirty",
        "discounted_price",
    )
    list_filter = (
        "published_at",
        "is_published",
        "product",
        "channel",
        "visible_in_listings",
        "available_for_purchase_at",
        "discounted_price_dirty",
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "private_metadata",
        "metadata",
        "external_reference",
        "sku",
        "name",
        "product",
        "track_inventory",
        "is_preorder",
        "preorder_end_date",
        "preorder_global_threshold",
        "quantity_limit_per_customer",
        "created_at",
        "updated_at",
        "weight",
    )
    list_filter = (
        "product",
        "track_inventory",
        "is_preorder",
        "preorder_end_date",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("media",)
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(ProductVariantTranslation)
class ProductVariantTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "language_code", "product_variant", "name")
    list_filter = ("product_variant",)
    search_fields = ("name",)


@admin.register(ProductVariantChannelListing)
class ProductVariantChannelListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "variant",
        "channel",
        "currency",
        "price_amount",
        "cost_price_amount",
        "discounted_price_amount",
        "preorder_quantity_threshold",
        "price",
        "cost_price",
        "discounted_price",
    )
    list_filter = ("variant", "channel")
    raw_id_fields = ("promotion_rules",)


@admin.register(VariantChannelListingPromotionRule)
class VariantChannelListingPromotionRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "variant_channel_listing",
        "promotion_rule",
        "discount_amount",
        "currency",
        "discount",
    )
    list_filter = ("variant_channel_listing", "promotion_rule")


@admin.register(DigitalContent)
class DigitalContentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "use_default_settings",
        "automatic_fulfillment",
        "content_type",
        "product_variant",
        "content_file",
        "max_downloads",
        "url_valid_days",
    )
    list_filter = (
        "use_default_settings",
        "automatic_fulfillment",
        "product_variant",
    )


@admin.register(DigitalContentUrl)
class DigitalContentUrlAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "token",
        "content",
        "created_at",
        "download_num",
        "line",
    )
    list_filter = ("content", "created_at", "line")
    date_hierarchy = "created_at"


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sort_order",
        "private_metadata",
        "metadata",
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


@admin.register(CollectionProduct)
class CollectionProductAdmin(admin.ModelAdmin):
    list_display = ("id", "sort_order", "collection", "product")
    list_filter = ("collection", "product")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "seo_title",
        "seo_description",
        "name",
        "slug",
        "background_image",
        "background_image_alt",
        "description",
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


@admin.register(CollectionTranslation)
class CollectionTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "language_code",
        "seo_title",
        "seo_description",
        "collection",
        "name",
        "description",
    )
    list_filter = ("collection",)
    search_fields = ("name",)
