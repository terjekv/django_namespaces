""""Admin interface for the django_namespaces app."""

# Register your models here.
from django.contrib import admin

from .models import Namespace

admin.site.register(Namespace)
