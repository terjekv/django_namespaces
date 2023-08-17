# Installation

## Add the app to your project

`poetry add git+https://github.com/terjekv/django_namespaces.git#main`

## Add the app to your settings

    ```python
    INSTALLED_APPS = [
        # ...
        "django_namespaces",
    ]
    ```

## Add namespaces to models you want to be namespaced

    ```python
    from django_namespaces.models import AbstractNamespaceModel

    class NamespacedExample(AbstractNamespaceModel):
        ...
    ```

!!! note
    This adds a `namespace` field to your model, which is a foreign key to the `Namespace` model. This is the namespace that the object belongs to.

## Add namespace mixin to your views

    ```python
    from .models import NamespacedExample


    class TestListViewDRF(NamespacePermissionMixin, ListCreateAPIView):
        """A DRF list view."""

        queryset = NamespacedExample.objects.all()
        ...


    class TestDetailViewDRF(NamespacePermissionMixin, RetrieveUpdateDestroyAPIView): 
        """A DRF detail view."""

        queryset = NamespacedExample.objects.all()
        ...
    ```

## Add the namespace endpoints to your urls.py

A set of endpoints are provided to work with namespaces. To use these endpoints, you need to add the following to your `urls.py`:

    ```python
    from django_namespaces import urls as django_namespaces_urls

    urlpatterns = [
        # ...
        path("namespaces/", include(django_namespaces_urls)),
    ]
    ```
