"""Permissions module for the django_namespaces app."""
from django.db.models import Q
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.exceptions import MethodNotAllowed

from .models import AbstractNamespaceModel, ObjectPermission
from .constants import HTTP_METHOD_TO_OBJECTACTION_MAP


class NamespacePermissions(BasePermission):
    """A custom permissions class to handle namespaced permissions.

    :param permission_required: The permission that a user/group needs to have.
           Defaults to "has_read".
    """

    def get_permission_filter(self, request: Request, view: APIView) -> Q:
        """Determine the permission filter to apply based on the user and the view.

        :param request: The incoming request.
        :param view: The view being accessed.
        :return: The queryset filter to apply.
        """
        user = request.user

        if user.is_superuser:
            return Q()

        if not user.is_authenticated:
            return Q(pk__in=[])

        permission_required = getattr(view, "permission_required", None)
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

        return Q(pk__in=[])

    def has_permission(self, request: Request, view: APIView) -> bool:  # type: ignore
        """Check if the incoming request has the required permissions.

        :param request: The incoming request.
        :param view: The view being accessed.
        :return: Always returns True for authenticated users for DRF compatibility.
        """
        if request.user.is_authenticated:
            return True
        return False
