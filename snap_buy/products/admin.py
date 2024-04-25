from django.contrib import admin

from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "seller",
        "category",
        "name",
        "desc",
        "image",
        "price",
        "quantity",
        "created_at",
        "updated_at",
    )
    list_filter = ("seller", "category", "created_at", "updated_at")
    search_fields = ("name",)
    date_hierarchy = "created_at"
