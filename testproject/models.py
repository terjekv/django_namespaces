"""Model(s) for use with the testproject."""
from django.db import models

from django_namespace_permissions.models import AbstractNamespaceModel


class NamespacedExample(AbstractNamespaceModel):
    """Example model for use with testproject."""

    name = models.CharField(max_length=255)
