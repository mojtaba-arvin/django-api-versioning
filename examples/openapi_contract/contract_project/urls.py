"""The public VersionedRouter instance drives runtime and schema generation."""

from contract_app.views import ProductViewSetV1, ProductViewSetV2
from django_api_versioning.routers import VersionedRouter

router = VersionedRouter()
router.register("products", ProductViewSetV1, version=1, basename="product")
router.register("products", ProductViewSetV2, version=2, basename="product")
urlpatterns = router.urls
