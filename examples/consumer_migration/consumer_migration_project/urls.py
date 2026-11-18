"""Versioned routes for the consumer migration walkthrough."""

from consumer_app.views import (
    OrderViewSetV1,
    OrderViewSetV2,
    OrderViewSetV3,
)

from django_api_versioning.routers import VersionedRouter

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")
router.register("orders", OrderViewSetV3, version=3, basename="order")
router.remove("orders", "order-legacy-export", from_version=3)

urlpatterns = router.urls
