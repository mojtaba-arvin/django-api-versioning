#!/usr/bin/env python
"""
Bootstrap the Segment Lab Django project, record what django-api-versioning
actually does, and write:

  ../../website/src/data/generated/routes.json          every recorded scenario
  ../../website/src/data/generated/check_versions_output.txt  main-scenario CLI output

Usage (from anywhere):

  python integration_test_project/segment_lab/generate_routes.py
  python integration_test_project/segment_lab/generate_routes.py --check

Nothing in the output is typed by hand: every behavioural value comes from
the repository package source (registry, management command, test client,
api_reverse), and source references are parsed from that same checkout.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent
INTEGRATION_ROOT = LAB_DIR.parent
REPO_ROOT = INTEGRATION_ROOT.parent
ROUTES_JSON = REPO_ROOT / "website" / "src" / "data" / "generated" / "routes.json"
CHECK_VERSIONS_TXT = ROUTES_JSON.parent / "check_versions_output.txt"
PACKAGE_DIR = REPO_ROOT / "django_api_versioning"
REPOSITORY = "https://github.com/mojtaba-arvin/django-api-versioning"
PACKAGE = "django-api-versioning"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(INTEGRATION_ROOT))
from segment_lab.scenario_catalog import SCENARIOS  # noqa: E402  (plain dict, no Django import)


# --------------------------------------------------------------------------
# Provenance: which commit is installed? (never guessed)
# --------------------------------------------------------------------------
def provenance() -> dict:
    """Describe the exact package source in this repository checkout."""
    supplied_commit = os.environ.get("SOURCE_COMMIT", "").strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    checkout_commit = head.stdout.strip() if head.returncode == 0 else None

    if supplied_commit and not re.fullmatch(r"[0-9a-f]{40}", supplied_commit):
        raise SystemExit(f"SOURCE_COMMIT must be a full Git SHA, got {supplied_commit!r}.")
    if supplied_commit and checkout_commit and supplied_commit != checkout_commit:
        raise SystemExit(
            f"SOURCE_COMMIT {supplied_commit} does not match checkout HEAD {checkout_commit}."
        )
    if not supplied_commit and not checkout_commit:
        raise SystemExit(
            "Git HEAD is unavailable. Set SOURCE_COMMIT from a verified checkout."
        )

    # Evidence depends on both the package and the executable lab. When Git
    # metadata is present, reject uncommitted changes to either input tree.
    # Some build containers intentionally omit .git; there SOURCE_COMMIT is
    # supplied by the host workflow after it verifies the checkout SHA.
    if checkout_commit:
        dirty = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                "django_api_versioning",
                "pyproject.toml",
                "integration_test_project",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        if dirty.stdout.strip():
            raise SystemExit(
                "Package source or pyproject.toml has uncommitted changes; "
                "commit them before generating evidence."
            )

    commit = supplied_commit or checkout_commit
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    package_dir = PACKAGE_DIR
    files = []
    for path in sorted(package_dir.rglob("*")):
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed"):
            files.append(
                {
                    "file": path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )

    evidence_inputs = [REPO_ROOT / "pyproject.toml"]
    evidence_inputs.extend(sorted(INTEGRATION_ROOT.rglob("*.py")))
    evidence_files = [
        {
            "file": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in evidence_inputs
        if path.is_file()
    ]

    return {
        "repository": REPOSITORY,
        "package": PACKAGE,
        "version": project["project"]["version"],
        "commit": commit,
        "install_url": f"{REPOSITORY}/tree/{commit}",
        "install_method": "repository-checkout",
        "archive_sha256": None,
        "source_mode": "repository-checkout",
        "package_dir": package_dir,
        "files": files,
        "evidence_files": evidence_files,
    }

# --------------------------------------------------------------------------
# Source references: line numbers parsed from the repository checkout
# --------------------------------------------------------------------------
SYMBOLS = {
    "endpoint": ("decorators.py", "endpoint"),
    "ver_range": ("decorators.py", "ver_range"),
    "_validate_version": ("decorators.py", "_validate_version"),
    "UrlRegistry.register": ("registry.py", "UrlRegistry.register"),
    "UrlRegistry._should_replace": ("registry.py", "UrlRegistry._should_replace"),
    "UrlRegistry._create_pattern": ("registry.py", "UrlRegistry._create_pattern"),
    "UrlRegistry._sort_urlpatterns": ("registry.py", "UrlRegistry._sort_urlpatterns"),
    "UrlRegistry.get_version_matrix": ("registry.py", "UrlRegistry.get_version_matrix"),
    "UrlRegistry._find_route_index": ("registry.py", "UrlRegistry._find_route_index"),
    "api_reverse": ("reverse.py", "api_reverse"),
    "check_versions.handle": ("management/commands/check_versions.py", "Command.handle"),
    "check_versions._warn_gaps": ("management/commands/check_versions.py", "Command._warn_gaps"),
    "LifecycleMiddleware.__call__": ("lifecycle.py", "LifecycleMiddleware.__call__"),
    "_extract_version_from_path": ("lifecycle.py", "_extract_version_from_path"),
    "build_version_matrix": ("testing.py", "build_version_matrix"),
    "assert_version_matrix": ("testing.py", "assert_version_matrix"),
    "APISettings.from_django_settings": ("settings.py", "APISettings.from_django_settings"),
    "extract_version (channels)": ("channels.py", "extract_version"),
}

# Single lines located by exact text. If upstream changes, generation fails
# instead of pointing at the wrong line.
LINES = {
    "segment_loop": ("decorators.py", "for ver in range(version, max_version + 1):"),
    "explicit_loop": ("decorators.py", "for ver in versions:"),
    "below_min_return": ("decorators.py", "return view"),
    "below_min_warning": ("decorators.py", '"No routes will be registered."'),
    "newer_wins": ("registry.py", "return source_version >= existing_version"),
    "none_wins": ("registry.py", "if existing_version is None or source_version is None:"),
    "as_view_call": ("registry.py", "view = view.as_view()"),
    "instance_check": ("registry.py", "if isinstance(view, View):"),
    "route_string": ("decorators.py", 'route = f"{base_path}{app_name_part}{postfix}"'),
    "api_settings_singleton": ("settings.py", "api_settings = APISettings.from_django_settings()"),
    "settings_read_in_decorator": ("decorators.py", "max_version: int = settings.API_MAX_VERSION"),
    "registry_urlpatterns": ("urls.py", "urlpatterns: list[URLPattern] = registry.urlpatterns"),
    "matrix_key": ("registry.py", "route = str(pattern.pattern)"),
    "gap_warning": ("management/commands/check_versions.py", 'f"  [{endpoint}] v{v} is not defined."'),
    "callback_name": ("management/commands/check_versions.py", "callback_name = self._get_callback_name(versions[version])"),
    "sunset_410": ("lifecycle.py", "if sunset and _is_past(sunset):"),
    "deprecated_header": ("lifecycle.py", 'if meta.get("status") == "deprecated":'),
    "reverse_ambiguous": ("reverse.py", "if version is None and len(matches) > 1:"),
}


def _symbol_lines(tree: ast.AST, dotted: str) -> tuple[int, int]:
    parts = dotted.split(".")
    nodes = tree.body
    node = None
    for part in parts:
        node = next(
            (
                n
                for n in nodes
                if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                and n.name == part
            ),
            None,
        )
        if node is None:
            raise SystemExit(f"Symbol {dotted!r} not found in installed source.")
        nodes = node.body
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return start, node.end_lineno


def source_refs(package_dir: Path) -> dict:
    refs: dict = {"symbols": {}, "lines": {}}
    trees: dict[str, tuple[ast.AST, list[str]]] = {}

    def load(rel: str):
        if rel not in trees:
            text = (package_dir / rel).read_text()
            trees[rel] = (ast.parse(text), text.splitlines())
        return trees[rel]

    for key, (rel, dotted) in SYMBOLS.items():
        tree, _ = load(rel)
        start, end = _symbol_lines(tree, dotted)
        refs["symbols"][key] = {"file": f"django_api_versioning/{rel}", "start": start, "end": end}
    for key, (rel, needle) in LINES.items():
        _, lines = load(rel)
        hits = [i + 1 for i, line in enumerate(lines) if needle in line]
        if not hits:
            raise SystemExit(f"Line {needle!r} not found in {rel}.")
        refs["lines"][key] = {
            "file": f"django_api_versioning/{rel}",
            "line": hits[0],
            "code": lines[hits[0] - 1].strip(),
        }

    # Where are the two non-routing settings referenced? (AST, whole package)
    usage: dict[str, list] = {"API_VERSIONING_CHANNELS": [], "API_EFFECTIVE_VERSION_RESOLVER": [], "channels_module_imported_by": []}
    for path in sorted(package_dir.rglob("*.py")):
        rel = path.relative_to(package_dir.parent).as_posix()
        text = path.read_text()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.append(node.value)
            for name in names:
                if name in ("API_VERSIONING_CHANNELS", "API_EFFECTIVE_VERSION_RESOLVER"):
                    usage[name].append({"file": rel, "line": node.lineno})
            if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("channels"):
                usage["channels_module_imported_by"].append({"file": rel, "line": node.lineno})
            if isinstance(node, ast.Import) and any(a.name.endswith(".channels") for a in node.names):
                usage["channels_module_imported_by"].append({"file": rel, "line": node.lineno})
    for key in usage:
        seen = set()
        usage[key] = [u for u in usage[key] if not ((u["file"], u["line"]) in seen or seen.add((u["file"], u["line"])))]
    refs["non_routing_settings_usage"] = usage
    return refs


# --------------------------------------------------------------------------
# Running the project
# --------------------------------------------------------------------------
def _env(scenario: str) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "LAB_SCENARIO": scenario,
            "DJANGO_SETTINGS_MODULE": "segment_lab.settings",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    python_paths = [str(REPO_ROOT), str(INTEGRATION_ROOT), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join(value for value in python_paths if value)
    env.pop("DJANGO_COLORS", None)
    return env


def _sanitize(text: str) -> str:
    for old, new in (
        (str(INTEGRATION_ROOT), "<integration_test_project>"),
        (str(REPO_ROOT), "<repo>"),
        (sys.prefix, "<venv>"),
    ):
        text = text.replace(old, new)
    return text


def run_check_versions(scenario: str, extra: list[str]) -> dict:
    cmd = [sys.executable, "manage.py", "check_versions", *extra]
    proc = subprocess.run(
        cmd, cwd=INTEGRATION_ROOT, env=_env(scenario), capture_output=True, text=True, timeout=120
    )
    stderr = _sanitize(proc.stderr)
    stderr_lines = stderr.strip().splitlines()
    return {
        "command": " ".join(["python", "manage.py", "check_versions", *extra]),
        "env": {"LAB_SCENARIO": scenario},
        "exit_code": proc.returncode,
        "stdout": _sanitize(proc.stdout),
        # Tracebacks are long; keep the exception line (last line) and size.
        "stderr": stderr if len(stderr_lines) <= 20 else None,
        "stderr_last_line": stderr_lines[-1] if stderr_lines else "",
        "stderr_line_count": len(stderr_lines),
    }


def run_probe(scenario: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "probe.json"
        proc = subprocess.run(
            [sys.executable, "-m", "segment_lab.probe", str(out)],
            cwd=INTEGRATION_ROOT,
            env=_env(scenario),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0 or not out.exists():
            raise SystemExit(f"Probe for {scenario!r} failed:\n{proc.stderr}")
        return json.loads(out.read_text())


def logical_matrix(registry: list[dict]) -> dict:
    """{postfix: {version|"unversioned": callback}} derived from registry rows."""
    matrix: dict = {}
    for row in registry:
        key = "unversioned" if row["route_version"] is None else str(row["route_version"])
        label = row["view_class"] or row["callback"]
        matrix.setdefault(row["postfix"], {})[key] = {
            "callback": label,
            "source_version": row["source_version"],
            "route": row["route"],
        }
    return matrix


def read_views_source(module: str | None) -> dict | None:
    if not module:
        return None
    rel = Path(*module.split(".")).with_suffix(".py")
    text = (INTEGRATION_ROOT / rel).read_text()
    return {"file": f"integration_test_project/{rel.as_posix()}", "code": text}


def environment() -> dict:
    def version(name: str) -> str | None:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return None

    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "django": version("Django"),
        "djangorestframework": version("djangorestframework"),
    }


def build() -> tuple[dict, str]:
    prov = provenance()
    package_dir = prov.pop("package_dir")
    data: dict = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator": "integration_test_project/segment_lab/generate_routes.py",
        "source": prov,
        "environment": environment(),
        "source_refs": source_refs(package_dir),
        "lab_settings_file": {"file": "integration_test_project/segment_lab/settings.py", "code": (LAB_DIR / "settings.py").read_text()},
        "lab_urls_file": {"file": "integration_test_project/segment_lab/urls.py", "code": (LAB_DIR / "urls.py").read_text()},
        "scenarios": {},
    }
    main_stdout = ""
    for name, spec in SCENARIOS.items():
        print(f"  recording {name} ...", file=sys.stderr)
        probe = run_probe(name)
        cv = [run_check_versions(name, [])]
        for variant in spec.get("check_versions_variants", []):
            cv.append(run_check_versions(name, variant))
        if name == "main":
            main_stdout = cv[0]["stdout"]
        data["scenarios"][name] = {
            "title": spec["title"],
            "question": spec["question"],
            "views_module": spec["views"],
            "views_source": read_views_source(spec["views"]),
            "settings_overrides": json.loads(json.dumps(spec["settings"], default=repr)),
            "matrix": logical_matrix(probe["registry"]),
            "check_versions": cv,
            **probe,
        }
    for name, spec in SCENARIOS.items():
        other = spec.get("compare_matrix_with")
        if other:
            data["scenarios"][name]["matrix_equal_to"] = {
                "scenario": other,
                "equal": data["scenarios"][name]["build_version_matrix"]
                == data["scenarios"][other]["build_version_matrix"],
            }
    return data, main_stdout


def _strip_volatile(data: dict) -> dict:
    return {k: v for k, v in data.items() if k != "generated_at"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if outputs are stale")
    args = parser.parse_args()

    data, main_stdout = build()
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        current = json.loads(ROUTES_JSON.read_text()) if ROUTES_JSON.exists() else {}
        stale = _strip_volatile(current) != _strip_volatile(json.loads(text))
        stale |= not CHECK_VERSIONS_TXT.exists() or CHECK_VERSIONS_TXT.read_text() != main_stdout
        print("stale" if stale else "up to date")
        raise SystemExit(1 if stale else 0)

    ROUTES_JSON.parent.mkdir(parents=True, exist_ok=True)
    ROUTES_JSON.write_text(text)
    CHECK_VERSIONS_TXT.write_text(main_stdout)
    src = data["source"]
    print(
        f"wrote {ROUTES_JSON.relative_to(REPO_ROOT)} and {CHECK_VERSIONS_TXT.relative_to(REPO_ROOT)}\n"
        f"  {src['package']} {src['version']} @ {src['commit']}\n"
        f"  {len(data['scenarios'])} scenarios, Django {data['environment']['django']}, "
        f"DRF {data['environment']['djangorestframework']}, Python {data['environment']['python']}"
    )


if __name__ == "__main__":
    main()