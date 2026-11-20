"""Consumer-owned adapter: the only module importing django-api-versioning.

Application views and the project's root URLconf depend on this module's
get_urlpatterns() contract, not on package internals. Replace this module with
ordinary Django URL patterns or DRF routers to remove the package dependency.
"""

import os

from django_api_versioning import endpoint, set_endpoint_lifecycle
from django_api_versioning.registry import registry
from django_api_versioning.routers import VersionedRouter

from .decorated_views import decorated_status
from .views import ProductViewSetV1, ProductViewSetV2


def get_urlpatterns():
    """Build the application's API URL patterns through the selected adapter."""
    router = VersionedRouter()
    router.register("products", ProductViewSetV1, version=1, basename="product")
    router.register("products", ProductViewSetV2, version=2, basename="product")
    router.remove("products", "product-legacy-export", from_version=2)

    # Isolated schema scenario: it must not change the released baseline.
    if os.environ.get("ENDPOINT_LIFECYCLE_SCHEMA_TEST") == "1":
        router.set_lifecycle(
            "products",
            "product-list",
            version=1,
            action="list",
            deprecated_at="2030-01-01T00:00:00Z",
        )

        endpoint(
            "decorated-status/",
            versions=[1, 2],
            view_name="decorated-status",
        )(decorated_status)
        set_endpoint_lifecycle(
            "decorated-status/",
            version=1,
            methods=["GET"],
            deprecated_at="2030-01-01T00:00:00Z",
        )
        decorator_patterns = [
            pattern
            for pattern in registry.urlpatterns
            if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == "decorated-status/"
        ]
        return router.urls + decorator_patterns

    return router.urls
