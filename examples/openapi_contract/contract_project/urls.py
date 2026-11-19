"""The public VersionedRouter instance drives runtime and schema generation."""

import os

from contract_app.views import ProductViewSetV1, ProductViewSetV2

from django_api_versioning.routers import VersionedRouter

router = VersionedRouter()
router.register("products", ProductViewSetV1, version=1, basename="product")
router.register("products", ProductViewSetV2, version=2, basename="product")
router.remove("products", "product-legacy-export", from_version=2)

# Isolated schema scenario; the normal contract baselines remain unchanged.
if os.environ.get("ENDPOINT_LIFECYCLE_SCHEMA_TEST") == "1":
    router.set_lifecycle(
        "products",
        "product-list",
        version=1,
        action="list",
        deprecated_at="2030-01-01T00:00:00Z",
    )

urlpatterns = router.urls
