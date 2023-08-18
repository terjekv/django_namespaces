"""Mixins for use with the django_namespace_permissions."""
from typing import Any, Type

from django.db.models import Model, Q, QuerySet
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_namespace_permissions.constants import ObjectActions
from django_namespace_permissions.models import (
    AbstractNamespaceModel,
    Namespace,
    ObjectPermission,
    has_permission,
)
from django_namespace_permissions.views import get_from_id_or_name

from .constants import HTTP_METHOD_TO_OBJECTACTION_MAP


class NamespacePermissionMixin:
    """A mixin that adds namespace-based permissions to views."""

    def get_permission_filter(self, request: Request, view: APIView) -> Q:
        """Determine the permission filter to apply based on the user and the view.

        :param request: The incoming request.
        :param view: The view being accessed.
        :return: The queryset filter to apply.
        """
        user = request.user

        # First check to see if the view has a hardcoded permission_required attribute
        permission_required = getattr(view, "permission_required", None)
        # If not, look up the default mapping table.
        if not permission_required:
            permission_required = HTTP_METHOD_TO_OBJECTACTION_MAP.get(request.method)
            if not permission_required:
                raise MethodNotAllowed(request.method)

        if issubclass(view.queryset.model, AbstractNamespaceModel):
            permitted_namespace_ids = ObjectPermission.objects.filter(
                Q(group__in=user.groups.all()) | Q(user=user),
                **{permission_required: True}
            ).values("namespace_id")

            return Q(namespace_id__in=permitted_namespace_ids)

        return Q()

    def get_queryset(self) -> QuerySet[Type[Model]]:
        """Override the get_queryset method to filter the queryset by permissions."""
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Authentication required")

        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset

        if issubclass(queryset.model, AbstractNamespaceModel):
            permission_filter = self.get_permission_filter(self.request, self)

            # Use the permission_filter directly with the queryset
            queryset = queryset.filter(permission_filter)

        return queryset

    # A distinct create method is required as we normally use filter_queryset
    # to remove objects that the user does not have permission to view,
    # based on the HTTP method. This is all well and good, but the create method
    # has no objects to retrieve, so it never calls filter_queryset and therefore
    # never checks permissions. We do that here instead.
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Override create method to check namespace permissions.

        :param request: The incoming request.
        :param args: Any positional arguments.
        :param kwargs: Any keyword arguments.

        :return: The response.
        """
        # Note: We check if the super class has a create method, because
        # some views (e.g. ListAPIView) do not have a create method and our purpose
        # is only to provide permissions checking, not to add the method itself.
        if not hasattr(super(), "create"):  # pragma: no cover
            return MethodNotAllowed("Method not supported for this endpoint.")

        namespace_id = request.data.get("namespace")
        namespace = get_from_id_or_name(Namespace, namespace_id)
        user = request.user
        if not has_permission(
            ObjectPermission, namespace, user, ObjectActions.CREATE, None
        ):
            raise PermissionDenied(
                "Permission denied for action 'create' in {str(namespace)}"
            )

        return super().create(request, *args, **kwargs)
