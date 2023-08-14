"""Mixins for use with the django_namespaces."""
from typing import Type

from django.db import models
from django.db.models import Model, QuerySet, Subquery

from django_namespaces.exceptions import raise_namespace_permission_denied
from django_namespaces.models import (
    AbstractNamespaceModel,
    ObjectPermission,
)
from django_namespaces.permissions import NamespacePermissions


class NamespacePermissionMixin:
    """A mixin that adds namespace-based permissions to views.

    To use this mixin, the view must define a `get_permission_required` method.
    """

    def get_queryset(self) -> QuerySet[Type[Model]]:
        """Override the get_queryset method to filter the queryset by permissions."""
        queryset = super().get_queryset()

        if issubclass(queryset.model, AbstractNamespaceModel):
            permission_filter = self.get_permission_filter()

            # Use the permission_filter directly with the queryset
            queryset = queryset.filter(permission_filter)

        return queryset

    def get_queryset_2(self) -> QuerySet[Type[Model]]:
        """Override the get_queryset method to filter the queryset by permissions."""
        queryset = super().get_queryset()

        if issubclass(queryset.model, AbstractNamespaceModel):
            permission_filter = self.get_permission_filter()

            # Define the permission subquery
            permission_subquery = (
                ObjectPermission.objects.filter(permission_filter)
                .values("namespace")
                .annotate(
                    has_permission=models.Exists(
                        ObjectPermission.objects.filter(permission_filter)
                    )
                )
                .values("has_permission")[:1]
            )

            # Use the subquery in the queryset annotation
            queryset = queryset.annotate(
                has_permission=Subquery(permission_subquery)
            ).filter(has_permission=True)

        return queryset

    def get_permission_filter(self):
        """Determine the permission filter to apply based on the user and the view."""
        permission_required = self.get_permission_required()

        print(permission_required)

        return NamespacePermissions(permission_required).get_permission_filter(
            self.request, self
        )

    def check_object_permissions(self, request, obj):
        """Check if the request should be permitted for a given object.

        Raises an appropriate exception if the request is not permitted.
        """
        super().check_object_permissions(request, obj)

        permission_required = self.get_permission_required()
        permission_filter = NamespacePermissions(
            permission_required
        ).get_permission_filter(request, self)

        has_permission = ObjectPermission.objects.filter(permission_filter).exists()

        if not has_permission:
            raise_namespace_permission_denied(self)

    def get_permission_required(self) -> str:
        """Determine the permission required based on the HTTP method."""
        if self.action in ["destroy", "create"]:
            return f"has_{self.action}"
        elif self.action in ["update", "partial_update"]:
            return "has_update"
        else:
            return "has_read"

    # if "create" in dir(super()):

    #     def create(self, request, *args, **kwargs):
    #         """Override the create method to add permission check."""
    #         if not self.get_permission_required() == "has_create":
    #             return Response(
    #                 {"detail": "You do not have permission to create"},
    #                 status=status.HTTP_403_FORBIDDEN,
    #             )

    #         return super().create(request, *args, **kwargs)

    # if "update" in dir(super()):

    #     def update(self, request, *args, **kwargs):
    #         """Override the update method to add permission check."""
    #         if not self.get_permission_required() == "has_update":
    #             return Response(
    #                 {"detail": "You do not have permission to update"},
    #                 status=status.HTTP_403_FORBIDDEN,
    #             )

    #         return super().update(request, *args, **kwargs)

    # if "partial_update" in dir(super()):

    #     def partial_update(self, request, *args, **kwargs):
    #         """Override the partial_update method to add permission check."""
    #         if not self.get_permission_required() == "has_update":
    #             return Response(
    #                 {"detail": "You do not have permission to update"},
    #                 status=status.HTTP_403_FORBIDDEN,
    #             )

    #         return super().partial_update(request, *args, **kwargs)

    # if "destroy" in dir(super()):

    #     def destroy(self, request, *args, **kwargs):
    #         instance = self.get_object()
    #         self.check_object_permissions(self.request, instance)
    #         self.perform_destroy(instance)
    #         return Response(status=status.HTTP_204_NO_CONTENT)
