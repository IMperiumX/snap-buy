import datetime
import logging
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework.exceptions import NotAcceptable
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from .managers import UserManager

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Default custom user model for Snap Buy.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
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


class Address(models.Model):
    # Address options
    BILLING = "B"
    SHIPPING = "S"

    ADDRESS_CHOICES = ((BILLING, _("billing")), (SHIPPING, _("shipping")))

    user = models.ForeignKey(User, related_name="addresses", on_delete=models.CASCADE)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)
    country = CountryField()
    city = models.CharField(max_length=100)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.user.get_full_name()


class PhoneNumber(models.Model):
    user = models.OneToOneField(User, related_name="phone", on_delete=models.CASCADE)
    phone_number = PhoneNumberField(unique=True)
    security_code = models.CharField(max_length=120)
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.phone_number.as_e164

    def generate_security_code(self):
        """
        Returns a unique random `security_code` for given `TOKEN_LENGTH` in the settings.
        Default token length = 6
        """
        token_length = getattr(settings, "TOKEN_LENGTH", 6)
        return get_random_string(token_length, allowed_chars="0123456789")

    def is_security_code_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            minutes=settings.TOKEN_EXPIRE_MINUTES,
        )
        return expiration_date <= timezone.now()

    def send_confirmation(self):
        twilio_account_sid = settings.TWILIO_ACCOUNT_SID
        twilio_auth_token = settings.TWILIO_AUTH_TOKEN
        twilio_phone_number = settings.TWILIO_PHONE_NUMBER

        self.security_code = self.generate_security_code()

        if all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            try:
                twilio_client = Client(twilio_account_sid, twilio_auth_token)
                twilio_client.messages.create(
                    body=f"Your activation code is {self.security_code}",
                    to=str(self.phone_number),
                    from_=twilio_phone_number,
                )
            except TwilioRestException:
                logger.debug("Error while Sending SMS message")
            else:
                self.sent = timezone.now()
                self.save()
                return True
        else:
            logger.debug("Twilio credentials are not set")
        return False

    def check_verification(self, security_code):
        if (
            not self.is_security_code_expired()
            and security_code == self.security_code
            and not self.is_verified
        ):
            self.is_verified = True
            self.save()
        else:
            raise NotAcceptable(
                _(
                    "Your security code is wrong, expired or this phone is verified before.",
                ),
            )

        return self.is_verified


class Profile(models.Model):
    user = models.OneToOneField(
        "users.User",
        related_name="profile",
        on_delete=models.CASCADE,
    )
    avatar = models.ImageField(upload_to="avatar", blank=True)
    bio = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.get_full_name()}"
