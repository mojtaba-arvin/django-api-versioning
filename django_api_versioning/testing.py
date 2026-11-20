import difflib
import json
from collections.abc import Mapping
from pathlib import Path

from django.urls import get_resolver
from django.urls.resolvers import URLResolver

from .exceptions import ContractSnapshotError, VersionMatrixError
from .registry import REMOVED_ROUTE, registry


def _load_root_urlconf() -> None:
    """Import the root URLconf and recursively resolve included URLconfs."""
    seen: set[int] = set()

    def visit(resolver: URLResolver) -> None:
        resolver_id = id(resolver)
        if resolver_id in seen:
            return
        seen.add(resolver_id)

        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                visit(pattern)

    visit(get_resolver())


def build_version_matrix() -> dict:
    """
    Build a serializable matrix of ``{route: {version: callback_name}}``.

    ``version`` is the string ``"unversioned"`` for routes without a version.

    Note:
        This reads the live registry, which is populated by ``@endpoint``
        decorators at module import time. Call this only after all endpoint
        modules have been imported (e.g., after ``django.setup()`` in a test
        context). If called earlier, the returned matrix will be empty.
    """
    matrix = {}
    for route, versions in registry.get_version_matrix().items():
        matrix[route] = {
            str(v) if v is not None else "unversioned": _callback_name(callback)
            for v, callback in versions.items()
        }
    return matrix


def _callback_name(callback: object) -> str:
    """Return a stable display name for function, class-based, or callable views."""
    if callback is REMOVED_ROUTE:
        return "<removed>"
    view_class = getattr(callback, "view_class", None)
    if view_class is not None:
        return view_class.__name__

    viewset_class = getattr(callback, "cls", None)
    if viewset_class is not None:
        return viewset_class.__name__

    name = getattr(callback, "__name__", None)
    if isinstance(name, str) and name:
        return name
    return type(callback).__name__


def assert_version_matrix(
    snapshot: str | None = None,
    *,
    update: bool = False,
    strict: bool = False,
) -> None:
    """
    Compare the current route matrix with a JSON snapshot.

    Omitting snapshot keeps the historical no-op behavior. By default, a
    missing snapshot is created for backward compatibility. Set strict=True
    in CI to require an existing, non-empty baseline. Pass update=True
    explicitly to create or refresh a snapshot.

    Bootstrap once with update=True, review and commit the file, then run
    with strict=True and without update=True in CI.
    """
    if snapshot is None:
        if strict:
            raise VersionMatrixError("A snapshot path is required when strict=True.")
        return

    current = build_version_matrix()
    path = Path(snapshot)

    if strict and not current:
        raise VersionMatrixError(
            "No endpoints are registered. Check that endpoint modules are "
            "imported before building the version matrix."
        )

    if update:
        path.write_text(json.dumps(current, indent=2, sort_keys=True))
        return

    if not path.exists():
        if strict:
            raise VersionMatrixError(
                f"Version matrix snapshot {str(path)!r} does not exist. "
                "Create it explicitly with update=True, then commit the file."
            )
        path.write_text(json.dumps(current, indent=2, sort_keys=True))
        return

    expected = json.loads(path.read_text())
    if current != expected:
        diff = _diff(expected, current)
        raise VersionMatrixError(
            f"Version matrix changed. Diff:\n{diff}\n"
            f"Run with update=True to accept the new matrix."
        )


def _diff(expected: dict, current: dict) -> str:
    lines = []
    all_routes = sorted(set(expected) | set(current))
    for route in all_routes:
        exp = expected.get(route, {})
        cur = current.get(route, {})
        if exp == cur:
            continue
        lines.append(f"  {route}:")
        for version in sorted(
            set(exp) | set(cur), key=lambda v: (v == "unversioned", v)
        ):
            e = exp.get(version, "<missing>")
            c = cur.get(version, "<missing>")
            if e != c:
                label = version if version == "unversioned" else f"v{version}"
                lines.append(f"    {label}: {e} -> {c}")
    return "\n".join(lines)


def assert_schema_snapshot(
    schema: Mapping[str, object],
    snapshot: str | Path,
    *,
    update: bool = False,
    strict: bool = True,
) -> None:
    """Compare a generated OpenAPI document with a reviewed JSON snapshot.

    The helper has no OpenAPI, YAML, DRF, or schema-validation dependency:
    generate and validate the schema with the consumer's chosen tool, then
    pass its Python mapping here. Use one snapshot per API version.

    Bootstrap or deliberately accept a reviewed contract change with
    update=True. In CI, use strict=True without update=True so missing
    snapshots and unreviewed changes fail closed.
    """
    if not isinstance(schema, Mapping):
        raise ContractSnapshotError("schema must be a mapping/object.")
    path = Path(snapshot)
    try:
        rendered = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\\n"
    except (TypeError, ValueError) as exc:
        raise ContractSnapshotError(
            f"Schema cannot be serialized as deterministic JSON: {exc}"
        ) from exc

    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return

    if not path.is_file():
        if strict:
            raise ContractSnapshotError(
                f"Contract snapshot {str(path)!r} does not exist. "
                "Review the generated schema and create it explicitly with "
                "update=True."
            )
        return

    expected = path.read_text(encoding="utf-8")
    if rendered != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile=str(path),
                tofile="generated OpenAPI schema",
            )
        )
        raise ContractSnapshotError(
            "Generated API schema differs from its reviewed contract snapshot. "
            "Review the API change before refreshing the baseline.\\n" + diff
        )
