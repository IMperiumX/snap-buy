# Generated by Django 5.0.8 on 2024-08-10 13:01

import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("discount", "0001_initial"),
        ("product", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="promotionrule",
            name="gifts",
            field=models.ManyToManyField(
                blank=True, related_name="+", to="product.productvariant"
            ),
        ),
        migrations.AddField(
            model_name="promotionrule",
            name="promotion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rules",
                to="discount.promotion",
            ),
        ),
        migrations.AddField(
            model_name="promotionrule_variants",
            name="productvariant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="product.productvariant"
            ),
        ),
        migrations.AddField(
            model_name="promotionrule_variants",
            name="promotionrule",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="discount.promotionrule"
            ),
        ),
        migrations.AddField(
            model_name="promotionrule",
            name="variants",
            field=models.ManyToManyField(
                blank=True,
                through="discount.PromotionRule_Variants",
                to="product.productvariant",
            ),
        ),
        migrations.AddField(
            model_name="voucher",
            name="categories",
            field=models.ManyToManyField(blank=True, to="product.category"),
        ),
        migrations.AddField(
            model_name="voucher",
            name="collections",
            field=models.ManyToManyField(blank=True, to="product.collection"),
        ),
        migrations.AddField(
            model_name="voucher",
            name="products",
            field=models.ManyToManyField(blank=True, to="product.product"),
        ),
        migrations.AddField(
            model_name="voucher",
            name="variants",
            field=models.ManyToManyField(blank=True, to="product.productvariant"),
        ),
        migrations.AddField(
            model_name="vouchercode",
            name="voucher",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="codes",
                to="discount.voucher",
            ),
        ),
        migrations.AddField(
            model_name="vouchercustomer",
            name="voucher_code",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="discount.vouchercode",
            ),
        ),
        migrations.AddIndex(
            model_name="vouchercode",
            index=django.contrib.postgres.indexes.BTreeIndex(
                fields=["voucher"], name="vouchercode_voucher_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="vouchercustomer",
            index=django.contrib.postgres.indexes.BTreeIndex(
                fields=["voucher_code"], name="vouchercustomer_voucher_code_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="vouchercustomer",
            unique_together={("voucher_code", "customer_email")},
        ),
    ]
