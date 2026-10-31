import re
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Suggest 0.3.0 replacements for 0.2.0 @endpoint declarations."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False)
        parser.add_argument("--path", default=".")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        root = Path(options["path"])
        for py_file in root.rglob("*.py"):
            if "migrations" in py_file.parts:
                continue
            text = py_file.read_text()
            if "@endpoint" not in text:
                continue
            changes = _suggest(text)
            if not changes:
                continue
            self.stdout.write(f"\n{py_file}:")
            for old, new in changes:
                self.stdout.write(f"  - {old}")
                self.stdout.write(f"  + {new}")
                if not dry_run:
                    text = text.replace(old, new)
            if not dry_run:
                py_file.write_text(text)


def _suggest(text: str):
    changes = []
    pattern = re.compile(r"@endpoint\((?P<args>[^)]*)\)")
    for match in pattern.finditer(text):
        args = match.group("args")
        if "forward" not in args and "backward" not in args:
            continue
        old = match.group(0)
        new = _rewrite_args(args)
        changes.append((old, f"@endpoint({new})"))
    return changes


def _rewrite_args(args: str) -> str:
    version_match = re.search(r"version\s*=\s*(\d+)", args)
    if not version_match:
        return args

    version = int(version_match.group(1))

    # 0.2.0 defaults: backward=False, forward=True (segment behaviour).
    backward_match = re.search(r"backward\s*=\s*(True|False)", args)
    forward_match = re.search(r"forward\s*=\s*(True|False|None)", args)

    backward = (backward_match.group(1) == "True") if backward_match else False
    forward = (forward_match.group(1) == "True") if forward_match else True

    # Strip version / backward / forward from the original args.
    cleaned = re.sub(r"version\s*=\s*\d+\s*,?", "", args)
    cleaned = re.sub(r"backward\s*=\s*(True|False)\s*,?", "", cleaned)
    cleaned = re.sub(r"forward\s*=\s*(True|False|None)\s*,?", "", cleaned)
    cleaned = re.sub(r",\s*\)", ")", cleaned).strip().rstrip(",")

    prefix = f"{cleaned}, " if cleaned else ""

    if backward and forward:
        return f"{prefix}version=1"
    if backward and not forward:
        return f"{prefix}versions=ver_range(1, {version})"
    if not backward and not forward:
        return f"{prefix}versions=[{version}]"
    # backward=False, forward=True  →  segment, unchanged
    return f"{prefix}version={version}"
