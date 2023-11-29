from functools import partial
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from snap_buy.core.models import ModelWithExternalReference

from .managers import AddressManager, UserManager
from .models_mixin import AddressMixin, UserMixin
from .validators import validate_possible_number


class PossiblePhoneNumberField(PhoneNumberField):
    """Less strict field for phone numbers written to database."""

    default_validators = [validate_possible_number]


class Address(AddressMixin, models.Model):
    city = models.CharField(max_length=256, blank=True)
    city_area = models.CharField(max_length=128, blank=True)
    company_name = models.CharField(max_length=256, blank=True)
    country = CountryField()
    country_area = models.CharField(max_length=128, blank=True)
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    phone = PossiblePhoneNumberField(blank=True, default="", db_index=True)
    postal_code = models.CharField(max_length=20, blank=True)
    street_address_1 = models.CharField(max_length=256, blank=True)
    street_address_2 = models.CharField(max_length=256, blank=True)

    objects = AddressManager()

    class Meta:
        ordering = ("pk",)


class User(UserMixin, AbstractUser, ModelWithExternalReference):
    """
    Default custom user model for snap-buy.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    addresses = models.ManyToManyField(Address, blank=True, related_name="user_addresses")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
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
    jwt_token_key = models.CharField(max_length=12, default=partial(get_random_string, length=12))
    language_code = models.CharField(max_length=35, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    search_document = models.TextField(blank=True, default="")
    uuid = models.UUIDField(default=uuid4, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()
