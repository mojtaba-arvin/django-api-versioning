#!/usr/bin/env python
"""Management entry point for the consumer migration example."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

if __name__ == "__main__":
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "consumer_migration_project.settings"
    )
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
