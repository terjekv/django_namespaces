"""Views for the test project."""
from django.views.generic import ListView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from django_namespaces.mixins import NamespacePermissionMixin

from .models import NamespacedExample
from .serializers import NamespacedExampleSerializer


class TestView(ListView):
    """A django view, without custom permissions."""

    queryset = NamespacedExample.objects.all()
    model = NamespacedExample
    template_name = "test_view.html"


class TestListViewDRF(NamespacePermissionMixin, ListCreateAPIView):  # type: ignore
    """A DRF list view."""

    queryset = NamespacedExample.objects.all()
    serializer_class = NamespacedExampleSerializer


class TestDetailViewDRF(NamespacePermissionMixin, RetrieveUpdateDestroyAPIView):  # type: ignore
    """A DRF detail view."""

    serializer_class = NamespacedExampleSerializer
    queryset = NamespacedExample.objects.all()
