"""Test usage of the django_namespace_permissions app."""
from http import HTTPStatus
from typing import Dict, Union

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from django_namespace_permissions.constants import NamespaceActions, ObjectActions
from django_namespace_permissions.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
    has_permission,
)
from testproject.models import NamespacedExample


class NamespacePermissionTestBase(TestCase):
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
        model = NamespacePermission if isinstance(action, NamespaceActions) else ObjectPermission
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

        self.superuser = NamespaceUser.objects.create_superuser(username="superuser")
        self.superuser.is_superuser = True
        self.superuser.save()

        self.group1 = Group.objects.create(name="test_group1")
        self.group2 = Group.objects.create(name="test_group2")

        # Create test objects
        self.test1 = NamespacedExample.objects.create(name="test1", namespace=self.namespace1)
        self.test2 = NamespacedExample.objects.create(name="test2", namespace=self.namespace2)

        self.client = Client()
        self.client.force_login(self.superuser)

    def tearDown(self) -> None:
        """Tear down the test case."""
        self.namespace1.delete()
        self.namespace2.delete()
        self.user1.delete()
        self.user2.delete()
        self.superuser.delete()
        self.group1.delete()
        self.group2.delete()
        self.test1.delete()
        self.test2.delete()
        return super().tearDown()

    def test_get_namespace_failure(self):
        """Test getting a namespace."""
        url = reverse(
            "namespace-list-detail",
            kwargs={
                "id": 999999,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_namespace_ok(self):
        """Test getting a namespace."""
        for key in ["id", "name"]:
            url = reverse(
                "namespace-list-detail",
                kwargs={
                    "id": getattr(self.namespace1, key),
                },
            )
            self.namespace1.grant_namespace_permission(
                self.user1, NamespaceActions.READ, self.superuser
            )
            self.namespace1.grant_namespace_permission(
                self.group1, NamespaceActions.DELEGATE, self.superuser
            )

            self.namespace1.grant_object_permission(self.user2, ObjectActions.READ, self.superuser)
            self.user1.groups.add(self.group1)

            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            data = response.json()
            self.assertEqual(
                data["namespace_permissions"]["users"][str(self.user1.id)], ["has_read"]
            )
            self.assertEqual(
                data["namespace_permissions"]["groups"][str(self.group1.id)],
                ["has_delegate"],
            )
            self.assertEqual(data["object_permissions"]["users"][str(self.user2.id)], ["has_read"])

            # Check that the group is directly OK.
            self.assertTrue(
                has_permission(
                    NamespacePermission,
                    self.namespace1,
                    self.group1,
                    NamespaceActions.DELEGATE,
                    self.superuser,
                )
            )

    def test_granting_permission_with_wrong_data_gives_400(self):
        """Test that granting permissions with wrong data gives 400."""
        response = self.client.post(
            reverse(
                "namespace-grant-grant-permission",
                kwargs={
                    "namespace": self.namespace1.id,
                    "object_type": "namespace",
                    "entity": "user",
                    "id": self.user1.id,
                },
            ),
            {"nosuchkey": "false"},
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_granting_permissions(self):
        """Test granting permissions."""
        url = reverse(
            "namespace-grant-grant-permission",
            kwargs={
                "namespace": self.namespace1.id,
                "object_type": "namespace",
                "entity": "user",
                "id": self.user1.id,
            },
        )

        response = self.client.post(url, {"actions": ["has_read", "has_delete"]})

        self.assertEqual(response.status_code, HTTPStatus.OK)

        action_permission_map = {
            NamespaceActions.READ: True,
            NamespaceActions.DELETE: True,
            NamespaceActions.UPDATE: False,
            NamespaceActions.DELEGATE: False,
            NamespaceActions.CREATE: False,
        }

        self.assert_permission_map(action_permission_map)

    def test_unauthorized_listing_namespaces(self):
        """Test trying to list namespaces without having logged in."""
        client = Client()
        url = reverse("namespace-list-list")
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_listing_permissions(self):
        """Test listing permissions for a user on a namespace."""
        url = reverse(
            "namespace-grant-list-permissions",
            kwargs={
                "namespace": self.namespace1.id,
                "object_type": "namespace",
                "entity": "user",
                "id": self.user1.id,
            },
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Grant permissions, one directly, one via a group
        self.namespace1.grant_namespace_permission(
            self.user1, NamespaceActions.READ, self.superuser
        )
        self.user1.groups.add(self.group1)
        self.namespace1.grant_namespace_permission(
            self.group1, NamespaceActions.DELEGATE, self.superuser
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Ensure the response contains the granted permissions.
        # Depending on how your serializers are set up, adjust the following line:
        self.assertContains(response, "has_read")
        self.assertContains(response, "has_delegate")

    def test_modifying_permissions(self):
        """Test modifying permissions."""
        url = reverse(
            "namespace-grant-modify-permissions",
            kwargs={
                "namespace": self.namespace1.id,
                "object_type": "namespace",
                "entity": "user",
                "id": self.user1.id,
            },
        )

        # Try patching a non-existing permission
        response = self.client.patch(
            url, {"actions": ["has_read"]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Okay, create it, then try patch again.
        self.namespace1.grant_namespace_permission(
            self.user1, NamespaceActions.UPDATE, self.superuser
        )
        response = self.client.patch(
            url,
            {"actions": ["has_update", "has_delegate"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        action_permission_map = {
            NamespaceActions.READ: False,
            NamespaceActions.DELETE: False,
            NamespaceActions.UPDATE: True,
            NamespaceActions.DELEGATE: True,
            NamespaceActions.CREATE: False,
        }
        self.assert_permission_map(action_permission_map)

        # Also try patching with wrong data.
        response = self.client.patch(
            url,
            {"zooty": ["has_update", "has_delegate"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_revoking_permissions(self):
        """Test revoking permissions."""
        url = reverse(
            "namespace-grant-revoke-permissions",
            kwargs={
                "namespace": self.namespace1.id,
                "object_type": "namespace",
                "entity": "user",
                "id": self.user1.id,
            },
        )

        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
