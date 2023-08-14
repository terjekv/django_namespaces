"""Exception interface for django_namespaces.

Using raise_-methods for raising exceptions allows us to raise the appropriate exception
type based on the type of view (Django or DRF).
"""

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.views import View
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet


def is_drf_view(view: View) -> bool:
    """Check if the provided view is a Django Rest Framework view.

    :param view: The view to check.
    :return: True if the view is a DRF view, False otherwise.
    """
    return isinstance(view, (APIView, GenericViewSet))


def raise_namespace_permission_denied(view: View, *args: Any, **kwargs: Any) -> None:
    """Raise an appropriate permission denied exception based on the type of view.

    This function will raise a DRF exception if the view is a DRF view, and a Django
    exception otherwise.

    :param view: The view for which the exception is being raised.
    :param args: Positional arguments to pass to the exception.
    :param kwargs: Keyword arguments to pass to the exception.
    :raises: DRFPermissionDenied if the view is a DRF view, DjangoPermissionDenied otherwise.
    """
    if is_drf_view(view):
        raise DRFPermissionDenied(*args, **kwargs)
    else:
        raise DjangoPermissionDenied(*args, **kwargs)
