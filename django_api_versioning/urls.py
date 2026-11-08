from django.urls import URLPattern

from .registry import registry

urlpatterns: list[URLPattern] = registry.urlpatterns
