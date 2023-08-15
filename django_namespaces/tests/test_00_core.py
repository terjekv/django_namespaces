"""Tests for the core functionality of django_namespaces."""


from unittest.mock import Mock

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.test import TestCase
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.views import APIView

from django_namespaces.constants import (
    HTTP_METHOD_TO_OBJECTACTION_MAP,
    NamespaceActions,
    ObjectActions,
)
from django_namespaces.mixins import NamespacePermissionMixin
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
    grant_permission,
    has_permission,
    revoke_permission,
)
from django_namespaces.serializers import ActionEnumField
from django_namespaces.views import get_from_id_or_name


class MockModel:
    """An empty mock model, for queryset data."""

    pass


class DjangoNamespacesViewsTestCase(TestCase):
    """Test core functionality of the views."""

    def test_get_from_id_or_name(self):
        """Test that we get the correct objects when using get_from_id_or_name."""
        ns = Namespace.objects.create(name="namespacename")

        self.assertEqual(get_from_id_or_name(Namespace, ns.id), ns)
        self.assertEqual(get_from_id_or_name(Namespace, str(ns.id)), ns)
        self.assertEqual(get_from_id_or_name(Namespace, ns.name), ns)

        with self.assertRaises(NotFound):
            get_from_id_or_name(Namespace, "wrong")


class DjangoNamespacesMixinTestCase(TestCase):
    """Test core functionality of the mixin."""

    def test_http_method_support(self):
        """Test that the mixin supports the expected HTTP methods."""
        mixin = NamespacePermissionMixin()

        # We need to mock a request object and a view object.
        mock_request = Mock()
        mock_view = Mock(spec=APIView)  # Mocking an APIView object

        # Set the mock view's queryset's model to our mock model
        mock_view.queryset = Mock()
        mock_view.queryset.model = MockModel

        # We pass a request object with the HTTP methods (the keys) in
        # HTTP_METHOD_TO_OBJECTACTION_MAP and that should return an empty Q object.
        for http_method in HTTP_METHOD_TO_OBJECTACTION_MAP.keys():
            mock_request.method = http_method
            result_q_object = mixin.get_permission_filter(mock_request, mock_view)
            # Asserting that the result is an empty Q object.
            self.assertEqual(result_q_object, Q())

        # If we pass anything else, it should raise a MethodNotAllowed exception.
        mock_request.method = "RANDOM_METHOD"
        with self.assertRaises(MethodNotAllowed):
            mixin.get_permission_filter(mock_request, mock_view)


class DjangoPermissionStrTestCase(TestCase):
    """Test that stringifying permissions returns what we expect."""

    def setUp(self):
        """Set up the test case."""
        self.user = NamespaceUser.objects.create(username="username")
        self.group = Group.objects.create(name="groupname")
        self.namespace = Namespace.objects.create(name="namespacename")

    def test_namespace_permission_str(self):
        """Test that the string representation of a NamespacePermission is correct."""
        permission = NamespacePermission.objects.create(
            namespace=self.namespace,
            user=self.user,
            has_read=True,
        )

        userstring = f"user '{self.user.username}' ({self.user.id})"
        groupstring = f"group '{self.group.name}' ({self.group.id})"
        nsstring = f"for '{self.namespace.name}' ({self.namespace.id})"
        self.assertEqual(
            str(permission),
            f"NamespacePermissions for the {userstring} for {nsstring}",
        )
        permission.delete()

        permission = NamespacePermission.objects.create(
            namespace=self.namespace,
            group=self.group,
            has_read=True,
        )

        self.assertEqual(
            str(permission),
            f"NamespacePermissions for the {groupstring} for {nsstring}",
        )


class DjangoNamespacesSerializersTestCase(TestCase):
    """Test the serializers."""

    def test_action_enum_field(self):
        """Test the ActionEnumField."""
        with self.assertRaises(ValidationError):
            ActionEnumField(object_type="wrong")

        aef = ActionEnumField(object_type="objects")
        self.assertEqual(aef.to_representation(ObjectActions.READ), "has_read")
        self.assertEqual(aef.to_representation(ObjectActions.CREATE), "has_create")
        self.assertEqual(aef.to_internal_value("has_read"), ObjectActions.READ)

        with self.assertRaises(ValidationError):
            ActionEnumField(object_type="wrong")

        with self.assertRaises(ValidationError):
            self.assertEqual(aef.to_internal_value("wrong"), ObjectActions.READ)

        with self.assertRaises(ValidationError):
            aef.object_type = "wrong"
            self.assertEqual(aef.to_internal_value("has_read"), ObjectActions.READ)


class DjangoNamespacesModelTestCase(TestCase):
    """Test core functionality of model and their functions."""

    def setUp(self) -> None:
        """Set up the test case."""
        self.user = NamespaceUser.objects.create(username="username")
        self.namespace = Namespace.objects.create(name="namespacename")
        self.su = NamespaceUser.objects.create(username="su", is_superuser=True)
        self.group = Group.objects.create(name="groupname")
        return super().setUp()

    def test_permission_user_or_group_validation(self):
        """Test that we can't have both a group and a user in permisson object."""
        with self.assertRaises(DjangoValidationError):
            NamespacePermission.objects.create(
                namespace=self.namespace,
                user=self.user,
                group=self.group,
                has_read=True,
            )

        with self.assertRaises(DjangoValidationError):
            NamespacePermission.objects.create(
                namespace=self.namespace,
                has_read=True,
            )

    def test_permission_function_input(self):
        """Test that has_permission handles input correctly."""
        self.assertFalse(has_permission(NamespacePermission, "", "", "", None))

    def test_revoking_permissions(self):
        """Test that revoking a permission works."""
        cls = NamespacePermission
        rargs = (cls, self.namespace, self.user, NamespaceActions.READ, self.su)
        dargs = (cls, self.namespace, self.user, NamespaceActions.DELEGATE, self.su)

        # Revoke specific permission. We give DELETE and READ permissions,
        # revoke READ, and check that DELETE is still there.
        grant_permission(*dargs)
        grant_permission(*rargs)
        self.assertTrue(has_permission(*rargs))
        self.assertTrue(has_permission(*dargs))
        revoke_permission(*rargs)
        self.assertFalse(has_permission(*rargs))
        self.assertTrue(has_permission(*dargs))

        # Revoke all permissions (passing None as action).
        # We regrant READ to see that both are gone.
        grant_permission(*rargs)
        self.assertTrue(has_permission(*rargs))
        revoke_permission(NamespacePermission, self.namespace, self.user, None, self.su)
        self.assertFalse(has_permission(*rargs))
        self.assertFalse(has_permission(*dargs))

        # Test that we can revoke permissions via the namespace.
        grant_permission(*rargs)
        self.assertTrue(has_permission(*rargs))
        self.namespace.revoke_namespace_permission(
            self.user, NamespaceActions.READ, self.su
        )
        self.assertFalse(has_permission(*rargs))

        cls = ObjectPermission
        rargs = (cls, self.namespace, self.user, ObjectActions.READ, self.su)
        grant_permission(*rargs)
        self.assertTrue(has_permission(*rargs))
        self.namespace.revoke_object_permission(self.user, ObjectActions.READ, self.su)
        self.assertFalse(has_permission(*rargs))
