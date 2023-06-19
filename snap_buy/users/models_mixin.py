from django.db import models as django_models
from django.forms.models import model_to_dict
from django.urls import reverse
from django_countries.fields import Country
from phonenumber_field.modelfields import PhoneNumber

from . import models


class AddressMixin:
    def __eq__(self, other):
        if not isinstance(other, models.Address):
            return False
        return self.as_data() == other.as_data()

    __hash__ = django_models.Model.__hash__

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
        return models.Address.objects.create(**self.as_data())


class PermissionMixin:
    # TODO: create Permission app and include PermissionMixin with User

    pass


class UserMixin:
    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._effective_permissions = None

    def __str__(self):
        # Override the default __str__ of AbstractUser that returns username, which may
        # lead to leaking sensitive data in logs.
        return str(self.uuid)
