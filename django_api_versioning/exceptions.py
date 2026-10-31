class VersioningError(Exception):
    """Raised when there is a general error in API versioning."""


class InvalidVersionError(VersioningError):
    """Raised when an invalid API version is used."""


class VersionRangeError(VersioningError):
    """Raised when the version range is not valid (e.g., min > max)."""


class VersionTypeError(VersioningError):
    """Raised when the version type is invalid (e.g., not an integer)."""


class AmbiguousVersionError(VersioningError):
    """Raised when ``api_reverse`` cannot pick a version unambiguously."""


class VersionMatrixError(VersioningError):
    """Raised when the version matrix has gaps or overlaps."""
