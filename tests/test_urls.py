import pytest
from django.urls import URLPattern, resolve


@pytest.fixture(scope="module", autouse=True)
def clear_urlpatterns():
    """Ensure urlpatterns is cleared before each test."""
    from django_api_versioning.urls import urlpatterns
    urlpatterns.clear()  # Clear any existing patterns
    yield

@pytest.fixture(scope="module")
def register_routes():
    from django_api_versioning.decorators import endpoint

    # Registering the accounts route with the endpoint decorator
    @endpoint("accounts" , view_name="accounts_view")
    def test_accounts():
        pass

    yield

def test_urlpatterns_type():
    """Test to check that urlpatterns is a list of URLPattern."""
    from django_api_versioning.urls import urlpatterns

    assert isinstance(urlpatterns, list), "urlpatterns should be a list."
    assert all(isinstance(pattern, URLPattern) for pattern in urlpatterns), "All elements in urlpatterns should be of type URLPattern."

def test_registry_urlpatterns(register_routes):
    """Test to check that the 'accounts' route resolves correctly."""
    match = resolve('/accounts')
    assert match.view_name == 'accounts_view', f"Expected 'accounts_view', but got {match.view_name}"