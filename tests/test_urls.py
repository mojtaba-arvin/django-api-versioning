import pytest
from django.urls import URLPattern, clear_url_caches, resolve

from django_api_versioning.registry import registry


@pytest.fixture(autouse=True)
def clear_registered_routes():
    """Reset the registry and Django's URL resolver caches between tests."""
    registry.urlpatterns.clear()
    clear_url_caches()
    yield
    registry.urlpatterns.clear()
    clear_url_caches()


@pytest.fixture
def register_routes():
    from django_api_versioning.decorators import endpoint

    # Registering the accounts route with the endpoint decorator
    @endpoint("accounts", view_name="accounts_view")
    def test_accounts():
        return None

    yield


def test_urlpatterns_is_shared_registry_list():
    """The package's ``urlpatterns`` must be the same list object as the registry's."""
    from django_api_versioning.urls import urlpatterns

    assert urlpatterns is registry.urlpatterns


def test_urlpatterns_type():
    """Test to check that urlpatterns is a list of URLPattern."""
    from django_api_versioning.urls import urlpatterns

    assert isinstance(urlpatterns, list), "urlpatterns should be a list."
    assert all(
        isinstance(pattern, URLPattern) for pattern in urlpatterns
    ), "All elements in urlpatterns should be of type URLPattern."


def test_registry_urlpatterns(register_routes):
    """Test to check that the 'accounts' route resolves correctly."""
    match = resolve("/accounts")
    assert (
        match.view_name == "accounts_view"
    ), f"Expected 'accounts_view', but got {match.view_name}"
