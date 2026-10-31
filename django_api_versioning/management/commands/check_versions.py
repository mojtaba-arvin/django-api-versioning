from collections import defaultdict

from django.core.management.base import BaseCommand

from ...registry import registry
from ...settings import api_settings as settings


class Command(BaseCommand):
    help = "Print the API version matrix and warn about gaps."

    def handle(self, *args, **options):
        matrix = registry.get_version_matrix()
        grouped = defaultdict(dict)
        for route, versions in matrix.items():
            grouped[route] = versions

        for route in sorted(grouped):
            self.stdout.write(f"\n{route}:")
            versions = grouped[route]
            for version in sorted(versions, key=lambda v: (v is not None, v)):
                label = "unversioned" if version is None else f"v{version}"
                callback = versions[version].__name__
                self.stdout.write(f"  {label:12} → {callback}")

        self._warn_gaps(grouped)

    def _warn_gaps(self, grouped):
        min_v = settings.API_MIN_VERSION
        max_v = settings.API_MAX_VERSION
        for route, versions in grouped.items():
            numeric = sorted(v for v in versions if v is not None)
            if not numeric:
                continue
            for v in range(min_v, max_v + 1):
                if v not in versions:
                    self.stdout.write(
                        self.style.WARNING(f"  [{route}] v{v} is not defined.")
                    )
