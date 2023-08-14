"""App defaults for django_namespaces."""

from django.apps import AppConfig


class DjangoNamespacesConfig(AppConfig):
    """AppConfig for django_namespaces."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_namespaces"
