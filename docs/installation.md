# Installation

## Add the app to your project

`poetry add git+https://github.com/terjekv/django_namespace_permissions.git#main`

## Add the app to your settings

```python
INSTALLED_APPS = [
    # ...
    "django_namespace_permissions",
]
```

## Add namespaces to models you want to be namespaced

```python
from django_namespace_permissions.models import AbstractNamespaceModel

class NamespacedExample(AbstractNamespaceModel):
    ...
```

This adds a `namespace` field to your model, which is a foreign key to the `Namespace` model. This is the namespace that the object belongs to.

!!! warning
    Deleting a namespace deletes all objects within the namespace. Once you have added a namespace to a model, you cannot remove it without deleting all objects within the namespace.

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

## Add the namespace endpoints to your project

A set of endpoints are provided to work with namespaces. To use these endpoints, you need to add the following to your `urls.py`:

```python
from django_namespace_permissions import urls as django_namespace_permissions_urls

urlpatterns = [
    # ...
    path("namespaces/", include(django_namespace_permissions_urls)),
]
```
