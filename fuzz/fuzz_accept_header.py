"""Atheris target for hostile HTTP Accept and API-version parser inputs."""
from __future__ import annotations

import sys

import atheris

with atheris.instrument_imports():
    from django_api_versioning.negotiation import (
        _UnsupportedVersion,
        _header_version,
        _parse_accept_media_range,
        _parse_version,
    )


class _Headers(dict):
    def get(self, name: str, default=None):
        folded = name.casefold()
        for key, value in self.items():
            if key.casefold() == folded:
                return value
        return default


class _Request:
    def __init__(self, accept: str):
        self.headers = _Headers({"Accept": accept})


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    # Lossless byte mapping retains malformed UTF-8 and HTTP control bytes.
    raw = data.decode("latin-1")
    for parser in (
        lambda: _parse_accept_media_range(raw),
        lambda: _header_version(_Request(raw), "Accept-Version"),
        lambda: _parse_version(raw),
    ):
        try:
            parser()
        except (ValueError, _UnsupportedVersion):
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
