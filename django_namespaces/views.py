"""The base view for use with the django_namespaces."""
from typing import Any, Type, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from django_namespaces.constants import NamespaceActions
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    ObjectPermission,
    grant_permission,
    has_permission,
)
from django_namespaces.serializers import (
    GrantPermissionSerializer,
    NamespacePermissionSerializer,
    NamespaceSerializer,
    ObjectPermissionSerializer,
)


def get_from_id_or_name(model: Type[models.Model], identifier: str) -> models.Model:
    """Get a model instance based on the id or name.

    :param model: The model to query.
    :param id: The id or name of the model.
    """
    try:
        if identifier.isdigit():
            return model.objects.get(id=identifier)
        return model.objects.get(name=identifier)
    except model.DoesNotExist as exc:
        raise NotFound(f"{model.__name__} '{identifier}' does not exist") from exc


class NamespaceViewSet(viewsets.ModelViewSet):
    """A viewset for viewing and manipulating namespaces.

    Attributes
    ----------
        queryset (QuerySet[Namespace]): A dynamic queryset for namespaces based on the user.
        serializer_class (type): The serializer class used for the namespace.
    """

    serializer_class = NamespaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[Namespace]:  # type: ignore
        """Retrieve the queryset of namespaces based on user permissions.

        :returns QuerySet[Namespace]: The filtered queryset.
        """
        user = self.request.user
        action = NamespaceActions.READ
        # Building the dynamic queryset based on user and permissions
        return Namespace.objects.filter(
            Q(group__in=user.groups.all()) | Q(user=user)
        ).filter(**{action.value: True})

    def list(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:  # noqa
        """List all relevant namespaces for the authenticated user.

        :param request (Request): The DRF request object.

        :returns Response: The DRF response object containing the list of namespaces.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Create a new namespace.

        :param request (Request): The DRF request object.

        :returns Response: The DRF response object.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # If you need to add additional logic or transformations, do it here.

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class NamespaceGrantViewSet(viewsets.ViewSet):
    """Custom actions are defined for clarity. No defaults used."""

    def _get_namespace(self, namespace_id_or_name: Union[int, str]) -> Namespace:
        """Retrieve a namespace based on its ID or name.

        :param namespace_id_or_name: The ID or name of the namespace.
        :return: The Namespace instance.
        """
        return get_from_id_or_name(Namespace, namespace_id_or_name)

    def _get_permission_model(self, object_type: str) -> Type[models.Model]:
        """Determine the appropriate permission model based on the object type.

        :param object_type: The type of object, either 'namespace' or 'objects'.
        :return: The appropriate model class (NamespacePermission or ObjectPermission).
        """
        return NamespacePermission if object_type == "namespace" else ObjectPermission

    def _get_user_or_group(
        self, entity: str, identifier: Union[int, str]
    ) -> models.Model:
        """Retrieve a user or group based on its entity type and ID or name.

        :param entity: The type of entity, either 'user' or 'group'.
        :param identifier: The ID or name of the user or group.
        :return: The user or group instance.
        """
        return (
            get_from_id_or_name(get_user_model(), identifier)
            if entity == "user"
            else get_from_id_or_name(Group, identifier)
        )

    @action(detail=False, methods=["POST"], url_path="grant")
    def grant_permission(self, request: HttpRequest, **kwargs: Any):
        """Handle granting of permission logic."""
        serializer = GrantPermissionSerializer(
            data=request.data, object_type=kwargs["object_type"]
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        namespace = self._get_namespace(kwargs["namespace"])
        model = self._get_permission_model(kwargs["object_type"])
        user_or_group = self._get_user_or_group(kwargs["entity"], kwargs["id"])

        for perm in serializer.validated_data["actions"]:  # type: ignore
            grant_permission(model, namespace, user_or_group, perm, self.request.user)

        return Response(
            {"message": "Permission granted successfully."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["GET"])
    def list_permissions(self, request: HttpRequest, **kwargs: Any):
        """Handle listing of permissions for a user/group on a particular namespace or object."""
        namespace = self._get_namespace(kwargs["namespace"])
        model = self._get_permission_model(kwargs["object_type"])
        serializer_class = (
            NamespacePermissionSerializer
            if kwargs["object_type"] == "namespace"
            else ObjectPermissionSerializer
        )
        user_or_group = self._get_user_or_group(kwargs["entity"], kwargs["id"])
        user_or_group_filter = {kwargs["entity"]: user_or_group}

        permissions = model.objects.filter(namespace=namespace, **user_or_group_filter)

        if not permissions.exists():
            raise NotFound("No permissions found.")

        return Response(
            serializer_class(permissions, many=True).data, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["PATCH"], url_path="modify")
    def modify_permissions(self, request: HttpRequest, **kwargs: Any):
        """Modifiy permissions for a user/group on a particular namespace or object."""
        serializer = GrantPermissionSerializer(
            data=request.data, object_type=kwargs["object_type"]
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        namespace = self._get_namespace(kwargs["namespace"])
        model = self._get_permission_model(kwargs["object_type"])
        user_or_group = self._get_user_or_group(kwargs["entity"], kwargs["id"])
        user_or_group_filter = {kwargs["entity"]: user_or_group}

        permissions_to_remove = model.objects.filter(
            namespace=namespace, **user_or_group_filter
        )

        can_update = has_permission(
            model,
            namespace,
            user_or_group,
            NamespaceActions.UPDATE,
            None,
        )

        # We return 404 to avoid leaking the existence of the object to unauthorised users
        if not (can_update and permissions_to_remove.exists()):
            raise NotFound("Permission not found.")

        # We use a transaction to ensure that the permissions are either all updated or not
        # updated at all.
        with transaction.atomic():
            # Remove all existing permissions
            permissions_to_remove.delete()

            print("----ATOMIC----")
            print(model.objects.filter(namespace=namespace, **user_or_group_filter))

            # Re-grant permissions
            for perm in serializer.validated_data["actions"]:  # type: ignore
                grant_permission(
                    model, namespace, user_or_group, perm, self.request.user
                )

        return Response(
            {"message": "Permissions modified successfully."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["DELETE"], url_path="revoke")
    def revoke_permissions(self, request: HttpRequest, **kwargs: Any):
        """Revoke all permissions for a user/group on a particular namespace or object."""
        namespace = self._get_namespace(kwargs["namespace"])
        model = self._get_permission_model(kwargs["object_type"])
        user_or_group = self._get_user_or_group(kwargs["entity"], kwargs["id"])
        user_or_group_filter = {kwargs["entity"]: user_or_group}

        model.objects.filter(namespace=namespace, **user_or_group_filter).delete()

        return Response(
            {"message": "All permissions revoked successfully."},
            status=status.HTTP_200_OK,
        )
