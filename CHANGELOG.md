# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-28

The release that introduces **forward inheritance**. Routes declared for
0.1.x keep working unchanged unless you opt in by setting
`API_FORWARD_INHERITANCE = True` or passing `forward=True` to a single
endpoint.

> ⚠️ **Breaking:** Python 3.9 and Django 3.2 / 4.2 are no longer
> supported. See the *Changed* section below.

### Added

- **Forward endpoint inheritance.** An endpoint declared with
  `version=N` is registered for versions `N+1` through `API_MAX_VERSION`
  when `API_FORWARD_INHERITANCE = True`. The per-endpoint `forward`
  argument overrides the global setting in either direction. Opt out
  for a single endpoint with `forward=False`. See the *Forward
  inheritance* section in the README.
- **`py.typed` marker (PEP 561).** Type hints ship with the package, so
  `mypy` and `pyright` pick them up automatically in downstream
  projects.

### Changed

- **Python support raised from 3.9 to 3.10–3.15.** Python 3.9 reached
  end-of-life in October 2025 and received no security updates
  afterwards.
- **Django support raised from 3.2 to 5.2–6.1.** Django 3.2 and 4.2
  reached end-of-life in April 2024 and April 2026 respectively;
  5.2 LTS is supported until April 2028.

### Removed

- The class-based-view wrapper introduced in 0.1.x. The wrapper replaced
  the original class with a function, which silently dropped
  `view_class` metadata on the URL pattern. This broke
  `resolve().func.view_class` and some DRF integrations (authentication
  class discovery, schema generation). Decorated CBVs now return the
  original class unchanged.

## [0.1.4] - 2025-02-22

- Initial release: decorator-based URL versioning, backward compatibility,
  Django and DRF support.
