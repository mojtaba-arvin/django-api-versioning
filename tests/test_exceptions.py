import pytest

from django_api_versioning.exceptions import (
    AmbiguousVersionError,
    InvalidVersionError,
    VersioningError,
    VersionMatrixError,
    VersionRangeError,
    VersionTypeError,
)


class TestInheritance:
    def test_all_specific_errors_inherit_from_versioning_error(self):
        for exc in (
            InvalidVersionError,
            VersionRangeError,
            VersionTypeError,
            AmbiguousVersionError,
            VersionMatrixError,
        ):
            assert issubclass(exc, VersioningError)

    def test_versioning_error_inherits_from_exception(self):
        assert issubclass(VersioningError, Exception)


class TestRaisingAndCatching:
    def test_catch_specific_as_base(self):
        with pytest.raises(VersioningError):
            raise InvalidVersionError("bad")

    def test_catch_specific_as_itself(self):
        with pytest.raises(AmbiguousVersionError):
            raise AmbiguousVersionError("ambiguous")

    def test_message_is_preserved(self):
        with pytest.raises(VersionMatrixError, match="matrix changed"):
            raise VersionMatrixError("matrix changed unexpectedly")
