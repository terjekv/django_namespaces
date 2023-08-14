"""Tests for the core functionality of django_namespaces."""

from http import HTTPStatus
from typing import Dict, Union

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse, get_resolver

from django_namespaces.constants import NamespaceActions, ObjectActions
from django_namespaces.models import (
    Namespace,
    NamespacePermission,
    NamespaceUser,
    ObjectPermission,
    has_permission,
)


class DjangoNamespacesCoreTestCase(TestCase):
    """Test core functionality for django_namespaces."""
