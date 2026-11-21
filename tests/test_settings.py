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
            "api/../v{version}/",
            "api/./v{version}/",
            "api//v{version}/",
            "api/v{version}/?query/",
            r"api\\v{version}\\",
            "api/%252e%252e/v{version}/",
            "api%2Fv{version}/",
            "api/%FF/v{version}/",
        ],
    )
    def test_rejects_unsafe_url_path_segments(self, base_path):
        with pytest.raises(VersioningError):
            APISettings(API_BASE_PATH=base_path)

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

    @pytest.mark.parametrize(
        ("min_version", "max_version"),
        [(-1, 3), (1, -1), (-1, -1)],
    )
    def test_negative_version_bounds_raise(self, min_version, max_version):
        with pytest.raises(VersionRangeError, match="non-negative"):
            APISettings(
                API_MIN_VERSION=min_version,
                API_MAX_VERSION=max_version,
            )

    def test_zero_version_bounds_are_allowed(self):
        settings = APISettings(API_MIN_VERSION=0, API_MAX_VERSION=0)
        assert settings.API_MIN_VERSION == 0
        assert settings.API_MAX_VERSION == 0


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
    assert "values in API_VERSIONING_CHANNELS are ignored" in caplog.text


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
def test_timezone_normalization_overflow_raises_versioning_error(field_name, value):
    metadata = {"status": "active", field_name: value}

    with pytest.raises(VersioningError, match=field_name):
        APISettings(API_VERSION_LIFECYCLE={1: metadata})


def test_negative_lifecycle_key_raises():
    with pytest.raises(VersionRangeError, match="non-negative"):
        APISettings(API_VERSION_LIFECYCLE={-1: {"status": "active"}})


class TestNegotiationSettings:
    def test_path_scheme_is_the_default(self):
        settings = APISettings()
        assert settings.API_VERSIONING_SCHEME == "path"
        assert settings.API_UNVERSIONED_BASE_PATH == "api/"
        assert settings.API_DEFAULT_VERSION is None

    @pytest.mark.parametrize("scheme", ["path", "header", "query", "hostname"])
    def test_supported_schemes(self, scheme):
        settings = APISettings(
            API_MIN_VERSION=1,
            API_MAX_VERSION=3,
            API_VERSIONING_SCHEME=scheme,
            API_VERSIONING_HOSTS=(
                {"v2.example.com": 2} if scheme == "hostname" else {}
            ),
        )
        assert settings.API_VERSIONING_SCHEME == scheme

    @pytest.mark.parametrize("scheme", ["accept", "url", "tenant", None, 1, []])
    def test_unknown_or_invalid_scheme_is_rejected(self, scheme):
        with pytest.raises(VersioningError, match="API_VERSIONING_SCHEME"):
            APISettings(API_VERSIONING_SCHEME=scheme)

    def test_hostname_scheme_requires_explicit_mapping(self):
        with pytest.raises(VersioningError, match="at least one mapping"):
            APISettings(API_VERSIONING_SCHEME="hostname")

    def test_hostname_map_requires_versions_within_global_range(self):
        with pytest.raises(VersioningError, match="between 1 and 2"):
            APISettings(
                API_MIN_VERSION=1,
                API_MAX_VERSION=2,
                API_VERSIONING_SCHEME="hostname",
                API_VERSIONING_HOSTS={"v3.example.com": 3},
            )

    def test_hostname_map_normalizes_case_and_trailing_dot_for_duplicates(self):
        with pytest.raises(VersioningError, match="Duplicate"):
            APISettings(
                API_MIN_VERSION=1,
                API_MAX_VERSION=2,
                API_VERSIONING_HOSTS={
                    "API.example.com": 1,
                    "api.example.com.": 2,
                },
            )

    def test_default_version_must_be_inside_global_range(self):
        with pytest.raises(VersioningError, match="API_DEFAULT_VERSION"):
            APISettings(
                API_MIN_VERSION=1,
                API_MAX_VERSION=2,
                API_DEFAULT_VERSION=3,
            )

    @pytest.mark.parametrize(
        "base_path",
        [
            "api/../",
            "api/./",
            "api/?query/",
            r"api\\v1/",
            "api/%252e%252e/",
            "api%2Fv/",
        ],
    )
    def test_unversioned_base_path_rejects_unsafe_segments(self, base_path):
        with pytest.raises(VersioningError, match="API_UNVERSIONED_BASE_PATH"):
            APISettings(API_UNVERSIONED_BASE_PATH=base_path)

    def test_unversioned_base_path_must_be_relative_and_normalized(self):
        with pytest.raises(VersioningError, match="API_UNVERSIONED_BASE_PATH"):
            APISettings(API_UNVERSIONED_BASE_PATH="/api/")

    def test_query_parameter_and_header_names_must_be_non_empty_tokens(self):
        with pytest.raises(VersioningError, match="API_VERSIONING_HEADER"):
            APISettings(API_VERSIONING_HEADER="Accept Version")
        with pytest.raises(VersioningError, match="API_VERSIONING_QUERY_PARAMETER"):
            APISettings(API_VERSIONING_QUERY_PARAMETER="")

    @pytest.mark.parametrize("hostname", ["api.example.com..", "api..example.com"])
    def test_hostname_map_rejects_invalid_dot_structure(self, hostname):
        with pytest.raises(VersioningError):
            APISettings(
                API_VERSIONING_SCHEME="hostname",
                API_VERSIONING_HOSTS={hostname: 1},
            )


@pytest.mark.parametrize(
    "header",
    [
        "Bad:Name",
        "Bad/Name",
        "Bad Name",
        "Accept",
        "accept",
        "Bad\\rName",
    ],
)
def test_invalid_or_reserved_version_header_names_are_rejected(header):
    with pytest.raises(VersioningError, match="API_VERSIONING_HEADER"):
        APISettings(API_VERSIONING_HEADER=header)


def test_valid_custom_version_header_name_is_accepted():
    settings = APISettings(API_VERSIONING_HEADER="X-API-Version")

    assert settings.API_VERSIONING_HEADER == "X-API-Version"
