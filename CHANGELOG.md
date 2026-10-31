
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-31

This release replaces the forward/backward inheritance flags model with a **segment-based model**.

Each `@endpoint` declaration defines a change point for its route. Its view serves its declared version and subsequent versions up to the next declaration, or `API_MAX_VERSION` if no later declaration exists. Earlier versions can also be covered through backward inheritance, without overriding versions already assigned to another declaration.

This makes version resolution predictable and eliminates the route-collapsing behavior that could occur in 0.2.0.

> ⚠️ **Breaking:** `API_FORWARD_INHERITANCE` has been removed, and the default behavior and semantics of `forward` and `backward` have changed. See [Migration](#migration).

### Added

- **Segment-based endpoint resolution.** Each declaration defines a forward segment, ending immediately before the next declaration on the same route.
- **Backward extension.** By default, a declaration can cover unclaimed versions between the previous declaration and its own version.
- **Resolution logging.** An `INFO` log message is emitted when a later declaration shortens an earlier declaration's forward segment.

### Changed

- **Forward inheritance is now enabled by default.** `forward` defaults to `True`, so a declaration serves its own version through the next declaration or `API_MAX_VERSION`.
- **Backward inheritance is now non-destructive.** `backward=True` (the default) fills only unclaimed versions before the declaration. It cannot override another declaration's forward segment.
- **`forward=False` pins a declaration to its own version.** The declaration serves only its explicitly assigned version.
- **Registration order no longer affects resolution.** Segments are calculated from the complete set of declarations rather than their registration order.

### Fixed

- **Versioned route collapse.** Multiple declarations on the same route no longer cause all versions to resolve to the last registered view.
- **Backward inheritance overriding existing segments.** A later declaration no longer overwrites versions already covered by an earlier declaration's forward segment.
- **Silent routing changes.** When a new declaration shortens an existing declaration's forward segment, an informational log message is emitted.

### Removed

- **`API_FORWARD_INHERITANCE` setting.** Forward inheritance is now the default behavior and is controlled per endpoint through `forward`.
- **`ForwardTypeError` exception.** This exception is no longer part of the public API.

### Migration

The following table summarizes the changes when upgrading from 0.2.0 to 0.3.0.

| 0.2.0 | 0.3.0 |
| --- | --- |
| `API_FORWARD_INHERITANCE = True` | Remove the setting. Forward inheritance is now enabled by default. |
| `API_FORWARD_INHERITANCE = False` | Add `forward=False` to declarations that should serve only their explicitly assigned version. |
| `@endpoint("x/", version=2)` | Same syntax. Now serves v2 through the next declaration or `API_MAX_VERSION`. |
| `@endpoint("x/", version=2, forward=True)` | Same syntax. `forward=True` is now the default. |
| `@endpoint("x/", version=2, forward=False)` | Same syntax. Serves v2 only. |
| `@endpoint("x/", version=2, backward=True)` | Same syntax. Fills unclaimed earlier versions without overriding existing segments. |
| `@endpoint("x/", version=2, backward=False)` | Same syntax. Serves v2 onward; earlier versions are not filled by this declaration. |

**Important behavior change:** Consider two declarations on the same route:

```python
@endpoint("orders/", version=2)
class OrderListV2:
    ...

@endpoint("orders/", version=5)
class OrderListV5:
    ...
```

With `API_MAX_VERSION = 7`, the resulting resolution is:

| Version | 0.2.0 | 0.3.0 |
| --- | --- | --- |
| v1 | OrderListV5 | OrderListV2 |
| v2 | OrderListV2 | OrderListV2 |
| v3 | OrderListV5 | OrderListV2 |
| v4 | OrderListV5 | OrderListV2 |
| v5 | OrderListV5 | OrderListV5 |
| v6 | OrderListV2 | OrderListV5 |
| v7 | OrderListV2 | OrderListV5 |

In 0.3.0, the earlier declaration retains its forward segment, while the later declaration takes over from its own version onward.

If you relied on the 0.2.0 default behavior with `API_FORWARD_INHERITANCE = False`, add `forward=False` to every declaration that must remain restricted to its own version.

### Internal

- Added tests covering forward defaults, backward defaults, endpoint pinning, previous declaration precedence, and registration-order independence.
- Replaced the previous registration-order-based resolution test with tests covering the segment model.

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
