import ast
import difflib
import io
import os
import re
import stat
import tempfile
import tokenize
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "site-packages",
    "__pycache__",
    "migrations",
    "build",
    "dist",
}
_LEGACY_FLAGS = {"backward", "forward", "version"}
_LEGACY_MARKER = re.compile(
    r"@(?:[A-Za-z_]\w*\.)*endpoint\s*\("
)
_LEGACY_FLAG_MARKER = re.compile(r"\b(?:backward|forward)\s*=")


class Command(BaseCommand):
    help = (
        "Preview 0.2.0 @endpoint flag migrations. "
        "Pass --write to modify source files."
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--write",
            action="store_true",
            help="Apply the suggested changes to source files.",
        )
        mode.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying source files (the default).",
        )
        mode.add_argument(
            "--diff",
            action="store_true",
            help="Print a unified source diff without modifying files.",
        )
        parser.add_argument("--path", default=".")

    def handle(self, *args, **options):
        root = Path(options["path"]).expanduser().resolve()
        if not root.is_dir():
            raise CommandError(f"Migration path is not a directory: {root}")

        files_scanned = 0
        rewrite_count = 0
        skipped: list[tuple[str, int, str]] = []
        applied_files: list[str] = []
        py_files = sorted(
            root.rglob("*.py"),
            key=lambda item: item.relative_to(root).as_posix(),
        )

        for py_file in py_files:
            relative_parts = py_file.relative_to(root).parts
            if (
                py_file.is_symlink()
                or py_file.name.startswith(".")
                or any(
                    part in _EXCLUDED_DIRS or part.startswith(".")
                    for part in relative_parts[:-1]
                )
            ):
                continue

            files_scanned += 1
            relative_path = py_file.relative_to(root).as_posix()
            raw = py_file.read_bytes()
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            text = raw.decode(encoding)
            rewrites, file_skips = _collect_analysis(text)
            skipped.extend(
                (relative_path, line, reason)
                for line, _, _, reason in file_skips
            )

            updated = _apply_rewrites(text, rewrites)
            if updated == text and not file_skips:
                continue

            if options["diff"]:
                if updated != text:
                    self.stdout.writelines(
                        difflib.unified_diff(
                            text.splitlines(keepends=True),
                            updated.splitlines(keepends=True),
                            fromfile=relative_path,
                            tofile=relative_path,
                        )
                    )
            else:
                self.stdout.write(f"\n{py_file}:")
                for _, _, old, new in rewrites:
                    self.stdout.write(f"  - @{old}")
                    self.stdout.write(f"  + @{new}")
                for line, _, _, reason in file_skips:
                    self.stdout.write(
                        f"  ! {relative_path}:{line}: {reason}"
                    )

            if updated != text:
                rewrite_count += len(rewrites)
                if options["write"]:
                    try:
                        _atomic_write(py_file, updated.encode(encoding))
                    except OSError as exc:
                        details = (
                            f"Could not update {relative_path}: {exc}. "
                            f"Already updated files: "
                            f"{', '.join(applied_files) if applied_files else 'none'}."
                        )
                        self.stdout.write(details)
                        raise CommandError(details) from exc
                    applied_files.append(relative_path)

        if options["diff"] and skipped:
            self.stdout.write("\nSkipped legacy decorators (manual review required):")
            for relative_path, line, reason in skipped:
                self.stdout.write(f"  {relative_path}:{line}: {reason}")

        if rewrite_count or skipped:
            self.stdout.write(
                f"\nSummary: {rewrite_count} rewritable legacy decorator(s); "
                f"{len(skipped)} skipped for manual review; "
                f"{files_scanned} Python file(s) scanned."
            )


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace one source file atomically while preserving its permission bits."""
    original_mode = stat.S_IMODE(path.stat().st_mode)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, original_mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def _is_endpoint_call(func: ast.expr) -> bool:
    return (isinstance(func, ast.Name) and func.id == "endpoint") or (
        isinstance(func, ast.Attribute) and func.attr == "endpoint"
    )


def _has_comments(source: str) -> bool:
    try:
        return any(
            token.type == tokenize.COMMENT
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
        )
    except tokenize.TokenError:
        return True


def _literal_integer(node: ast.expr | None) -> int | None:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    return None


def _literal_boolean(node: ast.expr | None, default: bool) -> bool | None:
    if node is None:
        return default
    if not isinstance(node, ast.Constant) or type(node.value) is not bool:
        return None
    return node.value


def _literal_forward(node: ast.expr | None) -> bool | None:
    if node is None:
        return True
    if not isinstance(node, ast.Constant):
        return None
    if type(node.value) is bool:
        return node.value
    if node.value is None:
        return False
    return None


def _legacy_options(call: ast.Call) -> tuple[int, bool, bool] | None:
    if any(keyword.arg == "versions" for keyword in call.keywords):
        return None
    if not any(keyword.arg in {"backward", "forward"} for keyword in call.keywords):
        return None

    keywords: dict[str, ast.expr] = {}
    for keyword in call.keywords:
        if keyword.arg in _LEGACY_FLAGS:
            if keyword.arg in keywords:
                return None
            keywords[keyword.arg] = keyword.value

    version = _literal_integer(keywords.get("version"))
    if version is None:
        return None

    backward = _literal_boolean(keywords.get("backward"), default=False)
    forward = _literal_forward(keywords.get("forward"))
    if backward is None or forward is None:
        return None
    return version, backward, forward


def _legacy_skip_reason(text: str, call: ast.Call) -> str:
    call_source = ast.get_source_segment(text, call)
    if call_source is None:
        return "source segment could not be recovered safely"
    if _has_comments(call_source):
        return "contains comments inside the decorator; preserve and migrate manually"
    if any(keyword.arg is None for keyword in call.keywords):
        return "contains a **kwargs expansion that may conflict with rewritten arguments"
    if any(keyword.arg == "versions" for keyword in call.keywords):
        return "combines legacy flags with an explicit versions argument"

    keywords: dict[str, ast.expr] = {}
    for keyword in call.keywords:
        if keyword.arg not in _LEGACY_FLAGS:
            continue
        if keyword.arg in keywords:
            return f"contains duplicate {keyword.arg}= arguments"
        keywords[keyword.arg] = keyword.value

    if len(call.args) > 1:
        return "supplies the legacy version positionally; use a literal version= keyword"
    if "version" not in keywords:
        return "is missing a literal version= keyword"
    if _literal_integer(keywords.get("version")) is None:
        return "version must be a literal integer"
    if _literal_boolean(keywords.get("backward"), default=False) is None:
        return "backward must be a literal boolean"
    if _literal_forward(keywords.get("forward")) is None:
        return "forward must be a literal boolean or None"
    return "could not be reconstructed safely; migrate this decorator manually"


def _legacy_version_argument(version: int, backward: bool, forward: bool) -> str:
    if backward and forward:
        return "version=1"
    if backward:
        return f"versions=list(range(1, {version + 1}))"
    if not forward:
        return f"versions=[{version}]"
    return f"version={version}"


def _rewrite_call(text: str, call: ast.Call) -> str | None:
    legacy = _legacy_options(call)
    if legacy is None or any(keyword.arg is None for keyword in call.keywords):
        return None

    call_source = ast.get_source_segment(text, call)
    function_source = ast.get_source_segment(text, call.func)
    if not call_source or not function_source or _has_comments(call_source):
        return None

    remaining = []
    for argument in call.args:
        segment = ast.get_source_segment(text, argument)
        if segment is None:
            return None
        remaining.append(segment)

    for keyword in call.keywords:
        if keyword.arg in _LEGACY_FLAGS:
            continue
        segment = ast.get_source_segment(text, keyword)
        if segment is None:
            return None
        remaining.append(segment)

    remaining.append(_legacy_version_argument(*legacy))
    return f"{function_source}({', '.join(remaining)})"


def _absolute_offset(text: str, lineno: int, utf8_column: int) -> int:
    lines = text.splitlines(keepends=True)
    prefix = sum(len(line) for line in lines[: lineno - 1])
    line = lines[lineno - 1]
    character_column = len(line.encode("utf-8")[:utf8_column].decode("utf-8"))
    return prefix + character_column


def _collect_analysis(
    text: str,
) -> tuple[
    list[tuple[int, int, str, str]],
    list[tuple[int, int, str, str]],
]:
    """Return safe rewrites and line-addressable unsupported legacy occurrences."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        if _LEGACY_MARKER.search(text) and _LEGACY_FLAG_MARKER.search(text):
            reason = f"file syntax error prevents safe inspection: {exc.msg}"
            return [], [(exc.lineno or 1, exc.offset or 0, "", reason)]
        return [], []

    rewrites = []
    skipped = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not _is_endpoint_call(
                decorator.func
            ):
                continue
            if not any(
                keyword.arg in {"backward", "forward"}
                for keyword in decorator.keywords
            ):
                continue

            replacement = _rewrite_call(text, decorator)
            if replacement is None:
                old = ast.get_source_segment(text, decorator) or ""
                skipped.append(
                    (
                        decorator.lineno,
                        decorator.col_offset,
                        old,
                        _legacy_skip_reason(text, decorator),
                    )
                )
                continue

            old = ast.get_source_segment(text, decorator)
            if old is None:
                skipped.append(
                    (
                        decorator.lineno,
                        decorator.col_offset,
                        "",
                        "source segment could not be recovered safely",
                    )
                )
                continue

            start = _absolute_offset(text, decorator.lineno, decorator.col_offset)
            end = _absolute_offset(
                text, decorator.end_lineno, decorator.end_col_offset
            )
            if replacement != old:
                rewrites.append((start, end, old, replacement))

    return (
        sorted(rewrites, key=lambda item: item[0]),
        sorted(skipped, key=lambda item: (item[0], item[1])),
    )


def _collect_rewrites(text: str) -> list[tuple[int, int, str, str]]:
    """Compatibility wrapper returning only safe source replacements."""
    return _collect_analysis(text)[0]


def _apply_rewrites(text: str, rewrites: list[tuple[int, int, str, str]]) -> str:
    updated = text
    for start, end, _, replacement in reversed(rewrites):
        updated = updated[:start] + replacement + updated[end:]
    return updated


def _suggest(text: str) -> list[tuple[str, str]]:
    return [(f"@{old}", f"@{new}") for _, _, old, new in _collect_rewrites(text)]


def _rewrite_args(args: str) -> str:
    source = f"__endpoint({args})"
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError:
        return args

    call = tree.body
    if not isinstance(call, ast.Call):
        return args

    replacement = _rewrite_call(source, call)
    if replacement is None:
        return args

    opening = replacement.find("(")
    return replacement[opening + 1 : -1]
