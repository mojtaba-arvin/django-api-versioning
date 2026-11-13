from collections import defaultdict

from django.core.management.base import BaseCommand

from ...registry import registry
from ...settings import api_settings as settings


class Command(BaseCommand):
    help = "Print the API version matrix and warn about gaps."

    def handle(self, *args, **options):
        # Use logical version matrix to group by logical endpoint, not physical URL
        matrix = registry.get_logical_version_matrix()
        grouped = defaultdict(dict)
        for endpoint, versions in matrix.items():
            grouped[endpoint] = versions

        if not grouped:
            self.stdout.write("No endpoints registered.")
            return

        for endpoint in sorted(grouped):
            self.stdout.write(f"\n{endpoint}:")
            versions = grouped[endpoint]
            for version in sorted(versions, key=lambda v: (v is not None, v)):
                label = "unversioned" if version is None else f"v{version}"
                callback_name = self._get_callback_name(versions[version])
                self.stdout.write(f"  {label:12} → {callback_name}")

        self._warn_gaps(grouped)

    @staticmethod
    def _get_callback_name(callback):
        """Resolve callback name, handling both functions and class-based views."""
        # Try to get from class-based view metadata first
        if hasattr(callback, "view_class"):
            return callback.view_class.__name__
        # Try to get from ViewSet action callback
        if hasattr(callback, "cls"):
            return callback.cls.__name__
        # Fallback to __name__ attribute
        if hasattr(callback, "__name__"):
            return callback.__name__
        # Final fallback for callable instances
        return callback.__class__.__name__

    def _warn_gaps(self, grouped):
        for endpoint, versions in grouped.items():
            numeric = sorted(v for v in versions if v is not None)
            if not numeric:
                # Unversioned endpoints don't have gaps
                continue

            # Only check for gaps within the endpoint's actual span
            min_registered = min(numeric)
            max_registered = max(numeric)

            for v in range(min_registered, max_registered + 1):
                if v not in versions:
                    self.stdout.write(
                        self.style.WARNING(f"  [{endpoint}] v{v} is not defined.")
                    )
