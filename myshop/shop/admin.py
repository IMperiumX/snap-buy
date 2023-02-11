from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)} # slug value is automatically set using the value of name field.


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created', 'updated']
    fieldsets = (
        ('General', {
            'fields': ('name', 'slug', 'category', 'image', 'description', 'price', 'available')
        }),
        ('Meta', {
            'fields': ('created', 'updated')
        }),
    )
    raw_id_fields = ('category',)
    autocomplete_fields = ('category',)
    