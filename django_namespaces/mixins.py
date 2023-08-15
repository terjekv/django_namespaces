"""Mixins for use with the django_namespaces."""
from typing import Type

from django.db.models import Model, Q, QuerySet
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.request import Request
from rest_framework.views import APIView

from django_namespaces.models import AbstractNamespaceModel, ObjectPermission

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
