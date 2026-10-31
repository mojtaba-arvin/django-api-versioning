import pytest
from django.urls import clear_url_caches

from django_api_versioning.registry import registry


@pytest.fixture(autouse=True)
def _reset_registry():
    """Clear the global registry before and after every test."""
    registry.urlpatterns.clear()
    clear_url_caches()
    yield
    registry.urlpatterns.clear()
    clear_url_caches()
