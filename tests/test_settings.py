import pytest
from typing import Iterator
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django_api_versioning.settings import APISettings 
from django_api_versioning.exceptions import VersioningError, VersionTypeError

@pytest.fixture(autouse=True)
def reset_settings() -> Iterator[None]:
    """
    Automatically resets Django settings to their default values after each test.
    This prevents state leakage between tests.
    """
    settings.API_BASE_PATH = "api/v{version}/"
    settings.API_MAX_VERSION = 1
    settings.API_MIN_VERSION = 1
    settings.ROOT_URLCONF = "django_api_versioning.urls"
    yield  # Run the test
    # Reset settings after test execution
    settings.API_BASE_PATH = "api/v{version}/"
    settings.API_MAX_VERSION = 1
    settings.API_MIN_VERSION = 1
    settings.ROOT_URLCONF = "django_api_versioning.urls"

@override_settings(
    API_BASE_PATH="api/v{version}/",
    API_MAX_VERSION=1,
    API_MIN_VERSION=1,
    ROOT_URLCONF="django_api_versioning.urls",
)
def test_default_settings() -> None:
    """
    Verifies that default settings are correctly applied when using APISettings.
    """
    api_settings = APISettings(
        API_BASE_PATH=settings.API_BASE_PATH,
        API_MAX_VERSION=settings.API_MAX_VERSION,
        API_MIN_VERSION=settings.API_MIN_VERSION,
        ROOT_URLCONF=settings.ROOT_URLCONF,
    )

    assert api_settings.API_BASE_PATH == "api/v{version}/"
    assert api_settings.API_MAX_VERSION == 1
    assert api_settings.API_MIN_VERSION == 1
    assert api_settings.ROOT_URLCONF == "django_api_versioning.urls"

@override_settings(
    API_BASE_PATH="api/v{version}/custom/",
    API_MAX_VERSION=2,
    API_MIN_VERSION=1,
    ROOT_URLCONF="my_custom_urls",
)
def test_custom_settings() -> None:
    """
    Ensures that custom settings override the default values.
    """
    api_settings = APISettings(
        API_BASE_PATH=settings.API_BASE_PATH,
        API_MAX_VERSION=settings.API_MAX_VERSION,
        API_MIN_VERSION=settings.API_MIN_VERSION,
        ROOT_URLCONF=settings.ROOT_URLCONF,
    )

    assert api_settings.API_BASE_PATH == "api/v{version}/custom/"
    assert api_settings.API_MAX_VERSION == 2
    assert api_settings.API_MIN_VERSION == 1
    assert api_settings.ROOT_URLCONF == "my_custom_urls"

@override_settings(API_BASE_PATH="api/v1/")
def test_invalid_api_base_path() -> None:
    """
    Ensures that API_BASE_PATH without '{version}' raises a ValueError.
    """
    with pytest.raises(VersioningError, match="API_BASE_PATH must contain '{version}'"):
        APISettings(
            API_BASE_PATH=settings.API_BASE_PATH,
            API_MAX_VERSION=1,
            API_MIN_VERSION=1,
            ROOT_URLCONF="django_api_versioning.urls",
        )

@override_settings(API_MIN_VERSION=2, API_MAX_VERSION=1)
def test_invalid_version_range() -> None:
    """
    Ensures that API_MIN_VERSION > API_MAX_VERSION raises a ValueError.
    """
    with pytest.raises(VersioningError, match="API_MIN_VERSION cannot be greater than API_MAX_VERSION"):
        APISettings(
            API_BASE_PATH="api/v{version}/",
            API_MAX_VERSION=settings.API_MAX_VERSION,
            API_MIN_VERSION=settings.API_MIN_VERSION,
            ROOT_URLCONF="django_api_versioning.urls",
        )

@override_settings(API_MIN_VERSION="one")
def test_api_min_version_is_not_integer() -> None:
    """
    Ensures that API_MIN_VERSION is validated as an integer.
    """
    with pytest.raises(VersionTypeError, match="API_MIN_VERSION must be an integer"):
        APISettings(
            API_BASE_PATH="api/v{version}/",
            API_MAX_VERSION=1,
            API_MIN_VERSION=settings.API_MIN_VERSION,
            ROOT_URLCONF="django_api_versioning.urls",
        )

@override_settings(API_MAX_VERSION="two")
def test_api_max_version_is_not_integer() -> None:
    """
    Ensures that API_MAX_VERSION is validated as an integer.
    """
    with pytest.raises(VersionTypeError, match="API_MAX_VERSION must be an integer"):
        APISettings(
            API_BASE_PATH="api/v{version}/",
            API_MAX_VERSION=settings.API_MAX_VERSION,
            API_MIN_VERSION=1,
            ROOT_URLCONF="django_api_versioning.urls",
        )

@override_settings(API_BASE_PATH="api/v{version}")
def test_validate_version_path_format() -> None:
    """
    Ensures that API_BASE_PATH automatically ends with '/' if not already present.
    """
    api_settings = APISettings(
        API_BASE_PATH=settings.API_BASE_PATH,
        API_MAX_VERSION=1,
        API_MIN_VERSION=1,
        ROOT_URLCONF="django_api_versioning.urls",
    )

    assert api_settings.API_BASE_PATH == "api/v{version}/"

@override_settings(ROOT_URLCONF=None)
def test_missing_root_urlconf() -> None:
    """
    Ensures that missing ROOT_URLCONF raises an ImproperlyConfigured exception.
    """    
    with pytest.raises(ImproperlyConfigured, match="ROOT_URLCONF is required"):
        APISettings(
            API_BASE_PATH="api/v{version}/",
            API_MAX_VERSION=1,
            API_MIN_VERSION=1,
            ROOT_URLCONF=settings.ROOT_URLCONF,  # None
        )
