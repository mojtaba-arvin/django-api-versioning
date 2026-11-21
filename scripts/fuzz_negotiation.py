"""Atheris target for hostile request-version and lifecycle parser inputs."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import atheris

with atheris.instrument_imports():
    import django

    django.setup()

    from django.http import HttpRequest

    from django_api_versioning.lifecycle import (
        _coerce_version,
        _extract_version_from_value,
    )
    from django_api_versioning.negotiation import (
        _UnsupportedVersion,
        _header_version,
        _parse_accept_media_range,
        _parse_version,
        _split_quoted_header,
    )


def _ignore_expected_rejections(callable_, *args) -> None:
    try:
        callable_(*args)
    except (ValueError, _UnsupportedVersion):
        pass


def TestOneInput(data: bytes) -> None:
    if len(data) > 65536:
        return

    value = data.decode("latin-1")
    _ignore_expected_rejections(_parse_version, value)
    _ignore_expected_rejections(_split_quoted_header, value, ",")
    _ignore_expected_rejections(_split_quoted_header, value, ";")

    for media_range in value.split(",")[:32]:
        _ignore_expected_rejections(_parse_accept_media_range, media_range)

    request = HttpRequest()
    request.META["HTTP_ACCEPT"] = value
    request.META["HTTP_ACCEPT_VERSION"] = value[:4096]
    _ignore_expected_rejections(_header_version, request, "Accept-Version")

    _ignore_expected_rejections(_coerce_version, value)
    _ignore_expected_rejections(_extract_version_from_value, value)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
