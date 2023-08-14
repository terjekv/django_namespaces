"""Model(s) for use with the django_namespaces_testproject."""
from django.db import models

from django_namespaces.models import AbstractNamespaceModel


class NamespacedExample(AbstractNamespaceModel):
    """Example model for use with django_namespaces_testproject."""

    name = models.CharField(max_length=255)
