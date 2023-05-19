# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "name",
        "slug",
        "image",
        "description",
        "price",
        "available",
        "created",
        "updated",
    )
    list_filter = ("category", "available", "created", "updated")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}
