# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import TaxClass


@admin.register(TaxClass)
class TaxClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
