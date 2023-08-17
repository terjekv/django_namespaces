from typing import Dict
from http import HTTPStatus
from django.http import HttpResponse
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django_namespaces.constants import NamespaceActions as NA
from django_namespaces.constants import ObjectActions as OA
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
)
from django_namespaces_testproject.models import NamespacedExample


TEST_VIEW_LIST_URL = reverse("test-view-list")
NAMESPACE_LIST_URL = reverse("namespace-list-list")


class ObjectPermissionTestBase(TestCase):
    """Base class for testing permissions."""

    def setUp(self):
        """Set up the test case."""
        self._initialize_namespace_users_groups()
        self._initialize_objects()
        self._initialize_clients()

    def tearDown(self):
        """Tear down the test case."""
        self.namespace1.delete()
        self.namespace2.delete()
        self.user1.delete()
        self.user2.delete()
        self.superuser.delete()
        self.group1.delete()
        self.group2.delete()

    def _initialize_namespace_users_groups(self):
        """Initialize namespaces, users and groups."""
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

    def _initialize_objects(self):
        """Initialize objects."""
        self.objects: Dict[str, NamespacedExample] = {}
        for i in range(1, 9):
            namespace = self.namespace2 if i % 2 == 0 else self.namespace1
            name = f"test{i:02}"
            self.objects[name] = NamespacedExample.objects.create(
                name=name, namespace=namespace
            )

    def _initialize_clients(self):
        """Initialize clients."""
        self.superuserclient = self._create_and_login(self.superuser)
        self.user1client = self._create_and_login(self.user1)
        self.user2client = self._create_and_login(self.user2)
        self.unauthedclient = Client()

    def _create_and_login(self, user: NamespaceUser) -> Client:
        """Create a client and log in the user."""
        client = Client()
        client.force_login(user)
        return client

    def _assert_list_response(
        self,
        client: Client,
        expected_status: int,
        expected_length: int = None,
        url: str = TEST_VIEW_LIST_URL,
    ) -> HttpResponse:
        """Assert the response of a list request."""
        response = client.get(url)
        self.assertEqual(response.status_code, expected_status)
        if expected_length is not None:
            self.assertEqual(len(response.json()), expected_length)
        return response

    def _assert_detail_response(
        self,
        client: Client,
        obj_pk: str,
        expected_status: int,
        expected_name: str = None,
        url: str = None,
    ) -> HttpResponse:
        """Assert the response of a detail request."""
        url = url or reverse("test-view-detail", args=[obj_pk])
        response = client.get(url)
        self.assertEqual(response.status_code, expected_status)
        if expected_name:
            self.assertEqual(response.json()["name"], expected_name)
        return response

    def _assert_post_response(
        self,
        client: Client,
        data: Dict[str, str],
        expected_status: int,
        url: str = TEST_VIEW_LIST_URL,
        name: str = None,
    ) -> HttpResponse:
        """Assert the response of a POST request."""
        response = client.post(url, data)
        self.assertEqual(response.status_code, expected_status)
        if name:
            self.assertEqual(response.json()["name"], name)
        return response

    def _assert_patch_response(
        self,
        client: Client,
        object_key: str,
        data: Dict[str, str],
        expected_status: int,
        url: str = None,
        name: str = None,
    ) -> HttpResponse:
        """Assert the response of a PATCH request."""
        url = url or reverse("test-view-detail", args=[self.objects[object_key].pk])
        response = client.patch(url, data, content_type="application/json")
        self.assertEqual(response.status_code, expected_status)
        if expected_status == HTTPStatus.OK and name:
            self.assertEqual(response.json()["name"], name)
            self.objects[object_key].refresh_from_db()
            self.assertEqual(self.objects[object_key].name, name)

        return response

    def test_superuser_sees_everything(self):
        """Test that the superuser sees all objects."""
        for name, obj in self.objects.items():
            self._assert_detail_response(
                self.superuserclient, obj.pk, HTTPStatus.OK, name
            )

        self._assert_list_response(
            self.superuserclient, HTTPStatus.OK, expected_length=8
        )

    def test_users_see_nothing_without_permissions(self):
        """Test that the default users see nothing without permissions."""
        for client in self.user1client, self.user2client:
            for _, obj in self.objects.items():
                self._assert_detail_response(client, obj.pk, HTTPStatus.NOT_FOUND)

            self._assert_list_response(client, HTTPStatus.OK, expected_length=0)

    def test_users_see_nothing_without_auth(self):
        """Test that non-authed users see nothing without permissions."""
        client = self.unauthedclient
        for _, obj in self.objects.items():
            self._assert_detail_response(client, obj.pk, HTTPStatus.FORBIDDEN)

        self._assert_list_response(client, HTTPStatus.FORBIDDEN)
        self._assert_list_response(client, HTTPStatus.FORBIDDEN, url=NAMESPACE_LIST_URL)

    def test_users_see_objects_with_permissions(self):
        """Test that user1 sees objects in namespace1 when given permission."""
        self.namespace1.grant_permission(
            ObjectPermission, self.user1, OA.READ, self.superuser
        )
        self._assert_list_response(self.user1client, HTTPStatus.OK, expected_length=4)
        self._assert_detail_response(
            self.user1client, self.objects["test01"].pk, 200, "test01"
        )

    def test_users_can_create_objects_with_permissions(self):
        """Test that user1 can create objects in namespace1 when given permission."""
        with self.assertRaises(NamespacedExample.DoesNotExist):
            NamespacedExample.objects.get(name="test09")

        self.namespace1.revoke_object_permission(self.user1, OA.CREATE, self.superuser)

        post_data = {"name": "test09", "namespace": self.namespace1.pk}
        self._assert_post_response(self.user1client, post_data, 403)
        self.namespace1.grant_permission(
            ObjectPermission, self.user1, OA.CREATE, self.superuser
        )
        self._assert_post_response(self.user1client, post_data, 201, name="test09")
        NamespacedExample.objects.get(name="test09").delete()

    def test_that_create_methods_arent_added_to_views_without_them(self):
        """Test that create methods aren't added to views without them."""
        response = self.superuserclient.post("/testdetail/1", {"name": "test09"})
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_users_can_patch_objects_with_permissions(self):
        """Test that user1 can patch objects in namespace1 when given permission."""
        self._assert_patch_response(
            self.user1client, "test01", {"name": "test01patch"}, HTTPStatus.NOT_FOUND
        )

        self.namespace1.grant_permission(
            ObjectPermission, self.user1, OA.UPDATE, self.superuser
        )

        self._assert_patch_response(
            self.user1client,
            "test01",
            {"name": "test01patch"},
            HTTPStatus.OK,
            name="test01patch",
        )

    def test_users_see_namespaces_with_permissions(self):
        """Test that user1 sees namespaces when given permission."""
        self.namespace1.grant_permission(
            NamespacePermission, self.user1, NA.READ, self.superuser
        )
        self._assert_list_response(
            self.user1client, HTTPStatus.OK, expected_length=1, url=NAMESPACE_LIST_URL
        )
        self._assert_detail_response(
            self.user1client,
            self.namespace1.pk,
            HTTPStatus.OK,
            "test_namespace1",
            url=reverse("namespace-list-detail", args=[self.namespace1.pk]),
        )

    def test_only_read_gives_read_access(self):
        """Test that only READ gives read access."""
        for permission in [
            OA.CREATE,
            OA.UPDATE,
            OA.DELETE,
        ]:
            self.namespace1.grant_permission(
                ObjectPermission, self.user1, permission, self.superuser
            )
            self._assert_list_response(
                self.user1client, HTTPStatus.OK, expected_length=0
            )
            self._assert_detail_response(
                self.user1client, "test01", HTTPStatus.NOT_FOUND
            )

            self.namespace1.revoke_permission(
                ObjectPermission, self.user1, permission, self.superuser
            )

        self.namespace1.grant_object_permission(self.user1, OA.READ, self.superuser)
        self._assert_list_response(self.user1client, HTTPStatus.OK, expected_length=4)

    def test_read_through_group(self):
        """Test that users can read through groups."""
        self.namespace1.grant_object_permission(self.group1, OA.READ, self.superuser)

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
        self._assert_post_response(
            self.user1client,
            {"name": "tmp_namespace"},
            HTTPStatus.FORBIDDEN,
            url=NAMESPACE_LIST_URL,
        )

    def test_superuser_can_create_and_delete_namespaces(self):
        """Test that superuser can create namespaces."""
        response = self._assert_post_response(
            self.superuserclient,
            {"name": "tmp_namespace"},
            HTTPStatus.CREATED,
            url=NAMESPACE_LIST_URL,
        )

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
            NamespacePermission, self.user1, NA.DELETE, self.superuser
        )
        tmpns.grant_permission(NamespacePermission, self.user1, NA.READ, self.superuser)
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
            NamespacePermission, deletegroup, NA.DELETE, self.superuser
        )
        tmpns.grant_permission(NamespacePermission, readgroup, NA.READ, self.superuser)

        self.user1.groups.add(readgroup)

        self._assert_detail_response(
            self.user1client,
            tmpns.pk,
            HTTPStatus.OK,
            "tmp_namespace",
            url=reverse("namespace-list-detail", args=[tmpns.pk]),
        )

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
            NamespacePermission, self.user1, NA.UPDATE, self.superuser
        )
        response = self.user1client.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Need both read and update, so add read as well.
        tmpns.grant_permission(NamespacePermission, self.user1, NA.READ, self.superuser)
        response = self.user1client.patch(
            url, {"name": "tmp_namespace2"}, content_type="application/json"
        )
        tmpns.refresh_from_db()
        self.assertEqual(response.json()["name"], tmpns.name)
        tmpns.delete()
