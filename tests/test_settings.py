import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from django_api_versioning.exceptions import (
    ForwardTypeError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.settings import APISettings


def test_default_settings_are_valid():
    """Use the documented defaults when constructing APISettings."""
    config = APISettings()

    assert config.API_BASE_PATH == "api/v{version}/"
    assert config.API_MIN_VERSION == 1
    assert config.API_MAX_VERSION == 1
    assert config.API_FORWARD_INHERITANCE is False
    assert config.ROOT_URLCONF == "django_api_versioning.urls"


@pytest.mark.parametrize(
    "base_path",
    [
        pytest.param(None, id="none"),
        pytest.param(123, id="integer"),
    ],
)
def test_api_base_path_must_be_a_string(base_path):
    """Reject API base paths that are not strings."""
    with pytest.raises(VersioningError, match="API_BASE_PATH must be a string"):
        APISettings(API_BASE_PATH=base_path)


def test_api_base_path_must_contain_version_placeholder():
    """Reject a base path without the version placeholder."""
    with pytest.raises(
        VersioningError,
        match="API_BASE_PATH must contain",
    ):
        APISettings(API_BASE_PATH="api/")


def test_api_base_path_without_trailing_slash_is_normalized(caplog):
    """Append a trailing slash and log a warning when it is missing."""
    with caplog.at_level(
        logging.WARNING,
        logger="django_api_versioning.settings",
    ):
        config = APISettings(API_BASE_PATH="api/v{version}")

    assert config.API_BASE_PATH == "api/v{version}/"
    assert "Adding '/' automatically" in caplog.text


@pytest.mark.parametrize(
    ("setting_name", "value"),
    [
        pytest.param("API_MIN_VERSION", True, id="min-true"),
        pytest.param("API_MIN_VERSION", False, id="min-false"),
        pytest.param("API_MIN_VERSION", "1", id="min-string"),
        pytest.param("API_MAX_VERSION", True, id="max-true"),
        pytest.param("API_MAX_VERSION", False, id="max-false"),
        pytest.param("API_MAX_VERSION", 2.5, id="max-float"),
    ],
)
def test_version_boundaries_must_be_integers(setting_name, value):
    """Reject booleans and other invalid types for version boundaries."""
    with pytest.raises(
        VersionTypeError,
        match=f"{setting_name} must be an integer",
    ):
        APISettings(**{setting_name: value})


def test_minimum_version_cannot_exceed_maximum_version():
    """Reject an invalid configured version range."""
    with pytest.raises(
        VersionRangeError,
        match="API_MIN_VERSION cannot be greater",
    ):
        APISettings(API_MIN_VERSION=4, API_MAX_VERSION=3)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="none"),
        pytest.param(1, id="integer"),
        pytest.param("true", id="string"),
    ],
)
def test_forward_inheritance_must_be_boolean(value):
    """Reject non-boolean forward inheritance settings."""
    with pytest.raises(
        ForwardTypeError,
        match="API_FORWARD_INHERITANCE must be a boolean",
    ):
        APISettings(API_FORWARD_INHERITANCE=value)


def test_empty_root_urlconf_raises_improperly_configured():
    """Reject an empty Django root URL configuration."""
    with pytest.raises(
        ImproperlyConfigured,
        match="ROOT_URLCONF is required",
    ):
        APISettings(ROOT_URLCONF="")


@pytest.mark.parametrize(
    "root_urlconf",
    [
        pytest.param(None, id="none"),
        pytest.param("   ", id="whitespace"),
        pytest.param(123, id="integer"),
    ],
)
def test_invalid_root_urlconf_raises_improperly_configured(root_urlconf):
    """Reject a missing or invalid Django root URL configuration."""
    with pytest.raises(
        ImproperlyConfigured,
        match="ROOT_URLCONF is required",
    ):
        APISettings(ROOT_URLCONF=root_urlconf)


def test_from_django_settings_uses_configured_values():
    """Load API settings from Django without overriding supplied values."""
    django_settings = SimpleNamespace(
        API_BASE_PATH="custom/v{version}/",
        API_MIN_VERSION=2,
        API_MAX_VERSION=5,
        API_FORWARD_INHERITANCE=True,
        ROOT_URLCONF="project.urls",
    )

    with patch(
        "django_api_versioning.settings.settings",
        django_settings,
    ):
        config = APISettings.from_django_settings()

    assert config.API_BASE_PATH == "custom/v{version}/"
    assert config.API_MIN_VERSION == 2
    assert config.API_MAX_VERSION == 5
    assert config.API_FORWARD_INHERITANCE is True
    assert config.ROOT_URLCONF == "project.urls"


def test_from_django_settings_uses_defaults_without_mutating_settings():
    """Use package defaults without adding attributes to Django settings."""
    django_settings = SimpleNamespace(ROOT_URLCONF="project.urls")
    original_values = vars(django_settings).copy()

    with patch(
        "django_api_versioning.settings.settings",
        django_settings,
    ):
        config = APISettings.from_django_settings()

    assert config.API_BASE_PATH == "api/v{version}/"
    assert config.API_MIN_VERSION == 1
    assert config.API_MAX_VERSION == 1
    assert config.API_FORWARD_INHERITANCE is False
    assert config.ROOT_URLCONF == "project.urls"

    assert vars(django_settings) == original_values
