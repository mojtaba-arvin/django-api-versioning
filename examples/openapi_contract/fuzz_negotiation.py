"""Atheris target for hostile request-version negotiation inputs.

Run from the repository root:
    python examples/openapi_contract/fuzz_negotiation.py \
        examples/openapi_contract/fuzz_corpus -max_total_time=120

Only documented parser rejections are swallowed. Any other exception is a
fuzzer finding and must remain visible as a crash.
"""

from __future__ import annotations

import sys

import atheris
from django.http import HttpRequest

with atheris.instrument_imports():
    from django_api_versioning.negotiation import (
        _UnsupportedVersion,
        _header_version,
        _normalize_hostname,
        _parse_accept_media_range,
        _parse_version,
        _path_version,
        _split_quoted_header,
    )


_MAX_INPUT = 65_536


def _ignore_expected_rejection(callback, *args):
    try:
        callback(*args)
    except (ValueError, _UnsupportedVersion):
        # Invalid or unsupported client input is an expected parser outcome.
        return


def TestOneInput(data: bytes) -> None:
    if len(data) > _MAX_INPUT:
        data = data[:_MAX_INPUT]
    value = data.decode("latin-1")

    _ignore_expected_rejection(_parse_version, value)
    _ignore_expected_rejection(_split_quoted_header, value, ",")
    _ignore_expected_rejection(_split_quoted_header, value, ";")
    _ignore_expected_rejection(_parse_accept_media_range, value)
    _ignore_expected_rejection(_normalize_hostname, value)
    _ignore_expected_rejection(_path_version, value, "api/v{version}/")

    request = HttpRequest()
    request.method = "GET"
    request.META = {"HTTP_ACCEPT": value, "REQUEST_METHOD": "GET"}
    _ignore_expected_rejection(_header_version, request, "Accept-Version")


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
