"""
Record the actual behaviour of django-api-versioning for ONE scenario.

Usage (normally invoked by generate_routes.py):

    LAB_SCENARIO=main python -m segment_lab.probe /tmp/out.json

Runs in its own interpreter because the package keeps a process-global
registry and reads its settings once, at import time.
"""

import json
import logging
import os
import re
import sys
import traceback
from collections import Counter
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent
INTEGRATION_ROOT = LAB_DIR.parent
REPO_ROOT = INTEGRATION_ROOT.parent

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "segment_lab.settings")
os.environ.setdefault("LAB_SCENARIO", "main")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[dict] = []
        self.phase = "setup"

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {
                "phase": self.phase,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


class PackageCallTracer:
    """Count Python-level calls into django_api_versioning (sys.setprofile)."""

    def __init__(self, package_dir: str) -> None:
        self.package_dir = package_dir
        self.counts: Counter = Counter()

    def _profile(self, frame, event, arg):  # noqa: ANN001
        if event != "call":
            return
        code = frame.f_code
        if code.co_filename.startswith(self.package_dir):
            module = frame.f_globals.get("__name__", "?")
            qualname = getattr(code, "co_qualname", code.co_name)
            self.counts[f"{module}.{qualname}"] += 1

    @contextmanager
    def trace(self):
        self.counts = Counter()
        sys.setprofile(self._profile)
        try:
            yield self
        finally:
            sys.setprofile(None)

    def snapshot(self) -> dict:
        return dict(sorted(self.counts.items()))


def sanitize(text):
    """Replace machine-specific absolute paths so output is reproducible."""
    if not isinstance(text, str):
        return text
    import django

    replacements = [
        (str(INTEGRATION_ROOT), "<integration_test_project>"),
        (str(REPO_ROOT), "<repo>"),
        (str(Path(django.__file__).resolve().parent.parent), "<site-packages>"),
        (sys.prefix, "<venv>"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def error_info(exc: BaseException) -> dict:
    frames = traceback.extract_tb(exc.__traceback__)
    relevant = [
        {
            "file": sanitize(f.filename),
            "line": f.lineno,
            "function": f.name,
            "code": f.line,
        }
        for f in frames
        if "django_api_versioning" in f.filename
        or "rest_framework" in f.filename
        or str(INTEGRATION_ROOT) in f.filename
    ]
    return {
        "type": type(exc).__name__,
        "message": sanitize(str(exc)),
        "frames": relevant,
    }


def callback_info(callback) -> dict:
    view_class = getattr(callback, "view_class", None) or getattr(callback, "cls", None)
    return {
        "callback": getattr(callback, "__name__", repr(callback)),
        "view_class": view_class.__name__ if view_class else None,
        "actions": getattr(callback, "actions", None),
    }


def jsonable(value):
    return json.loads(json.dumps(value, default=repr))


# --------------------------------------------------------------------------
# Probe
# --------------------------------------------------------------------------
def run(out_path: str) -> None:
    log_handler = _ListHandler()
    pkg_logger = logging.getLogger("django_api_versioning")
    pkg_logger.addHandler(log_handler)
    pkg_logger.setLevel(logging.DEBUG)

    import importlib.util

    package_dir = str(
        Path(importlib.util.find_spec("django_api_versioning").origin).parent
    )
    tracer = PackageCallTracer(package_dir)
    result: dict = {"scenario": os.environ["LAB_SCENARIO"]}

    # Phase 1: django.setup() -- imports INSTALLED_APPS, including the package.
    import django

    with tracer.trace():
        django.setup()
    result["setup_package_calls"] = tracer.snapshot()

    from django.conf import settings
    from django.test import Client
    from django.urls import Resolver404, resolve
    from django.urls import reverse as django_reverse
    from segment_lab.scenario_catalog import active_scenario

    from django_api_versioning import api_reverse
    from django_api_versioning.registry import registry
    from django_api_versioning.settings import api_settings
    from django_api_versioning.testing import build_version_matrix

    scenario = active_scenario()

    result["effective_settings"] = {
        "django.conf.settings": {
            "API_BASE_PATH": settings.API_BASE_PATH,
            "API_MIN_VERSION": settings.API_MIN_VERSION,
            "API_MAX_VERSION": settings.API_MAX_VERSION,
            "API_VERSION_LIFECYCLE": jsonable(
                getattr(settings, "API_VERSION_LIFECYCLE", None)
            ),
            "MIDDLEWARE": list(settings.MIDDLEWARE),
            "REST_FRAMEWORK": jsonable(getattr(settings, "REST_FRAMEWORK", {})),
            "LAB_VIEWS_MODULE": settings.LAB_VIEWS_MODULE,
        },
        "django_api_versioning.settings.api_settings": {
            "API_BASE_PATH": api_settings.API_BASE_PATH,
            "API_MIN_VERSION": api_settings.API_MIN_VERSION,
            "API_MAX_VERSION": api_settings.API_MAX_VERSION,
        },
    }
    result["registry_size_after_setup"] = len(registry.urlpatterns)

    # Phase 2: URLconf import -- this is where @endpoint decorators run.
    log_handler.phase = "urlconf-import"
    import_error = None
    with tracer.trace():
        try:
            import_module(settings.ROOT_URLCONF)
        except Exception as exc:  # noqa: BLE001
            import_error = error_info(exc)
    result["urlconf_import"] = {
        "ok": import_error is None,
        "error": import_error,
        "package_calls": tracer.snapshot(),
        "registry_size_after": len(registry.urlpatterns),
    }

    # Registry as stored by the package (order preserved).
    base_path = api_settings.API_BASE_PATH
    entries = []
    for index, pattern in enumerate(registry.urlpatterns):
        route = str(pattern.pattern)
        route_version = getattr(pattern, "_django_api_versioning_route_version", None)
        source_version = getattr(pattern, "_django_api_versioning_source_version", None)
        prefix = base_path.format(version=route_version) if route_version else ""
        entries.append(
            {
                "index": index,
                "route": route,
                "postfix": route[len(prefix) :] if route.startswith(prefix) else route,
                "name": pattern.name,
                "route_version": route_version,
                "source_version": source_version,
                **callback_info(pattern.callback),
            }
        )
    result["registry"] = entries
    result["build_version_matrix"] = build_version_matrix()

    # Requests through Django's test client (full middleware + resolver stack).
    log_handler.phase = "request"
    client = Client(raise_request_exception=False)
    requests = []
    if result["urlconf_import"]["ok"]:
        for path in scenario.get("requests", []):
            record: dict = {"method": "GET", "path": path}
            try:
                match = resolve(path)
                matched_index = next(
                    (
                        e["index"]
                        for e, p in zip(entries, registry.urlpatterns)
                        if p.callback is match.func and e["route"] == match.route
                    ),
                    None,
                )
                record["resolve"] = {
                    "route": match.route,
                    "url_name": match.url_name,
                    "kwargs": match.kwargs,
                    "registry_index": matched_index,
                    "patterns_tried": len(getattr(match, "tried", []) or []),
                    **callback_info(match.func),
                }
            except Resolver404 as exc:
                tried = exc.args[0].get("tried", []) if exc.args else []
                record["resolve"] = {
                    "error": "Resolver404",
                    "patterns_tried": len(tried),
                }
            with tracer.trace():
                response = client.get(path)
            record["status"] = response.status_code
            record["headers"] = {
                k: response[k]
                for k in ("Content-Type", "Deprecation", "Sunset")
                if k in response
            }
            body = response.content.decode("utf-8", "replace")
            try:
                record["body"] = json.loads(body)
            except ValueError:
                title = re.search(r"<title>(.*?)</title>", body, re.S)
                record["body"] = (
                    (
                        {"html_title": " ".join(title.group(1).split())}
                        if title
                        else body[:300]
                    )
                    if not body.lstrip().startswith("<")
                    else (
                        "<html: Django debug 404 page>"
                        if response.status_code == 404
                        else "<html>"
                    )
                )
            record["package_calls"] = tracer.snapshot()
            requests.append(record)
    result["requests"] = requests

    # Reverse lookups.
    reverses = []
    for kind, name, kwargs in scenario.get("reverse", []):
        kw = dict(kwargs)
        if kind == "api_reverse":
            call = (
                f"api_reverse({name!r}"
                + "".join(f", {k}={v!r}" for k, v in kw.items())
                + ")"
            )
            func = lambda: api_reverse(name, **kw)  # noqa: E731
        else:
            call = f"django.urls.reverse({name!r})"
            func = lambda: django_reverse(name)  # noqa: E731
        try:
            reverses.append({"call": call, "result": func(), "error": None})
        except Exception as exc:  # noqa: BLE001
            reverses.append(
                {
                    "call": call,
                    "result": None,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
    result["reverse"] = reverses

    # Scenario-specific recordings made by the views module itself.
    views = sys.modules.get(scenario["views"]) if scenario["views"] else None
    if views is not None and hasattr(views, "RECORDED_ERRORS"):
        result["recorded_errors"] = [
            {**e, "message": sanitize(e["message"])} for e in views.RECORDED_ERRORS
        ]

    result["logs"] = log_handler.records
    Path(out_path).write_text(
        json.dumps(result, indent=2, sort_keys=True, default=repr)
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m lab.probe <output.json>")
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(INTEGRATION_ROOT))
    run(sys.argv[1])
