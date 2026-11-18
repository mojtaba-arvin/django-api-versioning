from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from ...registry import registry
from ...testing import _load_root_urlconf


class Command(BaseCommand):
    help = "Print the API version matrix and warn about gaps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-empty",
            action="store_true",
            help=(
                "Exit with an error when no @endpoint declarations are registered. "
                "The project's root URLconf is loaded first."
            ),
        )

    def handle(self, *args, **options):
        # Resolve the root URLconf so imports of endpoint modules execute.
        _load_root_urlconf()

        # Use logical version matrix to group by logical endpoint, not physical URL
        matrix = registry.get_logical_version_matrix()
        grouped = defaultdict(dict)
        for endpoint, versions in matrix.items():
            grouped[endpoint] = versions

        if not grouped:
            message = (
                "No endpoints registered. Check that the project's root URLconf "
                "imports the modules containing @endpoint declarations."
            )
            self.stdout.write(message)
            if options.get("fail_on_empty"):
                raise CommandError(message)
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
