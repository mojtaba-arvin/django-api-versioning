import json
from pathlib import Path

from .exceptions import VersionMatrixError
from .registry import registry


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
            str(v) if v is not None else "unversioned": cb.__name__
            for v, cb in versions.items()
        }
    return matrix


def assert_version_matrix(
    snapshot: str | None = None,
    *,
    update: bool = False,
) -> None:
    """
    Compare the current version matrix against a JSON snapshot.

    - If ``snapshot`` does not exist, it is created.
    - If ``update=True``, the snapshot is overwritten.
    - Otherwise, raises ``VersionMatrixError`` with a diff.

    Usage::

        def test_version_matrix():
            assert_version_matrix(snapshot=".version_matrix.json")

    Note:
        Same import requirement as ``build_version_matrix`` — call after all
        ``@endpoint``-decorated modules have been imported. If the snapshot is
        generated before imports complete, it will be empty and later test runs
        that do import the modules will fail against it.
    """
    current = build_version_matrix()
    if snapshot is None:
        return

    path = Path(snapshot)
    if not path.exists() or update:
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
