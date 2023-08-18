"""Serializers for the django_namespace_permissions app."""

from typing import Any, Dict, Union

from rest_framework import serializers

from .constants import NamespaceActions, ObjectActions
from .models import Namespace, NamespacePermission, ObjectPermission


class ActionEnumField(serializers.ChoiceField):
    """Serializer field for validating actions."""

    def __init__(self, *args: Any, object_type: str = None, **kwargs: Any) -> None:
        """Initialize the field."""
        self.object_type = object_type
        if self.object_type == "namespace":
            choices = [action.value for action in NamespaceActions]
        elif self.object_type == "objects":
            choices = [action.value for action in ObjectActions]
        else:
            raise serializers.ValidationError("Invalid object_type provided.")

        super().__init__(*args, choices=choices, **kwargs)

    def to_representation(self, value: Union[NamespaceActions, ObjectActions]) -> str:
        """Convert the enum to a string."""
        return value.value

    def to_internal_value(self, data: Any) -> Union[NamespaceActions, ObjectActions]:
        """Convert the string to an enum."""
        if self.object_type == "namespace":
            enum_class = NamespaceActions
        elif self.object_type == "objects":
            enum_class = ObjectActions
        else:
            raise serializers.ValidationError("Invalid object_type provided.")

        try:
            return enum_class(data)
        except ValueError as exc:
            valid_choices = [e.value for e in enum_class]
            raise serializers.ValidationError(
                f"'{data}' is not a valid action. Valid choices are {valid_choices}."
            ) from exc


class NamespaceSerializer(serializers.ModelSerializer):
    """Serializer for Namespace model.

    Also includes the namespace permissions and object permissions.
    """

    namespace_permissions = serializers.SerializerMethodField()
    object_permissions = serializers.SerializerMethodField()

    class Meta:
        """Meta class for NamespaceSerializer."""

        model = Namespace
        fields = [
            "id",
            "name",
            "description",
            "namespace_permissions",
            "object_permissions",
        ]

    def get_namespace_permissions(self, obj: Namespace) -> Dict[str, Any]:
        """Get the namespace permissions representation."""
        return obj.get_namespace_permissions_representation()

    def get_object_permissions(self, obj: Namespace) -> Dict[str, Any]:
        """Get the object permissions representation."""
        return obj.get_object_permissions_representation()


class ObjectPermissionSerializer(serializers.ModelSerializer):
    """Serializer for ObjectPermission model."""

    class Meta:
        """Meta class for ObjectPermissionSerializer."""

        model = ObjectPermission
        fields = "__all__"


class NamespacePermissionSerializer(serializers.ModelSerializer):
    """Serializer for NamespacePermission model."""

    class Meta:
        """Meta class for NamespacePermissionSerializer."""

        model = NamespacePermission
        fields = "__all__"


class GrantPermissionSerializer(serializers.Serializer):
    """Serializer to validate actions for granting permissions."""

    def __init__(self, *args: Any, object_type: str = None, **kwargs: Any):
        """Initialize the serializer."""
        self.object_type = object_type

        # Modify the child of the ListField to be our custom field
        self.fields["actions"] = serializers.ListField(
            child=ActionEnumField(object_type=self.object_type), required=True
        )

        super().__init__(*args, **kwargs)
