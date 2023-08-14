"""Serializers for the test app."""
from rest_framework import serializers

from .models import NamespacedExample


class NamespacedExampleSerializer(serializers.ModelSerializer):
    """Serialize a Test object."""

    class Meta:
        """How to serialize the object."""

        model = NamespacedExample
        fields = "__all__"
