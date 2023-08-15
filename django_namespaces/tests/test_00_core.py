"""Tests for the core functionality of django_namespaces."""


from unittest.mock import Mock

from django.db.models import Q
from django.test import TestCase
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.views import APIView

from django_namespaces.constants import (
    HTTP_METHOD_TO_OBJECTACTION_MAP,
    NamespaceActions,
)
from django_namespaces.mixins import NamespacePermissionMixin
from django_namespaces.models import (
    NamespacePermission,
    NamespaceUser,
    grant_permission,
    has_permission,
    revoke_permission,
)


class MockModel:
    """An empty mock model, for queryset data."""

    pass


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


class DjangoNamespacesModelTestCase(TestCase):
    """Test core functionality of model and their functions."""

    def test_permission_function_exceptions(self):
        """Test that has_permission handles input correctly."""
        user = NamespaceUser.objects.create_user("testuser")

        self.assertFalse(has_permission(NamespacePermission, "", "", "", None))

        with self.assertRaises(ValueError):
            self.assertFalse(grant_permission(NamespacePermission, "", "", "", user))

        with self.assertRaises(ValueError):
            self.assertFalse(revoke_permission(NamespacePermission, "", "", "", user))

        with self.assertRaises(ValueError):
            has_permission(NamespacePermission, "", "", NamespaceActions.READ, None)

        with self.assertRaises(ValueError):
            grant_permission(NamespacePermission, "", "", NamespaceActions.READ, user)

        with self.assertRaises(ValueError):
            revoke_permission(NamespacePermission, "", "", NamespaceActions.READ, user)

        user.delete()
