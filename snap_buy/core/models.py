import datetime

import pytz
from django.db import models, transaction
from django.db.models import F, Max, Q


class SortableModel(models.Model):
    sort_order = models.IntegerField(editable=False, db_index=True, null=True)

    class Meta:
        abstract = True

    def get_ordering_queryset(self):
        raise NotImplementedError("Unknown ordering queryset")

    def get_max_sort_order(self, qs):
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
            qs.filter(sort_order__gt=self.sort_order).update(sort_order=F("sort_order") - 1)
        super().delete(*args, **kwargs)


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


class PublishedQuerySet(models.QuerySet):
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

    objects = PublishableManager()

    class Meta:
        abstract = True

    @property
    def is_visible(self):
        return self.is_published and (
            self.published_at is None or self.published_at <= datetime.datetime.now(pytz.UTC)
        )
