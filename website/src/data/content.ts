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
    body: 'LifecycleMiddleware handles version-wide deprecation and retirement. The upcoming 1.2.0 release adds route-level lifecycle headers and optional OpenAPI deprecation metadata; publication is pending.',
    icon: '◐',
  },
  {
    title: 'Versioned DRF ViewSets',
    body: 'VersionedRouter delegates URL generation to DRF SimpleRouter and inherits or replaces implementations per generated action.',
    icon: '⇄',
  },
  {
    title: 'Explicit route removal',
    body: 'The upcoming 1.2.0 release adds remove_endpoint() and VersionedRouter.remove() so inherited routes can be removed from a chosen version onward; publication is pending.',
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
    title: 'request.version depends on the registration path',
    body: '@endpoint selects a view through its URL pattern but does not populate DRF request.version. Configure a DRF versioning scheme separately for decorator-registered views; use VersionedRouterVersioning for ViewSets registered through VersionedRouter.',
  },
  {
    title: 'Route settings and lifecycle settings have different timing',
    body: 'Changing route settings after URL patterns are imported does not rebuild the registry. LifecycleMiddleware reads lifecycle settings per request.',
  },
  {
    title: 'Import order matters',
    body: 'Import your endpoint modules in the root URLconf before including django_api_versioning.urls.',
  },
  {
    title: 'ViewSet integration scope',
    body: 'VersionedRouter supports DRF SimpleRouter, not DefaultRouter API-root or format-suffix behavior. It selects route callbacks; it does not transform serializers or response payloads.',
  },
  {
    title: 'Path-based version selection',
    body: 'The package selects implementations from concrete URL-path routes. Header, query-parameter, hostname, and tenant negotiation are not enabled by the reserved channel settings.',
  },
  {
    title: 'Routing is not contract compatibility',
    body: 'The registry selects the view callable for each route. Your application still owns serializer and response compatibility, permissions, business behavior, and contract tests.',
  },
  {
    title: 'Explicit registration, not auto-discovery',
    body: 'Import modules that declare @endpoint before the generated URL patterns are resolved. The package does not scan arbitrary application modules or provide a built-in version-discovery endpoint.',
  },
]
