import itertools
import socket
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from operator import attrgetter
from pathlib import Path
from re import match
from typing import TYPE_CHECKING, Optional, TypedDict, TypeVar, Union, cast
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models
from django.db.models import (
    Case,
    Exists,
    F,
    Model,
    OrderBy,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
    signals,
)
from django.db.models.expressions import Exists, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.encoding import iri_to_uri
from django.utils.safestring import SafeText
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django_measurement.models import MeasurementField
from django_prices.models import MoneyField
from measurement.measures import Weight
from prices import Money
from text_unidecode import unidecode

default_app_config = "saleor.core.app.CoreAppConfig"


StockWithAvailableQuantity = "Stock"


class DistanceUnits:
    MM = "mm"
    CM = "cm"
    DM = "dm"
    M = "m"
    KM = "km"
    FT = "ft"
    YD = "yd"
    INCH = "inch"

    CHOICES = [
        (MM, "Millimeter"),
        (CM, "Centimeter"),
        (DM, "Decimeter"),
        (M, "Meter"),
        (KM, "Kilometers"),
        (FT, "Feet"),
        (YD, "Yard"),
        (INCH, "Inch"),
    ]


class AreaUnits:
    SQ_MM = "sq_mm"
    SQ_CM = "sq_cm"
    SQ_DM = "sq_dm"
    SQ_M = "sq_m"
    SQ_KM = "sq_km"
    SQ_FT = "sq_ft"
    SQ_YD = "sq_yd"
    SQ_INCH = "sq_inch"

    CHOICES = [
        (SQ_MM, "Square millimeter"),
        (SQ_CM, "Square centimeters"),
        (SQ_DM, "Square decimeter"),
        (SQ_M, "Square meters"),
        (SQ_KM, "Square kilometers"),
        (SQ_FT, "Square feet"),
        (SQ_YD, "Square yards"),
        (SQ_INCH, "Square inches"),
    ]


class VolumeUnits:
    CUBIC_MILLIMETER = "cubic_millimeter"
    CUBIC_CENTIMETER = "cubic_centimeter"
    CUBIC_DECIMETER = "cubic_decimeter"
    CUBIC_METER = "cubic_meter"
    LITER = "liter"
    CUBIC_FOOT = "cubic_foot"
    CUBIC_INCH = "cubic_inch"
    CUBIC_YARD = "cubic_yard"
    QT = "qt"
    PINT = "pint"
    FL_OZ = "fl_oz"
    ACRE_IN = "acre_in"
    ACRE_FT = "acre_ft"

    CHOICES = [
        (CUBIC_MILLIMETER, "Cubic millimeter"),
        (CUBIC_CENTIMETER, "Cubic centimeter"),
        (CUBIC_DECIMETER, "Cubic decimeter"),
        (CUBIC_METER, "Cubic meter"),
        (LITER, "Liter"),
        (CUBIC_FOOT, "Cubic foot"),
        (CUBIC_INCH, "Cubic inch"),
        (CUBIC_YARD, "Cubic yard"),
        (QT, "Quart"),
        (PINT, "Pint"),
        (FL_OZ, "Fluid ounce"),
        (ACRE_IN, "Acre inch"),
        (ACRE_FT, "Acre feet"),
    ]


class WeightUnits:
    G = "g"
    LB = "lb"
    OZ = "oz"
    KG = "kg"
    TONNE = "tonne"

    CHOICES = [
        (G, "Gram"),
        (LB, "Pound"),
        (OZ, "Ounce"),
        (KG, "kg"),
        (TONNE, "Tonne"),
    ]


def prepare_all_units_dict():
    measurement_dict = {
        unit.upper(): unit
        for unit_choices in [
            DistanceUnits.CHOICES,
            AreaUnits.CHOICES,
            VolumeUnits.CHOICES,
            WeightUnits.CHOICES,
        ]
        for unit, _ in unit_choices
    }
    return dict(measurement_dict, CHOICES=[(v, v) for v in measurement_dict.values()])


MeasurementUnits = type("MeasurementUnits", (object,), prepare_all_units_dict())


class JobStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    DELETED = "deleted"

    CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (DELETED, "Deleted"),
    ]


class TimePeriodType:
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

    CHOICES = [(DAY, "Day"), (WEEK, "Week"), (MONTH, "Month"), (YEAR, "Year")]


class EventDeliveryStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

    CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    ]


class DiscountValueType:
    FIXED = "fixed"
    PERCENTAGE = "percentage"

    CHOICES = [
        (FIXED, "fixed"),
        (PERCENTAGE, "%"),
    ]


class DiscountType:
    SALE = "sale"
    PROMOTION = "promotion"
    ORDER_PROMOTION = "order_promotion"
    VOUCHER = "voucher"
    MANUAL = "manual"

    CHOICES = [
        (SALE, "Sale"),
        (VOUCHER, "Voucher"),
        (MANUAL, "Manual"),
        (PROMOTION, "Promotion"),
        (ORDER_PROMOTION, "Order promotion"),
    ]


class VoucherType:
    SHIPPING = "shipping"
    ENTIRE_ORDER = "entire_order"
    SPECIFIC_PRODUCT = "specific_product"

    CHOICES = [
        (ENTIRE_ORDER, "Entire order"),
        (SHIPPING, "Shipping"),
        (SPECIFIC_PRODUCT, "Specific products, collections and categories"),
    ]


class PromotionType:
    CATALOGUE = "catalogue"
    ORDER = "order"

    CHOICES = [
        (CATALOGUE, "Catalogue"),
        (ORDER, "Order"),
    ]


class RewardValueType:
    FIXED = "fixed"
    PERCENTAGE = "percentage"

    CHOICES = [
        (FIXED, "fixed"),
        (PERCENTAGE, "%"),
    ]


class RewardType:
    SUBTOTAL_DISCOUNT = "subtotal_discount"
    GIFT = "gift"

    CHOICES = [
        (SUBTOTAL_DISCOUNT, "subtotal_discount"),
        (GIFT, "gift"),
    ]


class PromotionEvents:
    PROMOTION_CREATED = "promotion_created"
    PROMOTION_UPDATED = "promotion_updated"
    PROMOTION_STARTED = "promotion_started"
    PROMOTION_ENDED = "promotion_ended"

    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_DELETED = "rule_deleted"

    CHOICES = [
        (PROMOTION_CREATED, "Promotion created"),
        (PROMOTION_UPDATED, "Promotion updated"),
        (PROMOTION_STARTED, "Promotion started"),
        (PROMOTION_ENDED, "Promotion ended"),
        (RULE_CREATED, "Rule created"),
        (RULE_UPDATED, "Rule updated"),
        (RULE_DELETED, "Rule deleted"),
    ]


@dataclass
class PromotionRuleInfo:
    rule: "PromotionRule"
    channel_ids: list[int]


@deconstructible
class UniqueUploadImagePath:
    """
    A callable to be passed as upload_to parameter to FileField.

    Uploaded files will get random names based on UUIDs inside the given directory;
    strftime-style formatting is supported within the directory path. If keep_basename
    is True, the original file name is prepended to the UUID. If keep_ext is disabled,
    the filename extension will be dropped.
    """

    def __init__(self, directory=None, *, keep_basename=False, keep_ext=True):
        self.directory = directory
        self.keep_basename = keep_basename
        self.keep_ext = keep_ext

    def __call__(self, model_instance, filename):
        filename_path = Path(filename)
        filename = (
            f"{model_instance.id}.{filename_path.stem}_{uuid4()}"
            if self.keep_basename
            else str(uuid4())
        )
        if self.keep_ext:
            filename += filename_path.suffix
        if self.directory is None:
            return filename
        return str(now().strftime(self.directory) / filename_path)


class ProductCategory(models.Model):
    name = models.CharField(_("Category name"), max_length=100)
    icon = models.ImageField(
        upload_to=UniqueUploadImagePath("product/category/icons"),
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")

    def __str__(self):
        return f"{self.name}"


def get_default_product_category():
    return ProductCategory.objects.get_or_create(name="Others")[0]


class Product(models.Model):
    seller = models.ForeignKey(
        "users.User",
        related_name="products",
        on_delete=models.CASCADE,
    )
    # TODO: do soft delete
    category = models.ForeignKey(
        ProductCategory,
        related_name="product_list",
        on_delete=models.SET(get_default_product_category),
    )
    name = models.CharField(max_length=200)
    desc = models.TextField(_("Description"), blank=True)
    image = models.ImageField(
        upload_to=UniqueUploadImagePath("product/images"),
        blank=True,
    )
    price = models.DecimalField(decimal_places=2, max_digits=10)
    quantity = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name


"""
Saleor Model Scheme (intial)
"""

task_logger = get_task_logger(__name__)


def get_domain(site: Optional[Site] = None) -> str:
    if settings.PUBLIC_URL:
        return urlparse(settings.PUBLIC_URL).netloc
    if site is None:
        site = Site.objects.get_current()
    return site.domain


def get_public_url(domain: Optional[str] = None) -> str:
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL
    host = domain or Site.objects.get_current().domain
    protocol = "https" if settings.ENABLE_SSL else "http"
    return f"{protocol}://{host}"


def is_ssl_enabled() -> bool:
    if settings.PUBLIC_URL:
        return urlparse(settings.PUBLIC_URL).scheme.lower() == "https"
    return settings.ENABLE_SSL


def build_absolute_uri(location: str, domain: Optional[str] = None) -> str:
    """Create absolute uri from location.

    If provided location is absolute uri by itself, it returns unchanged value,
    otherwise if provided location is relative, absolute uri is built and returned.
    """
    current_uri = get_public_url(domain)
    location = urljoin(current_uri, location)
    return iri_to_uri(location)


def get_client_ip(request):
    """Retrieve the IP address from the request data.

    Tries to get a valid IP address from X-Forwarded-For, if the user is hiding behind
    a transparent proxy or if the server is behind a proxy.

    If no forwarded IP was provided or all of them are invalid,
    it fallback to the requester IP.
    """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ips = ip.split(",")
    for ip in ips:
        if is_valid_ipv4(ip) or is_valid_ipv6(ip):
            return ip
    return request.META.get("REMOTE_ADDR", None)


def is_valid_ipv4(ip: str) -> bool:
    """Check whether the passed IP is a valid V4 IP address."""
    try:
        socket.inet_pton(socket.AF_INET, ip)
    except OSError:
        return False
    return True


def is_valid_ipv6(ip: str) -> bool:
    """Check whether the passed IP is a valid V6 IP address."""
    try:
        socket.inet_pton(socket.AF_INET6, ip)
    except OSError:
        return False
    return True


def generate_unique_slug(
    instance: Model,
    slugable_value: str,
    slug_field_name: str = "slug",
    *,
    additional_search_lookup=None,
) -> str:
    """Create unique slug for model instance.

    The function uses `django.utils.text.slugify` to generate a slug from
    the `slugable_value` of model field. If the slug already exists it adds
    a numeric suffix and increments it until a unique value is found.

    Args:
        instance: model instance for which slug is created
        slugable_value: value used to create slug
        slug_field_name: name of slug field in instance model
        additional_search_lookup: when provided, it will be used to find the instances
            with the same slug that passed also additional conditions

    """
    slug = slugify(unidecode(slugable_value))

    # in case when slugable_value contains only not allowed in slug characters, slugify
    # function will return empty string, so we need to provide some default value
    if slug == "":
        slug = "-"

    ModelClass = instance.__class__

    search_field = f"{slug_field_name}__iregex"
    pattern = rf"{slug}-\d+$|{slug}$"
    lookup = {search_field: pattern}
    if additional_search_lookup:
        lookup.update(additional_search_lookup)

    slug_values = (
        ModelClass._default_manager.filter(**lookup)
        .exclude(pk=instance.pk)
        .values_list(slug_field_name, flat=True)
    )

    unique_slug = prepare_unique_slug(slug, slug_values)

    return unique_slug


def prepare_unique_slug(slug: str, slug_values: Iterable):
    """Prepare unique slug value based on provided list of existing slug values."""
    unique_slug: Union["SafeText", str] = slug
    extension = 1

    while unique_slug in slug_values:
        extension += 1
        unique_slug = f"{slug}-{extension}"

    return unique_slug


def prepare_unique_attribute_value_slug(attribute: "Attribute", slug: str):
    value_slugs = attribute.values.filter(slug__startswith=slug).values_list(
        "slug", flat=True
    )
    return prepare_unique_slug(slug, value_slugs)


from collections.abc import Iterable
from enum import Enum

from django.conf import settings


class AttributeInputType:
    """The type that we expect to render the attribute's values as."""

    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    FILE = "file"
    REFERENCE = "reference"
    NUMERIC = "numeric"
    RICH_TEXT = "rich-text"
    PLAIN_TEXT = "plain-text"
    SWATCH = "swatch"
    BOOLEAN = "boolean"
    DATE = "date"
    DATE_TIME = "date-time"

    CHOICES = [
        (DROPDOWN, "Dropdown"),
        (MULTISELECT, "Multi Select"),
        (FILE, "File"),
        (REFERENCE, "Reference"),
        (NUMERIC, "Numeric"),
        (RICH_TEXT, "Rich Text"),
        (PLAIN_TEXT, "Plain Text"),
        (SWATCH, "Swatch"),
        (BOOLEAN, "Boolean"),
        (DATE, "Date"),
        (DATE_TIME, "Date Time"),
    ]

    # list of the input types that can be used in variant selection
    ALLOWED_IN_VARIANT_SELECTION = [DROPDOWN, BOOLEAN, SWATCH, NUMERIC]

    TYPES_WITH_CHOICES = [
        DROPDOWN,
        MULTISELECT,
        SWATCH,
    ]

    # list of the input types that are unique per instances
    TYPES_WITH_UNIQUE_VALUES = [
        FILE,
        REFERENCE,
        RICH_TEXT,
        PLAIN_TEXT,
        NUMERIC,
        DATE,
        DATE_TIME,
    ]

    # list of the translatable attributes, excluding attributes with choices.
    TRANSLATABLE_ATTRIBUTES = [
        RICH_TEXT,
        PLAIN_TEXT,
    ]


ATTRIBUTE_PROPERTIES_CONFIGURATION = {
    "filterable_in_storefront": [
        AttributeInputType.DROPDOWN,
        AttributeInputType.MULTISELECT,
        AttributeInputType.NUMERIC,
        AttributeInputType.SWATCH,
        AttributeInputType.BOOLEAN,
        AttributeInputType.DATE,
        AttributeInputType.DATE_TIME,
    ],
    "filterable_in_dashboard": [
        AttributeInputType.DROPDOWN,
        AttributeInputType.MULTISELECT,
        AttributeInputType.NUMERIC,
        AttributeInputType.SWATCH,
        AttributeInputType.BOOLEAN,
        AttributeInputType.DATE,
        AttributeInputType.DATE_TIME,
    ],
    "available_in_grid": [
        AttributeInputType.DROPDOWN,
        AttributeInputType.MULTISELECT,
        AttributeInputType.NUMERIC,
        AttributeInputType.SWATCH,
        AttributeInputType.BOOLEAN,
        AttributeInputType.DATE,
        AttributeInputType.DATE_TIME,
    ],
    "storefront_search_position": [
        AttributeInputType.DROPDOWN,
        AttributeInputType.MULTISELECT,
        AttributeInputType.BOOLEAN,
        AttributeInputType.DATE,
        AttributeInputType.DATE_TIME,
    ],
}


class AttributeType:
    PRODUCT_TYPE = "product-type"
    PAGE_TYPE = "page-type"

    CHOICES = [(PRODUCT_TYPE, "Product type"), (PAGE_TYPE, "Page type")]


class AttributeEntityType:
    """Type of a reference entity type. Must match the name of the graphql type.

    After adding a new value the `ENTITY_TYPE_MAPPING` in
    saleor/graphql/attribute/utils.py must be updated.
    """

    PAGE = "Page"
    PRODUCT = "Product"
    PRODUCT_VARIANT = "ProductVariant"

    CHOICES = [
        (PAGE, "Page"),
        (PRODUCT, "Product"),
        (PRODUCT_VARIANT, "Product Variant"),
    ]


class BasePermissionEnum(Enum):
    @property
    def codename(self):
        return self.value.split(".")[1]


class AccountPermissions(BasePermissionEnum):
    MANAGE_USERS = "account.manage_users"
    MANAGE_STAFF = "account.manage_staff"
    IMPERSONATE_USER = "account.impersonate_user"


class AppPermission(BasePermissionEnum):
    MANAGE_APPS = "app.manage_apps"
    MANAGE_OBSERVABILITY = "app.manage_observability"


class ChannelPermissions(BasePermissionEnum):
    MANAGE_CHANNELS = "channel.manage_channels"


class DiscountPermissions(BasePermissionEnum):
    MANAGE_DISCOUNTS = "discount.manage_discounts"


class PluginsPermissions(BasePermissionEnum):
    MANAGE_PLUGINS = "plugins.manage_plugins"


class GiftcardPermissions(BasePermissionEnum):
    MANAGE_GIFT_CARD = "giftcard.manage_gift_card"


class MenuPermissions(BasePermissionEnum):
    MANAGE_MENUS = "menu.manage_menus"


class CheckoutPermissions(BasePermissionEnum):
    MANAGE_CHECKOUTS = "checkout.manage_checkouts"
    HANDLE_CHECKOUTS = "checkout.handle_checkouts"
    HANDLE_TAXES = "checkout.handle_taxes"
    MANAGE_TAXES = "checkout.manage_taxes"


class OrderPermissions(BasePermissionEnum):
    MANAGE_ORDERS = "order.manage_orders"
    MANAGE_ORDERS_IMPORT = "order.manage_orders_import"


class PaymentPermissions(BasePermissionEnum):
    HANDLE_PAYMENTS = "payment.handle_payments"


class PagePermissions(BasePermissionEnum):
    MANAGE_PAGES = "page.manage_pages"


class PageTypePermissions(BasePermissionEnum):
    MANAGE_PAGE_TYPES_AND_ATTRIBUTES = "page.manage_page_types_and_attributes"


class ProductPermissions(BasePermissionEnum):
    MANAGE_PRODUCTS = "product.manage_products"


class ProductTypePermissions(BasePermissionEnum):
    MANAGE_PRODUCT_TYPES_AND_ATTRIBUTES = "product.manage_product_types_and_attributes"


class ShippingPermissions(BasePermissionEnum):
    MANAGE_SHIPPING = "shipping.manage_shipping"


class SitePermissions(BasePermissionEnum):
    MANAGE_SETTINGS = "site.manage_settings"
    MANAGE_TRANSLATIONS = "site.manage_translations"


PERMISSIONS_ENUMS = [
    AccountPermissions,
    AppPermission,
    CheckoutPermissions,
    ChannelPermissions,
    DiscountPermissions,
    GiftcardPermissions,
    MenuPermissions,
    OrderPermissions,
    PagePermissions,
    PageTypePermissions,
    PaymentPermissions,
    PluginsPermissions,
    ProductPermissions,
    ProductTypePermissions,
    ShippingPermissions,
    SitePermissions,
]


def get_permissions_codename():
    permissions_values = [
        enum.codename
        for permission_enum in PERMISSIONS_ENUMS
        for enum in permission_enum
    ]
    return permissions_values


def get_permissions_enum_list():
    permissions_list = [
        (enum.name, enum.value)
        for permission_enum in PERMISSIONS_ENUMS
        for enum in permission_enum
    ]
    return permissions_list


def get_permissions_enum_dict():
    return {
        enum.name: enum
        for permission_enum in PERMISSIONS_ENUMS
        for enum in permission_enum
    }


def get_permissions_from_names(names: list[str]):
    """Convert list of permission names - ['MANAGE_ORDERS'] to Permission db objects."""
    permissions = get_permissions_enum_dict()
    return get_permissions([permissions[name].value for name in names])


def get_permission_names(permissions: Iterable["Permission"]):
    """Convert Permissions db objects to list of Permission enums."""
    permission_dict = get_permissions_enum_dict()
    names = set()
    for perm in permissions:
        for _, perm_enum in permission_dict.items():
            if perm.codename == perm_enum.codename:
                names.add(perm_enum.name)
    return names


def split_permission_codename(permissions):
    return [permission.split(".")[1] for permission in permissions]


def get_permissions(
    permissions=None,
    database_connection_name: str = settings.DATABASE_CONNECTION_DEFAULT_NAME,
):
    if permissions is None:
        codenames = get_permissions_codename()
    else:
        codenames = split_permission_codename(permissions)
    return get_permissions_from_codenames(codenames, database_connection_name)


def get_permissions_from_codenames(
    permission_codenames: list[str],
    database_connection_name: str = settings.DATABASE_CONNECTION_DEFAULT_NAME,
) -> QuerySet:
    return (
        Permission.objects.using(database_connection_name)
        .filter(codename__in=permission_codenames)
        .prefetch_related("content_type")
        .order_by("codename")
    )


from typing import TYPE_CHECKING, Any, TypeVar, Union

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models, transaction

from .. import AttributeEntityType, AttributeInputType, AttributeType


def permission_required(
    requestor: Union["User", "App", None], perms: Iterable[BasePermissionEnum]
) -> bool:

    if isinstance(requestor, User):
        return requestor.has_perms(perms)
    elif requestor:
        # for now MANAGE_STAFF permission for app is not supported
        if AccountPermissions.MANAGE_STAFF in perms:
            return False
        return requestor.has_perms(perms)
    return False


def has_one_of_permissions(
    requestor: Union["User", "App", None], permissions: Iterable[BasePermissionEnum]
) -> bool:
    if not permissions:
        return True
    if not requestor:
        return False
    for perm in permissions:
        if permission_required(requestor, (perm,)):
            return True
    return False


class TranslationWrapper:
    def __init__(self, instance, locale):
        self.instance = instance
        self.translation = next(
            (t for t in instance.translations.all() if t.language_code == locale), None
        )

    def __getattr__(self, item):
        if all(
            [
                item not in ["id", "pk"],
                self.translation is not None,
                hasattr(self.translation, item),
            ]
        ):
            return getattr(self.translation, item)
        return getattr(self.instance, item)

    def __str__(self):
        instance = self.translation or self.instance
        return str(instance)


class Translation(models.Model):
    language_code = models.CharField(max_length=35)

    class Meta:
        abstract = True

    def get_translated_object_id(self) -> tuple[str, Union[int, str]]:
        raise NotImplementedError(
            "Models extending Translation should implement get_translated_object_id"
        )

    def get_translated_keys(self) -> dict[str, Any]:
        raise NotImplementedError(
            "Models extending Translation should implement get_translated_keys"
        )

    def get_translation_context(self) -> dict[str, Any]:
        return {}


def get_translation(instance, language_code=None) -> TranslationWrapper:
    if not language_code:
        language_code = settings.LANGUAGE_CODE
    return TranslationWrapper(instance, language_code)


import re
import warnings
from typing import Literal, Union, overload

from django.utils.html import strip_tags
from urllib3.util import parse_url

BLACKLISTED_URL_SCHEMES = ("javascript",)
HYPERLINK_TAG_WITH_URL_PATTERN = r"(.*?<a\s+href=\\?\")(\w+://\S+[^\\])(\\?\">)"

ITEM_TYPE_TO_CLEAN_FUNC_MAP = {
    "list": lambda *params: clean_list_item(*params),
    "image": lambda *params: clean_image_item(*params),
    "embed": lambda *params: clean_embed_item(*params),
}


@overload
def clean_editor_js(
    definitions: Union[dict, str, None], *, to_string: Literal[True]
) -> str: ...


@overload
def clean_editor_js(definitions: dict) -> dict: ...


@overload
def clean_editor_js(definitions: None) -> None: ...


def clean_editor_js(definitions, *, to_string=False) -> Union[dict, str, None]:
    """Sanitize a given EditorJS JSON definitions.

    Look for not allowed URLs, replaced them with `invalid` value, and clean valid ones.

    `to_string` flag is used for returning concatenated string from all blocks
     instead of returning json object.
    """
    if definitions is None:
        return "" if to_string else definitions

    blocks = definitions.get("blocks")

    if not blocks or not isinstance(blocks, list):
        return "" if to_string else definitions

    plain_text_list: list[str] = []

    for index, block in enumerate(blocks):
        block_type = block["type"]
        data = block.get("data")
        if not data or not isinstance(data, dict):
            continue

        params = [blocks, block, plain_text_list, to_string, index]
        if clean_func := ITEM_TYPE_TO_CLEAN_FUNC_MAP.get(block_type):
            clean_func(*params)
        else:
            clean_other_items(*params)

    return " ".join(plain_text_list) if to_string else definitions


def clean_list_item(blocks, block, plain_text_list, to_string, index):
    for item_index, item in enumerate(block["data"]["items"]):
        if not item:
            return
        if to_string:
            plain_text_list.append(strip_tags(item))
        else:
            new_text = clean_text_data_block(item)
            blocks[index]["data"]["items"][item_index] = new_text


def clean_image_item(blocks, block, plain_text_list, to_string, index):
    file_url = block["data"].get("file", {}).get("url")
    caption = block["data"].get("caption")
    if file_url:
        if to_string:
            plain_text_list.append(strip_tags(file_url))
        else:
            file_url = clean_text_data_block(file_url)
            blocks[index]["data"]["file"]["ulr"] = file_url
    if caption:
        if to_string:
            plain_text_list.append(strip_tags(caption))
        else:
            caption = clean_text_data_block(caption)
            blocks[index]["data"]["caption"] = caption


def clean_embed_item(blocks, block, plain_text_list, to_string, index):
    for field in ["source", "embed", "caption"]:
        data = block["data"].get(field)
        if not data:
            return
        if to_string:
            plain_text_list.append(strip_tags(data))
        else:
            data = clean_text_data_block(data)
            blocks[index]["data"][field] = data


def clean_other_items(
    blocks,
    block,
    plain_text_list,
    to_string,
    index,
):
    text = block["data"].get("text")
    if not text:
        return
    if to_string:
        plain_text_list.append(strip_tags(text))
    else:
        new_text = clean_text_data_block(text)
        blocks[index]["data"]["text"] = new_text


def clean_text_data_block(text: str) -> str:
    """Look for url in text, check if URL is allowed and return the cleaned URL.

    By default, only the protocol ``javascript`` is denied.
    """

    if not text:
        return text

    end_of_match = 0
    new_text = ""
    for match in re.finditer(HYPERLINK_TAG_WITH_URL_PATTERN, text):
        original_url = match.group(2)
        original_url.strip()

        url = parse_url(original_url)
        new_url = url.url
        url_scheme = url.scheme
        if url_scheme in BLACKLISTED_URL_SCHEMES:
            warnings.warn(
                f"An invalid url was sent: {original_url} "
                f"-- Scheme: {url_scheme} is blacklisted"
            )
            new_url = "#invalid"

        new_text += match.group(1) + new_url + match.group(3)
        end_of_match = match.end()

    if end_of_match:
        new_text += text[end_of_match:]

    return new_text if new_text else text


class BaseAssignedAttribute(models.Model):
    # TODO: stop using this class in new code
    # See: https://github.com/saleor/saleor/issues/12881
    class Meta:
        abstract = True

    @property
    def attribute(self):
        return self.assignment.attribute  # type: ignore[attr-defined] # mixin


T = TypeVar("T", bound=models.Model)


class BaseAttributeQuerySet(models.QuerySet[T]):
    def get_public_attributes(self):
        raise NotImplementedError

    def get_visible_to_user(self, requestor: Union["User", "App", None]):
        if has_one_of_permissions(
            requestor,
            [
                PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,
                ProductTypePermissions.MANAGE_PRODUCT_TYPES_AND_ATTRIBUTES,
            ],
        ):
            return self.all()
        return self.get_public_attributes()


class AssociatedAttributeQuerySet(BaseAttributeQuerySet[T]):
    def get_public_attributes(self):
        attributes = Attribute.objects.filter(visible_in_storefront=True)
        return self.filter(Exists(attributes.filter(id=OuterRef("attribute_id"))))


AssociatedAttributeManager = models.Manager.from_queryset(AssociatedAttributeQuerySet)


class AttributeQuerySet(BaseAttributeQuerySet[T]):
    def get_unassigned_product_type_attributes(self, product_type_pk: int):
        return self.product_type_attributes().exclude(
            Q(attributeproduct__product_type_id=product_type_pk)
            | Q(attributevariant__product_type_id=product_type_pk)
        )

    def get_unassigned_page_type_attributes(self, page_type_pk: int):
        return self.page_type_attributes().exclude(
            attributepage__page_type_id=page_type_pk
        )

    def get_assigned_product_type_attributes(self, product_type_pk: int):
        return self.product_type_attributes().filter(
            Q(attributeproduct__product_type_id=product_type_pk)
            | Q(attributevariant__product_type_id=product_type_pk)
        )

    def get_assigned_page_type_attributes(self, product_type_pk: int):
        return self.page_type_attributes().filter(
            Q(attributepage__page_type_id=product_type_pk)
        )

    def get_public_attributes(self):
        return self.filter(visible_in_storefront=True)

    def _get_sorted_m2m_field(self, m2m_field_name: str, asc: bool):
        sort_order_field = F(f"{m2m_field_name}__sort_order")
        id_field = F(f"{m2m_field_name}__id")
        if asc:
            sort_method = sort_order_field.asc(nulls_last=True)
            id_sort: Union[OrderBy, F] = id_field
        else:
            sort_method = sort_order_field.desc(nulls_first=True)
            id_sort = id_field.desc()

        return self.order_by(sort_method, id_sort)

    def product_attributes_sorted(self, asc=True):
        return self._get_sorted_m2m_field("attributeproduct", asc)

    def variant_attributes_sorted(self, asc=True):
        return self._get_sorted_m2m_field("attributevariant", asc)

    def product_type_attributes(self):
        return self.filter(type=AttributeType.PRODUCT_TYPE)

    def page_type_attributes(self):
        return self.filter(type=AttributeType.PAGE_TYPE)


AttributeManager = models.Manager.from_queryset(AttributeQuerySet)


class Attribute(ModelWithMetadata, ModelWithExternalReference):
    slug = models.SlugField(max_length=250, unique=True, allow_unicode=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=AttributeType.CHOICES)

    input_type = models.CharField(
        max_length=50,
        choices=AttributeInputType.CHOICES,
        default=AttributeInputType.DROPDOWN,
    )
    entity_type = models.CharField(
        max_length=50, choices=AttributeEntityType.CHOICES, blank=True, null=True
    )

    product_types = models.ManyToManyField(
        ProductType,
        blank=True,
        related_name="product_attributes",
        through="attribute.AttributeProduct",
        through_fields=("attribute", "product_type"),
    )
    product_variant_types = models.ManyToManyField(
        ProductType,
        blank=True,
        related_name="variant_attributes",
        through="attribute.AttributeVariant",
        through_fields=("attribute", "product_type"),
    )
    page_types = models.ManyToManyField(
        PageType,
        blank=True,
        related_name="page_attributes",
        through="attribute.AttributePage",
        through_fields=("attribute", "page_type"),
    )

    unit = models.CharField(
        max_length=100,
        # MeasurementUnits is constructed programmatically, so mypy can't see its fields
        choices=MeasurementUnits.CHOICES,  # type: ignore[attr-defined]
        blank=True,
        null=True,
    )
    value_required = models.BooleanField(default=False, blank=True)
    is_variant_only = models.BooleanField(default=False, blank=True)
    visible_in_storefront = models.BooleanField(default=True, blank=True)

    filterable_in_storefront = models.BooleanField(default=False, blank=True)
    filterable_in_dashboard = models.BooleanField(default=False, blank=True)

    storefront_search_position = models.IntegerField(default=0, blank=True)
    available_in_grid = models.BooleanField(default=False, blank=True)
    max_sort_order = models.IntegerField(default=None, null=True, blank=True)

    objects = AttributeManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("storefront_search_position", "slug")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="attribute_gin",
                # `opclasses` and `fields` should be the same length
                fields=["slug", "name", "type", "input_type", "entity_type", "unit"],
                opclasses=["gin_trgm_ops"] * 6,
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def has_values(self) -> bool:
        return self.values.exists()


class AttributeTranslation(Translation):
    attribute = models.ForeignKey(
        Attribute, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = (("language_code", "attribute"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, attribute_pk={self.attribute_id!r})"

    def __str__(self) -> str:
        return self.name

    def get_translated_object_id(self):
        return "Attribute", self.attribute_id

    def get_translated_keys(self):
        return {"name": self.name}


class AttributeValueManager(models.Manager):
    def _prepare_query_for_bulk_operation(self, objects_data):
        query_params = models.Q()

        for obj in objects_data:
            defaults = obj.pop("defaults")
            query_params |= models.Q(**obj)
            obj["defaults"] = defaults

        return self.filter(query_params)

    def _is_correct_record(self, record, obj):
        is_correct_record = (
            getattr(record, field_name) == field_value
            for field_name, field_value in obj.items()
            if field_name != "defaults"
        )
        return all(is_correct_record)

    def bulk_get_or_create(self, objects_data):
        # this method mimics django's queryset.get_or_create method on bulk objects
        # instead of performing it one by one
        # https://docs.djangoproject.com/en/5.0/ref/models/querysets/#get-or-create

        results = []
        objects_not_in_db: list[AttributeValue] = []

        # prepare a list that will save order index of attribute values
        objects_enumerated = list(enumerate(objects_data))
        query = self._prepare_query_for_bulk_operation(objects_data)

        # iterate over all records in db and check if they match any of objects data
        for record in query.iterator():
            # iterate over all objects data and check if they match any of records in db
            for index, obj in objects_enumerated:
                if self._is_correct_record(record, obj):
                    # upon finding existing record add it to results
                    results.append((index, record))
                    # remove it from objects list, so it won't be added to new records
                    objects_enumerated.remove((index, obj))

                    break

        # add what is left to the list of new records
        self._add_new_records(objects_enumerated, objects_not_in_db, results)
        # sort results by index as db record order might be different from sort_order
        results.sort()
        results = [obj for index, obj in results]

        if objects_not_in_db:
            # After migrating to Django 4.0 we should use `update_conflicts` instead
            # of `ignore_conflicts`
            # https://docs.djangoproject.com/en/4.1/ref/models/querysets/#bulk-create
            self.bulk_create(
                objects_not_in_db,  # type: ignore[arg-type]
                ignore_conflicts=True,
            )

        return results

    def bulk_update_or_create(self, objects_data):
        # this method mimics django's queryset.update_or_create method on bulk objects
        # https://docs.djangoproject.com/en/5.0/ref/models/querysets/#update-or-create
        results = []
        objects_not_in_db: list[AttributeValue] = []
        objects_to_be_updated = []
        update_fields = set()
        objects_enumerated = list(enumerate(objects_data))
        query = self._prepare_query_for_bulk_operation(objects_data)

        # iterate over all records in db and check if they match any of objects data
        for record in query.iterator():
            # iterate over all objects data and check if they match any of records in db
            for index, obj in objects_enumerated:
                if self._is_correct_record(record, obj):
                    # upon finding a matching record, update it with defaults
                    for key, value in obj["defaults"].items():
                        setattr(record, key, value)
                        update_fields.add(key)

                    # add it to results and objects to be updated
                    results.append((index, record))

                    # add it to objects to be updated, so it can be bulk updated later
                    objects_to_be_updated.append(record)

                    # remove it from objects data, so it won't be added to new records
                    objects_enumerated.remove((index, obj))

                    break

        # add what is left to the list of new records
        self._add_new_records(objects_enumerated, objects_not_in_db, results)

        # sort results by index as db record order might be different from sort_order
        results.sort()
        results = [obj for index, obj in results]

        if objects_not_in_db:
            # After migrating to Django 4.0 we should use `update_conflicts` instead
            # of `ignore_conflicts`
            # https://docs.djangoproject.com/en/4.1/ref/models/querysets/#bulk-create
            self.bulk_create(
                objects_not_in_db,  # type: ignore[arg-type]
                ignore_conflicts=True,
            )

        if objects_to_be_updated:
            self.bulk_update(
                objects_to_be_updated,
                fields=update_fields,  # type: ignore[arg-type]
            )

        return results

    def _add_new_records(self, objects_enumerated, objects_not_in_db, results):
        for index, obj in objects_enumerated:
            # updating object data with defaults as they contain new values
            defaults = obj.pop("defaults")
            obj.update(defaults)

            # add new record to the list of new records, so it can be bulk created later
            record = self.model(**obj)
            objects_not_in_db.append(record)
            results.append((index, record))


class AttributeValue(ModelWithExternalReference):
    name = models.CharField(max_length=250)
    # keeps hex code color value in #RRGGBBAA format
    value = models.CharField(max_length=255, blank=True, default="")
    slug = models.SlugField(max_length=255, allow_unicode=True)
    file_url = models.URLField(null=True, blank=True)
    content_type = models.CharField(max_length=50, null=True, blank=True)
    attribute = models.ForeignKey(
        Attribute, related_name="values", on_delete=models.CASCADE
    )
    rich_text = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    plain_text = models.TextField(
        blank=True,
        null=True,
    )
    boolean = models.BooleanField(blank=True, null=True)
    date_time = models.DateTimeField(blank=True, null=True)

    reference_product = models.ForeignKey(
        Product,
        related_name="references",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    reference_variant = models.ForeignKey(
        ProductVariant,
        related_name="references",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    reference_page = models.ForeignKey(
        Page, related_name="references", on_delete=models.CASCADE, null=True, blank=True
    )
    sort_order = models.IntegerField(editable=False, db_index=True, null=True)

    objects = AttributeValueManager()

    class Meta:
        ordering = ("sort_order", "pk")
        unique_together = ("slug", "attribute")
        indexes = [
            GinIndex(
                name="attribute_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["name", "slug"],
                opclasses=["gin_trgm_ops"] * 2,
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def input_type(self):
        return self.attribute.input_type

    def get_ordering_queryset(self):
        return self.attribute.values.all()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk is None or self.sort_order is None:
            self.set_current_sorting_order()

        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.sort_order is not None:
            qs = self.get_ordering_queryset()
            if qs.filter(sort_order__gt=self.sort_order).update(
                sort_order=F("sort_order") - 1
            ):
                if self.attribute.max_sort_order is None:
                    value = self._calculate_sort_order_value()
                    self.attribute.max_sort_order = max(value - 1, 0)
                    self.attribute.save(update_fields=["max_sort_order"])
                else:
                    Attribute.objects.filter(pk=self.attribute.pk).update(
                        max_sort_order=Case(
                            When(
                                Q(max_sort_order__gt=0),
                                then=F("max_sort_order") - 1,
                            ),
                            default=Value(0),
                        )
                    )

        super().delete(*args, **kwargs)

    def _calculate_sort_order_value(self):
        qs = self.get_ordering_queryset()
        existing_max = SortableModel.get_max_sort_order(qs)
        return -1 if existing_max is None else existing_max

    def _save_new_max_sort_order(self, value):
        self.sort_order = value
        self.attribute.max_sort_order = value
        self.attribute.save(update_fields=["max_sort_order"])

    def set_current_sorting_order(self):
        if self.attribute.max_sort_order is None:
            value = self._calculate_sort_order_value()
            self._save_new_max_sort_order(value + 1)
        else:
            Attribute.objects.filter(pk=self.attribute.pk).update(
                max_sort_order=F("max_sort_order") + 1
            )
            self.attribute.refresh_from_db()
            self.sort_order = self.attribute.max_sort_order


class AttributeValueTranslation(Translation):
    attribute_value = models.ForeignKey(
        AttributeValue, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=250)
    rich_text = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    plain_text = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = (("language_code", "attribute_value"),)

    def __repr__(self) -> str:
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, attribute_value_pk={self.attribute_value_id!r})"

    def __str__(self) -> str:
        return self.name

    def get_translated_object_id(self):
        return "AttributeValue", self.attribute_value_id

    def get_translated_keys(self):
        return {"name": self.name, "rich_text": self.rich_text}

    def get_translation_context(self):
        context = {}
        attribute_value = self.attribute_value
        attribute = attribute_value.attribute
        context["attribute_id"] = attribute.id
        if attribute.input_type in AttributeInputType.TYPES_WITH_UNIQUE_VALUES:
            if attribute.type == AttributeType.PRODUCT_TYPE:
                if assigned_variant_attribute_value := (
                    attribute_value.variantvalueassignment.first()
                ):
                    if variant := assigned_variant_attribute_value.assignment.variant:
                        context["product_variant_id"] = variant.id
                        context["product_id"] = variant.product_id
                elif assigned_product_attribute_value := (
                    attribute_value.productvalueassignment.first()
                ):
                    if product_id := assigned_product_attribute_value.product_id:
                        context["product_id"] = product_id
            elif attribute.type == AttributeType.PAGE_TYPE:
                if assigned_page_attribute_value := (
                    attribute_value.pagevalueassignment.first()
                ):
                    if page := assigned_page_attribute_value.page:
                        context["page_id"] = page.id
                        if page_type_id := page.page_type_id:
                            context["page_type_id"] = page_type_id
        return context


from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


def _user_has_perm(user, perm, obj):
    """Backend can raise `PermissionDenied` to short-circuit permission checking."""
    for backend in auth.get_backends():
        if not hasattr(backend, "has_perm"):
            continue
        try:
            if backend.has_perm(user, perm, obj):
                return True
        except PermissionDenied:
            return False
    return False


def _user_get_permissions(user, obj, from_name):
    permissions = set()
    name = "get_%s_permissions" % from_name
    for backend in auth.get_backends():
        if hasattr(backend, name):
            permissions.update(getattr(backend, name)(user, obj))
    return permissions


class PermissionManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, codename, app_label, model):
        return self.get(
            codename=codename,
            content_type=ContentType.objects.db_manager(self.db).get_by_natural_key(
                app_label, model
            ),
        )


class Permission(models.Model):
    """The system provides a way to assign permissions to users and groups of users.

    The permission system is used by the Django admin site, but may also be
    useful in your own code. The Django admin site uses permissions as follows:

        - The "add" permission limits the user's ability to view the "add" form
          and add an object.
        - The "change" permission limits a user's ability to view the change
          list, view the "change" form and change an object.
        - The "delete" permission limits the ability to delete an object.
        - The "view" permission limits the ability to view an object.

    Permissions are set globally per type of object, not per specific object
    instance. It is possible to say "Mary may change news stories," but it's
    not currently possible to say "Mary may change news stories, but only the
    ones she created herself" or "Mary may only change news stories that have a
    certain status or publication date."

    The permissions listed above are automatically created for each model.
    """

    name = models.CharField(_("name"), max_length=255)
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name=_("content type"),
        related_name="content_type",
    )
    codename = models.CharField(_("codename"), max_length=100)

    objects = PermissionManager()

    class Meta:
        verbose_name = _("permission")
        verbose_name_plural = _("permissions")
        unique_together = [["content_type", "codename"]]
        ordering = ["content_type__app_label", "content_type__model", "codename"]

    def __str__(self):
        return f"{self.content_type} | {self.name}"

    def natural_key(self):
        return (self.codename,) + self.content_type.natural_key()

    natural_key.dependencies = ["contenttypes.contenttype"]  # type: ignore[attr-defined] # noqa: E501


class PermissionsMixin(models.Model):  # noqa: D205, D212, D400, D415
    """Add the fields and methods necessary to support permissions."""

    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_(
            "Designates that this user has all permissions without "
            "explicitly assigning them."
        ),
    )
    groups = models.ManyToManyField(
        "account.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="user_set",
        related_query_name="user",
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):  # noqa: D205, D212
        """Return a list of permission strings that this user has directly.

        Query all available auth backends. If an object is passed in, return only
        permissions matching this object.
        """
        return _user_get_permissions(self, obj, "user")

    def get_group_permissions(self, obj=None):  # noqa: D205, D212, D400, D415
        """Return a list of permission strings that this user has through their groups.

        Query all available auth backends. If an object is passed in, return only
        permissions matching this object.
        """
        return _user_get_permissions(self, obj, "group")

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "all")

    def has_perm(self, perm, obj=None):  # noqa: D205, D212, D400, D415
        """Return True if the user has the specified permission.

        Query all available auth backends, but return immediately if any backend
        returns True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:  # type: ignore[attr-defined] # mixin
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):  # noqa: D205, D212, D400, D415
        """Return True if the user has each of the specified permissions.

        If an object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)


import datetime
from collections.abc import Iterable
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import pytz
from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from measurement.measures import Weight
from mptt.managers import TreeManager
from prices import Money

ALL_PRODUCTS_PERMISSIONS = [
    # List of permissions, where each of them allows viewing all products
    # (including unpublished).
    OrderPermissions.MANAGE_ORDERS,
    DiscountPermissions.MANAGE_DISCOUNTS,
    ProductPermissions.MANAGE_PRODUCTS,
]

"""In Saleor we are using 'weight' instead of a 'mass'.

For those of us who are earth-bound, weight is what we usually experience.
Mass is a theoretical construct.
Unless we are dealing with inertia and momentum, we are encountering
the attractive force between ourselves and the earth,
the isolated effects of mass alone being a little more esoteric.

So even though mass is more fundamental, most people think
in terms of weight.

In the end, it does not really matter unless you travel between
different planets.
"""

from measurement.measures import Weight


def zero_weight():
    """Represent the zero weight value."""
    return Weight(kg=0)


def convert_weight(weight: Weight, unit: str) -> Weight:
    """Covert weight to given unit and round it to 3 digits after decimal point."""
    # Weight amount from the Weight instance can be retrieved in several units
    # via its properties. eg. Weight(lb=10).kg
    converted_weight = getattr(weight, unit)
    weight = Weight(**{unit: converted_weight})
    weight.value = round(weight.value, 3)
    return weight


def get_default_weight_unit():
    site = Site.objects.get_current()
    return site.settings.default_weight_unit


def convert_weight_to_default_weight_unit(weight: Weight) -> Weight:
    """Weight is kept in one unit, but should be returned in site default unit."""
    default_unit = get_default_weight_unit()
    if weight is not None:
        if weight.unit != default_unit:
            weight = convert_weight(weight, default_unit)
        else:
            weight.value = round(weight.value, 3)
    return weight


class Category(ModelWithMetadata, MPTTModel, SeoModel):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    description_plaintext = TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    background_image = models.ImageField(
        upload_to="category-backgrounds", blank=True, null=True
    )
    background_image_alt = models.CharField(max_length=128, blank=True)

    objects = models.Manager()
    tree = TreeManager()  # type: ignore[django-manager-missing]

    class Meta:
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="category_search_name_slug_gin",
                # `opclasses` and `fields` should be the same length
                fields=["name", "slug", "description_plaintext"],
                opclasses=["gin_trgm_ops"] * 3,
            ),
            BTreeIndex(fields=["updated_at"], name="updated_at_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class CategoryTranslation(SeoModelTranslation):
    category = models.ForeignKey(
        Category, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=128, blank=True, null=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        unique_together = (("language_code", "category"),)

    def __str__(self) -> str:
        return self.name if self.name else str(self.pk)

    def __repr__(self) -> str:
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, category_pk={self.category_id!r})"

    def get_translated_object_id(self):
        return "Category", self.category_id

    def get_translated_keys(self):
        translated_keys = super().get_translated_keys()
        translated_keys.update(
            {
                "name": self.name,
                "description": self.description,
            }
        )
        return translated_keys


class ProductType(ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    kind = models.CharField(max_length=32, choices=ProductTypeKind.CHOICES)
    has_variants = models.BooleanField(default=True)
    is_shipping_required = models.BooleanField(default=True)
    is_digital = models.BooleanField(default=False)
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
    )
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="product_types",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        app_label = "product"
        permissions = (
            (
                ProductTypePermissions.MANAGE_PRODUCT_TYPES_AND_ATTRIBUTES.codename,
                "Manage product types and attributes.",
            ),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="product_type_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["name", "slug"],
                opclasses=["gin_trgm_ops"] * 2,
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        class_ = type(self)
        return f"<{class_.__module__}.{class_.__name__}(pk={self.pk!r}, name={self.name!r})>"


class Product(SeoModel, ModelWithMetadata, ModelWithExternalReference):
    product_type = models.ForeignKey(
        ProductType, related_name="products", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    description_plaintext = TextField(blank=True)
    search_document = models.TextField(blank=True, default="")
    search_vector = SearchVectorField(blank=True, null=True)
    search_index_dirty = models.BooleanField(default=False, db_index=True)

    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    rating = models.FloatField(null=True, blank=True)
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="products",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    objects = managers.ProductManager()

    class Meta:
        app_label = "product"
        ordering = ("slug",)
        permissions = (
            (ProductPermissions.MANAGE_PRODUCTS.codename, "Manage products."),
        )
        indexes = [
            GinIndex(
                name="product_search_gin",
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="product_tsearch",
                fields=["search_vector"],
            ),
            GinIndex(
                name="product_gin",
                fields=["name", "slug"],
                opclasses=["gin_trgm_ops"] * 2,
            ),
        ]
        indexes.extend(ModelWithMetadata.Meta.indexes)

    def __iter__(self):
        if not hasattr(self, "__variants"):
            setattr(self, "__variants", self.variants.all())
        return iter(getattr(self, "__variants"))

    def __repr__(self) -> str:
        class_ = type(self)
        return f"<{class_.__module__}.{class_.__name__}(pk={self.pk!r}, name={self.name!r})>"

    def __str__(self) -> str:
        return self.name

    def get_first_image(self):
        all_media = self.media.all()
        images = [media for media in all_media if media.type == ProductMediaTypes.IMAGE]
        return images[0] if images else None

    @staticmethod
    def sort_by_attribute_fields() -> list:
        return ["concatenated_values_order", "concatenated_values", "name"]


class ProductTranslation(SeoModelTranslation):
    product = models.ForeignKey(
        Product, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=250, blank=True, null=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        unique_together = (("language_code", "product"),)

    def __str__(self) -> str:
        return self.name if self.name else str(self.pk)

    def __repr__(self) -> str:
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, product_pk={self.product_id!r})"

    def get_translated_object_id(self):
        return "Product", self.product_id

    def get_translated_keys(self):
        translated_keys = super().get_translated_keys()
        translated_keys.update(
            {
                "name": self.name,
                "description": self.description,
            }
        )
        return translated_keys


class ProductChannelListing(PublishableModel):
    product = models.ForeignKey(
        Product,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="product_listings",
        on_delete=models.CASCADE,
    )
    visible_in_listings = models.BooleanField(default=False)
    available_for_purchase_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    discounted_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    discounted_price = MoneyField(
        amount_field="discounted_price_amount", currency_field="currency"
    )
    discounted_price_dirty = models.BooleanField(default=False)

    class Meta:
        unique_together = [["product", "channel"]]
        ordering = ("pk",)
        indexes = [
            models.Index(fields=["published_at"]),
            BTreeIndex(fields=["discounted_price_amount"]),
        ]

    def is_available_for_purchase(self):
        return (
            self.available_for_purchase_at is not None
            and datetime.datetime.now(pytz.UTC) >= self.available_for_purchase_at
        )


class ProductVariant(SortableModel, ModelWithMetadata, ModelWithExternalReference):
    sku = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    product = models.ForeignKey(
        Product, related_name="variants", on_delete=models.CASCADE
    )
    media = models.ManyToManyField(
        "product.ProductMedia", through="product.VariantMedia"
    )
    track_inventory = models.BooleanField(default=True)
    is_preorder = models.BooleanField(default=False)
    preorder_end_date = models.DateTimeField(null=True, blank=True)
    preorder_global_threshold = models.IntegerField(blank=True, null=True)
    quantity_limit_per_customer = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )

    objects = managers.ProductVariantManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("sort_order", "sku")
        app_label = "product"

    def __str__(self) -> str:
        return self.name or self.sku or f"ID:{self.pk}"

    def get_base_price(
        self,
        channel_listing: "ProductVariantChannelListing",
        price_override: Optional["Decimal"] = None,
    ) -> "Money":
        """Return the base variant price before applying the promotion discounts."""
        return (
            channel_listing.price
            if price_override is None
            else Money(price_override, channel_listing.currency)
        )

    def get_price(
        self,
        channel_listing: "ProductVariantChannelListing",
        price_override: Optional["Decimal"] = None,
        promotion_rules: Optional[Iterable["PromotionRule"]] = None,
    ) -> "Money":
        """Return the variant discounted price with applied promotions.

        If a custom price is provided, return the price with applied discounts from
        valid promotion rules for this variant.
        """
        from ..discount.utils import calculate_discounted_price_for_rules

        if price_override is None:
            return channel_listing.discounted_price or channel_listing.price
        price: "Money" = self.get_base_price(channel_listing, price_override)
        rules = promotion_rules or []
        return calculate_discounted_price_for_rules(
            price=price, rules=rules, currency=channel_listing.currency
        )

    def get_weight(self):
        return self.weight or self.product.weight or self.product.product_type.weight

    def is_shipping_required(self) -> bool:
        return self.product.product_type.is_shipping_required

    def is_gift_card(self) -> bool:
        return self.product.product_type.kind == ProductTypeKind.GIFT_CARD

    def is_digital(self) -> bool:
        is_digital = self.product.product_type.is_digital
        return not self.is_shipping_required() and is_digital

    def display_product(self, translated: bool = False) -> str:
        if translated:
            product = get_translation(self.product).name
            variant_display = get_translation(self).name
        else:
            variant_display = str(self)
            product = self.product
        product_display = (
            f"{product} ({variant_display})" if variant_display else str(product)
        )
        return product_display

    def get_ordering_queryset(self):
        return self.product.variants.all()

    def is_preorder_active(self):
        return self.is_preorder and (
            self.preorder_end_date is None or timezone.now() <= self.preorder_end_date
        )


class ProductVariantTranslation(Translation):
    product_variant = models.ForeignKey(
        ProductVariant, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = (("language_code", "product_variant"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, variant_pk={self.product_variant_id!r})"

    def __str__(self):
        return self.name or str(self.product_variant)

    def get_translated_object_id(self):
        return "ProductVariant", self.product_variant_id

    def get_translated_keys(self):
        return {"name": self.name}


class ProductVariantChannelListing(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="variant_listings",
        on_delete=models.CASCADE,
    )
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    price = MoneyField(amount_field="price_amount", currency_field="currency")

    cost_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    cost_price = MoneyField(amount_field="cost_price_amount", currency_field="currency")

    discounted_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    discounted_price = MoneyField(
        amount_field="discounted_price_amount", currency_field="currency"
    )
    promotion_rules = models.ManyToManyField(
        PromotionRule,
        help_text=("Promotion rules that were included in the discounted price."),
        through="product.VariantChannelListingPromotionRule",
        blank=True,
    )

    preorder_quantity_threshold = models.IntegerField(blank=True, null=True)

    objects = managers.ProductVariantChannelListingManager()

    class Meta:
        unique_together = [["variant", "channel"]]
        ordering = ("pk",)
        indexes = [
            GinIndex(fields=["price_amount", "channel_id"]),
        ]


class VariantChannelListingPromotionRule(models.Model):
    variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        related_name="variantlistingpromotionrule",
        on_delete=models.CASCADE,
    )
    promotion_rule = models.ForeignKey(
        PromotionRule,
        related_name="variantlistingpromotionrule",
        on_delete=models.CASCADE,
    )
    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    discount = MoneyField(amount_field="discount_amount", currency_field="currency")
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    class Meta:
        unique_together = [["variant_channel_listing", "promotion_rule"]]


class DigitalContent(ModelWithMetadata):
    FILE = "file"
    TYPE_CHOICES = ((FILE, "digital_product"),)
    use_default_settings = models.BooleanField(default=True)
    automatic_fulfillment = models.BooleanField(default=False)
    content_type = models.CharField(max_length=128, default=FILE, choices=TYPE_CHOICES)
    product_variant = models.OneToOneField(
        ProductVariant, related_name="digital_content", on_delete=models.CASCADE
    )
    content_file = models.FileField(upload_to="digital_contents", blank=True)
    max_downloads = models.IntegerField(blank=True, null=True)
    url_valid_days = models.IntegerField(blank=True, null=True)

    def create_new_url(self) -> "DigitalContentUrl":
        return self.urls.create()


class DigitalContentUrl(models.Model):
    token = models.UUIDField(editable=False, unique=True)
    content = models.ForeignKey(
        DigitalContent, related_name="urls", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    download_num = models.IntegerField(default=0)
    line = models.OneToOneField(
        "order.OrderLine",
        related_name="digital_content_url",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.token:
            self.token = str(uuid4()).replace("-", "")
        super().save(force_insert, force_update, using, update_fields)

    def get_absolute_url(self) -> Optional[str]:
        url = reverse("digital-product", kwargs={"token": str(self.token)})
        return build_absolute_uri(url)


class ProductMedia(SortableModel, ModelWithMetadata):
    product = models.ForeignKey(
        Product,
        related_name="media",
        on_delete=models.CASCADE,
        # DEPRECATED
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="products", blank=True, null=True)
    alt = models.CharField(max_length=250, blank=True)
    type = models.CharField(
        max_length=32,
        choices=ProductMediaTypes.CHOICES,
        default=ProductMediaTypes.IMAGE,
    )
    external_url = models.CharField(max_length=256, blank=True, null=True)
    oembed_data = JSONField(blank=True, default=dict)
    # DEPRECATED
    to_remove = models.BooleanField(default=False)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("sort_order", "pk")
        app_label = "product"

    def get_ordering_queryset(self):
        if not self.product:
            return ProductMedia.objects.none()
        return self.product.media.all()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super(SortableModel, self).delete(*args, **kwargs)


class VariantMedia(models.Model):
    variant = models.ForeignKey(
        "ProductVariant", related_name="variant_media", on_delete=models.CASCADE
    )
    media = models.ForeignKey(
        ProductMedia, related_name="variant_media", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("variant", "media")


class CollectionProduct(SortableModel):
    collection = models.ForeignKey(
        "Collection", related_name="collectionproduct", on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, related_name="collectionproduct", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("collection", "product"),)

    def get_ordering_queryset(self):
        return self.product.collectionproduct.all()


class Collection(SeoModel, ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="collections",
        through=CollectionProduct,
        through_fields=("collection", "product"),
    )
    background_image = models.ImageField(
        upload_to="collection-backgrounds", blank=True, null=True
    )
    background_image_alt = models.CharField(max_length=128, blank=True)

    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    objects = managers.CollectionManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="collection_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["name", "slug"],
                opclasses=["gin_trgm_ops"] * 2,
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CollectionChannelListing(PublishableModel):
    collection = models.ForeignKey(
        Collection,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="collection_listings",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = [["collection", "channel"]]
        ordering = ("pk",)


class CollectionTranslation(SeoModelTranslation):
    collection = models.ForeignKey(
        Collection, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=128, blank=True, null=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        unique_together = (("language_code", "collection"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, name={self.name!r}, collection_pk={self.collection_id!r})"

    def __str__(self) -> str:
        return self.name if self.name else str(self.pk)

    def get_translated_object_id(self):
        return "Collection", self.collection_id

    def get_translated_keys(self):
        translated_keys = super().get_translated_keys()
        translated_keys.update(
            {
                "name": self.name,
                "description": self.description,
            }
        )
        return translated_keys


import importlib

from celery.schedules import BaseSchedule
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import models
from django_celery_beat import models as base_models
from django_celery_beat import querysets


class CustomSchedule(models.Model):  # type: ignore[django-manager-missing] # problem with django-stubs # noqa: E501
    """Defines the db model storing the details of a custom Celery beat schedulers.

    This model keeps track of the Python import path of the custom Celery beat scheduler
    (class MyCustomScheduler(celery.schedules.BaseScheduler)).
    Then uses the import path to invoke the custom scheduler when the time is due
    to invoke it.

    Import path should be pointing to the initialized object (variable), like so:
    >>> # ./my_pkg/scheduler.py
    >>> class MyScheduler(BaseSchedule):
    ...     # Do something
    ...     pass
    ...
    >>> my_scheduler = MyScheduler()
    >>> import_path = "my_pkg.scheduler.my_scheduler"
    """

    no_changes = False

    CACHED_SCHEDULES: dict[str, BaseSchedule] = {}
    schedule_import_path = models.CharField(
        max_length=255,
        help_text="The python import path where the Celery scheduler is defined at",
        unique=True,
    )

    @property
    def schedule(self):
        """Return the custom Celery scheduler from cache or from the import path."""
        obj = self.CACHED_SCHEDULES.get(self.schedule_import_path)
        if obj is None:
            module_path, class_name = self.schedule_import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            obj = getattr(module, class_name)
            if not isinstance(obj, BaseSchedule):
                raise SuspiciousOperation(
                    f"Expected type of {self.schedule_import_path!r} to be inheriting "
                    f"from BaseScheduler but found: "
                    f"{type(obj)!r} ({obj.__class__.__bases__!r})",
                )
            self.CACHED_SCHEDULES[module_path] = obj
        return obj

    @classmethod
    def from_schedule(cls, schedule: customschedule.CustomSchedule):
        spec = {
            "schedule_import_path": schedule.import_path,
        }
        try:
            return cls.objects.get(**spec)
        except cls.DoesNotExist:
            return cls(**spec)

    def __str__(self):
        return f"{self.schedule_import_path=}"


PeriodicTaskManager = models.Manager.from_queryset(querysets.PeriodicTaskQuerySet)


class CustomPeriodicTask(base_models.PeriodicTask):
    no_changes = False

    custom = models.ForeignKey(
        CustomSchedule,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Custom Schedule",
        help_text=(
            "Custom Schedule to run the task on. "
            "Set only one schedule type, leave the others null."
        ),
    )

    objects = PeriodicTaskManager()

    def validate_unique(self, *args, **kwargs):
        models.Model.validate_unique(self, *args, **kwargs)

        # Schedule types list is hard-coded in the super-method
        schedule_types = ["interval", "crontab", "solar", "clocked", "custom"]
        selected_schedule_types = [s for s in schedule_types if getattr(self, s)]

        if len(selected_schedule_types) == 0:
            raise ValidationError(
                "One of clocked, interval, crontab, solar, or custom must be set."
            )

        err_msg = "Only one of clocked, interval, crontab, solar, or custom must be set"
        if len(selected_schedule_types) > 1:
            error_info = {}
            for selected_schedule_type in selected_schedule_types:
                error_info[selected_schedule_type] = [err_msg]
            raise ValidationError(error_info)

        # clocked must be one off task
        if self.clocked and not self.one_off:
            err_msg = "clocked must be one off, one_off must set True"
            raise ValidationError(err_msg)

    @property
    def schedule(self):
        if self.custom:
            return self.custom.schedule
        return super().schedule


# The hooks are needed by django-celery-beat in order to detect other Python modules
# dynamically changing the model data
# CustomPeriodicTask
signals.pre_delete.connect(base_models.PeriodicTasks.changed, sender=CustomPeriodicTask)
signals.pre_save.connect(base_models.PeriodicTasks.changed, sender=CustomPeriodicTask)

# CustomSchedule
signals.pre_delete.connect(base_models.PeriodicTasks.changed, sender=CustomSchedule)
signals.pre_save.connect(base_models.PeriodicTasks.changed, sender=CustomSchedule)
import re
from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Union

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django_countries.fields import CountryField
from measurement.measures import Weight
from prices import Money


class PostalCodeRuleInclusionType:
    INCLUDE = "include"
    EXCLUDE = "exclude"

    CHOICES = [
        (INCLUDE, "Shipping method should include postal code rule"),
        (EXCLUDE, "Shipping method should exclude postal code rule"),
    ]


def group_values(pattern, *values):
    result: list[Optional[tuple[Any, ...]]] = []
    for value in values:
        try:
            val = re.match(pattern, value)
        except TypeError:
            result.append(None)
        else:
            result.append(val.groups() if val else None)
    return result


def cast_tuple_index_to_type(index, target_type, *tuples):
    """Cast tuple index to type.

    Return list of tuples same as received but with index item casted to
    tagret_type.
    """
    result = []
    for _tuple in tuples:
        to_result = []
        try:
            for i, entry in enumerate(_tuple):
                to_result.append(entry if i != index else target_type(entry))
        except TypeError:
            pass
        result.append(tuple(to_result))
    return result


def compare_values(code, start, end):
    if not code or not start:
        return False
    if not end:
        return start <= code
    return start <= code <= end


def check_uk_postal_code(code, start, end):
    """Check postal code for uk, split the code by regex.

    Example postal codes: BH20 2BC  (UK), IM16 7HF  (Isle of Man).
    """
    pattern = r"^([A-Z]{1,2})([0-9]+)([A-Z]?) ?([0-9][A-Z]{2})$"
    code, start, end = group_values(pattern, code, start, end)
    # replace second item of each tuple with it's value casted to int
    code, start, end = cast_tuple_index_to_type(1, int, code, start, end)
    return compare_values(code, start, end)


def check_irish_postal_code(code, start, end):
    """Check postal code for Ireland, split the code by regex.

    Example postal codes: A65 2F0A, A61 2F0G.
    """
    pattern = r"([\dA-Z]{3}) ?([\dA-Z]{4})"
    code, start, end = group_values(pattern, code, start, end)
    return compare_values(code, start, end)


def check_any_postal_code(code, start, end):
    """Fallback for any country not present in country_func_map.

    Perform simple lexicographical comparison without splitting to sections.
    """
    return compare_values(code, start, end)


def check_postal_code_in_range(country, code, start, end):
    country_func_map = {
        "GB": check_uk_postal_code,  # United Kingdom
        "IM": check_uk_postal_code,  # Isle of Man
        "GG": check_uk_postal_code,  # Guernsey
        "JE": check_uk_postal_code,  # Jersey
        "IE": check_irish_postal_code,  # Ireland
    }
    return country_func_map.get(country, check_any_postal_code)(code, start, end)


def check_shipping_method_for_postal_code(customer_shipping_address, method):
    country = customer_shipping_address.country.code
    postal_code = customer_shipping_address.postal_code
    postal_code_rules = method.postal_code_rules.all()
    return {
        rule: check_postal_code_in_range(country, postal_code, rule.start, rule.end)
        for rule in postal_code_rules
    }


def is_shipping_method_applicable_for_postal_code(
    customer_shipping_address, method
) -> bool:
    """Return if shipping method is applicable with the postal code rules."""
    results = check_shipping_method_for_postal_code(customer_shipping_address, method)
    if not results:
        return True
    if all(
        map(
            lambda rule: rule.inclusion_type == PostalCodeRuleInclusionType.INCLUDE,
            results.keys(),
        )
    ):
        return any(results.values())
    if all(
        map(
            lambda rule: rule.inclusion_type == PostalCodeRuleInclusionType.EXCLUDE,
            results.keys(),
        )
    ):
        return not any(results.values())
    # Shipping methods with complex rules are not supported for now
    return False


def filter_shipping_methods_by_postal_code_rules(shipping_methods, shipping_address):
    """Filter shipping methods for given address by postal code rules."""

    excluded_methods_by_postal_code = []
    for method in shipping_methods:
        if not is_shipping_method_applicable_for_postal_code(shipping_address, method):
            excluded_methods_by_postal_code.append(method.pk)
    if excluded_methods_by_postal_code:
        return shipping_methods.exclude(pk__in=excluded_methods_by_postal_code)
    return shipping_methods


def _applicable_weight_based_methods(weight, qs):
    """Return weight based shipping methods that are applicable for the total weight."""
    qs = qs.weight_based()
    min_weight_matched = Q(minimum_order_weight__lte=weight) | Q(
        minimum_order_weight__isnull=True
    )
    max_weight_matched = Q(maximum_order_weight__gte=weight) | Q(
        maximum_order_weight__isnull=True
    )
    return qs.filter(min_weight_matched & max_weight_matched)


def _applicable_price_based_methods(
    price: Money,
    qs,
    channel_id,
    database_connection_name: str = settings.DATABASE_CONNECTION_DEFAULT_NAME,
):
    """Return price based shipping methods that are applicable for the given total."""
    qs_shipping_method = qs.price_based()

    price_based = Q(shipping_method_id__in=qs_shipping_method)
    channel_filter = Q(channel_id=channel_id)
    min_price_is_null = Q(minimum_order_price_amount__isnull=True)
    min_price_matched = Q(minimum_order_price_amount__lte=price.amount)
    no_price_limit = Q(maximum_order_price_amount__isnull=True)
    max_price_matched = Q(maximum_order_price_amount__gte=price.amount)

    applicable_price_based_methods = (
        ShippingMethodChannelListing.objects.using(database_connection_name)
        .filter(
            channel_filter
            & price_based
            & (min_price_is_null | min_price_matched)
            & (no_price_limit | max_price_matched)
        )
        .values_list("shipping_method__id", flat=True)
    )
    return qs_shipping_method.filter(id__in=applicable_price_based_methods)


def _get_weight_type_display(min_weight, max_weight):
    default_unit = get_default_weight_unit()

    if min_weight.unit != default_unit:
        min_weight = convert_weight(min_weight, default_unit)
    if max_weight and max_weight.unit != default_unit:
        max_weight = convert_weight(max_weight, default_unit)

    if max_weight is None:
        return f"{min_weight} and up"
    return f"{min_weight} to {max_weight}"


class ShippingZone(ModelWithMetadata):
    name = models.CharField(max_length=100)
    countries = CountryField(multiple=True, default=[], blank=True)
    default = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    channels = models.ManyToManyField(Channel, related_name="shipping_zones")

    def __str__(self):
        return self.name

    class Meta(ModelWithMetadata.Meta):
        permissions = (
            (ShippingPermissions.MANAGE_SHIPPING.codename, "Manage shipping."),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                fields=["countries"],
                name="s_z_countries_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]


class ShippingMethodQueryset(models.QuerySet["ShippingMethod"]):
    def price_based(self):
        return self.filter(type=ShippingMethodType.PRICE_BASED)

    def weight_based(self):
        return self.filter(type=ShippingMethodType.WEIGHT_BASED)

    def for_channel(self, channel_slug: str):
        return self.filter(
            shipping_zone__channels__slug=channel_slug,
            channel_listings__channel__slug=channel_slug,
        )

    def applicable_shipping_methods_by_channel(self, shipping_methods, channel_id):
        query = (
            ShippingMethodChannelListing.objects.using(self.db)
            .filter(shipping_method=OuterRef("pk"), channel_id=channel_id)
            .values_list("price_amount")
        )
        return shipping_methods.annotate(price_amount=Subquery(query)).order_by(
            "price_amount"
        )

    def exclude_shipping_methods_for_excluded_products(
        self, qs, product_ids: list[int]
    ):
        """Exclude the ShippingMethods which have excluded given products."""
        return qs.exclude(excluded_products__id__in=product_ids)

    def applicable_shipping_methods(
        self, price: Money, channel_id, weight, country_code, product_ids=None
    ):
        """Return the ShippingMethods that can be used on an order with shipment.

        It is based on the given country code, and by shipping methods that are
        applicable to the given price, weight and products.
        """
        qs = self.filter(
            shipping_zone__countries__contains=country_code,
            shipping_zone__channels__id=channel_id,
            channel_listings__currency=price.currency,
            channel_listings__channel_id=channel_id,
        )
        qs = self.applicable_shipping_methods_by_channel(qs, channel_id)
        qs = qs.prefetch_related("shipping_zone")

        # Products IDs are used to exclude shipping methods that may be not applicable
        # to some of these products, based on exclusion rules defined in shipping method
        # instances.
        if product_ids:
            qs = self.exclude_shipping_methods_for_excluded_products(qs, product_ids)

        price_based_methods = _applicable_price_based_methods(
            price, qs, channel_id, database_connection_name=self.db
        )
        weight_based_methods = _applicable_weight_based_methods(weight, qs)
        shipping_methods = price_based_methods | weight_based_methods

        return shipping_methods


ShippingMethodManager = models.Manager.from_queryset(ShippingMethodQueryset)


class ShippingMethod(ModelWithMetadata):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, choices=ShippingMethodType.CHOICES)
    shipping_zone = models.ForeignKey(
        ShippingZone, related_name="shipping_methods", on_delete=models.CASCADE
    )
    minimum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
        blank=True,
        null=True,
    )
    maximum_order_weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        blank=True,
        null=True,
    )
    excluded_products = models.ManyToManyField("product.Product", blank=True)
    maximum_delivery_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_delivery_days = models.PositiveIntegerField(null=True, blank=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    tax_class = models.ForeignKey(
        TaxClass,
        related_name="shipping_methods",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    objects = ShippingMethodManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)

    def __str__(self):
        return self.name

    def __repr__(self):
        if self.type == ShippingMethodType.PRICE_BASED:
            return f"ShippingMethod(type={self.type})"
        weight_type_display = _get_weight_type_display(
            self.minimum_order_weight, self.maximum_order_weight
        )
        return f"ShippingMethod(type={self.type} weight_range=({weight_type_display})"


class ShippingMethodPostalCodeRule(models.Model):
    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.CASCADE, related_name="postal_code_rules"
    )
    start = models.CharField(max_length=32)
    end = models.CharField(max_length=32, blank=True, null=True)
    inclusion_type = models.CharField(
        max_length=32,
        choices=PostalCodeRuleInclusionType.CHOICES,
        default=PostalCodeRuleInclusionType.EXCLUDE,
    )

    class Meta:
        unique_together = ("shipping_method", "start", "end")


class ShippingMethodChannelListing(models.Model):
    shipping_method = models.ForeignKey(
        ShippingMethod,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="shipping_method_listings",
        on_delete=models.CASCADE,
    )
    minimum_order_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        blank=True,
        null=True,
    )
    minimum_order_price = MoneyField(
        amount_field="minimum_order_price_amount", currency_field="currency"
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    maximum_order_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    maximum_order_price = MoneyField(
        amount_field="maximum_order_price_amount", currency_field="currency"
    )
    price = MoneyField(amount_field="price_amount", currency_field="currency")
    price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    def get_total(self):
        return self.price

    class Meta:
        unique_together = [["shipping_method", "channel"]]
        ordering = ("pk",)


class ShippingMethodTranslation(Translation):
    name = models.CharField(max_length=255, null=True, blank=True)
    shipping_method = models.ForeignKey(
        ShippingMethod, related_name="translations", on_delete=models.CASCADE
    )
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        unique_together = (("language_code", "shipping_method"),)

    def get_translated_object_id(self):
        return "ShippingMethod", self.shipping_method_id

    def get_translated_keys(self):
        return {
            "name": self.name,
            "description": self.description,
        }


from email.headerregistry import Address
from email.utils import parseaddr
from typing import Final, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MaxLengthValidator, MinValueValidator, RegexValidator
from django.db import models

from ..core import TimePeriodType
from ..core.units import WeightUnits
from ..core.utils.translations import Translation
from .error_codes import SiteErrorCode
from .patch_sites import patch_contrib_sites

patch_contrib_sites()

DEFAULT_LIMIT_QUANTITY_PER_CHECKOUT: Final[int] = 50


def email_sender_name_validators():
    return [
        RegexValidator(
            r"[\n\r]",
            inverse_match=True,
            message="New lines are not allowed.",
            code=SiteErrorCode.FORBIDDEN_CHARACTER.value,
        ),
        MaxLengthValidator(settings.DEFAULT_MAX_EMAIL_DISPLAY_NAME_LENGTH),
    ]


class SiteSettings(ModelWithMetadata):
    site = models.OneToOneField(Site, related_name="settings", on_delete=models.CASCADE)
    header_text = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=500, blank=True)
    top_menu = models.ForeignKey(
        "menu.Menu", on_delete=models.SET_NULL, related_name="+", blank=True, null=True
    )
    bottom_menu = models.ForeignKey(
        "menu.Menu", on_delete=models.SET_NULL, related_name="+", blank=True, null=True
    )
    track_inventory_by_default = models.BooleanField(default=True)
    default_weight_unit = models.CharField(
        max_length=30,
        choices=WeightUnits.CHOICES,
        default=WeightUnits.KG,
    )
    automatic_fulfillment_digital_products = models.BooleanField(default=False)
    default_digital_max_downloads = models.IntegerField(blank=True, null=True)
    default_digital_url_valid_days = models.IntegerField(blank=True, null=True)
    company_address = models.ForeignKey(
        "account.Address", blank=True, null=True, on_delete=models.SET_NULL
    )
    # FIXME these values are configurable from email plugin. Not needed to be placed
    # here
    default_mail_sender_name = models.CharField(
        max_length=settings.DEFAULT_MAX_EMAIL_DISPLAY_NAME_LENGTH,
        blank=True,
        default="",
        validators=email_sender_name_validators(),
    )
    default_mail_sender_address = models.EmailField(blank=True, null=True)
    enable_account_confirmation_by_email = models.BooleanField(default=True)
    allow_login_without_confirmation = models.BooleanField(default=False)
    customer_set_password_url = models.CharField(max_length=255, blank=True, null=True)
    fulfillment_auto_approve = models.BooleanField(default=True)
    fulfillment_allow_unpaid = models.BooleanField(default=True)

    # Duration in minutes
    reserve_stock_duration_anonymous_user = models.IntegerField(blank=True, null=True)
    reserve_stock_duration_authenticated_user = models.IntegerField(
        blank=True, null=True
    )

    limit_quantity_per_checkout = models.IntegerField(
        blank=True,
        null=True,
        default=DEFAULT_LIMIT_QUANTITY_PER_CHECKOUT,
        validators=[MinValueValidator(1)],
    )

    # gift card settings
    gift_card_expiry_type = models.CharField(
        max_length=32,
        choices=GiftCardSettingsExpiryType.CHOICES,
        default=GiftCardSettingsExpiryType.NEVER_EXPIRE,
    )
    gift_card_expiry_period_type = models.CharField(
        max_length=32, choices=TimePeriodType.CHOICES, null=True, blank=True
    )
    gift_card_expiry_period = models.PositiveIntegerField(null=True, blank=True)

    # deprecated
    charge_taxes_on_shipping = models.BooleanField(default=True)
    include_taxes_in_prices = models.BooleanField(default=True)
    display_gross_prices = models.BooleanField(default=True)

    class Meta:
        permissions = (
            (SitePermissions.MANAGE_SETTINGS.codename, "Manage settings."),
            (SitePermissions.MANAGE_TRANSLATIONS.codename, "Manage translations."),
        )

    @property
    def default_from_email(self) -> str:
        sender_name: str = self.default_mail_sender_name
        sender_address: Optional[str] = self.default_mail_sender_address

        if not sender_address:
            sender_address = settings.DEFAULT_FROM_EMAIL

            if not sender_address:
                raise ImproperlyConfigured("No sender email address has been set-up")

            sender_name, sender_address = parseaddr(sender_address)

        # Note: we only want to format the address in accordance to RFC 5322
        # but our job is not to sanitize the values. The sanitized value, encoding, etc.
        # will depend on the email backend being used.
        #
        # Refer to email.header.Header and django.core.mail.message.sanitize_address.
        value = str(Address(sender_name, addr_spec=sender_address))
        return value


class SiteSettingsTranslation(Translation):
    site_settings = models.ForeignKey(
        SiteSettings, related_name="translations", on_delete=models.CASCADE
    )
    header_text = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = (("language_code", "site_settings"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, site_settings_pk={self.site_settings_id!r})"

    def get_translated_object_id(self):
        return "Shop", self.site_settings_id

    def get_translated_keys(self):
        return {
            "header_text": self.header_text,
            "description": self.description,
        }


from django.conf import settings
from django.db import models
from django_countries.fields import CountryField


class TaxClass(ModelWithMetadata):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ("name", "pk")

    def __str__(self):
        return self.name


class TaxClassCountryRate(models.Model):
    tax_class = models.ForeignKey(
        TaxClass, related_name="country_rates", on_delete=models.CASCADE, null=True
    )
    country = CountryField()
    rate = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    class Meta:
        ordering = ("country", models.F("tax_class_id").asc(nulls_first=True), "pk")
        # Custom constraints to restrict unique pairs of ("country", "tax_class") and
        # allow exactly one object per country when tax_class is null ("country", None).
        # TaxClassCountryRate with tax_class=null is considered a default tax rate
        # value for a country.
        constraints = [
            models.constraints.UniqueConstraint(
                fields=("country", "tax_class"), name="unique_country_tax_class"
            ),
            models.constraints.UniqueConstraint(
                fields=("country",),
                condition=models.Q(tax_class=None),
                name="unique_country_without_tax_class",
            ),
        ]

    def __str__(self):
        return f"{self.country}: {self.rate}"


class TaxConfiguration(ModelWithMetadata):
    channel = models.OneToOneField(
        Channel, related_name="tax_configuration", on_delete=models.CASCADE
    )
    charge_taxes = models.BooleanField(default=True)
    tax_calculation_strategy = models.CharField(
        max_length=20,
        choices=TaxCalculationStrategy.CHOICES,
        blank=True,
        null=True,
        default=TaxCalculationStrategy.FLAT_RATES,
    )
    display_gross_prices = models.BooleanField(default=True)
    prices_entered_with_tax = models.BooleanField(default=True)
    tax_app_id = models.CharField(blank=True, null=True, max_length=256)

    class Meta:
        ordering = ("pk",)


class TaxConfigurationPerCountry(models.Model):
    tax_configuration = models.ForeignKey(
        TaxConfiguration, related_name="country_exceptions", on_delete=models.CASCADE
    )
    country = CountryField()
    charge_taxes = models.BooleanField(default=True)
    tax_calculation_strategy = models.CharField(
        max_length=20, choices=TaxCalculationStrategy.CHOICES, blank=True, null=True
    )
    display_gross_prices = models.BooleanField(default=True)
    tax_app_id = models.CharField(blank=True, null=True, max_length=256)

    class Meta:
        ordering = ("country", "pk")
        unique_together = (("tax_configuration", "country"),)

    def __str__(self):
        return str(self.country)


class WarehouseQueryset(models.QuerySet["Warehouse"]):
    def for_channel(self, channel_id: int):
        WarehouseChannel = Channel.warehouses.through
        return self.filter(
            Exists(
                WarehouseChannel.objects.filter(
                    channel_id=channel_id, warehouse_id=OuterRef("id")
                )
            )
        ).order_by("pk")

    def for_country_and_channel(self, country: str, channel_id: int):
        ShippingZoneChannel = Channel.shipping_zones.through
        WarehouseShippingZone = ShippingZone.warehouses.through
        WarehouseChannel = Channel.warehouses.through

        shipping_zones = ShippingZone.objects.filter(
            countries__contains=country
        ).values("pk")
        shipping_zone_channels = ShippingZoneChannel.objects.filter(
            Exists(shipping_zones.filter(pk=OuterRef("shippingzone_id"))),
            channel_id=channel_id,
        )

        warehouse_shipping_zones = WarehouseShippingZone.objects.filter(
            Exists(
                shipping_zone_channels.filter(
                    shippingzone_id=OuterRef("shippingzone_id")
                )
            ),
            Exists(
                WarehouseChannel.objects.filter(
                    channel_id=channel_id, warehouse_id=OuterRef("warehouse_id")
                )
            ),
        ).values("warehouse_id")
        return self.filter(
            Exists(warehouse_shipping_zones.filter(warehouse_id=OuterRef("pk")))
        ).order_by("pk")

    def applicable_for_click_and_collect_no_quantity_check(
        self,
        lines_qs: Union[QuerySet[CheckoutLine], QuerySet[OrderLine]],
        channel_id: int,
    ):
        """Return Warehouses which support click and collect.

        Note this method does not check stocks quantity for given `CheckoutLine`s.
        This method should be used only if stocks quantity will be checked in further
        validation steps, for instance in checkout completion.
        """
        if all(
            line.variant.is_preorder_active() if line.variant else False
            for line in lines_qs.select_related("variant").only("variant_id")
        ):
            return self._for_channel_click_and_collect(channel_id)

        stocks_qs = Stock.objects.filter(
            product_variant__id__in=lines_qs.values("variant_id"),
        ).select_related("product_variant")

        return self._for_channel_lines_and_stocks(lines_qs, stocks_qs, channel_id)

    def applicable_for_click_and_collect(
        self,
        lines_qs: Union[QuerySet[CheckoutLine], QuerySet[OrderLine]],
        channel_id: int,
    ) -> QuerySet["Warehouse"]:
        """Return Warehouses which support click and collect.

        Note additional check of stocks quantity for given `CheckoutLine`s.
        For `WarehouseClickAndCollect.LOCAL` all `CheckoutLine`s must be available from
        a single warehouse.
        """
        if all(
            line.variant.is_preorder_active() if line.variant else False
            for line in lines_qs.select_related("variant").only("variant_id")
        ):
            return self._for_channel_click_and_collect(channel_id)

        lines_quantity = (
            lines_qs.filter(variant_id=OuterRef("product_variant_id"))
            .order_by("variant_id")
            .values("variant_id")
            .annotate(prod_sum=Sum("quantity"))
            .values("prod_sum")
        )

        stocks_qs = (
            Stock.objects.using(self.db)
            .annotate_available_quantity()
            .annotate(line_quantity=F("available_quantity") - Subquery(lines_quantity))
            .order_by("line_quantity")
            .filter(
                product_variant__id__in=lines_qs.values("variant_id"),
                line_quantity__gte=0,
            )
            .select_related("product_variant")
        )

        return self._for_channel_lines_and_stocks(lines_qs, stocks_qs, channel_id)

    def _for_channel_lines_and_stocks(
        self,
        lines_qs: Union[QuerySet[CheckoutLine], QuerySet[OrderLine]],
        stocks_qs: QuerySet["Stock"],
        channel_id: int,
    ) -> QuerySet["Warehouse"]:
        warehouse_cc_option_enum = WarehouseClickAndCollectOption

        number_of_variants = (
            lines_qs.order_by("variant_id").distinct("variant_id").count()
        )

        return (
            self.for_channel(channel_id)
            .prefetch_related(Prefetch("stock_set", queryset=stocks_qs))
            .filter(stock__in=stocks_qs)
            .annotate(stock_num=Count("stock__id", distinct=True))
            .filter(
                Q(stock_num=number_of_variants)
                & Q(click_and_collect_option=warehouse_cc_option_enum.LOCAL_STOCK)
                | Q(click_and_collect_option=warehouse_cc_option_enum.ALL_WAREHOUSES)
            )
        )

    def _for_channel_click_and_collect(self, channel_id: int) -> QuerySet["Warehouse"]:
        return self.for_channel(channel_id).filter(
            click_and_collect_option__in=[
                WarehouseClickAndCollectOption.LOCAL_STOCK,
                WarehouseClickAndCollectOption.ALL_WAREHOUSES,
            ]
        )


class ChannelWarehouse(SortableModel):
    channel = models.ForeignKey(
        Channel, related_name="channelwarehouse", on_delete=models.CASCADE
    )
    warehouse = models.ForeignKey(
        "Warehouse", related_name="channelwarehouse", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("channel", "warehouse"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.channel.channelwarehouse.all()


WarehouseManager = models.Manager.from_queryset(WarehouseQueryset)


class Warehouse(ModelWithMetadata, ModelWithExternalReference):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    channels = models.ManyToManyField(
        Channel, related_name="warehouses", through=ChannelWarehouse
    )
    shipping_zones = models.ManyToManyField(
        ShippingZone, blank=True, related_name="warehouses"
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    email = models.EmailField(blank=True, default="")
    click_and_collect_option = models.CharField(
        max_length=30,
        choices=WarehouseClickAndCollectOption.CHOICES,
        default=WarehouseClickAndCollectOption.DISABLED,
    )
    is_private = models.BooleanField(default=True)

    objects = WarehouseManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("-slug",)

    def __str__(self):
        return self.name

    @property
    def countries(self) -> set[str]:
        shipping_zones = self.shipping_zones.all()
        return set(itertools.chain(*[zone.countries for zone in shipping_zones]))

    def delete(self, *args, **kwargs):
        address = self.address
        super().delete(*args, **kwargs)
        address.delete()


class StockQuerySet(models.QuerySet["Stock"]):
    def annotate_available_quantity(self) -> QuerySet[StockWithAvailableQuantity]:
        return cast(
            QuerySet[StockWithAvailableQuantity],
            self.annotate(
                available_quantity=F("quantity")
                - Coalesce(
                    Sum(
                        "allocations__quantity_allocated",
                        filter=Q(allocations__quantity_allocated__gt=0),
                    ),
                    0,
                )
            ),
        )

    def annotate_reserved_quantity(self):
        return self.annotate(
            reserved_quantity=Coalesce(
                Sum(
                    "reservations__quantity_reserved",
                    filter=Q(reservations__reserved_until__gt=timezone.now()),
                ),
                0,
            )
        )

    def for_channel_and_click_and_collect(self, channel_slug: str):
        """Return the stocks for a given channel for a click and collect.

        The click and collect warehouses don't have to be assigned to the shipping zones
        so all stocks for a given channel are returned.
        """
        WarehouseChannel = Channel.warehouses.through

        channels = Channel.objects.filter(slug=channel_slug).values("pk")

        warehouse_channels = WarehouseChannel.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id")))
        ).values("warehouse_id")

        return self.select_related("product_variant").filter(
            Exists(warehouse_channels.filter(warehouse_id=OuterRef("warehouse_id")))
        )

    def for_channel_and_country(
        self,
        channel_slug: str,
        country_code: Optional[str] = None,
        include_cc_warehouses: bool = False,
    ):
        """Get stocks for given channel and country_code.

        The returned stocks, must be in warehouse that is available in provided channel
        and in the shipping zone that is available in the given channel and country.
        When the country_code is not provided or include_cc_warehouses is set to True,
        also the stocks from collection point warehouses allowed in given channel are
        returned.
        """
        ShippingZoneChannel = Channel.shipping_zones.through
        WarehouseShippingZone = ShippingZone.warehouses.through
        WarehouseChannel = Channel.warehouses.through

        channels = Channel.objects.filter(slug=channel_slug).values("pk")

        shipping_zone_channels = ShippingZoneChannel.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id")))
        )
        warehouse_channels = WarehouseChannel.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id")))
        ).values("warehouse_id")

        cc_warehouses = Warehouse.objects.none()
        if country_code:
            shipping_zones = ShippingZone.objects.filter(
                countries__contains=country_code
            ).values("pk")
            shipping_zone_channels = shipping_zone_channels.filter(
                Exists(shipping_zones.filter(pk=OuterRef("shippingzone_id")))
            )
        if not country_code or include_cc_warehouses:
            # when the country code is not provided we should also include
            # the collection point warehouses
            cc_warehouses = Warehouse.objects.filter(
                Exists(warehouse_channels.filter(warehouse_id=OuterRef("id"))),
                click_and_collect_option__in=[
                    WarehouseClickAndCollectOption.LOCAL_STOCK,
                    WarehouseClickAndCollectOption.ALL_WAREHOUSES,
                ],
            )

        shipping_zone_channels.values("shippingzone_id")

        warehouse_shipping_zones = WarehouseShippingZone.objects.filter(
            Exists(
                shipping_zone_channels.filter(
                    shippingzone_id=OuterRef("shippingzone_id")
                )
            ),
            Exists(warehouse_channels.filter(warehouse_id=OuterRef("warehouse_id"))),
        ).values("warehouse_id")
        return self.select_related("product_variant").filter(
            Exists(
                warehouse_shipping_zones.filter(warehouse_id=OuterRef("warehouse_id"))
            )
            | Exists(cc_warehouses.filter(id=OuterRef("warehouse_id")))
        )

    def get_variant_stocks_for_country(
        self, country_code: str, channel_slug: str, product_variant: ProductVariant
    ):
        """Return the stock information about the a stock for a given country.

        Note it will raise a 'Stock.DoesNotExist' exception if no such stock is found.
        """
        return self.for_channel_and_country(channel_slug, country_code).filter(
            product_variant=product_variant
        )

    def get_variants_stocks_for_country(
        self,
        country_code: str,
        channel_slug: str,
        products_variants: Iterable[ProductVariant],
    ):
        """Return the stock information about the a stock for a given country.

        Note it will raise a 'Stock.DoesNotExist' exception if no such stock is found.
        """
        return self.for_channel_and_country(channel_slug, country_code).filter(
            product_variant__in=products_variants
        )

    def get_product_stocks_for_country_and_channel(
        self, country_code: str, channel_slug: str, product: Product
    ):
        return self.for_channel_and_country(channel_slug, country_code).filter(
            product_variant__product_id=product.pk
        )


StockManager = models.Manager.from_queryset(StockQuerySet)


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        ProductVariant, null=False, on_delete=models.CASCADE, related_name="stocks"
    )
    quantity = models.IntegerField(default=0)
    quantity_allocated = models.IntegerField(default=0)

    objects = StockManager()

    class Meta:
        unique_together = [["warehouse", "product_variant"]]
        ordering = ("pk",)

    def increase_stock(self, quantity: int, commit: bool = True):
        """Return given quantity of product to a stock."""
        self.quantity = F("quantity") + quantity
        if commit:
            self.save(update_fields=["quantity"])

    def decrease_stock(self, quantity: int, commit: bool = True):
        self.quantity = F("quantity") - quantity
        if commit:
            self.save(update_fields=["quantity"])


class AllocationQueryset(models.QuerySet["Allocation"]):
    def annotate_stock_available_quantity(self):
        return self.annotate(
            stock_available_quantity=F("stock__quantity")
            - Coalesce(Sum("stock__allocations__quantity_allocated"), 0)
        )

    def available_quantity_for_stock(self, stock: "Stock"):
        allocated_quantity = (
            self.filter(stock=stock).aggregate(Sum("quantity_allocated"))[
                "quantity_allocated__sum"
            ]
            or 0
        )
        return max(stock.quantity - allocated_quantity, 0)


AllocationManager = models.Manager.from_queryset(AllocationQueryset)


class Allocation(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    stock = models.ForeignKey(
        Stock,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    quantity_allocated = models.PositiveIntegerField(default=0)

    objects = AllocationManager()

    class Meta:
        unique_together = [["order_line", "stock"]]
        ordering = ("pk",)


class PreorderAllocation(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="preorder_allocations",
    )
    quantity = models.PositiveIntegerField(default=0)
    product_variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="preorder_allocations",
    )

    class Meta:
        unique_together = [["order_line", "product_variant_channel_listing"]]
        ordering = ("pk",)


T = TypeVar("T", bound=models.Model)


class ReservationQuerySet(models.QuerySet[T]):
    def not_expired(self):
        return self.filter(reserved_until__gt=timezone.now())

    def exclude_checkout_lines(self, checkout_lines: Optional[Iterable[CheckoutLine]]):
        if checkout_lines:
            return self.exclude(checkout_line__in=checkout_lines)

        return self


ReservationManager = models.Manager.from_queryset(ReservationQuerySet)


class PreorderReservation(models.Model):
    checkout_line = models.ForeignKey(
        CheckoutLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="preorder_reservations",
    )
    product_variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="preorder_reservations",
    )
    quantity_reserved = models.PositiveIntegerField(default=0)
    reserved_until = models.DateTimeField()

    objects = ReservationManager()

    class Meta:
        unique_together = [["checkout_line", "product_variant_channel_listing"]]
        indexes = [
            models.Index(fields=["checkout_line", "reserved_until"]),
        ]
        ordering = ("pk",)


class Reservation(models.Model):
    checkout_line = models.ForeignKey(
        CheckoutLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    stock = models.ForeignKey(
        Stock,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    quantity_reserved = models.PositiveIntegerField(default=0)
    reserved_until = models.DateTimeField()

    objects = ReservationManager()

    class Meta:
        unique_together = [["checkout_line", "stock"]]
        indexes = [
            models.Index(fields=["checkout_line", "reserved_until"]),
        ]
        ordering = ("pk",)


from django.db import models
from django.utils import timezone

from ..core.utils.json_serializer import CustomJsonEncoder


class ExportFile(Job):
    user = models.ForeignKey(
        User, related_name="export_files", on_delete=models.CASCADE, null=True
    )
    app = models.ForeignKey(
        App, related_name="export_files", on_delete=models.CASCADE, null=True
    )
    content_file = models.FileField(upload_to="export_files", null=True)


class ExportEvent(models.Model):
    """Model used to store events that happened during the export file lifecycle."""

    date = models.DateTimeField(default=timezone.now, editable=False)
    type = models.CharField(max_length=255, choices=ExportEvents.CHOICES)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)
    export_file = models.ForeignKey(
        ExportFile, related_name="events", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, related_name="export_csv_events", on_delete=models.SET_NULL, null=True
    )
    app = models.ForeignKey(
        App, related_name="export_csv_events", on_delete=models.SET_NULL, null=True
    )


import os

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from ..core.utils.json_serializer import CustomJsonEncoder


class GiftCardTag(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            GinIndex(
                name="gift_card_tag_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]


class GiftCardQueryset(models.QuerySet):
    def active(self, date):
        return self.filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gte=date),
            is_active=True,
        )


GiftCardManager = models.Manager.from_queryset(GiftCardQueryset)


class GiftCard(ModelWithMetadata):
    code = models.CharField(
        max_length=16, unique=True, validators=[MinLengthValidator(8)], db_index=True
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="gift_cards",
    )
    created_by_email = models.EmailField(null=True, blank=True)
    used_by_email = models.EmailField(null=True, blank=True)
    app = models.ForeignKey(
        App,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    expiry_date = models.DateField(null=True, blank=True)

    tags = models.ManyToManyField(GiftCardTag, "gift_cards")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_used_on = models.DateTimeField(null=True, blank=True)
    product = models.ForeignKey(
        "product.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gift_cards",
    )
    fulfillment_line = models.ForeignKey(
        "order.FulfillmentLine",
        related_name="gift_cards",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        default=os.environ.get("DEFAULT_CURRENCY", "USD"),
    )

    initial_balance_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    initial_balance = MoneyField(
        amount_field="initial_balance_amount", currency_field="currency"
    )

    current_balance_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    current_balance = MoneyField(
        amount_field="current_balance_amount", currency_field="currency"
    )
    search_vector = SearchVectorField(blank=True, null=True)
    search_index_dirty = models.BooleanField(default=True)

    objects = GiftCardManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("code",)
        permissions = (
            (GiftcardPermissions.MANAGE_GIFT_CARD.codename, "Manage gift cards."),
        )
        indexes = [GinIndex(name="giftcard_tsearch", fields=["search_vector"])]
        indexes.extend(ModelWithMetadata.Meta.indexes)

    @property
    def display_code(self):
        return self.code[-4:]


class GiftCardEvent(models.Model):
    date = models.DateTimeField(default=timezone.now, editable=False)
    type = models.CharField(max_length=255, choices=GiftCardEvents.CHOICES)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="gift_card_events",
        on_delete=models.SET_NULL,
        null=True,
    )
    app = models.ForeignKey(
        App, related_name="gift_card_events", on_delete=models.SET_NULL, null=True
    )
    order = models.ForeignKey("order.Order", null=True, on_delete=models.SET_NULL)
    gift_card = models.ForeignKey(
        GiftCard, related_name="events", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("date",)


from django.conf import settings
from django.db import models
from django.utils.timezone import now

from ..core import JobStatus
from ..core.utils import build_absolute_uri
from ..core.utils.json_serializer import CustomJsonEncoder


class InvoiceQueryset(models.QuerySet["Invoice"]):
    def ready(self):
        return self.filter(job__status=JobStatus.SUCCESS)


InvoiceManager = models.Manager.from_queryset(InvoiceQueryset)


class Invoice(ModelWithMetadata, Job):
    order = models.ForeignKey(
        Order,
        related_name="invoices",
        null=True,
        on_delete=models.SET_NULL,
    )
    number = models.CharField(max_length=255, null=True)
    created = models.DateTimeField(null=True)
    external_url = models.URLField(null=True, max_length=2048)
    invoice_file = models.FileField(upload_to="invoices")

    objects = InvoiceManager()

    @property
    def url(self):
        if self.invoice_file:
            return build_absolute_uri(self.invoice_file.url)
        return self.external_url

    @url.setter
    def url(self, value):
        self.external_url = value

    def update_invoice(self, number=None, url=None):
        if number is not None:
            self.number = number
        if url is not None:
            self.external_url = url

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)


class InvoiceEvent(models.Model):
    """Model used to store events that happened during the invoice lifecycle."""

    date = models.DateTimeField(default=now, editable=False)
    type = models.CharField(max_length=255, choices=InvoiceEvents.CHOICES)
    invoice = models.ForeignKey(
        Invoice, related_name="events", blank=True, null=True, on_delete=models.SET_NULL
    )
    order = models.ForeignKey(
        Order,
        related_name="invoice_events",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    app = models.ForeignKey(App, related_name="+", on_delete=models.SET_NULL, null=True)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)

    class Meta:
        ordering = ("date", "pk")

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.type!r}, user={self.user!r})"


from collections.abc import Iterable
from typing import Union, cast
from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils.text import Truncator
from oauthlib.common import generate_token

from ..webhook.event_types import WebhookEventAsyncType, WebhookEventSyncType
from .types import AppExtensionMount, AppExtensionTarget, AppType


class AppQueryset(models.QuerySet["App"]):
    def for_event_type(self, event_type: str):
        permissions = {}
        required_permission = WebhookEventAsyncType.PERMISSIONS.get(
            event_type, WebhookEventSyncType.PERMISSIONS.get(event_type)
        )
        if required_permission:
            app_label, codename = required_permission.value.split(".")
            permissions["permissions__content_type__app_label"] = app_label
            permissions["permissions__codename"] = codename
        return self.filter(
            is_active=True,
            webhooks__is_active=True,
            webhooks__events__event_type=event_type,
            **permissions,
        )


AppManager = models.Manager.from_queryset(AppQueryset)


class App(ModelWithMetadata):
    uuid = models.UUIDField(unique=True, default=uuid4)
    name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    removed_at = models.DateTimeField(blank=True, null=True)
    type = models.CharField(
        choices=AppType.CHOICES, default=AppType.LOCAL, max_length=60
    )
    identifier = models.CharField(max_length=256, blank=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text="Specific permissions for this app.",
        related_name="app_set",
        related_query_name="app",
    )
    about_app = models.TextField(blank=True, null=True)
    data_privacy = models.TextField(blank=True, null=True)
    data_privacy_url = models.URLField(blank=True, null=True)
    homepage_url = models.URLField(blank=True, null=True)
    support_url = models.URLField(blank=True, null=True)
    configuration_url = models.URLField(blank=True, null=True)
    app_url = models.URLField(blank=True, null=True)
    manifest_url = models.URLField(blank=True, null=True)
    version = models.CharField(max_length=60, blank=True, null=True)
    audience = models.CharField(blank=True, null=True, max_length=256)
    is_installed = models.BooleanField(default=True)
    author = models.CharField(blank=True, null=True, max_length=60)
    brand_logo_default = models.ImageField(
        upload_to="app-brand-data", blank=True, null=True
    )
    objects = AppManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("name", "pk")
        permissions = (
            (
                AppPermission.MANAGE_APPS.codename,
                "Manage apps",
            ),
            (
                AppPermission.MANAGE_OBSERVABILITY.codename,
                "Manage observability",
            ),
        )

    def __str__(self):
        return self.name

    def get_permissions(self) -> set[str]:
        """Return the permissions of the app."""
        if not self.is_active:
            return set()
        perm_cache_name = "_app_perm_cache"
        if not hasattr(self, perm_cache_name):
            perms = self.permissions.all()
            perms = perms.values_list("content_type__app_label", "codename").order_by()
            setattr(self, perm_cache_name, {f"{ct}.{name}" for ct, name in perms})
        return getattr(self, perm_cache_name)

    def has_perms(self, perm_list: Iterable[Union[BasePermissionEnum, str]]) -> bool:
        """Return True if the app has each of the specified permissions."""
        if not self.is_active:
            return False

        wanted_perms = {
            perm.value if isinstance(perm, BasePermissionEnum) else perm
            for perm in perm_list
        }
        actual_perms = self.get_permissions()

        return (wanted_perms & actual_perms) == wanted_perms

    def has_perm(self, perm: Union[BasePermissionEnum, str]) -> bool:
        """Return True if the app has the specified permission."""
        if not self.is_active:
            return False

        perm_value = perm.value if isinstance(perm, BasePermissionEnum) else perm
        return perm_value in self.get_permissions()


class AppTokenManager(models.Manager["AppToken"]):
    def create(self, app, name="", auth_token=None, **extra_fields):
        """Create an app token with the given name."""
        if not auth_token:
            auth_token = generate_token()
        app_token = self.model(app=app, name=name, **extra_fields)
        app_token.set_auth_token(auth_token)
        app_token.save()
        return app_token, auth_token

    def create_with_token(self, *args, **kwargs) -> tuple["AppToken", str]:
        # As `create` is waiting to be fixed, I'm using this proper method from future
        # to get both AppToken and auth_token.
        return self.create(*args, **kwargs)


class AppToken(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="tokens")
    name = models.CharField(blank=True, default="", max_length=128)
    auth_token = models.CharField(unique=True, max_length=128)
    token_last_4 = models.CharField(max_length=4)

    objects = AppTokenManager()

    def set_auth_token(self, raw_token=None):
        self.auth_token = make_password(raw_token)
        self.token_last_4 = raw_token[-4:]


class AppExtension(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="extensions")
    label = models.CharField(max_length=256)
    url = models.URLField()
    mount = models.CharField(choices=AppExtensionMount.CHOICES, max_length=256)
    target = models.CharField(
        choices=AppExtensionTarget.CHOICES,
        max_length=128,
        default=AppExtensionTarget.POPUP,
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text="Specific permissions for this app extension.",
    )


class AppInstallation(Job):
    uuid = models.UUIDField(unique=True, default=uuid4)
    app_name = models.CharField(max_length=60)
    manifest_url = models.URLField()
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text="Specific permissions which will be assigned to app.",
        related_name="app_installation_set",
        related_query_name="app_installation",
    )
    brand_logo_default = models.ImageField(
        upload_to="app-installation-brand-data", blank=True, null=True
    )

    def set_message(self, message: str, truncate=True):
        if truncate:
            message_field = cast(models.Field, self._meta.get_field("message"))
            max_length = message_field.max_length
            if max_length is None:
                raise ValueError("Cannot truncate message without max_length")
            message = Truncator(message).chars(max_length)
        self.message = message


from django.db import models

from ..core.utils.json_serializer import CustomJsonEncoder


class PluginConfiguration(models.Model):
    identifier = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    channel = models.ForeignKey(
        Channel, blank=True, null=True, on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=False)
    configuration = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )

    class Meta:
        unique_together = ("identifier", "channel")
        permissions = ((PluginsPermissions.MANAGE_PLUGINS.codename, "Manage plugins"),)

    def __str__(self):
        return f"{self.identifier}, active: {self.active}"


class EmailTemplate(models.Model):
    plugin_configuration = models.ForeignKey(
        PluginConfiguration, related_name="email_templates", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    value = models.TextField()

    def __str__(self):
        return self.name


from django.core.validators import MaxLengthValidator
from django.db import models

from ..core.utils.translations import Translation


class SeoModel(models.Model):
    seo_title = models.CharField(
        max_length=70, blank=True, null=True, validators=[MaxLengthValidator(70)]
    )
    seo_description = models.CharField(
        max_length=300, blank=True, null=True, validators=[MaxLengthValidator(300)]
    )

    class Meta:
        abstract = True


class SeoModelTranslation(Translation):
    seo_title = models.CharField(
        max_length=70, blank=True, null=True, validators=[MaxLengthValidator(70)]
    )
    seo_description = models.CharField(
        max_length=300, blank=True, null=True, validators=[MaxLengthValidator(300)]
    )

    class Meta:
        abstract = True

    def get_translated_keys(self):
        return {
            "seo_title": self.seo_title,
            "seo_description": self.seo_description,
        }


from django.db import models


class Book(models.Model):
    name = models.CharField(max_length=30)


from django.core.exceptions import ValidationError
from django.db import models


def validate_thumbnail_size(size: int):
    if size not in THUMBNAIL_SIZES:
        available_sizes = [str(size) for size in THUMBNAIL_SIZES]
        raise ValidationError(
            f"Only following sizes are available: {', '.join(available_sizes)}."
        )


class Thumbnail(models.Model):
    image = models.ImageField(upload_to="thumbnails")
    size = models.PositiveIntegerField(validators=[validate_thumbnail_size])
    format = models.CharField(
        max_length=32, null=True, blank=True, choices=ThumbnailFormat.CHOICES
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thumbnails",
    )
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thumbnails",
    )
    product_media = models.ForeignKey(
        ProductMedia,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thumbnails",
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="thumbnails"
    )
    app = models.ForeignKey(
        App, null=True, blank=True, on_delete=models.CASCADE, related_name="thumbnails"
    )
    app_installation = models.ForeignKey(
        AppInstallation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thumbnails",
    )


from django.db import models

from ..app.validators import AppURLValidator
from ..core.utils.json_serializer import CustomJsonEncoder
from .validators import custom_headers_validator


class WebhookURLField(models.URLField):
    default_validators = [
        AppURLValidator(schemes=["http", "https", "awssqs", "gcpubsub"])
    ]


class Webhook(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    app = models.ForeignKey(App, related_name="webhooks", on_delete=models.CASCADE)
    target_url = WebhookURLField(max_length=255)
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    subscription_query = models.TextField(null=True, blank=True)
    custom_headers = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
        validators=[custom_headers_validator],
    )

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return self.name


class WebhookEvent(models.Model):
    webhook = models.ForeignKey(
        Webhook, related_name="events", on_delete=models.CASCADE
    )
    event_type = models.CharField("Event type", max_length=128, db_index=True)

    def __repr__(self):
        return self.event_type


from datetime import timedelta

from django.conf import settings
from django.db import models
from django_countries.fields import CountryField


class Channel(ModelWithMetadata):
    name = models.CharField(max_length=250)
    is_active = models.BooleanField(default=False)
    slug = models.SlugField(max_length=255, unique=True)
    currency_code = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    default_country = CountryField()
    allocation_strategy = models.CharField(
        max_length=255,
        choices=AllocationStrategy.CHOICES,
        default=AllocationStrategy.PRIORITIZE_SORTING_ORDER,
    )
    order_mark_as_paid_strategy = models.CharField(
        max_length=255,
        choices=MarkAsPaidStrategy.CHOICES,
        default=MarkAsPaidStrategy.PAYMENT_FLOW,
    )

    default_transaction_flow_strategy = models.CharField(
        max_length=255,
        choices=TransactionFlowStrategy.CHOICES,
        default=TransactionFlowStrategy.CHARGE,
    )

    automatically_confirm_all_new_orders = models.BooleanField(default=True, null=True)
    allow_unpaid_orders = models.BooleanField(default=False)
    automatically_fulfill_non_shippable_gift_card = models.BooleanField(
        default=True,
        null=True,
    )
    expire_orders_after = models.IntegerField(default=None, null=True, blank=True)

    delete_expired_orders_after = models.DurationField(
        default=timedelta(days=60),
    )

    include_draft_order_in_voucher_usage = models.BooleanField(default=False)

    use_legacy_error_flow_for_checkout = models.BooleanField(default=True)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        app_label = "channel"
        permissions = (
            (
                ChannelPermissions.MANAGE_CHANNELS.codename,
                "Manage channels.",
            ),
        )

    def __str__(self):
        return self.slug


"""Checkout-related ORM models."""

from datetime import date
from decimal import Decimal
from operator import attrgetter
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.encoding import smart_str
from django_countries.fields import Country, CountryField
from prices import Money

from ..core.taxes import zero_money


def get_default_country():
    return settings.DEFAULT_COUNTRY


class Checkout(models.Model):
    """A shopping checkout."""

    created_at = models.DateTimeField(auto_now_add=True)
    last_change = models.DateTimeField(auto_now=True, db_index=True)
    completing_started_at = models.DateTimeField(blank=True, null=True)

    # Denormalized modified_at for the latest modified transactionItem assigned to
    # checkout
    last_transaction_modified_at = models.DateTimeField(null=True, blank=True)
    automatically_refundable = models.BooleanField(default=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.CASCADE,
    )
    email = models.EmailField(blank=True, null=True)
    token = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    channel = models.ForeignKey(
        Channel,
        related_name="checkouts",
        on_delete=models.PROTECT,
    )
    billing_address = models.ForeignKey(
        "account.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    shipping_address = models.ForeignKey(
        "account.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    shipping_method = models.ForeignKey(
        ShippingMethod,
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.SET_NULL,
    )
    collection_point = models.ForeignKey(
        "warehouse.Warehouse",
        blank=True,
        null=True,
        related_name="checkouts",
        on_delete=models.SET_NULL,
    )
    note = models.TextField(blank=True, default="")

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    country = CountryField(default=get_default_country)

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
    )
    # base price contains only catalogue discounts (does not contains voucher discount)
    base_total_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    base_total = MoneyField(amount_field="base_total_amount", currency_field="currency")

    subtotal_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal = TaxedMoneyField(
        net_amount_field="subtotal_net_amount",
        gross_amount_field="subtotal_gross_amount",
    )
    # base price contains only catalogue discounts (does not contains voucher discount)
    base_subtotal_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    base_subtotal = MoneyField(
        amount_field="base_subtotal_amount", currency_field="currency"
    )

    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    shipping_price = TaxedMoneyField(
        net_amount_field="shipping_price_net_amount",
        gross_amount_field="shipping_price_gross_amount",
    )
    shipping_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.0")
    )

    authorize_status = models.CharField(
        max_length=32,
        default=CheckoutAuthorizeStatus.NONE,
        choices=CheckoutAuthorizeStatus.CHOICES,
        db_index=True,
    )

    charge_status = models.CharField(
        max_length=32,
        default=CheckoutChargeStatus.NONE,
        choices=CheckoutChargeStatus.CHOICES,
        db_index=True,
    )

    price_expiration = models.DateTimeField(default=timezone.now)

    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    discount = MoneyField(amount_field="discount_amount", currency_field="currency")
    discount_name = models.CharField(max_length=255, blank=True, null=True)

    translated_discount_name = models.CharField(max_length=255, blank=True, null=True)
    gift_cards = models.ManyToManyField(GiftCard, blank=True, related_name="checkouts")
    voucher_code = models.CharField(max_length=255, blank=True, null=True)

    # The field prevents race condition when two different threads are processing
    # the same checkout with limited usage voucher assigned. Both threads increasing the
    # voucher usage would cause `NotApplicable` error for voucher.
    is_voucher_usage_increased = models.BooleanField(default=False)

    redirect_url = models.URLField(blank=True, null=True)
    tracking_code = models.CharField(max_length=255, blank=True, null=True)

    language_code = models.CharField(
        max_length=35, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )

    tax_exemption = models.BooleanField(default=False)
    tax_error = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ("-last_change", "pk")
        permissions = (
            (CheckoutPermissions.MANAGE_CHECKOUTS.codename, "Manage checkouts"),
            (CheckoutPermissions.HANDLE_CHECKOUTS.codename, "Handle checkouts"),
            (CheckoutPermissions.HANDLE_TAXES.codename, "Handle taxes"),
            (CheckoutPermissions.MANAGE_TAXES.codename, "Manage taxes"),
        )

    def __iter__(self):
        return iter(self.lines.all())

    def get_customer_email(self) -> Optional[str]:
        return self.user.email if self.user else self.email

    def is_shipping_required(self) -> bool:
        """Return `True` if any of the lines requires shipping."""
        return any(line.is_shipping_required() for line in self)

    def is_checkout_locked(self) -> bool:
        return bool(
            self.completing_started_at
            and (
                (timezone.now() - self.completing_started_at).seconds
                < settings.CHECKOUT_COMPLETION_LOCK_TIME
            )
        )

    def get_total_gift_cards_balance(
        self, database_connection_name: str = settings.DATABASE_CONNECTION_DEFAULT_NAME
    ) -> Money:
        """Return the total balance of the gift cards assigned to the checkout."""
        balance = (
            self.gift_cards.using(database_connection_name)
            .active(date=date.today())
            .aggregate(models.Sum("current_balance_amount"))[
                "current_balance_amount__sum"
            ]
        )
        if balance is None:
            return zero_money(currency=self.currency)
        return Money(balance, self.currency)

    def get_line(self, variant: "ProductVariant") -> Optional["CheckoutLine"]:
        """Return a line matching the given variant and data if any."""
        matching_lines = (line for line in self if line.variant.pk == variant.pk)
        return next(matching_lines, None)

    def get_last_active_payment(self) -> Optional["Payment"]:
        payments = [payment for payment in self.payments.all() if payment.is_active]
        return max(payments, default=None, key=attrgetter("pk"))

    def set_country(
        self, country_code: str, commit: bool = False, replace: bool = True
    ):
        """Set country for checkout."""
        if not replace and self.country is not None:
            return
        self.country = Country(country_code)
        if commit:
            self.save(update_fields=["country"])

    def get_country(self):
        address = self.shipping_address or self.billing_address
        saved_country = self.country
        if address is None or not address.country:
            return saved_country.code

        country_code = address.country.code
        if not country_code == saved_country.code:
            self.set_country(country_code, commit=True)
        return country_code


class CheckoutLine(ModelWithMetadata):
    """A single checkout line.

    Multiple lines in the same checkout can refer to the same product variant if
    their `data` field is different.
    """

    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    old_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    checkout = models.ForeignKey(
        Checkout, related_name="lines", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "product.ProductVariant", related_name="+", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_gift = models.BooleanField(default=False)
    price_override = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    total_price = TaxedMoneyField(
        net_amount_field="total_price_net_amount",
        gross_amount_field="total_price_gross_amount",
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.0")
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")

    def __str__(self):
        return smart_str(self.variant)

    __hash__ = models.Model.__hash__

    def __eq__(self, other):
        if not isinstance(other, CheckoutLine):
            return NotImplemented

        return self.variant == other.variant and self.quantity == other.quantity

    def __ne__(self, other):
        return not self == other  # pragma: no cover

    def __repr__(self):
        return f"CheckoutLine(variant={self.variant!r}, quantity={self.quantity!r})"

    def __getstate__(self):
        return self.variant, self.quantity

    def __setstate__(self, data):
        self.variant, self.quantity = data

    def is_shipping_required(self) -> bool:
        """Return `True` if the related product variant requires shipping."""
        return self.variant.is_shipping_required()


# Checkout metadata is moved to separate model so it can be used when checkout model is
# locked by select_for_update during complete_checkout.
class CheckoutMetadata(ModelWithMetadata):
    checkout = models.OneToOneField(
        Checkout, related_name="metadata_storage", on_delete=models.CASCADE
    )


import datetime
from typing import Any, TypeVar

import pytz
from django.contrib.postgres.indexes import GinIndex
from django.db import models, transaction

from .utils.json_serializer import CustomJsonEncoder


class SortableModel(models.Model):
    sort_order = models.IntegerField(editable=False, db_index=True, null=True)

    class Meta:
        abstract = True

    def get_ordering_queryset(self):
        raise NotImplementedError("Unknown ordering queryset")

    @staticmethod
    def get_max_sort_order(qs):
        existing_max = qs.aggregate(Max("sort_order"))
        existing_max = existing_max.get("sort_order__max")
        return existing_max

    def save(self, *args, **kwargs):
        if self.pk is None:
            qs = self.get_ordering_queryset()
            existing_max = self.get_max_sort_order(qs)
            self.sort_order = 0 if existing_max is None else existing_max + 1
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.sort_order is not None:
            qs = self.get_ordering_queryset()
            qs.filter(sort_order__gt=self.sort_order).update(
                sort_order=F("sort_order") - 1
            )
        super().delete(*args, **kwargs)


T = TypeVar("T", bound="PublishableModel")


class PublishedQuerySet(models.QuerySet[T]):
    def published(self):
        today = datetime.datetime.now(pytz.UTC)
        return self.filter(
            Q(published_at__lte=today) | Q(published_at__isnull=True),
            is_published=True,
        )


PublishableManager = models.Manager.from_queryset(PublishedQuerySet)


class PublishableModel(models.Model):
    published_at = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)

    objects: Any = PublishableManager()

    class Meta:
        abstract = True

    @property
    def is_visible(self):
        return self.is_published and (
            self.published_at is None
            or self.published_at <= datetime.datetime.now(pytz.UTC)
        )


from django.db.models import F, JSONField, Max, Q


class ModelWithMetadata(models.Model):
    private_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )
    metadata = JSONField(blank=True, null=True, default=dict, encoder=CustomJsonEncoder)

    class Meta:
        indexes = [
            GinIndex(fields=["private_metadata"], name="%(class)s_p_meta_idx"),
            GinIndex(fields=["metadata"], name="%(class)s_meta_idx"),
        ]
        abstract = True

    def get_value_from_private_metadata(self, key: str, default: Any = None) -> Any:
        return self.private_metadata.get(key, default)

    def store_value_in_private_metadata(self, items: dict):
        if not self.private_metadata:
            self.private_metadata = {}
        self.private_metadata.update(items)

    def clear_private_metadata(self):
        self.private_metadata = {}

    def delete_value_from_private_metadata(self, key: str):
        if key in self.private_metadata:
            del self.private_metadata[key]

    def get_value_from_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def store_value_in_metadata(self, items: dict):
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(items)

    def clear_metadata(self):
        self.metadata = {}

    def delete_value_from_metadata(self, key: str):
        if key in self.metadata:
            del self.metadata[key]


class ModelWithExternalReference(models.Model):
    external_reference = models.CharField(
        max_length=250,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        abstract = True


class Job(models.Model):
    status = models.CharField(
        max_length=50, choices=JobStatus.CHOICES, default=JobStatus.PENDING
    )
    message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EventPayload(models.Model):
    payload = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class EventDelivery(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=255,
        choices=EventDeliveryStatus.CHOICES,
        default=EventDeliveryStatus.PENDING,
    )
    event_type = models.CharField(max_length=255)
    payload = models.ForeignKey(
        EventPayload, related_name="deliveries", null=True, on_delete=models.CASCADE
    )
    webhook = models.ForeignKey("webhook.Webhook", on_delete=models.CASCADE)

    class Meta:
        ordering = ("-created_at",)


class EventDeliveryAttempt(models.Model):
    delivery = models.ForeignKey(
        EventDelivery, related_name="attempts", null=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    task_id = models.CharField(max_length=255, null=True)
    duration = models.FloatField(null=True)
    response = models.TextField(null=True)
    response_headers = models.TextField(null=True)
    response_status_code = models.PositiveSmallIntegerField(null=True)
    request_headers = models.TextField(null=True)
    status = models.CharField(
        max_length=255,
        choices=EventDeliveryStatus.CHOICES,
        default=EventDeliveryStatus.PENDING,
    )

    class Meta:
        ordering = ("-created_at",)


import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from typing import TYPE_CHECKING, Callable, Optional
from uuid import uuid4

import pytz
from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.db import connection, models
from django.utils import timezone
from django_countries.fields import CountryField
from django_prices.templatetags.prices import amount
from prices import Money, fixed_discount, percentage_discount

from ..core.utils.editorjs import clean_editor_js
from ..core.utils.json_serializer import CustomJsonEncoder
from ..core.utils.translations import Translation


class SanitizedJSONField(JSONField):
    description = "A JSON field that runs a given sanitization method "
    "before saving into the database."

    def __init__(self, *args, sanitizer: Callable[[dict], dict], **kwargs):
        super().__init__(*args, **kwargs)
        self._sanitizer_method = sanitizer

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["sanitizer"] = self._sanitizer_method
        return name, path, args, kwargs

    def get_db_prep_save(self, value: dict, connection):
        """Sanitize the value for saving using the passed sanitizer."""
        return json.dumps(self._sanitizer_method(value))


class NotApplicable(ValueError):
    """Exception raised when a discount is not applicable to a checkout.

    The error is raised if the order value is below the minimum required
    price or the order quantity is below the minimum quantity of items.
    Minimum price will be available as the `min_spent` attribute.
    Minimum quantity will be available as the `min_checkout_items_quantity` attribute.
    """

    def __init__(self, msg, min_spent=None, min_checkout_items_quantity=None):
        super().__init__(msg)
        self.min_spent = min_spent
        self.min_checkout_items_quantity = min_checkout_items_quantity


class VoucherQueryset(models.QuerySet["Voucher"]):
    def active(self, date):
        subquery = (
            VoucherCode.objects.filter(voucher_id=OuterRef("pk"))
            .annotate(total_used=Sum("used"))
            .values("total_used")[:1]
        )
        return self.filter(
            Q(usage_limit__isnull=True) | Q(usage_limit__gt=Subquery(subquery)),
            Q(end_date__isnull=True) | Q(end_date__gte=date),
            start_date__lte=date,
        )

    def active_in_channel(self, date, channel_slug: str):
        channels = Channel.objects.filter(
            slug=str(channel_slug), is_active=True
        ).values("id")
        channel_listings = VoucherChannelListing.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id"))),
        ).values("id")

        return self.active(date).filter(
            Exists(channel_listings.filter(voucher_id=OuterRef("pk")))
        )

    def expired(self, date):
        subquery = (
            VoucherCode.objects.filter(voucher_id=OuterRef("pk"))
            .annotate(total_used=Sum("used"))
            .values("total_used")[:1]
        )
        return self.filter(
            Q(usage_limit__lte=Subquery(subquery)) | Q(end_date__lt=date),
            start_date__lt=date,
        )


VoucherManager = models.Manager.from_queryset(VoucherQueryset)


class Voucher(ModelWithMetadata):
    type = models.CharField(
        max_length=20, choices=VoucherType.CHOICES, default=VoucherType.ENTIRE_ORDER
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # this field indicates if discount should be applied per order or
    # individually to every item
    apply_once_per_order = models.BooleanField(default=False)
    apply_once_per_customer = models.BooleanField(default=False)
    single_use = models.BooleanField(default=False)

    only_for_staff = models.BooleanField(default=False)

    discount_value_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )

    # not mandatory fields, usage depends on type
    countries = CountryField(multiple=True, blank=True)
    min_checkout_items_quantity = models.PositiveIntegerField(null=True, blank=True)
    products = models.ManyToManyField("product.Product", blank=True)
    variants = models.ManyToManyField("product.ProductVariant", blank=True)
    collections = models.ManyToManyField("product.Collection", blank=True)
    categories = models.ManyToManyField("product.Category", blank=True)

    objects = VoucherManager()

    class Meta:
        ordering = ("name", "pk")

    @property
    def code(self):
        # this function should be removed after field `code` will be deprecated
        code_instance = self.codes.last()
        return code_instance.code if code_instance else None

    @property
    def promo_codes(self):
        return list(self.codes.values_list("code", flat=True))

    def get_discount(self, channel: Channel):
        """Return proper discount amount for given channel.

        It operates over all channel listings as assuming that we have prefetched them.
        """
        voucher_channel_listing = None

        for channel_listing in self.channel_listings.all():
            if channel.id == channel_listing.channel_id:
                voucher_channel_listing = channel_listing
                break

        if not voucher_channel_listing:
            raise NotApplicable("This voucher is not assigned to this channel")
        if self.discount_value_type == DiscountValueType.FIXED:
            discount_amount = Money(
                voucher_channel_listing.discount_value, voucher_channel_listing.currency
            )
            return partial(fixed_discount, discount=discount_amount)
        if self.discount_value_type == DiscountValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=voucher_channel_listing.discount_value,
                rounding=ROUND_HALF_UP,
            )
        raise NotImplementedError("Unknown discount type")

    def get_discount_amount_for(self, price: Money, channel: Channel):
        discount = self.get_discount(channel)
        after_discount = discount(price)
        if after_discount.amount < 0:
            return price
        return price - after_discount

    def validate_min_spent(self, value: Money, channel: Channel):
        voucher_channel_listing = self.channel_listings.filter(channel=channel).first()
        if not voucher_channel_listing:
            raise NotApplicable("This voucher is not assigned to this channel")
        min_spent = voucher_channel_listing.min_spent
        if min_spent and value < min_spent:
            msg = f"This offer is only valid for orders over {amount(min_spent)}."
            raise NotApplicable(msg, min_spent=min_spent)

    def validate_min_checkout_items_quantity(self, quantity):
        min_checkout_items_quantity = self.min_checkout_items_quantity
        if min_checkout_items_quantity and min_checkout_items_quantity > quantity:
            msg = (
                "This offer is only valid for orders with a minimum of "
                f"{min_checkout_items_quantity} quantity."
            )
            raise NotApplicable(
                msg,
                min_checkout_items_quantity=min_checkout_items_quantity,
            )

    def validate_once_per_customer(self, customer_email):
        voucher_codes = self.codes.all()
        voucher_customer = VoucherCustomer.objects.filter(
            Exists(voucher_codes.filter(id=OuterRef("voucher_code_id"))),
            customer_email=customer_email,
        )
        if voucher_customer:
            msg = "This offer is valid only once per customer."
            raise NotApplicable(msg)

    def validate_only_for_staff(self, customer: Optional["User"]):
        if not self.only_for_staff:
            return

        if not customer or not customer.is_staff:
            msg = "This offer is valid only for staff customers."
            raise NotApplicable(msg)


class VoucherCode(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    code = models.CharField(max_length=255, unique=True, db_index=True)
    used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    voucher = models.ForeignKey(
        Voucher, related_name="codes", on_delete=models.CASCADE, db_index=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [BTreeIndex(fields=["voucher"], name="vouchercode_voucher_idx")]
        ordering = ("-created_at", "code")


class VoucherChannelListing(models.Model):
    voucher = models.ForeignKey(
        Voucher,
        null=False,
        blank=False,
        related_name="channel_listings",
        on_delete=models.CASCADE,
    )
    channel = models.ForeignKey(
        Channel,
        null=False,
        blank=False,
        related_name="voucher_listings",
        on_delete=models.CASCADE,
    )
    discount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    discount = MoneyField(amount_field="discount_value", currency_field="currency")
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    min_spent_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
    )
    min_spent = MoneyField(amount_field="min_spent_amount", currency_field="currency")

    class Meta:
        unique_together = (("voucher", "channel"),)
        ordering = ("pk",)


class VoucherCustomer(models.Model):
    voucher_code = models.ForeignKey(
        VoucherCode,
        related_name="customers",
        on_delete=models.CASCADE,
        db_index=False,
    )
    customer_email = models.EmailField()

    class Meta:
        indexes = [
            BTreeIndex(fields=["voucher_code"], name="vouchercustomer_voucher_code_idx")
        ]
        ordering = ("voucher_code", "customer_email", "pk")
        unique_together = (("voucher_code", "customer_email"),)


class VoucherTranslation(Translation):
    voucher = models.ForeignKey(
        Voucher, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ("language_code", "voucher", "pk")
        unique_together = (("language_code", "voucher"),)

    def get_translated_object_id(self):
        return "Voucher", self.voucher_id

    def get_translated_keys(self):
        return {"name": self.name}


class PromotionQueryset(models.QuerySet["Promotion"]):
    def active(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date), start_date__lte=date
        )

    def expired(self, date=None):
        if date is None:
            date = timezone.now()
        return self.filter(end_date__lt=date, start_date__lt=date)


PromotionManager = models.Manager.from_queryset(PromotionQueryset)


class Promotion(ModelWithMetadata):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=255,
        choices=PromotionType.CHOICES,
        default=PromotionType.CATALOGUE,
    )
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    old_sale_id = models.IntegerField(blank=True, null=True, unique=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    last_notification_scheduled_at = models.DateTimeField(null=True, blank=True)
    objects = PromotionManager()

    class Meta:
        ordering = ("name", "pk")
        permissions = (
            (
                DiscountPermissions.MANAGE_DISCOUNTS.codename,
                "Manage promotions and vouchers.",
            ),
        )
        indexes = [
            BTreeIndex(fields=["start_date"], name="start_date_idx"),
            BTreeIndex(fields=["end_date"], name="end_date_idx"),
        ]

    def is_active(self, date=None):
        if date is None:
            date = datetime.now(pytz.utc)
        return (not self.end_date or self.end_date >= date) and self.start_date <= date

    def assign_old_sale_id(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('discount_promotion_old_sale_id_seq')")
            result = cursor.fetchone()
            self.old_sale_id = result[0]
            self.save(update_fields=["old_sale_id"])


class PromotionTranslation(Translation):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    promotion = models.ForeignKey(
        Promotion, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("language_code", "promotion"),)

    def get_translated_object_id(self):
        return "Promotion", self.promotion_id

    def get_translated_keys(self):
        return {"name": self.name, "description": self.description}


class PromotionRule(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="rules"
    )
    channels = models.ManyToManyField(Channel)
    catalogue_predicate = models.JSONField(
        blank=True, default=dict, encoder=CustomJsonEncoder
    )
    order_predicate = models.JSONField(
        blank=True, default=dict, encoder=CustomJsonEncoder
    )
    variants = models.ManyToManyField(  # type: ignore[var-annotated]
        "product.ProductVariant", blank=True, through="PromotionRule_Variants"
    )
    reward_value_type = models.CharField(
        max_length=255, choices=RewardValueType.CHOICES, blank=True, null=True
    )
    reward_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    reward_type = models.CharField(
        max_length=255, choices=RewardType.CHOICES, blank=True, null=True
    )
    gifts = models.ManyToManyField(
        "product.ProductVariant", blank=True, related_name="+"
    )
    old_channel_listing_id = models.IntegerField(blank=True, null=True, unique=True)
    variants_dirty = models.BooleanField(default=False)

    class Meta:
        ordering = ("name", "pk")

    def get_discount(self, currency):
        if self.reward_value_type == RewardValueType.FIXED:
            discount_amount = Money(self.reward_value, currency)
            return partial(fixed_discount, discount=discount_amount)
        if self.reward_value_type == RewardValueType.PERCENTAGE:
            return partial(
                percentage_discount,
                percentage=self.reward_value,
                rounding=ROUND_HALF_UP,
            )
        raise NotImplementedError("Unknown discount type")

    @staticmethod
    def get_old_channel_listing_ids(qunatity):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT nextval('discount_promotionrule_old_channel_listing_id_seq')
                FROM generate_series(1, {qunatity})
                """
            )
            return cursor.fetchall()


class PromotionRule_Variants(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False, unique=True)
    promotionrule = models.ForeignKey(
        PromotionRule,
        on_delete=models.CASCADE,
    )
    productvariant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.CASCADE,
    )


class PromotionRuleTranslation(Translation):
    name = models.CharField(max_length=255, null=True, blank=True)
    description = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    promotion_rule = models.ForeignKey(
        PromotionRule, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("language_code", "promotion_rule"),)

    def get_translated_object_id(self):
        return "PromotionRule", self.promotion_rule_id

    def get_translated_keys(self):
        return {"name": self.name, "description": self.description}


class BaseDiscount(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    type = models.CharField(
        max_length=64,
        choices=DiscountType.CHOICES,
        default=DiscountType.MANUAL,
    )
    value_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )
    value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    amount = MoneyField(amount_field="amount_value", currency_field="currency")
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    translated_name = models.CharField(max_length=255, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    promotion_rule = models.ForeignKey(
        PromotionRule,
        related_name="+",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        db_index=False,
    )
    voucher = models.ForeignKey(
        Voucher, related_name="+", blank=True, null=True, on_delete=models.SET_NULL
    )
    voucher_code = models.CharField(
        max_length=255, null=True, blank=True, db_index=False
    )

    class Meta:
        abstract = True


class OrderDiscount(BaseDiscount):
    order = models.ForeignKey(
        "order.Order",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    old_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"], name="orderdiscount_promotion_rule_idx"
            ),
            # Orders searching index
            GinIndex(fields=["name", "translated_name"]),
            GinIndex(fields=["voucher_code"], name="orderdiscount_voucher_code_idx"),
        ]
        ordering = ("created_at", "id")


class OrderLineDiscount(BaseDiscount):
    line = models.ForeignKey(
        "order.OrderLine",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    # Saleor in version 3.19 and below, doesn't have any unique constraint applied on
    # discounts for checkout/order. To not have an impact on existing DB objects,
    # the new field `unique_type` will be used for new discount records.
    # This will ensure that we always apply a single specific discount type.
    unique_type = models.CharField(
        max_length=64, null=True, blank=True, choices=DiscountType.CHOICES
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"], name="orderlinedisc_promotion_rule_idx"
            ),
            GinIndex(fields=["voucher_code"], name="orderlinedisc_voucher_code_idx"),
        ]
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["line_id", "unique_type"],
                name="unique_orderline_discount_type",
            ),
        ]


class CheckoutDiscount(BaseDiscount):
    checkout = models.ForeignKey(
        "checkout.Checkout",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            BTreeIndex(fields=["promotion_rule"], name="checkoutdiscount_rule_idx"),
            # Orders searching index
            GinIndex(fields=["name", "translated_name"]),
            GinIndex(fields=["voucher_code"], name="checkoutdiscount_voucher_idx"),
        ]
        ordering = ("created_at", "id")
        unique_together = ("checkout_id", "promotion_rule_id")


class CheckoutLineDiscount(BaseDiscount):
    line = models.ForeignKey(
        "checkout.CheckoutLine",
        related_name="discounts",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    # Saleor in version 3.19 and below, doesn't have any unique constraint applied on
    # discounts for checkout/order. To not have an impact on existing DB objects,
    # the new field `unique_type` will be used for new discount records.
    # This will ensure that we always apply a single specific discount type.
    unique_type = models.CharField(
        max_length=64, null=True, blank=True, choices=DiscountType.CHOICES
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["promotion_rule"], name="checklinedisc_promotion_rule_idx"
            ),
            GinIndex(fields=["voucher_code"], name="checklinedisc_voucher_code_idx"),
        ]
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["line_id", "unique_type"],
                name="unique_checkoutline_discount_type",
            ),
        ]


class PromotionEvent(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    date = models.DateTimeField(auto_now_add=True, db_index=True, editable=False)
    type = models.CharField(max_length=255, choices=PromotionEvents.CHOICES)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="promotion_events",
        on_delete=models.SET_NULL,
    )
    app = models.ForeignKey(
        App,
        blank=True,
        null=True,
        related_name="promotion_events",
        on_delete=models.SET_NULL,
    )
    promotion = models.ForeignKey(
        Promotion, related_name="events", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("date",)


from django.db import models
from mptt.managers import TreeManager

from ..core.utils.translations import Translation


class Menu(ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)
        permissions = ((MenuPermissions.MANAGE_MENUS.codename, "Manage navigation."),)

    def __str__(self):
        return self.name


class MenuItem(ModelWithMetadata, MPTTModel, SortableModel):
    menu = models.ForeignKey(Menu, related_name="items", on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )

    # not mandatory fields, usage depends on what type of link is stored
    url = models.URLField(max_length=256, blank=True, null=True)
    category = models.ForeignKey(
        Category, blank=True, null=True, on_delete=models.CASCADE
    )
    collection = models.ForeignKey(
        Collection, blank=True, null=True, on_delete=models.CASCADE
    )
    page = models.ForeignKey(Page, blank=True, null=True, on_delete=models.CASCADE)

    objects = models.Manager()
    tree = TreeManager()  # type: ignore[django-manager-missing]

    class Meta(ModelWithMetadata.Meta):
        ordering = ("sort_order", "pk")
        app_label = "menu"

    def __str__(self):
        return self.name

    def get_ordering_queryset(self):
        return (
            self.menu.items.filter(level=0)
            if not self.parent
            else self.parent.children.all()
        )

    @property
    def linked_object(self):
        return self.category or self.collection or self.page


class MenuItemTranslation(Translation):
    menu_item = models.ForeignKey(
        MenuItem, related_name="translations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ("language_code", "menu_item", "pk")
        unique_together = (("language_code", "menu_item"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.id!r}, name={self.name!r}, menu_item_pk={self.menu_item_id!r})"

    def __str__(self):
        return self.name

    def get_translated_object_id(self):
        return "MenuItem", self.menu_item_id

    def get_translated_keys(self):
        return {
            "name": self.name,
        }


class OrderQueryset(models.QuerySet["Order"]):
    def get_by_checkout_token(self, token):
        """Return non-draft order with matched checkout token."""
        return self.non_draft().filter(checkout_token=token).first()

    def confirmed(self):
        """Return orders that aren't draft or unconfirmed."""
        return self.exclude(status__in=[OrderStatus.DRAFT, OrderStatus.UNCONFIRMED])

    def non_draft(self):
        """Return orders that aren't draft."""
        return self.exclude(status=OrderStatus.DRAFT)

    def drafts(self):
        """Return draft orders."""
        return self.filter(status=OrderStatus.DRAFT)

    def ready_to_fulfill(self):
        """Return orders that can be fulfilled.

        Orders ready to fulfill are fully paid but unfulfilled (or partially
        fulfilled).
        """
        statuses = {OrderStatus.UNFULFILLED, OrderStatus.PARTIALLY_FULFILLED}
        payments = Payment.objects.filter(is_active=True).values("id")
        return self.filter(
            Exists(payments.filter(order_id=OuterRef("id"))),
            status__in=statuses,
            total_gross_amount__lte=F("total_charged_amount"),
        )

    def ready_to_capture(self):
        """Return orders with payments to capture.

        Orders ready to capture are those which are not draft or canceled and
        have a preauthorized payment. The preauthorized payment can not
        already be partially or fully captured.
        """
        payments = Payment.objects.filter(
            is_active=True, charge_status=ChargeStatus.NOT_CHARGED
        ).values("id")
        qs = self.filter(Exists(payments.filter(order_id=OuterRef("id"))))
        return qs.exclude(
            status={OrderStatus.DRAFT, OrderStatus.CANCELED, OrderStatus.EXPIRED}
        )

    def ready_to_confirm(self):
        """Return unconfirmed orders."""
        return self.filter(status=OrderStatus.UNCONFIRMED)


OrderManager = models.Manager.from_queryset(OrderQueryset)


def get_order_number():
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('order_order_number_seq')")
        result = cursor.fetchone()
        return result[0]


class Order(ModelWithMetadata, ModelWithExternalReference):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    number = models.IntegerField(unique=True, default=get_order_number, editable=False)
    use_old_id = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False, db_index=True)
    expired_at = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=32, default=OrderStatus.UNFULFILLED, choices=OrderStatus.CHOICES
    )
    authorize_status = models.CharField(
        max_length=32,
        default=OrderAuthorizeStatus.NONE,
        choices=OrderAuthorizeStatus.CHOICES,
        db_index=True,
    )
    charge_status = models.CharField(
        max_length=32,
        default=OrderChargeStatus.NONE,
        choices=OrderChargeStatus.CHOICES,
        db_index=True,
    )
    user = models.ForeignKey(
        "account.User",
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    language_code = models.CharField(
        max_length=35, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    tracking_client_id = models.CharField(max_length=36, blank=True, editable=False)
    billing_address = models.ForeignKey(
        "account.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    shipping_address = models.ForeignKey(
        "account.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    user_email = models.EmailField(blank=True, default="")
    original = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )
    origin = models.CharField(max_length=32, choices=OrderOrigin.CHOICES)

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    shipping_method = models.ForeignKey(
        ShippingMethod,
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    collection_point = models.ForeignKey(
        "warehouse.Warehouse",
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    shipping_method_name = models.CharField(
        max_length=255, null=True, default=None, blank=True, editable=False
    )
    collection_point_name = models.CharField(
        max_length=255, null=True, default=None, blank=True, editable=False
    )

    channel = models.ForeignKey(
        Channel,
        related_name="orders",
        on_delete=models.PROTECT,
    )
    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        editable=False,
    )
    shipping_price_net = MoneyField(
        amount_field="shipping_price_net_amount", currency_field="currency"
    )

    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        editable=False,
    )
    shipping_price_gross = MoneyField(
        amount_field="shipping_price_gross_amount", currency_field="currency"
    )

    shipping_price = TaxedMoneyField(
        net_amount_field="shipping_price_net_amount",
        gross_amount_field="shipping_price_gross_amount",
        currency_field="currency",
    )
    base_shipping_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    base_shipping_price = MoneyField(
        amount_field="base_shipping_price_amount", currency_field="currency"
    )
    shipping_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, blank=True, null=True
    )
    shipping_tax_class = models.ForeignKey(
        "tax.TaxClass",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    shipping_tax_class_name = models.CharField(max_length=255, blank=True, null=True)
    shipping_tax_class_private_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )
    shipping_tax_class_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )

    # Token of a checkout instance that this order was created from
    checkout_token = models.CharField(max_length=36, blank=True)

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    total_net = MoneyField(amount_field="total_net_amount", currency_field="currency")
    undiscounted_total_net = MoneyField(
        amount_field="undiscounted_total_net_amount", currency_field="currency"
    )

    total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    total_gross = MoneyField(
        amount_field="total_gross_amount", currency_field="currency"
    )
    undiscounted_total_gross = MoneyField(
        amount_field="undiscounted_total_gross_amount", currency_field="currency"
    )

    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        currency_field="currency",
    )
    undiscounted_total = TaxedMoneyField(
        net_amount_field="undiscounted_total_net_amount",
        gross_amount_field="undiscounted_total_gross_amount",
        currency_field="currency",
    )

    total_charged_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    total_authorized_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    total_authorized = MoneyField(
        amount_field="total_authorized_amount", currency_field="currency"
    )
    total_charged = MoneyField(
        amount_field="total_charged_amount", currency_field="currency"
    )
    subtotal_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0),
    )
    subtotal = TaxedMoneyField(
        net_amount_field="subtotal_net_amount",
        gross_amount_field="subtotal_gross_amount",
    )

    voucher = models.ForeignKey(
        Voucher, blank=True, null=True, related_name="+", on_delete=models.SET_NULL
    )

    voucher_code = models.CharField(
        max_length=255, null=True, blank=True, db_index=False
    )
    gift_cards = models.ManyToManyField(GiftCard, blank=True, related_name="orders")
    display_gross_prices = models.BooleanField(default=True)
    customer_note = models.TextField(blank=True, default="")
    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
    )
    redirect_url = models.URLField(blank=True, null=True)
    search_document = models.TextField(blank=True, default="")
    search_vector = SearchVectorField(blank=True, null=True)
    # this field is used only for draft/unconfirmed orders
    should_refresh_prices = models.BooleanField(default=True)
    tax_exemption = models.BooleanField(default=False)
    tax_error = models.CharField(max_length=255, null=True, blank=True)

    objects = OrderManager()

    class Meta:
        ordering = ("-number",)
        permissions = (
            (OrderPermissions.MANAGE_ORDERS.codename, "Manage orders."),
            (OrderPermissions.MANAGE_ORDERS_IMPORT.codename, "Manage orders import."),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="order_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="order_tsearch",
                fields=["search_vector"],
            ),
            GinIndex(
                name="order_email_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["user_email"],
                opclasses=["gin_trgm_ops"],
            ),
            models.Index(fields=["created_at"], name="idx_order_created_at"),
            GinIndex(fields=["voucher_code"], name="order_voucher_code_idx"),
            GinIndex(
                fields=["user_email", "user_id"],
                name="order_user_email_user_id_idx",
            ),
        ]

    def is_fully_paid(self):
        return self.total_charged >= self.total.gross

    def is_partly_paid(self):
        return self.total_charged_amount > 0

    def get_customer_email(self):
        if self.user_id:
            # we know that when user_id is set, user is set as well
            return cast("User", self.user).email
        return self.user_email

    def __repr__(self):
        return f"<Order #{self.id!r}>"

    def __str__(self):
        return f"#{self.id}"

    def get_last_payment(self) -> Optional[Payment]:
        # Skipping a partial payment is a temporary workaround for storing a basic data
        # about partial payment from Adyen plugin. This is something that will removed
        # in 3.1 by introducing a partial payments feature.
        payments: list[Payment] = [
            payment for payment in self.payments.all() if not payment.partial
        ]
        return max(payments, default=None, key=attrgetter("pk"))

    def is_pre_authorized(self):
        return (
            self.payments.filter(
                is_active=True,
                transactions__kind=TransactionKind.AUTH,
                transactions__action_required=False,
            )
            .filter(transactions__is_success=True)
            .exists()
        )

    def is_captured(self):
        return (
            self.payments.filter(
                is_active=True,
                transactions__kind=TransactionKind.CAPTURE,
                transactions__action_required=False,
            )
            .filter(transactions__is_success=True)
            .exists()
        )

    def get_subtotal(self):
        return get_subtotal(self.lines.all(), self.currency)

    def is_shipping_required(self):
        return any(line.is_shipping_required for line in self.lines.all())

    def get_total_quantity(self):
        return sum([line.quantity for line in self.lines.all()])

    def is_draft(self):
        return self.status == OrderStatus.DRAFT

    def is_unconfirmed(self):
        return self.status == OrderStatus.UNCONFIRMED

    def is_expired(self):
        return self.status == OrderStatus.EXPIRED

    def is_open(self):
        statuses = {OrderStatus.UNFULFILLED, OrderStatus.PARTIALLY_FULFILLED}
        return self.status in statuses

    def can_cancel(self):
        statuses_allowed_to_cancel = [
            FulfillmentStatus.CANCELED,
            FulfillmentStatus.REFUNDED,
            FulfillmentStatus.REPLACED,
            FulfillmentStatus.REFUNDED_AND_RETURNED,
            FulfillmentStatus.RETURNED,
        ]
        return (
            not self.fulfillments.exclude(
                status__in=statuses_allowed_to_cancel
            ).exists()
        ) and self.status not in {
            OrderStatus.CANCELED,
            OrderStatus.DRAFT,
            OrderStatus.EXPIRED,
        }

    def can_capture(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        order_status_ok = self.status not in {
            OrderStatus.DRAFT,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
        }
        return payment.can_capture() and order_status_ok

    def can_void(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        return payment.can_void()

    def can_refund(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        return payment.can_refund()

    def can_mark_as_paid(self, payments=None):
        if not payments:
            payments = self.payments.all()
        return len(payments) == 0

    @property
    def total_balance(self):
        return self.total_charged - self.total.gross


class OrderLineQueryset(models.QuerySet["OrderLine"]):
    def digital(self):
        """Return lines with digital products."""
        for line in self.all():
            if line.is_digital:
                yield line

    def physical(self):
        """Return lines with physical products."""
        for line in self.all():
            if not line.is_digital:
                yield line


OrderLineManager = models.Manager.from_queryset(OrderLineQueryset)


class OrderLine(ModelWithMetadata):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    old_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(
        Order,
        related_name="lines",
        editable=False,
        on_delete=models.CASCADE,
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        related_name="order_lines",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    # max_length is as produced by ProductVariant's display_product method
    product_name = models.CharField(max_length=386)
    variant_name = models.CharField(max_length=255, default="", blank=True)
    translated_product_name = models.CharField(max_length=386, default="", blank=True)
    translated_variant_name = models.CharField(max_length=255, default="", blank=True)
    product_sku = models.CharField(max_length=255, null=True, blank=True)
    # str with GraphQL ID used as fallback when product SKU is not available
    product_variant_id = models.CharField(max_length=255, null=True, blank=True)
    is_shipping_required = models.BooleanField()
    is_gift_card = models.BooleanField()
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_fulfilled = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )
    is_gift = models.BooleanField(default=False)

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    unit_discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    unit_discount = MoneyField(
        amount_field="unit_discount_amount", currency_field="currency"
    )
    unit_discount_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        default=DiscountValueType.FIXED,
    )
    unit_discount_reason = models.TextField(blank=True, null=True)

    unit_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    # stores the value of the applied discount. Like 20 of %
    unit_discount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    unit_price_net = MoneyField(
        amount_field="unit_price_net_amount", currency_field="currency"
    )

    unit_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    unit_price_gross = MoneyField(
        amount_field="unit_price_gross_amount", currency_field="currency"
    )

    unit_price = TaxedMoneyField(
        net_amount_field="unit_price_net_amount",
        gross_amount_field="unit_price_gross_amount",
        currency="currency",
    )

    total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    total_price_net = MoneyField(
        amount_field="total_price_net_amount",
        currency_field="currency",
    )

    total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    total_price_gross = MoneyField(
        amount_field="total_price_gross_amount",
        currency_field="currency",
    )

    total_price = TaxedMoneyField(
        net_amount_field="total_price_net_amount",
        gross_amount_field="total_price_gross_amount",
        currency="currency",
    )

    undiscounted_unit_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_unit_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_unit_price = TaxedMoneyField(
        net_amount_field="undiscounted_unit_price_net_amount",
        gross_amount_field="undiscounted_unit_price_gross_amount",
        currency="currency",
    )

    undiscounted_total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_total_price = TaxedMoneyField(
        net_amount_field="undiscounted_total_price_net_amount",
        gross_amount_field="undiscounted_total_price_gross_amount",
        currency="currency",
    )

    base_unit_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    base_unit_price = MoneyField(
        amount_field="base_unit_price_amount", currency_field="currency"
    )

    undiscounted_base_unit_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscounted_base_unit_price = MoneyField(
        amount_field="undiscounted_base_unit_price_amount", currency_field="currency"
    )

    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, blank=True, null=True
    )
    tax_class = models.ForeignKey(
        "tax.TaxClass",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    tax_class_name = models.CharField(max_length=255, blank=True, null=True)
    tax_class_private_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )
    tax_class_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )

    # Fulfilled when voucher code was used for product in the line
    voucher_code = models.CharField(max_length=255, null=True, blank=True)

    # Fulfilled when sale was applied to product in the line
    sale_id = models.CharField(max_length=255, null=True, blank=True)

    objects = OrderLineManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")

    def __str__(self):
        return (
            f"{self.product_name} ({self.variant_name})"
            if self.variant_name
            else self.product_name
        )

    @property
    def quantity_unfulfilled(self):
        return self.quantity - self.quantity_fulfilled

    @property
    def is_digital(self) -> bool:
        """Check if a variant is digital and contains digital content."""
        if not self.variant:
            return False
        is_digital = self.variant.is_digital()
        has_digital = hasattr(self.variant, "digital_content")
        return is_digital and has_digital


class Fulfillment(ModelWithMetadata):
    fulfillment_order = models.PositiveIntegerField(editable=False)
    order = models.ForeignKey(
        Order,
        related_name="fulfillments",
        editable=False,
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=32,
        default=FulfillmentStatus.FULFILLED,
        choices=FulfillmentStatus.CHOICES,
    )
    tracking_number = models.CharField(max_length=255, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    shipping_refund_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    total_refund_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)

    def __str__(self):
        return f"Fulfillment #{self.composed_id}"

    def __iter__(self):
        return iter(self.lines.all())

    def save(self, *args, **kwargs):
        """Assign an auto incremented value as a fulfillment order."""
        if not self.pk:
            groups = self.order.fulfillments.all()
            existing_max = groups.aggregate(Max("fulfillment_order"))
            existing_max = existing_max.get("fulfillment_order__max")
            self.fulfillment_order = existing_max + 1 if existing_max is not None else 1
        return super().save(*args, **kwargs)

    @property
    def composed_id(self):
        return f"{self.order.number}-{self.fulfillment_order}"

    def can_edit(self):
        return self.status != FulfillmentStatus.CANCELED

    def get_total_quantity(self):
        return sum([line.quantity for line in self.lines.all()])

    @property
    def is_tracking_number_url(self):
        return bool(match(r"^[-\w]+://", self.tracking_number))


class FulfillmentLine(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        related_name="fulfillment_lines",
        on_delete=models.CASCADE,
    )
    fulfillment = models.ForeignKey(
        Fulfillment, related_name="lines", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    stock = models.ForeignKey(
        "warehouse.Stock",
        related_name="fulfillment_lines",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )


class OrderEvent(models.Model):
    """Model used to store events that happened during the order lifecycle.

    Args:
        parameters: Values needed to display the event on the storefront
        type: Type of an order

    """

    date = models.DateTimeField(default=now, editable=False)
    type = models.CharField(
        max_length=255,
        choices=[
            (type_name.upper(), type_name) for type_name, _ in OrderEvents.CHOICES
        ],
    )
    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    app = models.ForeignKey(App, related_name="+", on_delete=models.SET_NULL, null=True)
    related = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="related_events",
        db_index=False,
    )

    class Meta:
        ordering = ("date",)
        indexes = [
            BTreeIndex(fields=["related"], name="order_orderevent_related_id_idx")
        ]

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.type!r}, user={self.user!r})"


class OrderGrantedRefund(models.Model):
    """Model used to store granted refund for the order."""

    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount = MoneyField(amount_field="amount_value", currency_field="currency")
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    reason = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    app = models.ForeignKey(
        App, related_name="+", on_delete=models.SET_NULL, null=True, blank=True
    )
    order = models.ForeignKey(
        Order, related_name="granted_refunds", on_delete=models.CASCADE
    )
    shipping_costs_included = models.BooleanField(default=False)

    transaction_item = models.ForeignKey(
        "payment.TransactionItem",
        related_name="granted_refund",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(
        choices=OrderGrantedRefundStatus.CHOICES,
        default=OrderGrantedRefundStatus.NONE,
        max_length=128,
    )

    class Meta:
        ordering = ("created_at", "id")


class OrderGrantedRefundLine(models.Model):
    """Model used to store granted refund line for the order."""

    order_line = models.ForeignKey(
        OrderLine, related_name="granted_refund_lines", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()

    granted_refund = models.ForeignKey(
        OrderGrantedRefund, related_name="lines", on_delete=models.CASCADE
    )

    reason = models.TextField(blank=True, null=True, default="")


class PageQueryset(PublishedQuerySet):
    def visible_to_user(self, requestor: Union["App", "User", None]):
        if requestor and requestor.has_perm(PagePermissions.MANAGE_PAGES):
            return self.all()
        return self.published()


PageManager = models.Manager.from_queryset(PageQueryset)


class Page(ModelWithMetadata, SeoModel, PublishableModel):
    slug = models.SlugField(unique=True, max_length=255)
    title = models.CharField(max_length=250)
    page_type = models.ForeignKey(
        "PageType", related_name="pages", on_delete=models.CASCADE
    )
    content = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = PageManager()  # type: ignore[assignment,misc]

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        permissions = ((PagePermissions.MANAGE_PAGES.codename, "Manage pages."),)
        indexes = [*ModelWithMetadata.Meta.indexes, GinIndex(fields=["title", "slug"])]

    def __str__(self):
        return self.title


class PageTranslation(SeoModelTranslation):
    page = models.ForeignKey(
        Page, related_name="translations", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    content = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        ordering = ("language_code", "page", "pk")
        unique_together = (("language_code", "page"),)

    def __repr__(self):
        class_ = type(self)
        return f"{class_.__name__}(pk={self.pk!r}, title={self.title!r}, page_pk={self.page_id!r})"

    def __str__(self):
        return self.title if self.title else str(self.pk)

    def get_translated_object_id(self):
        return "Page", self.page_id

    def get_translated_keys(self):
        translated_keys = super().get_translated_keys()
        translated_keys.update(
            {
                "title": self.title,
                "content": self.content,
            }
        )
        return translated_keys


class PageType(ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        permissions = (
            (
                PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES.codename,
                "Manage page types and attributes.",
            ),
        )
        indexes = [*ModelWithMetadata.Meta.indexes, GinIndex(fields=["name", "slug"])]


class TransactionItem(ModelWithMetadata):
    token = models.UUIDField(unique=True, default=uuid4)
    use_old_id = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    idempotency_key = models.CharField(max_length=512, blank=True, null=True)
    name = models.CharField(max_length=512, blank=True, null=True, default="")
    message = models.CharField(max_length=512, blank=True, null=True, default="")
    psp_reference = models.CharField(max_length=512, blank=True, null=True)
    available_actions = ArrayField(
        models.CharField(max_length=128, choices=TransactionAction.CHOICES),
        default=list,
    )

    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)

    amount_charged = MoneyField(amount_field="charged_value", currency_field="currency")
    charged_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_authorized = MoneyField(
        amount_field="authorized_value", currency_field="currency"
    )
    authorized_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_refunded = MoneyField(
        amount_field="refunded_value", currency_field="currency"
    )
    refunded_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_canceled = MoneyField(
        amount_field="canceled_value", currency_field="currency"
    )
    canceled_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_refund_pending = MoneyField(
        amount_field="refund_pending_value", currency_field="currency"
    )
    refund_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    amount_charge_pending = MoneyField(
        amount_field="charge_pending_value", currency_field="currency"
    )
    charge_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    amount_authorize_pending = MoneyField(
        amount_field="authorize_pending_value", currency_field="currency"
    )
    authorize_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    cancel_pending_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    amount_cancel_pending = MoneyField(
        amount_field="cancel_pending_value", currency_field="currency"
    )

    external_url = models.URLField(blank=True, null=True)

    checkout = models.ForeignKey(
        Checkout,
        null=True,
        related_name="payment_transactions",
        on_delete=models.SET_NULL,
    )
    order = models.ForeignKey(
        "order.Order",
        related_name="payment_transactions",
        null=True,
        on_delete=models.PROTECT,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # We store app and app_identifier, as the app field stores apps of
    # all types (local, third-party), and the app_identifier field stores
    # only third-party apps.
    # In the case of re-installing the third-party app, we are able to match
    # existing transactions with the re-installed app by using `app_identifier`.
    app = models.ForeignKey(
        "app.App",
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    app_identifier = models.CharField(blank=True, null=True, max_length=256)

    # If last release funds action failed the flag will be set to False
    # Used to define if the checkout with transaction is refundable or not
    last_refund_success = models.BooleanField(default=True)

    class Meta:
        ordering = ("pk",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["app_identifier", "idempotency_key"],
                name="unique_transaction_idempotency",
            ),
        ]


class TransactionEvent(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.CharField(max_length=512, blank=True, null=True)
    psp_reference = models.CharField(max_length=512, blank=True, null=True)
    message = models.CharField(max_length=512, blank=True, null=True, default="")
    transaction = models.ForeignKey(
        TransactionItem, related_name="events", on_delete=models.CASCADE
    )
    external_url = models.URLField(blank=True, null=True)
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    type = models.CharField(
        max_length=128,
        choices=TransactionEventType.CHOICES,
        default=TransactionEventType.INFO,
    )
    amount = MoneyField(amount_field="amount_value", currency_field="currency")
    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # We store app and app_identifier, as the app field stores apps of
    # all types (local, third-party), and the app_identifier field stores
    # only third-party apps.
    # In the case of re-installing the third-party app, we are able to match
    # existing transactions with the re-installed app by using `app_identifier`.
    app = models.ForeignKey(
        "app.App", related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )
    app_identifier = models.CharField(blank=True, null=True, max_length=256)

    include_in_calculations = models.BooleanField(default=False)

    related_granted_refund = models.ForeignKey(
        "order.OrderGrantedRefund",
        related_name="transaction_events",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=["transaction_id", "idempotency_key"],
                name="unique_transaction_event_idempotency",
            )
        ]


class Payment(ModelWithMetadata):
    """A model that represents a single payment.

    This might be a transactable payment information such as credit card
    details, gift card information or a customer's authorization to charge
    their PayPal account.

    All payment process related pieces of information are stored
    at the gateway level, we are operating on the reusable token
    which is a unique identifier of the customer for given gateway.

    Several payment methods can be used within a single order. Each payment
    method may consist of multiple transactions.
    """

    gateway = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    to_confirm = models.BooleanField(default=False)
    partial = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    charge_status = models.CharField(
        max_length=20, choices=ChargeStatus.CHOICES, default=ChargeStatus.NOT_CHARGED
    )
    token = models.CharField(max_length=512, blank=True, default="")
    total = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    captured_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH
    )  # FIXME: add ISO4217 validator

    checkout = models.ForeignKey(
        Checkout, null=True, related_name="payments", on_delete=models.SET_NULL
    )
    order = models.ForeignKey(
        "order.Order",
        related_name="payments",
        null=True,
        on_delete=models.PROTECT,
    )
    store_payment_method = models.CharField(
        max_length=11,
        choices=StorePaymentMethod.CHOICES,
        default=StorePaymentMethod.NONE,
    )

    billing_email = models.EmailField(blank=True)
    billing_first_name = models.CharField(max_length=256, blank=True)
    billing_last_name = models.CharField(max_length=256, blank=True)
    billing_company_name = models.CharField(max_length=256, blank=True)
    billing_address_1 = models.CharField(max_length=256, blank=True)
    billing_address_2 = models.CharField(max_length=256, blank=True)
    billing_city = models.CharField(max_length=256, blank=True)
    billing_city_area = models.CharField(max_length=128, blank=True)
    billing_postal_code = models.CharField(max_length=256, blank=True)
    billing_country_code = models.CharField(max_length=2, blank=True)
    billing_country_area = models.CharField(max_length=256, blank=True)

    cc_first_digits = models.CharField(max_length=6, blank=True, default="")
    cc_last_digits = models.CharField(max_length=4, blank=True, default="")
    cc_brand = models.CharField(max_length=40, blank=True, default="")
    cc_exp_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)], null=True, blank=True
    )
    cc_exp_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1000)], null=True, blank=True
    )

    payment_method_type = models.CharField(max_length=256, blank=True)

    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
    extra_data = models.TextField(blank=True, default="")
    return_url = models.URLField(blank=True, null=True)
    psp_reference = models.CharField(
        max_length=512, null=True, blank=True, db_index=True
    )

    class Meta:
        ordering = ("pk",)
        permissions = (
            (
                PaymentPermissions.HANDLE_PAYMENTS.codename,
                "Handle payments",
            ),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            # Orders filtering by status index
            GinIndex(fields=["order_id", "is_active", "charge_status"]),
        ]

    def __repr__(self):
        return (
            f"Payment(gateway={self.gateway}, is_active={self.is_active}, "
            f"created={self.created_at}, charge_status={self.charge_status})"
        )

    def get_last_transaction(self):
        return max(self.transactions.all(), default=None, key=attrgetter("pk"))

    def get_total(self):
        return Money(self.total, self.currency)

    def get_authorized_amount(self):
        money = zero_money(self.currency)

        # Query all the transactions which should be prefetched
        # to optimize db queries
        transactions = self.transactions.all()

        # There is no authorized amount anymore when capture is succeeded
        # since capture can only be made once, even it is a partial capture
        if any(
            [
                txn.kind == TransactionKind.CAPTURE and txn.is_success
                for txn in transactions
            ]
        ):
            return money

        # Filter the succeeded auth transactions
        authorized_txns = [
            txn
            for txn in transactions
            if txn.kind == TransactionKind.AUTH
            and txn.is_success
            and not txn.action_required
        ]

        # Calculate authorized amount from all succeeded auth transactions
        for txn in authorized_txns:
            money += Money(txn.amount, self.currency)

        # If multiple partial capture is supported later though it's unlikely,
        # the authorized amount should exclude the already captured amount here
        return money

    def get_captured_amount(self):
        return Money(self.captured_amount, self.currency)

    def get_charge_amount(self):
        """Retrieve the maximum capture possible."""
        return self.total - self.captured_amount

    @property
    def is_authorized(self):
        return any(
            [
                txn.kind == TransactionKind.AUTH
                and txn.is_success
                and not txn.action_required
                for txn in self.transactions.all()
            ]
        )

    @property
    def not_charged(self):
        return self.charge_status == ChargeStatus.NOT_CHARGED

    def can_authorize(self):
        return self.is_active and self.not_charged

    def can_capture(self):
        if not (self.is_active and self.not_charged):
            return False
        return True

    def can_void(self):
        return self.not_charged and self.is_authorized

    def can_refund(self):
        can_refund_charge_status = (
            ChargeStatus.PARTIALLY_CHARGED,
            ChargeStatus.FULLY_CHARGED,
            ChargeStatus.PARTIALLY_REFUNDED,
        )
        return self.charge_status in can_refund_charge_status

    def can_confirm(self):
        return self.is_active and self.not_charged

    def is_manual(self):
        return self.gateway == CustomPaymentChoices.MANUAL


class Transaction(models.Model):
    """Represents a single payment operation.

    Transaction is an attempt to transfer money between your store
    and your customers, with a chosen payment method.
    """

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    payment = models.ForeignKey(
        Payment, related_name="transactions", on_delete=models.PROTECT
    )
    token = models.CharField(max_length=512, blank=True, default="")
    kind = models.CharField(max_length=25, choices=TransactionKind.CHOICES)
    is_success = models.BooleanField(default=False)
    action_required = models.BooleanField(default=False)
    action_required_data = JSONField(
        blank=True, default=dict, encoder=DjangoJSONEncoder
    )
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )
    amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    error = models.TextField(null=True)
    customer_id = models.CharField(max_length=256, null=True)
    gateway_response = JSONField(encoder=DjangoJSONEncoder)
    already_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ("pk",)

    def __repr__(self):
        return (
            f"Transaction(type={self.kind}, is_success={self.is_success}, "
            f"created={self.created_at})"
        )

    def get_amount(self):
        return Money(self.amount, self.currency)


from collections.abc import Iterable
from functools import partial
from typing import Union
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models.expressions import Exists, OuterRef
from django.utils import timezone
from django.utils.crypto import get_random_string
from django_countries.fields import Country, CountryField
from phonenumber_field.modelfields import PhoneNumber, PhoneNumberField


class PossiblePhoneNumberField(PhoneNumberField):
    """Less strict field for phone numbers written to database."""

    default_validators = [validate_possible_number]


class AddressQueryset(models.QuerySet["Address"]):
    def annotate_default(self, user):
        # Set default shipping/billing address pk to None
        # if default shipping/billing address doesn't exist
        default_shipping_address_pk, default_billing_address_pk = None, None
        if user.default_shipping_address:
            default_shipping_address_pk = user.default_shipping_address.pk
        if user.default_billing_address:
            default_billing_address_pk = user.default_billing_address.pk

        return user.addresses.annotate(
            user_default_shipping_address_pk=Value(
                default_shipping_address_pk, models.IntegerField()
            ),
            user_default_billing_address_pk=Value(
                default_billing_address_pk, models.IntegerField()
            ),
        )


AddressManager = models.Manager.from_queryset(AddressQueryset)


class Address(ModelWithMetadata):
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    company_name = models.CharField(max_length=256, blank=True)
    street_address_1 = models.CharField(max_length=256, blank=True)
    street_address_2 = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=256, blank=True)
    city_area = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = CountryField()
    country_area = models.CharField(max_length=128, blank=True)
    phone = PossiblePhoneNumberField(blank=True, default="", db_index=True)

    objects = AddressManager()

    class Meta:
        ordering = ("pk",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            GinIndex(
                name="address_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["first_name", "last_name", "city", "country"],
                opclasses=["gin_trgm_ops"] * 4,
            ),
            GinIndex(
                name="warehouse_address_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=[
                    "company_name",
                    "street_address_1",
                    "street_address_2",
                    "city",
                    "postal_code",
                    "phone",
                ],
                opclasses=["gin_trgm_ops"] * 6,
            ),
        ]

    def __eq__(self, other):
        if not isinstance(other, Address):
            return False
        return self.as_data() == other.as_data()

    __hash__ = models.Model.__hash__

    def as_data(self):
        """Return the address as a dict suitable for passing as kwargs.

        Result does not contain the primary key or an associated user.
        """
        data = model_to_dict(self, exclude=["id", "user"])
        if isinstance(data["country"], Country):
            data["country"] = data["country"].code
        if isinstance(data["phone"], PhoneNumber):
            data["phone"] = data["phone"].as_e164
        return data

    def get_copy(self):
        """Return a new instance of the same address."""
        return Address.objects.create(**self.as_data())


class UserManager(BaseUserManager["User"]):
    def create_user(
        self, email, password=None, is_staff=False, is_active=True, **extra_fields
    ):
        """Create a user instance with the given email and password."""
        email = UserManager.normalize_email(email)
        # Google OAuth2 backend send unnecessary username field
        extra_fields.pop("username", None)

        user = self.model(
            email=email, is_active=is_active, is_staff=is_staff, **extra_fields
        )
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(
            email, password, is_staff=True, is_superuser=True, **extra_fields
        )
        group, created = Group.objects.get_or_create(name="Full Access")
        if created:
            group.permissions.add(*get_permissions())
        group.user_set.add(user)  # type: ignore[attr-defined]
        return user

    def customers(self):
        orders = Order.objects.values("user_id")
        return self.get_queryset().filter(
            Q(is_staff=False)
            | (Q(is_staff=True) & (Exists(orders.filter(user_id=OuterRef("pk")))))
        )

    def staff(self):
        return self.get_queryset().filter(is_staff=True)


class User(
    PermissionsMixin, ModelWithMetadata, AbstractBaseUser, ModelWithExternalReference
):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    addresses = models.ManyToManyField(
        Address, blank=True, related_name="user_addresses"
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_confirmed = models.BooleanField(default=True)
    last_confirm_email_request = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    last_password_reset_request = models.DateTimeField(null=True, blank=True)
    default_shipping_address = models.ForeignKey(
        Address, related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )
    default_billing_address = models.ForeignKey(
        Address, related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )
    avatar = models.ImageField(upload_to="user-avatars", blank=True, null=True)
    jwt_token_key = models.CharField(
        max_length=12, default=partial(get_random_string, length=12)
    )
    language_code = models.CharField(
        max_length=35, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    search_document = models.TextField(blank=True, default="")
    uuid = models.UUIDField(default=uuid4, unique=True)

    USERNAME_FIELD = "email"

    objects = UserManager()

    class Meta:
        ordering = ("email",)
        permissions = (
            (AccountPermissions.MANAGE_USERS.codename, "Manage customers."),
            (AccountPermissions.MANAGE_STAFF.codename, "Manage staff."),
            (AccountPermissions.IMPERSONATE_USER.codename, "Impersonate user."),
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            # Orders searching index
            GinIndex(
                name="order_user_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["email", "first_name", "last_name"],
                opclasses=["gin_trgm_ops"] * 3,
            ),
            # Account searching index
            GinIndex(
                name="user_search_gin",
                # `opclasses` and `fields` should be the same length
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="user_p_meta_jsonb_path_idx",
                fields=["private_metadata"],
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._effective_permissions = None

    def __str__(self):
        # Override the default __str__ of AbstractUser that returns username, which may
        # lead to leaking sensitive data in logs.
        return str(self.uuid)

    @property
    def effective_permissions(self) -> models.QuerySet[Permission]:
        if self._effective_permissions is None:
            self._effective_permissions = get_permissions()
            if not self.is_superuser:
                UserPermission = User.user_permissions.through
                user_permission_queryset = UserPermission._default_manager.filter(
                    user_id=self.pk
                ).values("permission_id")

                UserGroup = User.groups.through
                GroupPermission = Group.permissions.through
                user_group_queryset = UserGroup._default_manager.filter(
                    user_id=self.pk
                ).values("group_id")
                group_permission_queryset = GroupPermission.objects.filter(
                    Exists(user_group_queryset.filter(group_id=OuterRef("group_id")))
                ).values("permission_id")

                self._effective_permissions = self._effective_permissions.filter(
                    Q(
                        Exists(
                            user_permission_queryset.filter(
                                permission_id=OuterRef("pk")
                            )
                        )
                    )
                    | Q(
                        Exists(
                            group_permission_queryset.filter(
                                permission_id=OuterRef("pk")
                            )
                        )
                    )
                )
        return self._effective_permissions

    @effective_permissions.setter
    def effective_permissions(self, value: models.QuerySet[Permission]):
        self._effective_permissions = value
        # Drop cache for authentication backend
        self._effective_permissions_cache = None

    def get_full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        if self.default_billing_address:
            first_name = self.default_billing_address.first_name
            last_name = self.default_billing_address.last_name
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
        return self.email

    def get_short_name(self):
        return self.email

    def has_perm(self, perm: Union[BasePermissionEnum, str], obj=None) -> bool:
        # This method is overridden to accept perm as BasePermissionEnum
        perm = perm.value if isinstance(perm, BasePermissionEnum) else perm

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser and not self._effective_permissions:
            return True
        return _user_has_perm(self, perm, obj)

    def has_perms(
        self, perm_list: Iterable[Union[BasePermissionEnum, str]], obj=None
    ) -> bool:
        # This method is overridden to accept perm as BasePermissionEnum
        perm_list = [
            perm.value if isinstance(perm, BasePermissionEnum) else perm
            for perm in perm_list
        ]
        return super().has_perms(perm_list, obj)

    def can_login(self, site_settings: SiteSettings):
        return self.is_active and (
            site_settings.allow_login_without_confirmation
            or not site_settings.enable_account_confirmation_by_email
            or self.is_confirmed
        )


class CustomerNote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL
    )
    date = models.DateTimeField(db_index=True, auto_now_add=True)
    content = models.TextField()
    is_public = models.BooleanField(default=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="notes", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("date",)


class CustomerEvent(models.Model):
    """Model used to store events that happened during the customer lifecycle."""

    date = models.DateTimeField(default=timezone.now, editable=False)
    type = models.CharField(
        max_length=255,
        choices=[
            (type_name.upper(), type_name) for type_name, _ in CustomerEvents.CHOICES
        ],
    )
    order = models.ForeignKey("order.Order", on_delete=models.SET_NULL, null=True)
    parameters = JSONField(blank=True, default=dict, encoder=CustomJsonEncoder)
    user = models.ForeignKey(
        User, related_name="events", on_delete=models.CASCADE, null=True
    )
    app = models.ForeignKey(App, related_name="+", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ("date",)

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.type!r}, user={self.user!r})"


class StaffNotificationRecipient(models.Model):
    user = models.OneToOneField(
        User,
        related_name="staff_notification",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    staff_email = models.EmailField(unique=True, blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("staff_email",)

    def get_email(self):
        return self.user.email if self.user else self.staff_email


class GroupManager(models.Manager):
    """The manager for the auth's Group model."""

    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Group(models.Model):
    """The system provides a way to group users.

    Groups are a generic way of categorizing users to apply permissions, or
    some other label, to those users. A user can belong to any number of
    groups.

    A user in a group automatically has all the permissions granted to that
    group. For example, if the group 'Site editors' has the permission
    can_edit_home_page, any user in that group will have that permission.

    Beyond permissions, groups are a convenient way to categorize users to
    apply some label, or extended functionality, to them. For example, you
    could create a group 'Special users', and you could write code that would
    do special things to those users -- such as giving them access to a
    members-only portion of your site, or sending them members-only email
    messages.
    """

    name = models.CharField("name", max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="permissions",
        blank=True,
    )
    restricted_access_to_channels = models.BooleanField(default=False)
    channels = models.ManyToManyField("channel.Channel", blank=True)

    objects = GroupManager()

    class Meta:
        verbose_name = "group"
        verbose_name_plural = "groups"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


from django.contrib.postgres.indexes import BTreeIndex
from django.db import models

from .base import AssociatedAttributeManager


class AssignedPageAttributeValue(SortableModel):
    value = models.ForeignKey(
        "AttributeValue",
        on_delete=models.CASCADE,
        related_name="pagevalueassignment",
    )
    page = models.ForeignKey(
        Page,
        related_name="attributevalues",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        db_index=False,
    )

    class Meta:
        unique_together = (("value", "page"),)
        ordering = ("sort_order", "pk")
        indexes = [BTreeIndex(fields=["page"], name="assignedpageattrvalue_page_idx")]

    def get_ordering_queryset(self):
        return self.page.attributevalues.all()


class AttributePage(SortableModel):
    attribute = models.ForeignKey(
        "Attribute", related_name="attributepage", on_delete=models.CASCADE
    )
    page_type = models.ForeignKey(
        PageType, related_name="attributepage", on_delete=models.CASCADE
    )

    objects = AssociatedAttributeManager()

    class Meta:
        unique_together = (("attribute", "page_type"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.page_type.attributepage.all()


from django.contrib.postgres.indexes import BTreeIndex
from django.db import models

from .base import AssociatedAttributeManager


class AssignedProductAttributeValue(SortableModel):
    value = models.ForeignKey(
        "AttributeValue",
        on_delete=models.CASCADE,
        related_name="productvalueassignment",
    )
    product = models.ForeignKey(
        Product,
        related_name="attributevalues",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        db_index=False,
    )

    class Meta:
        unique_together = (("value", "product"),)
        ordering = ("sort_order", "pk")
        indexes = [
            BTreeIndex(fields=["product"], name="assignedprodattrval_product_idx")
        ]

    def get_ordering_queryset(self):
        return self.product.attributevalues.all()


class AttributeProduct(SortableModel):
    attribute = models.ForeignKey(
        "Attribute", related_name="attributeproduct", on_delete=models.CASCADE
    )
    product_type = models.ForeignKey(
        ProductType, related_name="attributeproduct", on_delete=models.CASCADE
    )

    objects = AssociatedAttributeManager()

    class Meta:
        unique_together = (("attribute", "product_type"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.product_type.attributeproduct.all()


from django.db import models

from .base import AssociatedAttributeManager, AttributeValue, BaseAssignedAttribute


class AssignedVariantAttributeValue(SortableModel):
    value = models.ForeignKey(
        "AttributeValue",
        on_delete=models.CASCADE,
        related_name="variantvalueassignment",
    )
    assignment = models.ForeignKey(
        "AssignedVariantAttribute",
        on_delete=models.CASCADE,
        related_name="variantvalueassignment",
    )

    class Meta:
        unique_together = (("value", "assignment"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.assignment.variantvalueassignment.all()


class AssignedVariantAttribute(BaseAssignedAttribute):
    """Associate a product type attribute and selected values to a given variant."""

    variant = models.ForeignKey(
        ProductVariant, related_name="attributes", on_delete=models.CASCADE
    )
    assignment = models.ForeignKey(
        "AttributeVariant", on_delete=models.CASCADE, related_name="variantassignments"
    )
    values = models.ManyToManyField(
        AttributeValue,
        blank=True,
        related_name="variantassignments",
        through=AssignedVariantAttributeValue,
    )

    class Meta:
        unique_together = (("variant", "assignment"),)


class AttributeVariant(SortableModel):
    attribute = models.ForeignKey(
        "Attribute", related_name="attributevariant", on_delete=models.CASCADE
    )
    product_type = models.ForeignKey(
        ProductType, related_name="attributevariant", on_delete=models.CASCADE
    )
    assigned_variants = models.ManyToManyField(
        ProductVariant,
        blank=True,
        through=AssignedVariantAttribute,
        through_fields=("assignment", "variant"),
        related_name="attributesrelated",
    )
    variant_selection = models.BooleanField(default=False)

    objects = AssociatedAttributeManager()

    class Meta:
        unique_together = (("attribute", "product_type"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.product_type.attributevariant.all()
