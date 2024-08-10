# Generated by Django 5.0.8 on 2024-08-10 13:01

import django.contrib.postgres.search
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import django_measurement.models
import measurement.measures.mass
import snap_buy.core.utils.json_serializer
import snap_buy.core.weight
import snap_buy.order.models
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Fulfillment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                ("fulfillment_order", models.PositiveIntegerField(editable=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("fulfilled", "Fulfilled"),
                            ("refunded", "Refunded"),
                            ("returned", "Returned"),
                            ("replaced", "Replaced"),
                            ("refunded_and_returned", "Refunded and returned"),
                            ("canceled", "Canceled"),
                            ("waiting_for_approval", "Waiting for approval"),
                        ],
                        default="fulfilled",
                        max_length=32,
                    ),
                ),
                (
                    "tracking_number",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "shipping_refund_amount",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=12, null=True
                    ),
                ),
                (
                    "total_refund_amount",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=12, null=True
                    ),
                ),
            ],
            options={
                "ordering": ("pk",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "external_reference",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=250,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "number",
                    models.IntegerField(
                        default=snap_buy.order.models.get_order_number,
                        editable=False,
                        unique=True,
                    ),
                ),
                ("use_old_id", models.BooleanField(default=False)),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("expired_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("unconfirmed", "Unconfirmed"),
                            ("unfulfilled", "Unfulfilled"),
                            ("partially fulfilled", "Partially fulfilled"),
                            ("partially_returned", "Partially returned"),
                            ("returned", "Returned"),
                            ("fulfilled", "Fulfilled"),
                            ("canceled", "Canceled"),
                            ("expired", "Expired"),
                        ],
                        default="unfulfilled",
                        max_length=32,
                    ),
                ),
                (
                    "authorize_status",
                    models.CharField(
                        choices=[
                            ("none", "The funds are not authorized"),
                            (
                                "partial",
                                "The funds that are authorized and charged don't cover fully the order's total",
                            ),
                            (
                                "full",
                                "The funds that are authorized and charged fully cover the order's total",
                            ),
                        ],
                        db_index=True,
                        default="none",
                        max_length=32,
                    ),
                ),
                (
                    "charge_status",
                    models.CharField(
                        choices=[
                            ("none", "The order is not charged."),
                            ("partial", "The order is partially charged"),
                            ("full", "The order is fully charged"),
                            ("overcharged", "The order is overcharged"),
                        ],
                        db_index=True,
                        default="none",
                        max_length=32,
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        choices=[
                            ("af", "Afrikaans"),
                            ("ar", "Arabic"),
                            ("ar-dz", "Algerian Arabic"),
                            ("ast", "Asturian"),
                            ("az", "Azerbaijani"),
                            ("bg", "Bulgarian"),
                            ("be", "Belarusian"),
                            ("bn", "Bengali"),
                            ("br", "Breton"),
                            ("bs", "Bosnian"),
                            ("ca", "Catalan"),
                            ("ckb", "Central Kurdish (Sorani)"),
                            ("cs", "Czech"),
                            ("cy", "Welsh"),
                            ("da", "Danish"),
                            ("de", "German"),
                            ("dsb", "Lower Sorbian"),
                            ("el", "Greek"),
                            ("en", "English"),
                            ("en-au", "Australian English"),
                            ("en-gb", "British English"),
                            ("eo", "Esperanto"),
                            ("es", "Spanish"),
                            ("es-ar", "Argentinian Spanish"),
                            ("es-co", "Colombian Spanish"),
                            ("es-mx", "Mexican Spanish"),
                            ("es-ni", "Nicaraguan Spanish"),
                            ("es-ve", "Venezuelan Spanish"),
                            ("et", "Estonian"),
                            ("eu", "Basque"),
                            ("fa", "Persian"),
                            ("fi", "Finnish"),
                            ("fr", "French"),
                            ("fy", "Frisian"),
                            ("ga", "Irish"),
                            ("gd", "Scottish Gaelic"),
                            ("gl", "Galician"),
                            ("he", "Hebrew"),
                            ("hi", "Hindi"),
                            ("hr", "Croatian"),
                            ("hsb", "Upper Sorbian"),
                            ("hu", "Hungarian"),
                            ("hy", "Armenian"),
                            ("ia", "Interlingua"),
                            ("id", "Indonesian"),
                            ("ig", "Igbo"),
                            ("io", "Ido"),
                            ("is", "Icelandic"),
                            ("it", "Italian"),
                            ("ja", "Japanese"),
                            ("ka", "Georgian"),
                            ("kab", "Kabyle"),
                            ("kk", "Kazakh"),
                            ("km", "Khmer"),
                            ("kn", "Kannada"),
                            ("ko", "Korean"),
                            ("ky", "Kyrgyz"),
                            ("lb", "Luxembourgish"),
                            ("lt", "Lithuanian"),
                            ("lv", "Latvian"),
                            ("mk", "Macedonian"),
                            ("ml", "Malayalam"),
                            ("mn", "Mongolian"),
                            ("mr", "Marathi"),
                            ("ms", "Malay"),
                            ("my", "Burmese"),
                            ("nb", "Norwegian Bokmål"),
                            ("ne", "Nepali"),
                            ("nl", "Dutch"),
                            ("nn", "Norwegian Nynorsk"),
                            ("os", "Ossetic"),
                            ("pa", "Punjabi"),
                            ("pl", "Polish"),
                            ("pt", "Portuguese"),
                            ("pt-br", "Brazilian Portuguese"),
                            ("ro", "Romanian"),
                            ("ru", "Russian"),
                            ("sk", "Slovak"),
                            ("sl", "Slovenian"),
                            ("sq", "Albanian"),
                            ("sr", "Serbian"),
                            ("sr-latn", "Serbian Latin"),
                            ("sv", "Swedish"),
                            ("sw", "Swahili"),
                            ("ta", "Tamil"),
                            ("te", "Telugu"),
                            ("tg", "Tajik"),
                            ("th", "Thai"),
                            ("tk", "Turkmen"),
                            ("tr", "Turkish"),
                            ("tt", "Tatar"),
                            ("udm", "Udmurt"),
                            ("ug", "Uyghur"),
                            ("uk", "Ukrainian"),
                            ("ur", "Urdu"),
                            ("uz", "Uzbek"),
                            ("vi", "Vietnamese"),
                            ("zh-hans", "Simplified Chinese"),
                            ("zh-hant", "Traditional Chinese"),
                        ],
                        default="en-us",
                        max_length=35,
                    ),
                ),
                (
                    "tracking_client_id",
                    models.CharField(blank=True, editable=False, max_length=36),
                ),
                (
                    "user_email",
                    models.EmailField(blank=True, default="", max_length=254),
                ),
                (
                    "origin",
                    models.CharField(
                        choices=[
                            ("checkout", "Checkout"),
                            ("draft", "Draft"),
                            ("reissue", "Reissue"),
                            ("bulk_create", "Bulk create"),
                        ],
                        max_length=32,
                    ),
                ),
                ("currency", models.CharField(max_length=3)),
                (
                    "shipping_method_name",
                    models.CharField(
                        blank=True,
                        default=None,
                        editable=False,
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "collection_point_name",
                    models.CharField(
                        blank=True,
                        default=None,
                        editable=False,
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "shipping_price_net_amount",
                    models.DecimalField(
                        decimal_places=3,
                        default=Decimal("0.0"),
                        editable=False,
                        max_digits=12,
                    ),
                ),
                (
                    "shipping_price_gross_amount",
                    models.DecimalField(
                        decimal_places=3,
                        default=Decimal("0.0"),
                        editable=False,
                        max_digits=12,
                    ),
                ),
                (
                    "base_shipping_price_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_base_shipping_price_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "shipping_tax_rate",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=5, null=True
                    ),
                ),
                (
                    "shipping_tax_class_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "shipping_tax_class_private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "shipping_tax_class_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                ("checkout_token", models.CharField(blank=True, max_length=36)),
                (
                    "total_net_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_total_net_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "total_gross_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_total_gross_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "total_charged_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "total_authorized_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "subtotal_net_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0"), max_digits=12
                    ),
                ),
                (
                    "subtotal_gross_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0"), max_digits=12
                    ),
                ),
                (
                    "voucher_code",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("display_gross_prices", models.BooleanField(default=True)),
                ("customer_note", models.TextField(blank=True, default="")),
                (
                    "weight",
                    django_measurement.models.MeasurementField(
                        default=snap_buy.core.weight.zero_weight,
                        measurement=measurement.measures.mass.Mass,
                    ),
                ),
                ("redirect_url", models.URLField(blank=True, null=True)),
                ("search_document", models.TextField(blank=True, default="")),
                (
                    "search_vector",
                    django.contrib.postgres.search.SearchVectorField(
                        blank=True, null=True
                    ),
                ),
                ("should_refresh_prices", models.BooleanField(default=True)),
                ("tax_exemption", models.BooleanField(default=False)),
                ("tax_error", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "ordering": ("-number",),
                "permissions": (
                    ("manage_orders", "Manage orders."),
                    ("manage_orders_import", "Manage orders import."),
                ),
            },
        ),
        migrations.CreateModel(
            name="OrderGrantedRefund",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "amount_value",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0"), max_digits=12
                    ),
                ),
                ("currency", models.CharField(max_length=3)),
                ("reason", models.TextField(blank=True, default="")),
                ("shipping_costs_included", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            (
                                "none",
                                "The refund on related transactionItem is not processed",
                            ),
                            (
                                "pending",
                                "The refund on related transactionItem is pending",
                            ),
                            (
                                "success",
                                "The refund on related transactionItem is successfully processed",
                            ),
                            ("failure", "The refund on related transactionItem failed"),
                        ],
                        default="none",
                        max_length=128,
                    ),
                ),
            ],
            options={
                "ordering": ("created_at", "id"),
            },
        ),
        migrations.CreateModel(
            name="OrderLine",
            fields=[
                (
                    "private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "old_id",
                    models.PositiveIntegerField(blank=True, null=True, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product_name", models.CharField(max_length=386)),
                (
                    "variant_name",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "translated_product_name",
                    models.CharField(blank=True, default="", max_length=386),
                ),
                (
                    "translated_variant_name",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "product_sku",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "product_variant_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("is_shipping_required", models.BooleanField()),
                ("is_gift_card", models.BooleanField()),
                (
                    "quantity",
                    models.IntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                (
                    "quantity_fulfilled",
                    models.IntegerField(
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ("is_gift", models.BooleanField(default=False)),
                ("currency", models.CharField(max_length=3)),
                (
                    "unit_discount_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "unit_discount_type",
                    models.CharField(
                        blank=True,
                        choices=[("fixed", "fixed"), ("percentage", "%")],
                        max_length=10,
                        null=True,
                    ),
                ),
                ("unit_discount_reason", models.TextField(blank=True, null=True)),
                (
                    "unit_price_net_amount",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "unit_discount_value",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "unit_price_gross_amount",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "total_price_net_amount",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "total_price_gross_amount",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "undiscounted_unit_price_gross_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_unit_price_net_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_total_price_gross_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_total_price_net_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "base_unit_price_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "undiscounted_base_unit_price_amount",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0.0"), max_digits=12
                    ),
                ),
                (
                    "tax_rate",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=5, null=True
                    ),
                ),
                (
                    "tax_class_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "tax_class_private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "tax_class_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=snap_buy.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                ("is_price_overridden", models.BooleanField(blank=True, null=True)),
                (
                    "voucher_code",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("sale_id", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "ordering": ("created_at", "id"),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="FulfillmentLine",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                (
                    "fulfillment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="order.fulfillment",
                    ),
                ),
            ],
        ),
    ]
