#!/usr/bin/env python
"""Management entry point for the versioned OpenAPI contract example."""
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
