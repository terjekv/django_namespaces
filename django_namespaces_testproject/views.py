"""Views for the test project."""
from django.views.generic import ListView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from django_namespaces.mixins import NamespacePermissionMixin
from django_namespaces.permissions import NamespacePermissions

from .models import NamespacedExample
from .serializers import NamespacedExampleSerializer


class TestView(NamespacePermissionMixin, ListView):
    """A standard django view."""

    queryset = NamespacedExample.objects.all()
    model = NamespacedExample
    template_name = "test_view.html"


class TestListViewDRF(NamespacePermissionMixin, ListCreateAPIView):  # type: ignore
    """A DRF list view."""

    queryset = NamespacedExample.objects.all()
    serializer_class = NamespacedExampleSerializer

    permission_classes = [NamespacePermissions]


class TestDetailViewDRF(NamespacePermissionMixin, RetrieveUpdateDestroyAPIView):  # type: ignore
    """A DRF detail view."""

    serializer_class = NamespacedExampleSerializer
    queryset = NamespacedExample.objects.all()

    # Specify permission_classes as a list
    permission_classes = [NamespacePermissions]
