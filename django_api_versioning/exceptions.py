class VersioningError(Exception):
    """Raised when there is a general error in API versioning."""
    pass


class InvalidVersionError(VersioningError):
    """Raised when an invalid API version is used."""
    pass


class VersionRangeError(VersioningError):
    """Raised when the version range is not valid (e.g., min_version > max_version)."""
    pass


class VersionTypeError(VersioningError):
    """Raised when the version type is invalid (e.g., not an integer)."""
    pass
