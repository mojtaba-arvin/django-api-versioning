#!/usr/bin/env python3
"""Install-wheel smoke test: prove the built artifact matches and runs as source."""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = ROOT / "django_api_versioning"


def digest_tree(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed")
    }


def evidence_hashes(root: Path) -> dict[str, str]:
    inputs = [
        root / "pyproject.toml",
        root / "pytest.ini",
        root / "requirements-ci.txt",
        *sorted((root / "tests").rglob("*.py")),
        *sorted((root / "integration_test_project").rglob("*.py")),
    ]
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(inputs), key=lambda item: item.as_posix())
        if path.is_file()
    }


def main() -> None:
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected_version = project["project"]["version"]
    installed_version = metadata.version("django-api-versioning")
    if installed_version != expected_version:
        raise SystemExit(
            f"Installed wheel version {installed_version} does not match "
            f"pyproject version {expected_version}."
        )

    routes_data = json.loads(
        (ROOT / "website/src/data/generated/routes.json").read_text(encoding="utf-8")
    )
    recorded_source = routes_data["source"]
    if recorded_source["version"] != expected_version:
        raise SystemExit(
            "Generated route evidence package version does not match pyproject."
        )
    recorded_package_hashes = {
        item["file"].removeprefix("django_api_versioning/"): item["sha256"]
        for item in recorded_source["files"]
    }
    current_package_hashes = {
        name: digest
        for name, digest in digest_tree(SOURCE_PACKAGE).items()
        if name.endswith(".py")
    }
    if recorded_package_hashes != current_package_hashes:
        raise SystemExit(
            "Generated route evidence is stale: package source hashes differ."
        )

    recorded_evidence_hashes = {
        item["file"]: item["sha256"] for item in recorded_source["evidence_files"]
    }
    current_evidence_hashes = evidence_hashes(ROOT)
    if recorded_evidence_hashes != current_evidence_hashes:
        raise SystemExit(
            "Generated route evidence is stale: test or integration input hashes differ."
        )

    import django
    from django.conf import settings

    settings.configure(
        SECRET_KEY="installed-wheel-smoke-test",
        DEBUG=False,
        ALLOWED_HOSTS=["testserver"],
        ROOT_URLCONF="__main__",
        INSTALLED_APPS=["django_api_versioning"],
        MIDDLEWARE=[],
        API_BASE_PATH="api/v{version}/",
        API_MIN_VERSION=1,
        API_MAX_VERSION=3,
    )
    django.setup()

    import django_api_versioning
    from django.http import JsonResponse
    from django.test import Client
    from django.urls import NoReverseMatch, include, path

    from django_api_versioning import api_reverse, endpoint
    from django_api_versioning.exceptions import VersionTypeError

    installed_package = Path(django_api_versioning.__file__).resolve().parent
    if (
        installed_package == SOURCE_PACKAGE
        or SOURCE_PACKAGE in installed_package.parents
    ):
        raise SystemExit(
            "The smoke test imported the repository checkout instead of "
            "the installed wheel."
        )

    source_hashes = digest_tree(SOURCE_PACKAGE)
    installed_hashes = digest_tree(installed_package)
    if source_hashes != installed_hashes:
        differing = sorted(
            name
            for name in set(source_hashes) | set(installed_hashes)
            if source_hashes.get(name) != installed_hashes.get(name)
        )
        raise SystemExit(
            "Installed wheel contents differ from the repository package source: "
            + ", ".join(differing)
        )

    @endpoint("users/", version=1, view_name="smoke-user-list")
    def users_v1(request):
        return JsonResponse({"version": 1})

    @endpoint("users/", version=3, view_name="smoke-user-list")
    def users_v3(request):
        return JsonResponse({"version": 3})

    @endpoint("users/<int:pk>/", version=1, view_name="smoke-user-detail")
    def user_detail(request, pk):
        return JsonResponse({"version": 1, "pk": pk})

    urlpatterns = [path("", include("django_api_versioning.urls"))]

    client = Client()
    expected_responses = {
        "/api/v1/users/": {"version": 1},
        "/api/v2/users/": {"version": 1},
        "/api/v3/users/": {"version": 3},
        "/api/v2/users/7/": {"version": 1, "pk": 7},
    }
    for url, expected in expected_responses.items():
        response = client.get(url)
        if response.status_code != 200 or response.json() != expected:
            raise SystemExit(
                f"Installed wheel routing failed for {url}: "
                f"HTTP {response.status_code}, body={response.content!r}"
            )

    if api_reverse("smoke-user-list", version=2) != "/api/v2/users/":
        raise SystemExit("Installed wheel api_reverse() returned an unexpected route.")
    if api_reverse("smoke-user-detail", version=2, pk=7) != "/api/v2/users/7/":
        raise SystemExit("Installed wheel converter-aware api_reverse() failed.")

    try:
        api_reverse("smoke-user-detail", version=2, pk="not-an-int")
    except NoReverseMatch:
        pass
    else:
        raise SystemExit("Installed wheel api_reverse() accepted an invalid <int:pk>.")

    try:
        api_reverse("smoke-user-list", version=True)
    except VersionTypeError:
        pass
    else:
        raise SystemExit(
            "Installed wheel api_reverse() accepted bool as an API version."
        )

    print(
        f"PASS installed wheel {installed_version}: "
        f"{len(installed_hashes)} package files match source; "
        "inherited routing, route overrides, api_reverse and converters work."
    )


if __name__ == "__main__":
    main()
