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

    def test_leading_slash_is_rejected(self):
        with pytest.raises(VersioningError, match="must not start with"):
            APISettings(API_BASE_PATH="/api/v{version}/")

    def test_adds_trailing_slash(self):
        s = APISettings(API_BASE_PATH="api/v{version}")
        assert s.API_BASE_PATH == "api/v{version}/"

    @pytest.mark.parametrize(
        "base_path",
        [
            "api/v{version}/v{version}/",
            "api/v{version}/{other}/",
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

    def test_deprecated_status_requires_deprecated_at(self):
        with pytest.raises(VersioningError, match="requires a 'deprecated_at'"):
            APISettings(API_VERSION_LIFECYCLE={1: {"status": "deprecated"}})

    def test_retired_status_requires_sunset(self):
        with pytest.raises(VersioningError, match="requires a 'sunset'"):
            APISettings(API_VERSION_LIFECYCLE={1: {"status": "retired"}})

    def test_unknown_lifecycle_status_raises(self):
        with pytest.raises(VersioningError, match="Lifecycle status"):
            APISettings(API_VERSION_LIFECYCLE={1: {"status": "disabled"}})

    @pytest.mark.parametrize("status", [[], {}, ["active"]])
    def test_unhashable_lifecycle_status_raises(self, status):
        with pytest.raises(VersioningError, match="Lifecycle status"):
            APISettings(API_VERSION_LIFECYCLE={1: {"status": status}})

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("deprecated_at", "not-a-date"),
            ("sunset", "not-a-date"),
            ("deprecated_at", 123),
            ("sunset", 123),
        ],
    )
    def test_invalid_lifecycle_dates_raise(self, field_name, value):
        metadata = {"status": "active", field_name: value}
        with pytest.raises(VersioningError, match=field_name):
            APISettings(API_VERSION_LIFECYCLE={1: metadata})

    @pytest.mark.parametrize(
        ("deprecated_at", "sunset"),
        [
            ("2027-06-30", "2027-06-29"),
            (
                "2027-06-30T12:00:00+03:00",
                "2027-06-30T08:59:59Z",
            ),
        ],
    )
    def test_sunset_cannot_precede_deprecation(self, deprecated_at, sunset):
        with pytest.raises(VersioningError, match="sunset.*earlier"):
            APISettings(
                API_VERSION_LIFECYCLE={
                    1: {
                        "status": "deprecated",
                        "deprecated_at": deprecated_at,
                        "sunset": sunset,
                    }
                }
            )

    def test_sunset_equal_to_deprecation_is_allowed(self):
        APISettings(
            API_VERSION_LIFECYCLE={
                1: {
                    "status": "deprecated",
                    "deprecated_at": "2027-06-30T12:00:00Z",
                    "sunset": "2027-06-30T15:00:00+03:00",
                }
            }
        )

    def test_retired_sunset_must_not_precede_optional_deprecation(self):
        with pytest.raises(VersioningError, match="sunset.*earlier"):
            APISettings(
                API_VERSION_LIFECYCLE={
                    1: {
                        "status": "retired",
                        "deprecated_at": "2027-06-30",
                        "sunset": "2027-06-29",
                    }
                }
            )

    def test_active_lifecycle_dates_do_not_apply_deprecation_ordering(self):
        APISettings(
            API_VERSION_LIFECYCLE={
                1: {
                    "status": "active",
                    "deprecated_at": "2027-06-30",
                    "sunset": "2027-06-29",
                }
            }
        )


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

    def test_callable_ok(self, caplog):
        def resolver(request):
            return None

        settings = APISettings(API_EFFECTIVE_VERSION_RESOLVER=resolver)
        assert settings.API_EFFECTIVE_VERSION_RESOLVER is resolver
        assert "is reserved and is not invoked" in caplog.text


def test_non_default_versioning_channels_warn_that_they_are_ignored(caplog):
    settings = APISettings(API_VERSIONING_CHANNELS=["header", "query"])

    assert settings.API_VERSIONING_CHANNELS == ["header", "query"]
    assert "non-default channel values are ignored" in caplog.text


def test_path_only_versioning_channels_do_not_warn(caplog):
    APISettings(API_VERSIONING_CHANNELS=["path"])

    assert "API_VERSIONING_CHANNELS is reserved" not in caplog.text

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("deprecated_at", "0001-01-01T00:00:00+23:59"),
            ("deprecated_at", "9999-12-31T23:59:59-23:59"),
            ("sunset", "0001-01-01T00:00:00+23:59"),
            ("sunset", "9999-12-31T23:59:59-23:59"),
        ],
    )
    def test_timezone_normalization_overflow_raises_versioning_error(
        self, field_name, value
    ):
        metadata = {"status": "active", field_name: value}

        with pytest.raises(VersioningError, match=field_name):
            APISettings(API_VERSION_LIFECYCLE={1: metadata})
