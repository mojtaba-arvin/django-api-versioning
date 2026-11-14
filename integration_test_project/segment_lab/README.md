# Segment Lab evidence harness

## Status

This directory is reserved for a reproducible evidence harness that extends the existing integration test project. The harness has not yet been ported or verified against the current package source. Do not treat it as executable or as a source of published behavioural claims.

The existing integration project remains authoritative and must be preserved:
- `../manage.py`
- `../project/`
- `../api/`
- `../test_integration.py`

Do not replace or duplicate the existing integration suite.

## Recovered scenario inventory

The interrupted Netlify Agent session produced a separate Django mini-project with these useful scenario ideas:

- Main v1/v3 endpoint declarations and forward inheritance.
- Declarations loaded in reverse import order.
- Explicit `versions=[...]` and `ver_range(...)`.
- Declarations below `API_MIN_VERSION`.
- No import of a module containing endpoint declarations.
- Literal route identity (trailing slash and converter-name differences).
- Duplicate declarations at the same route/version.
- Invalid declarations and the point at which validation occurs.
- Lifecycle middleware headers and sunset responses.
- DRF default request-version behaviour.
- DRF `URLPathVersioning`, including allowed/default versions.
- Bare DRF ViewSet class decoration.
- A configured ViewSet callable and a DRF router mounted beside package routes.

These are scenario proposals from the captured implementation, not verified results for the current package version. Each scenario must be inspected, adapted if necessary, executed, and recorded against one immutable source commit before the website may present its output.

## Provenance requirements

A future generator should record:
- full repository commit SHA;
- package version from root `pyproject.toml`;
- Python, Django, and DRF versions;
- scenario identifier and exact command;
- registry/matrix/HTTP/CLI observations actually produced;
- source-file hashes and source line references where applicable.

The generator must fail on an unknown or stale source locator rather than silently emitting misleading line references. Generated output should be stored under `website/src/data/generated/`, not mixed into the existing integration test suite.

## Historical baseline warning

The captured Agent run installed package commit `e5a5466ac0fab1eb1ef41d8d570ccac1301f2cd9` (version 0.3.5). It is not the current branch baseline. In particular, its `check_versions` output must not be reused as current evidence.
