import pytest

from django_api_versioning.exceptions import (
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.settings import APISettings


class TestAPISettingsDefaults:
    def test_default_base_path(self):
        s = APISettings()
        assert s.API_BASE_PATH == "api/v{version}/"

    def test_default_min_max(self):
        s = APISettings()
        assert s.API_MIN_VERSION == 1
        assert s.API_MAX_VERSION == 1

    def test_default_channels(self):
        s = APISettings()
        assert s.API_VERSIONING_CHANNELS == ["path"]

    def test_default_lifecycle(self):
        s = APISettings()
        assert s.API_VERSION_LIFECYCLE == {}

    def test_default_resolver_is_none(self):
        s = APISettings()
        assert s.API_EFFECTIVE_VERSION_RESOLVER is None


class TestBasePathValidation:
    def test_missing_version_placeholder_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_BASE_PATH="api/")

    def test_non_string_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_BASE_PATH=123)

    def test_adds_trailing_slash(self):
        s = APISettings(API_BASE_PATH="api/v{version}")
        assert s.API_BASE_PATH == "api/v{version}/"

    @pytest.mark.parametrize(
        "base_path",
        [
            "api/v{version}/v{version}/",
            "api/v{version}/<other>/",
            "api/v{version:02d}/",
            "api/v{version!s}/",
            "api/v{version/",
        ],
    )
    def test_rejects_unsupported_format_fields(self, base_path):
        with pytest.raises(VersioningError):
            APISettings(API_BASE_PATH=base_path)


class TestRootURLConfValidation:
    def test_non_string_root_urlconf_raises(self):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            APISettings(ROOT_URLCONF=123)

    def test_whitespace_root_urlconf_raises(self):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            APISettings(ROOT_URLCONF="   ")


class TestVersionSettings:
    def test_non_int_min_raises(self):
        with pytest.raises(VersionTypeError):
            APISettings(API_MIN_VERSION="1")

    def test_bool_is_rejected(self):
        with pytest.raises(VersionTypeError):
            APISettings(API_MIN_VERSION=True)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(VersionRangeError):
            APISettings(API_MIN_VERSION=5, API_MAX_VERSION=2)


class TestLifecycleValidation:
    def test_non_dict_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_VERSION_LIFECYCLE=[1, 2, 3])

    def test_non_int_key_raises(self):
        with pytest.raises(VersionTypeError):
            APISettings(API_VERSION_LIFECYCLE={"v1": {}})

    def test_non_dict_metadata_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_VERSION_LIFECYCLE={1: "active"})


class TestChannelsValidation:
    def test_unknown_channel_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_VERSIONING_CHANNELS=["url"])

    def test_non_list_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_VERSIONING_CHANNELS="path")

    def test_unhashable_channel_raises_versioning_error(self):
        with pytest.raises(VersioningError, match="Unknown versioning channel"):
            APISettings(API_VERSIONING_CHANNELS=[["path"]])


class TestResolverValidation:
    def test_non_callable_raises(self):
        with pytest.raises(VersioningError):
            APISettings(API_EFFECTIVE_VERSION_RESOLVER="not-callable")

    def test_callable_ok(self):
        def resolver(request):
            return None

        settings = APISettings(API_EFFECTIVE_VERSION_RESOLVER=resolver)
        assert settings.API_EFFECTIVE_VERSION_RESOLVER is resolver
