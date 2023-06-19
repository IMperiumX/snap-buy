from django.contrib.auth.models import Group
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Value


class AddressQueryset(models.QuerySet):
    def annotate_default(self, user):
        # Set default shipping/billing address pk to None
        # if default shipping/billing address doesn't exist
        default_shipping_address_pk, default_billing_address_pk = None, None
        if user.default_shipping_address:
            default_shipping_address_pk = user.default_shipping_address.pk
        if user.default_billing_address:
            default_billing_address_pk = user.default_billing_address.pk

        return user.addresses.annotate(
            user_default_shipping_address_pk=Value(default_shipping_address_pk, models.IntegerField()),
            user_default_billing_address_pk=Value(default_billing_address_pk, models.IntegerField()),
        )


class UserManager(DjangoUserManager):
    def create_user(self, email, password=None, is_staff=False, is_active=True, **extra_fields):
        """Create a user instance with the given email and password."""
        email = UserManager.normalize_email(email)
        # Google OAuth2 backend send unnecessary username field
        extra_fields.pop("username", None)

        user = self.model(email=email, is_active=is_active, is_staff=is_staff, **extra_fields)
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(email, password, is_staff=True, is_superuser=True, **extra_fields)
        group, created = Group.objects.get_or_create(name="Full Access")
        if created:
            pass
            # TODO: group.permissions.add(*get_permissions())
        group.user_set.add(user)
        return user

    def staff(self):
        return self.get_queryset().filter(is_staff=True)


AddressManager = models.Manager.from_queryset(AddressQueryset)
