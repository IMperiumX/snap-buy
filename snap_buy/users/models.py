from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import Value
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_countries.fields import Country
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumber
from phonenumber_field.modelfields import PhoneNumberField

from snap_buy.core.models import ModelWithMetadata

from .managers import UserManager
from .validators import validate_possible_number


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
                default_shipping_address_pk,
                models.IntegerField(),
            ),
            user_default_billing_address_pk=Value(
                default_billing_address_pk,
                models.IntegerField(),
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
    validation_skipped = models.BooleanField(default=False)

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
        if isinstance(data["phone"], PhoneNumber) and not data["validation_skipped"]:
            data["phone"] = data["phone"].as_e164
        return data

    def get_copy(self):
        """Return a new instance of the same address."""
        return Address.objects.create(**self.as_data())


class User(AbstractUser):
    """
    Default custom user model for Snap Buy.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})
