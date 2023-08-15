"""Tests for object permissions."""
from http import HTTPStatus

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from django_namespaces.constants import NamespaceActions, ObjectActions
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
)
from django_namespaces_testproject.models import NamespacedExample


class ObjectPermissionTestBase(TestCase):
    """Base class for testing permissions."""

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

        response = client.get(reverse("namespace-list-list"))
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

    def test_users_see_namespaces_with_permissions(self):
        """Test that user1 sees namespaces when given permission."""
        self.namespace1.grant_permission(
            NamespacePermission, self.user1, NamespaceActions.READ, self.superuser
        )
        response = self.user1client.get(reverse("namespace-list-list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()), 1)

        response = self.user1client.get(
            reverse("namespace-list-detail", args=[self.namespace1.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["name"], "test_namespace1")

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

    def test_users_cannot_create_namespaces(self):
        """Test that users cannot create namespaces."""
        url = reverse("namespace-list-list")
        response = self.user1client.post(url, {"name": "tmp_namespace"})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_superuser_can_create_and_delete_namespaces(self):
        """Test that superuser can create namespaces."""
        url = reverse("namespace-list-list")
        response = self.superuserclient.post(url, {"name": "tmp_namespace"})
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        ns = Namespace.objects.get(name="tmp_namespace")
        self.assertEqual(ns.name, response.json()["name"])

        response = self.superuserclient.delete(
            reverse("namespace-list-detail", args=[response.json()["id"]])
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        with self.assertRaises(Namespace.DoesNotExist):
            Namespace.objects.get(name="tmp_namespace")

    def test_users_delete_namespaces_same_permission_source(self):
        """Test that users can get permissions to delete namespaces.

        This tests that the user can delete the namespace if both read and delete
        permissions are granted to the same source (the user themselves).
        """
        tmpns = Namespace.objects.create(name="tmp_namespace")
        tmpns.grant_permission(
            NamespacePermission, self.user1, NamespaceActions.DELETE, self.superuser
        )
        tmpns.grant_permission(
            NamespacePermission, self.user1, NamespaceActions.READ, self.superuser
        )
        response = self.user1client.delete(
            reverse("namespace-list-detail", args=[tmpns.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        with self.assertRaises(Namespace.DoesNotExist):
            Namespace.objects.get(id=tmpns.id)

    def test_users_delete_namespaces_different_permission_source(self):
        """Test that users can get permissions to delete namespaces.

        This tests that the user can delete the namespace if the read and delete
        permissions are granted through different sources.

        One group allows for reading, another for deleting, the user is a member
        of both.
        """
        tmpns = Namespace.objects.create(name="tmp_namespace")
        readgroup = Group.objects.create(name="readgroup")
        deletegroup = Group.objects.create(name="deletegroup")
        tmpns.grant_permission(
            NamespacePermission, deletegroup, NamespaceActions.DELETE, self.superuser
        )
        tmpns.grant_permission(
            NamespacePermission, readgroup, NamespaceActions.READ, self.superuser
        )

        self.user1.groups.add(readgroup)
        response = self.user1client.get(
            reverse("namespace-list-detail", args=[tmpns.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.user1client.delete(
            reverse("namespace-list-detail", args=[tmpns.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        self.user1.groups.add(deletegroup)
        response = self.user1client.delete(
            reverse("namespace-list-detail", args=[tmpns.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        with self.assertRaises(Namespace.DoesNotExist):
            Namespace.objects.get(id=tmpns.id)

        self.user1.groups.remove(deletegroup)
        self.user1.groups.remove(readgroup)
        deletegroup.delete()
        readgroup.delete()

    def test_superuser_can_update_namespace(self):
        """Test that superuser can update namespaces."""
        tmpns = Namespace.objects.create(name="tmp_namespace")
        url = reverse("namespace-list-detail", args=[tmpns.id])
        response = self.superuserclient.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        tmpns.refresh_from_db()
        self.assertEqual(response.json()["name"], tmpns.name)
        tmpns.delete()

    def test_user_needs_permissions_to_update_namespace(self):
        """Test that users need permissions to update namespaces."""
        tmpns = Namespace.objects.create(name="tmp_namespace")
        url = reverse("namespace-list-detail", args=[tmpns.id])
        response = self.user1client.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        tmpns.grant_permission(
            NamespacePermission, self.user1, NamespaceActions.UPDATE, self.superuser
        )
        response = self.user1client.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Need both read and update, so add read as well.
        tmpns.grant_permission(
            NamespacePermission, self.user1, NamespaceActions.READ, self.superuser
        )
        response = self.user1client.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        tmpns.refresh_from_db()
        self.assertEqual(response.json()["name"], tmpns.name)
        tmpns.delete()
