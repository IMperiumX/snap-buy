from pathlib import Path
from uuid import uuid4

from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


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
