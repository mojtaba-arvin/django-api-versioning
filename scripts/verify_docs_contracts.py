"""Focused, deterministic documentation contracts backed by canonical source."""

from __future__ import annotations

import ast
import re

TICK = chr(96)


def markdown_tables(source: str, first_header: str, second_header: str) -> list[list[list[str]]]:
    """Return rows from Markdown tables with the requested first two headers."""
    lines = source.splitlines()
    tables = []
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        headers = [cell.strip().strip(TICK) for cell in line.strip().strip("|").split("|")]
        if headers[:2] != [first_header, second_header]:
            continue
        rows = []
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            cells = [cell.strip().strip(TICK) for cell in row.strip().strip("|").split("|")]
            if cells:
                rows.append(cells)
        tables.append(rows)
    if not tables:
        raise ValueError(
            f"Documentation table {first_header!r}/{second_header!r} is missing."
        )
    return tables


def _assignments(tree: ast.Module) -> dict[str, ast.AST]:
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result[node.target.id] = node.value
    return result


def _literal(node: ast.AST, assignments: dict[str, ast.AST]):
    if isinstance(node, ast.Name) and node.id in assignments:
        return _literal(assignments[node.id], assignments)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "field":
            factory = next(
                (item.value for item in node.keywords if item.arg == "default_factory"),
                None,
            )
            if isinstance(factory, ast.Lambda):
                return _literal(factory.body, assignments)
        if node.func.id in {"dict", "list", "set"} and len(node.args) == 1:
            value = _literal(node.args[0], assignments)
            return {"dict": dict, "list": list, "set": set}[node.func.id](value)
    return ast.literal_eval(node)


def verify_settings_and_endpoint_contract(
    reference: str, settings_source: str, decorators_source: str
) -> None:
    settings_tree = ast.parse(settings_source)
    assignments = _assignments(settings_tree)
    settings_class = next(
        item
        for item in settings_tree.body
        if isinstance(item, ast.ClassDef) and item.name == "APISettings"
    )
    actual_settings = {
        item.target.id: _literal(item.value, assignments)
        for item in settings_class.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    documented_settings = {}
    for table in markdown_tables(reference, "Setting", "Default"):
        for row in table:
            if len(row) >= 2:
                documented_settings[row[0]] = ast.literal_eval(row[1])
    for name, value in documented_settings.items():
        if name not in actual_settings or actual_settings[name] != value:
            raise ValueError(
                f"docs/reference/index.md: setting {name!r} default differs from "
                "django_api_versioning/settings.py; update the reference table."
            )

    decorator_tree = ast.parse(decorators_source)
    endpoint = next(
        item
        for item in decorator_tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "endpoint"
    )
    positional = endpoint.args.args
    defaults = endpoint.args.defaults
    required = len(positional) - len(defaults)
    actual_arguments = {}
    for index, argument in enumerate(positional):
        actual_arguments[argument.arg] = (
            "required"
            if index < required
            else ast.literal_eval(defaults[index - required])
        )
    for argument, default in zip(endpoint.args.kwonlyargs, endpoint.args.kw_defaults):
        actual_arguments[argument.arg] = (
            "required" if default is None else ast.literal_eval(default)
        )
    documented_arguments = {}
    for table in markdown_tables(reference, "Argument", "Default"):
        for row in table:
            if len(row) >= 2:
                documented_arguments[row[0]] = (
                    "required" if row[1] == "required" else ast.literal_eval(row[1])
                )
    if actual_arguments != documented_arguments:
        missing = sorted(set(actual_arguments) - set(documented_arguments))
        stale = sorted(set(documented_arguments) - set(actual_arguments))
        changed = sorted(
            name
            for name in set(actual_arguments) & set(documented_arguments)
            if actual_arguments[name] != documented_arguments[name]
        )
        raise ValueError(
            "docs/reference/index.md: @endpoint arguments/defaults differ from "
            f"django_api_versioning/decorators.py (missing={missing}, stale={stale}, "
            f"changed={changed}); update the reference table."
        )


def _classifiers(pyproject: str, prefix: str) -> set[str]:
    return set(re.findall(re.escape(prefix) + r"([0-9]+\.[0-9]+)", pyproject))


def _tox_matrix(tox: str) -> dict[str, list[str]]:
    match = re.search(r"(?ms)^\[tox\]\s+.*?^envlist\s*=\s*(.*?)(?=^\S|\Z)", tox)
    if match is None:
        raise ValueError("tox.ini: canonical [tox] envlist could not be parsed.")
    matrix = {}
    for python_versions, django_version in re.findall(
        r"py\{([^}]+)\}-django([0-9]+)", match.group(1)
    ):
        django = f"{django_version[0]}.{django_version[1:]}"
        matrix[django] = [f"{item[0]}.{item[1:]}" for item in python_versions.split(",")]
    return matrix


def verify_compatibility_article(article: str, pyproject: str, tox: str) -> None:
    python_versions = _classifiers(pyproject, "Programming Language :: Python :: ")
    django_versions = _classifiers(pyproject, "Framework :: Django :: ")
    documented_python = {
        row[0]
        for table in markdown_tables(
            article, "Python version", "Listed in package classifiers?"
        )
        for row in table
        if len(row) >= 2 and row[1].casefold() == "yes"
    }
    documented_django = {
        row[0]
        for table in markdown_tables(
            article, "Django version", "Listed in package classifiers?"
        )
        for row in table
        if len(row) >= 2 and row[1].casefold() == "yes"
    }
    if documented_python != python_versions:
        raise ValueError(
            "docs/articles/024...: Python classifier table differs from "
            "pyproject.toml; update the documented versions."
        )
    if documented_django != django_versions:
        raise ValueError(
            "docs/articles/024...: Django classifier table differs from "
            "pyproject.toml; update the documented versions."
        )

    configured = _tox_matrix(tox)
    documented = {}
    for table in markdown_tables(article, "Django version", "Python versions"):
        for row in table:
            if len(row) >= 3:
                versions = [item.strip() for item in row[1].split(",")]
                if int(row[2]) != len(versions):
                    raise ValueError(
                        f"docs/articles/024...: Django {row[0]} environment count "
                        "does not match its Python version list."
                    )
                documented[row[0]] = versions
    if documented != configured:
        raise ValueError(
            "docs/articles/024...: configured Python/Django combinations differ "
            "from tox.ini; update the table and per-row counts."
        )
    total = sum(len(versions) for versions in configured.values())
    if not re.search(
        rf"This results in {total} configured test environments\.", article
    ):
        raise ValueError(
            f"docs/articles/024...: environment total must be {total} according to tox.ini."
        )
