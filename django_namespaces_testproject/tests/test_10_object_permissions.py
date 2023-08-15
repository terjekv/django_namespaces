"""Tests for object permissions."""
from http import HTTPStatus
from typing import Dict, Union

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from django_namespaces.constants import NamespaceActions, ObjectActions
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
    has_permission,
)
from django_namespaces_testproject.models import NamespacedExample


class ObjectPermissionTestBase(TestCase):
    """Base class for testing permissions."""

    def assert_permission_map(
        self, permission_map: Dict[Union[NamespaceActions, ObjectActions], bool]
    ):
        """Assert a map of permissions."""
        for action, expected_result in permission_map.items():
            self.assert_permission(action, expected_result)

    def assert_permission(
        self, action: Union[NamespaceActions, ObjectActions], expected_result: bool
    ):
        """Assert a single permission."""
        model = (
            NamespacePermission
            if isinstance(action, NamespaceActions)
            else ObjectPermission
        )
        result = has_permission(
            model,
            self.namespace1,
            self.user1,
            action,
            self.superuser,
        )
        self.assertEqual(result, expected_result, f"Action {action} failed")

    def setUp(self):
        """Set up the test case."""
        self.namespace1 = Namespace.objects.create(name="test_namespace1")
        self.namespace2 = Namespace.objects.create(name="test_namespace2")

        self.user1 = NamespaceUser.objects.create_user(username="test_user1")
        self.user2 = NamespaceUser.objects.create_user(username="test_user2")

        self.superuser = NamespaceUser.objects.create_superuser(
            username="superuser", is_superuser=True
        )

        self.group1 = Group.objects.create(name="test_group1")
        self.group2 = Group.objects.create(name="test_group2")

        self.user1.groups.add(self.group1)

        self.objects = {}
        # Create test objects
        for i in range(1, 9):
            if i % 2 == 0:
                namespace = self.namespace2
            else:
                namespace = self.namespace1

            name = f"test{i:02}"
            self.objects[name] = NamespacedExample.objects.create(
                name=name, namespace=namespace
            )

        self.superuserclient = Client()
        self.superuserclient.force_login(self.superuser)

        self.user1client = Client()
        self.user1client.force_login(self.user1)

        self.user2client = Client()
        self.user2client.force_login(self.user2)

        self.unauthedclient = Client()

    def tearDown(self) -> None:
        """Tear down the test case."""
        self.namespace1.delete()
        self.namespace2.delete()
        self.user1.delete()
        self.user2.delete()
        self.superuser.delete()
        self.group1.delete()
        self.group2.delete()
        return super().tearDown()

    def test_superuser_sees_everything(self):
        """Test that the superuser sees all objects."""
        for name, obj in self.objects.items():
            response = self.superuserclient.get(
                reverse("test-view-detail", args=[obj.pk])
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(response.json()["name"], name)

        response = self.superuserclient.get(reverse("test-view-list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()), len(self.objects))

    def test_users_see_nothing_without_permissions(self):
        """Test that the default users see nothing without permissions."""
        for client in self.user1client, self.user2client:
            for _, obj in self.objects.items():
                response = client.get(reverse("test-view-detail", args=[obj.pk]))
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

            response = self.user1client.get(reverse("test-view-list"))
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(len(response.json()), 0)

    def test_users_see_nothing_without_auth(self):
        """Test that non-authed users see nothing without permissions."""
        client = self.unauthedclient
        for _, obj in self.objects.items():
            response = client.get(reverse("test-view-detail", args=[obj.pk]))
            self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        response = client.get(reverse("test-view-list"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_users_see_objects_with_permissions(self):
        """Test that user1 sees objects in namespace1 when given permission."""
        self.namespace1.grant_permission(
            ObjectPermission, self.user1, ObjectActions.READ, self.superuser
        )
        response = self.user1client.get(reverse("test-view-list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()), 4)

        response = self.user1client.get(
            reverse("test-view-detail", args=[self.objects["test01"].pk])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["name"], "test01")

    def test_users_can_create_objects_with_permissions(self):
        """Test that user1 can create objects in namespace1 when given permission."""
        with self.assertRaises(NamespacedExample.DoesNotExist):
            NamespacedExample.objects.get(name="test09")

        self.namespace1.grant_permission(
            ObjectPermission, self.user1, ObjectActions.CREATE, self.superuser
        )
        response = self.user1client.post(
            reverse("test-view-list"),
            {"name": "test09", "namespace": self.namespace1.pk},
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json()["name"], "test09")

    def test_only_read_gives_read_access(self):
        """Test that only READ gives read access."""
        for permission in [
            ObjectActions.CREATE,
            ObjectActions.UPDATE,
            ObjectActions.DELETE,
        ]:
            self.namespace1.grant_permission(
                ObjectPermission, self.user1, permission, self.superuser
            )
            response = self.user1client.get(reverse("test-view-list"))
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(len(response.json()), 0)

            response = self.user1client.get(
                reverse("test-view-detail", args=[self.objects["test01"].pk])
            )
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

            self.namespace1.revoke_permission(
                ObjectPermission, self.user1, permission, self.superuser
            )

        self.namespace1.grant_object_permission(
            self.user1, ObjectActions.READ, self.superuser
        )

        response = self.user1client.get(reverse("test-view-list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()), 4)

    def test_read_through_group(self):
        """Test that users can read through groups."""
        self.namespace1.grant_object_permission(
            self.group1, ObjectActions.READ, self.superuser
        )

        response = self.user1client.get(reverse("test-view-list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()), 4)

        response = self.user1client.get(
            reverse("test-view-detail", args=[self.objects["test01"].pk])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["name"], "test01")
