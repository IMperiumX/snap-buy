from django.contrib import admin

from .models import TaxClass
from .models import TaxClassCountryRate
from .models import TaxConfiguration
from .models import TaxConfigurationPerCountry


@admin.register(TaxClass)
class TaxClassAdmin(admin.ModelAdmin):
    list_display = ("id", "private_metadata", "metadata", "name")
    search_fields = ("name",)


@admin.register(TaxClassCountryRate)
class TaxClassCountryRateAdmin(admin.ModelAdmin):
    list_display = ("id", "tax_class", "country", "rate")
    list_filter = ("tax_class",)


@admin.register(TaxConfiguration)
class TaxConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "private_metadata",
        "metadata",
        "channel",
        "charge_taxes",
        "tax_calculation_strategy",
        "display_gross_prices",
        "prices_entered_with_tax",
        "tax_app_id",
    )
    list_filter = (
        "channel",
        "charge_taxes",
        "display_gross_prices",
        "prices_entered_with_tax",
    )


@admin.register(TaxConfigurationPerCountry)
class TaxConfigurationPerCountryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tax_configuration",
        "country",
        "charge_taxes",
        "tax_calculation_strategy",
        "display_gross_prices",
        "tax_app_id",
    )
    list_filter = (
        "tax_configuration",
        "charge_taxes",
        "display_gross_prices",
    )
