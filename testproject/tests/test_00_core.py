"""Tests for the core functionality of django_namespace_permissions."""

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from django_namespace_permissions.constants import NamespaceActions, ObjectActions
from django_namespace_permissions.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
)
from testproject.models import NamespacedExample


class DjangoNamespacesCoreTestCase(TestCase):
    """Test core functionality for django_namespace_permissions."""

    def setUp(self):
        """Set up the test case."""
        self.namespace1 = Namespace.objects.create(name="test_namespace1")
        self.namespace2 = Namespace.objects.create(name="test_namespace2")

        self.user1 = NamespaceUser.objects.create_user(username="test_user1")
        self.user2 = NamespaceUser.objects.create_user(username="test_user2")

        self.superuser = NamespaceUser.objects.create_superuser(username="superuser")
        self.superuser.is_superuser = True
        self.superuser.save()

        self.group1 = Group.objects.create(name="test_group1")
        self.group2 = Group.objects.create(name="test_group2")

        # Create test objects
        self.test1 = NamespacedExample.objects.create(name="test1", namespace=self.namespace1)
        self.test2 = NamespacedExample.objects.create(name="test2", namespace=self.namespace2)

    def test_grant_user1_read_permission_to_namespace_namespace1(self):
        """Test granting a user read permission to a namespace."""
        self.namespace1.grant_namespace_permission(
            self.user1, NamespaceActions.READ, self.superuser
        )

        self.assertTrue(
            NamespacePermission.objects.filter(
                namespace=self.namespace1, user=self.user1, has_read=True
            ).exists()
        )

        self.assertTrue(
            self.superuser.target_can_namespace(self.user1, NamespaceActions.READ, self.namespace1)
        )

        self.assertTrue(self.user1.i_can_namespace(NamespaceActions.READ, self.namespace1))

        self.assertTrue(self.user1.i_can(NamespaceActions.READ, self.namespace1))

        # We still only have namespace access, no object access.
        with self.assertRaises(PermissionDenied):
            self.user1.i_can_object(ObjectActions.READ, self.test1)

        with self.assertRaises(PermissionDenied):
            self.user1.i_can(ObjectActions.READ, self.test1)

    def test_grant_user1_read_permission_to_object_test1(self):
        """Test granting a user read permission to an object."""
        self.namespace1.grant_object_permission(self.user1, ObjectActions.READ, self.superuser)

        self.assertTrue(
            ObjectPermission.objects.filter(
                namespace=self.namespace1, user=self.user1, has_read=True
            ).exists()
        )

        self.assertTrue(
            self.superuser.target_can_object(self.user1, ObjectActions.READ, self.test1)
        )

        # Here user1 is given access to the object (ObjectActions.READ on test1) but the
        # user is not given access to the namespace itself.
        self.assertTrue(self.user1.i_can_object(ObjectActions.READ, self.test1))
        with self.assertRaises(PermissionDenied):
            self.user1.i_can_namespace(NamespaceActions.READ, self.test1.namespace)
