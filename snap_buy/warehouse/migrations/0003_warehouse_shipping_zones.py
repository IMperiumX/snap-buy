# Generated by Django 5.0.8 on 2024-08-09 18:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shipping", "0002_shippingmethod_excluded_products"),
        ("warehouse", "0002_stock_product_variant_alter_stock_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="shipping_zones",
            field=models.ManyToManyField(
                blank=True, related_name="warehouses", to="shipping.shippingzone"
            ),
        ),
    ]