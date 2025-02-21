import pytest
from django_api_versioning.exceptions import VersioningError, InvalidVersionError, VersionRangeError, VersionTypeError

def test_versioning_error():
    with pytest.raises(VersioningError, match="General versioning error"):
        raise VersioningError("General versioning error")


def test_invalid_version_error():
    with pytest.raises(InvalidVersionError, match="Invalid version specified"):
        raise InvalidVersionError("Invalid version specified")

def test_version_range_error():
    with pytest.raises(VersionRangeError, match="Invalid version range: min_version > max_version"):
        raise VersionRangeError("Invalid version range: min_version > max_version")

def test_version_type_error():
    with pytest.raises(VersionTypeError, match="Version must be an integer"):
        raise VersionTypeError("Version must be an integer")