"""URLs for the django_namespaces app."""


from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NamespaceGrantViewSet, NamespaceViewSet

router = DefaultRouter()
router.register(r"", NamespaceViewSet, basename="namespace-list")
router.register(
    r"(?P<namespace>[^/]+)/(?P<object_type>namespace|objects)/(?P<entity>user|group)/(?P<id>[^/]+)",
    NamespaceGrantViewSet,
    basename="namespace-grant",
)

urlpatterns = [
    path("", include(router.urls)),
]
