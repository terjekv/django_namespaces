"""Models for the django_namespaces app."""
# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false

from typing import Any, Type, Union

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from django_namespaces.constants import NamespaceActions, ObjectActions

AnyAction = Union[NamespaceActions, ObjectActions]
UserOrGroup = Union[AbstractUser, Group]


def _check_requestor(
    requestor: AbstractUser,
    namespace: "Namespace",
    action: AnyAction,  # type: ignore,
    message: str,
) -> None:
    """Check if a requestor has permission to perform an action on a namespace or its objects.

    :param requestor: The user requesting the permission check.
    :param namespace: The namespace to check the permission in.
    :param action (NamespaceActions or OjbectActions): The action to check for.

    :raises PermissionDenied: If the requestor does not have has_read on the namespace
        for the given action.
    :return: None
    """
    if requestor.is_superuser:
        return

    # We use the requestor as the target here because we want to check if the requestor
    # has permission to perform the action on the namespace. We thus pass has_permission
    # None as requestor to bypass the requestor check.
    model = NamespacePermission
    if isinstance(action, ObjectActions):
        model = ObjectPermission

    if not has_permission(model, namespace, requestor, action, None):
        raise PermissionDenied(message)


def has_permission(
    model: Type[models.Model],
    namespace: "Namespace",
    target: UserOrGroup,
    action: AnyAction,
    requestor: AbstractUser,
) -> bool:
    """Check if a user or group has a specific permission.

    :param model: The Permission model (either NamespacePermission or ObjectPermission).
    :param namespace: The namespace to check the permission in.
    :param target: The user or group to check the permission for.
    :param action: The action to check for (either NamespaceActions or ObjectActions)
    :param requestor: The user requesting the permission check. If None, the check is
        performed as-is (no requestor checking)

    :raises PermissionDenied: If the requestor does not have has_read on the namespace.
    :return: True if the user or group has the permission, False otherwise.
    """
    if requestor:
        if isinstance(action, NamespaceActions):
            read_to_check = NamespaceActions.READ
        else:
            read_to_check = ObjectActions.READ

        _check_requestor(
            requestor,
            namespace,
            read_to_check,
            f"{requestor} does not have access to information about {namespace}",
        )

    try:
        if isinstance(target, AbstractUser):
            filter_criteria = Q(group__in=target.groups.all()) | Q(user=target)
        else:
            filter_criteria = Q(group=target)

        filter_criteria &= Q(namespace=namespace, **{action.value: True})
        return model.objects.filter(filter_criteria).exists()
    except ValidationError:
        return False


def grant_permission(
    model: Type[models.Model],
    namespace: "Namespace",
    target: UserOrGroup,
    action: AnyAction,
    requestor: AbstractUser,
) -> bool:
    """Grant the given permission to a user or a group.

    :param model: The Permission model (either NamespacePermission or ObjectPermission).
    :param namespace: The namespace to grant the permission in.
    :param target: The user or group to grant the permission to.
    :param action: The action to grant permissions for.
    :param requestor: The user granting the permission.

    :raises PermissionDenied: If the requestor does not have permission to grant permissions.
    :return: True if the operation was successful, False otherwise.
    """
    _check_requestor(
        requestor,
        namespace,
        NamespaceActions.DELEGATE,
        f"{requestor} is not authorized to grant permissions in {namespace}.",
    )

    target_type = "user" if isinstance(target, AbstractUser) else "group"

    try:
        create_criteria = {
            target_type: target,
            "namespace": namespace,
        }

        perm_obj, created = model.objects.get_or_create(
            **create_criteria, defaults={action.value: True}
        )

        if not created:
            setattr(perm_obj, action.value, True)
            perm_obj.save()
    except ValidationError:
        return False

    return True


def revoke_permission(
    model: Type[models.Model],
    namespace: "Namespace",
    target: UserOrGroup,
    action: AnyAction,
    requestor: AbstractUser,
) -> bool:
    """Revoke a specific permission or all permissions from a user or group.

    :param model: The Permission model (either NamespacePermission or ObjectPermission).
    :param namespace: The namespace to revoke the permission from.
    :param target: The user or group to revoke the permission from.
    :param action: The action to revoke. If None, all permissions are revoked.
    :param requestor: The user revoking the permission.

    :raises PermissionDenied: If the requestor does not have permission to revoke permissions.
    :return: True if the operation was successful, False otherwise.
    """
    _check_requestor(
        requestor,
        namespace,
        NamespaceActions.DELEGATE,
        f"{requestor} is not authorized to revoke permissions in {namespace}.",
    )

    target_type = "user" if isinstance(target, AbstractUser) else "group"

    try:
        filter_criteria = {"namespace": namespace, target_type: target}

        if action:
            # Revoke a specific permission
            perm_obj = model.objects.get(**filter_criteria)
            setattr(perm_obj, action.value, False)

            # If all permissions are now False, we delete the object
            # otherwise, just save the changes.
            if all(
                [getattr(perm_obj, perm.value) is False for perm in action.__class__]
            ):
                perm_obj.delete()
            else:
                perm_obj.save()
        else:
            # Revoke all permissions (remove the entry completely)
            model.objects.filter(**filter_criteria).delete()
    except (model.DoesNotExist, ValidationError):
        return False

    return True


class BasePermission(models.Model):
    """An abstract base model for permissions."""

    namespace = models.ForeignKey(
        "Namespace",
        related_name="%(class)s_permissions",
        on_delete=models.CASCADE,
        null=False,
    )
    group = models.ForeignKey(
        "auth.Group",
        related_name="%(class)s_permissions",
        on_delete=models.CASCADE,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_permissions",
        on_delete=models.CASCADE,
        null=True,
    )
    has_create: bool = models.BooleanField(default=False)
    has_read: bool = models.BooleanField(default=False)
    has_update: bool = models.BooleanField(default=False)
    has_delete: bool = models.BooleanField(default=False)

    class Meta:
        """Meta options for the BasePermission model."""

        abstract = True
        unique_together = ("namespace", "group", "user")

    def __str__(self) -> str:
        """Return a string representation of the permission."""
        if self.group:
            return (
                f"{self._meta.verbose_name} for {self.group} in {self.namespace.name}"
            )

        return f"{self._meta.verbose_name} for {self.user} in {self.namespace.name}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override the save method to validate that either group or user is set, but not both."""
        if not self.group and not self.user:
            raise ValidationError("Either group or user must be set.")
        if self.group and self.user:
            raise ValidationError(
                "Permission cannot belong to both a group and a user."
            )
        super().save(*args, **kwargs)


class NamespacePermission(BasePermission):
    """A model for permissions to namespaces themselves."""

    has_delegate: bool = models.BooleanField(default=False)

    class Meta:
        """Meta options for the NamespacePermission model."""

        verbose_name = "Namespace Permissions"

    def user_can(
        self,
        user: AbstractUser,
        namespace: "Namespace",
        action: NamespaceActions,
        requestor: AbstractUser,
    ) -> bool:
        """Check if a user can perform the given action on the given namespace.

        params: user (AbstractUser): The user to check permissions for.
        params: action (ValidNamespaceActions): The action to check permissions for.

        returns: bool: True if the user can perform the action, False otherwise.
        """
        return has_permission(ObjectPermission, namespace, user, action, requestor)


class ObjectPermission(BasePermission):
    """A model for permissions on objects within a namespace."""

    class Meta:
        """Meta options for the ObjectPermission model."""

        verbose_name = "Permissions for objects in a Namespace"

    def user_can(
        self,
        user: AbstractUser,
        namespace: "Namespace",
        action: ObjectActions,
        requestor: AbstractUser,
    ) -> bool:
        """Check if a user can perform the given action on objects in the given namespace.

        params: user (AbstractUser): The user to check permissions for.
        params: namespace (Namespace): The namespace to check permissions for.
        params: action (ValidObjectActions): The action to check permissions for.

        returns: bool: True if the user can perform the action, False otherwise.
        """
        return has_permission(ObjectPermission, namespace, user, action, requestor)


class Namespace(models.Model):
    """A model for namespaces ('domains') of objects."""

    name: str = models.CharField(max_length=255, unique=True)
    description: str = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return the name of the namespace."""
        return self.name

    def grant_permission_to_user(
        self,
        model: "AbstractNamespaceModel",
        user: AbstractUser,
        action: AnyAction,
        requestor: AbstractUser,
    ) -> bool:
        """Grant the given user the given permission.

        params:
        model: The Permission model (either NamespacePermission or ObjectPermission).
        user (AbstractUser): The user to grant the permission to.
        action: The action to grant permissions for.
        """
        return grant_permission(model, self, user, action, requestor)

    def grant_namespace_permission_to_user(
        self, user: AbstractUser, action: NamespaceActions, requestor: AbstractUser
    ) -> bool:
        """Grant the given user the given namespace permission.

        params: user (AbstractUser): The user to grant the permission to.
        params: action (NamespacePermissions) The action to grant permissions for.
        """
        return self.grant_permission_to_user(
            NamespacePermission, user, action, requestor
        )

    def grant_object_permission_to_user(
        self, user: AbstractUser, action: ObjectActions, requestor: AbstractUser
    ) -> bool:
        """Grant the given user the given object permission.

        params: user (AbstractUser): The user to grant the permission to.
        params: action (ObjectPermissions) The action to grant permissions for.
        """
        return self.grant_permission_to_user(ObjectPermission, user, action, requestor)

    def revoke_permission_from_user(
        self,
        model: Type[models.Model],
        user: AbstractUser,
        action: AnyAction,
        requestor: AbstractUser,
    ) -> bool:
        """Revoke a specific permission or all permissions from a user.

        :param model: The Permission model (either NamespacePermission or ObjectPermission).
        :param user: The user to revoke the permission from.
        :param action: The action to revoke. If None, all permissions are revoked.
        :return: True if the operation was successful, False otherwise.
        """
        revoke_permission(model, self, user, action, requestor)

    def revoke_namespace_permission_from_user(
        self, user: AbstractUser, action: NamespaceActions, requestor: AbstractUser
    ) -> bool:
        """Revoke a specific namespace permission or all namespace permissions from a user.

        :param user: The user to revoke the permission from.
        :param action: The action to revoke. If None, all permissions are revoked.
        :return: True if the operation was successful, False otherwise.
        """
        return self.revoke_permission_from_user(
            NamespacePermission, user, action, requestor
        )

    def revoke_object_permission_from_user(
        self, user: AbstractUser, action: ObjectActions, requestor: AbstractUser
    ) -> bool:
        """Revoke a specific object permission or all object permissions from a user.

        :param user: The user to revoke the permission from.
        :param action: The action to revoke. If None, all permissions are revoked.
        :return: True if the operation was successful, False otherwise.
        """
        return self.revoke_permission_from_user(
            ObjectPermission, user, action, requestor
        )


class PermissionMixin:
    """A mixin for models that can have permissions."""

    def i_can(
        self, action: AnyAction, obj: Union["Namespace", "AbstractNamespaceModel"]
    ) -> bool:
        """Check if the current user can perform an action on an object or a namespace.

        :param action (NamespaceAction or ObjectAction): The action to check permissions for.
        :param obj (Namespace or AbstractNamespaceModel): The object to check permissions for.
        """
        return self.target_can(action, obj, self)

    def i_can_namespace(self, action: NamespaceActions, obj: Namespace) -> bool:
        """Check if the current user can perform the given action on the given namespace.

        :param action (NamespaceActions): The action to check permissions for.
        :param obj (Namespace): The namespace object to check permissions for.
        """
        return self.target_can_namespace(self, action, obj)

    def i_can_object(
        self, action: ObjectActions, obj: "AbstractNamespaceModel"
    ) -> bool:
        """Check if the current user can perform the given action on the given object.

        :param action (ObjectActions): The action to check permissions for.
        :param obj (AbstractNamespaceModel): The object to check permissions for.
        """
        return self.target_can_object(self, action, obj)

    def target_can(
        self,
        target: UserOrGroup,
        action: AnyAction,
        obj: Union["Namespace", "AbstractNamespaceModel"],
    ) -> bool:
        """Check if the target user can perform an action on an object or a namespace.

        :param target: The user or group to check permissions for.
        :param action (NamespaceAction or ObjectAction): The action to check permissions for.
        :param obj (Namespace or AbstractNamespaceModel): The object to check permissions for.
        """
        if isinstance(action, NamespaceActions):
            return self.target_can_namespace(action, obj, target)

        return self.target_can_object(action, obj, target)

    def target_can_namespace(
        self,
        target: UserOrGroup,
        action: NamespaceActions,
        obj: Namespace,
    ) -> bool:
        """Check if the current user can perform the given action on the given namespace.

        :param target: The user or group to check permissions for.
        :param action (NamespaceActions): The action to check permissions for.
        :param obj (Namespace): The namespace object to check permissions for.
        """
        return has_permission(NamespacePermission, obj, target, action, self)

    def target_can_object(
        self,
        target: UserOrGroup,
        action: ObjectActions,
        obj: "AbstractNamespaceModel",
    ) -> bool:
        """Check if the target can perform the given action on the given object.

        :param target: The user or group to check permissions for.
        :param action (ObjectActions): The action to check permissions for.
        :param obj (AbstractNamespaceModel): The object to check permissions for.
        """
        return has_permission(ObjectPermission, obj.namespace, target, action, self)


class NamespaceUser(PermissionMixin, User):
    """A user that can have permissions."""

    class Meta:
        """Meta options for the NamespaceUser."""

        proxy = True


class AbstractNamespaceModel(models.Model):
    """An abstract model for objects that use namespaces."""

    namespace: Namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)

    class Meta:
        """Meta options for the AbstractNamespaceModel."""

        abstract = True

    def __str__(self) -> str:
        """Return a string indicating which namespace the object belongs to."""
        return f"Object in {self.namespace.name} namespace"

    def user_can(
        self, user: AbstractUser, action: ObjectActions, requestor: AbstractUser
    ) -> bool:
        """Check if the given user can perform the given action on the current object.

        :param user: The user to check permissions for.
        :param action: The action to check permissions for.
        """
        return has_permission(ObjectPermission, self.namespace, user, action, requestor)
