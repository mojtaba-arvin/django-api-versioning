export const snippets = {
  heroView: `from django_api_versioning import endpoint
from rest_framework.views import APIView
from rest_framework.response import Response

@endpoint("invoices/<int:invoice_id>/", version=2, view_name="invoice-detail")
class InvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        return Response({"id": invoice_id, "status": "paid"})`,

  settings: `# settings.py
INSTALLED_APPS = [
    # ...
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3`,

  urls: `# urls.py
from django.urls import include, path
from your_app import views  # noqa: F401 — import endpoint modules first
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]`,

  checkVersions: `$ python manage.py check_versions
users/:
  v1           → users_list_v1
  v2           → users_list_v2
  v3           → users_list_v2
  v4           → users_list_v2`,

  snapshot: `from django_api_versioning.testing import assert_version_matrix

def test_version_matrix():
    # Creates the snapshot on first run.
    # Raises VersionMatrixError with a diff when routes change.
    assert_version_matrix(snapshot=".version_matrix.json")

# Accept an intentional change:
# assert_version_matrix(snapshot=".version_matrix.json", update=True)`,

  reverse: `from django_api_versioning import api_reverse

url = api_reverse("order-list", version=2)

# version can be omitted when only one route has the name
url = api_reverse("health-check")

# ...but raises AmbiguousVersionError if several match.`,

  lifecycle: `MIDDLEWARE = [
    # ...
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]

API_VERSION_LIFECYCLE = {
    1: {"status": "retired", "sunset": "2025-01-01"},
    2: {
        "status": "deprecated",
        "deprecated_at": "2026-01-01T00:00:00+00:00",
        "sunset": "2027-06-01",
    },
    3: {"status": "active"},
}`,

  migrate: `$ python manage.py migrate_endpoints --dry-run`,

  dev: `$ pip install -e ".[dev]" && pre-commit install
$ python -m pytest tests
$ python -m pytest integration_test_project
$ tox run-parallel -p auto`,
}

export const features = [
  {
    title: 'Declare once, serve forward',
    body: 'Decorate a view with @endpoint and a starting version. Every later version reuses it until a newer implementation takes over.',
    icon: '→',
  },
  {
    title: 'Generated URL patterns',
    body: 'The package builds versioned routes from API_BASE_PATH. No hand-maintained v1/, v2/, v3/ URLconfs.',
    icon: '{}',
  },
  {
    title: 'Django & DRF',
    body: 'Use @endpoint for Django views and APIViews, or VersionedRouter for DRF ViewSets. DRF remains optional for Django-native projects.',
    icon: '⌘',
  },
  {
    title: 'Route matrix & gap checks',
    body: 'check_versions prints every logical endpoint across versions and warns about gaps inside a span.',
    icon: '▦',
  },
  {
    title: 'CI snapshot guard',
    body: 'assert_version_matrix pins the matrix to a JSON snapshot so accidental route changes fail the build.',
    icon: '✓',
  },
  {
    title: 'Deprecation & Sunset',
    body: 'LifecycleMiddleware handles version-wide deprecation and retirement. Version 1.2.0 adds endpoint-level lifecycle headers and optional OpenAPI deprecation metadata.',
    icon: '◐',
  },
  {
    title: 'Versioned DRF ViewSets',
    body: 'VersionedRouter delegates URL generation to DRF SimpleRouter and inherits or replaces implementations per generated action.',
    icon: '⇄',
  },
  {
    title: 'Explicit route removal',
    body: 'Version 1.2.0 adds remove_endpoint() and VersionedRouter.remove() so inherited routes can be removed from a chosen version onward.',
    icon: '−',
  },
]

export const patterns = [
  {
    name: 'Forward segment',
    code: '@endpoint("reports/", version=3)',
    on: [3, 4, 5],
    result: 'v3 → v5',
  },
  {
    name: 'Explicit set',
    code: '@endpoint("ranking/", versions=[2, 4])',
    on: [2, 4],
    result: 'v2 and v4 only',
  },
  {
    name: 'Bounded range',
    code: '@endpoint("legacy/", versions=ver_range(1, 3))',
    on: [1, 2, 3],
    result: 'v1 → v3 inclusive',
  },
  {
    name: 'Unversioned',
    code: '@endpoint("health/")',
    on: [],
    result: '/health/',
  },
]

export const caveats = [
  {
    title: 'Routing is not semantic compatibility',
    body: 'The package isolates implementations and can lock path contracts. It does not transform serializers or payloads, and it does not claim backward-compatible behavior. Contract and response tests stay yours.',
  },
  {
    title: 'Make the matrix visible before release',
    body: 'Endpoint-to-view mapping is not line-by-line in urls.py. That is the DRY trade-off. Run check_versions and pin assert_version_matrix(strict=True) in CI so the real matrix is reviewed and locked.',
  },
  {
    title: 'Import order and route settings timing',
    body: 'Import endpoint modules in the root URLconf before including django_api_versioning.urls. Changing route settings after patterns are imported does not rebuild the registry; LifecycleMiddleware still reads lifecycle settings per request.',
  },
  {
    title: 'One negotiation scheme; path-based resolution',
    body: 'Choose path, header, query, or hostname with API_VERSIONING_SCHEME. Non-path schemes need VersionNegotiationMiddleware, which rewrites the internal path so the same registry serves the view. There is no multi-scheme fallback chain.',
  },
  {
    title: 'ViewSet routers have a clear scope',
    body: 'VersionedRouter follows SimpleRouter. Use VersionedDefaultRouter when you need a version-specific API root and format suffixes. Configure VersionedRouterVersioning when ViewSets need request.version, reverse_action(), or hyperlinked URLs. Neither transforms serializers.',
  },
  {
    title: 'Keep a replaceable integration boundary',
    body: 'Confine package imports to one project module that exposes your URL patterns. If you ever leave the package, rewrite only that module—views and the root URLconf stay free of package internals.',
  },
]
