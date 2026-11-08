"""
URL configuration for integration test project.

IMPORTANT: The views MUST be imported before django_api_versioning.urls
so that the @endpoint decorators execute and register the routes.
"""
# Import views first to trigger @endpoint decorator registration
from api import views  # noqa: F401

from django.urls import path, include
from django_api_versioning.urls import urlpatterns as api_urlpatterns
from django_api_versioning.decorators import endpoint

# Router-based ViewSet configuration for testing
try:
    from rest_framework.routers import DefaultRouter, SimpleRouter

    # DefaultRouter for v1
    router_v1 = DefaultRouter()
    router_v1.register(r'blogposts', views.BlogPostViewSetV1, basename='blogpost-v1')

    # SimpleRouter for v2
    router_v2 = SimpleRouter()
    router_v2.register(r'blogposts', views.BlogPostViewSetV2, basename='blogpost-v2')

    # Wrap router URLs with @endpoint decorator for versioning
    # Version 1
    router_v1_urlpatterns = endpoint("blog/", version=1, view_name="blog-router-v1")(
        lambda request: None
    )
    # Note: This is a workaround - routers don't directly support @endpoint.
    # Instead, we'll add the router URLs directly and test them separately.

    router_urls = [
        path('api/v1/', include(router_v1.urls)),
        path('api/v2/', include(router_v2.urls)),
    ]
except ImportError:
    router_urls = []

urlpatterns = [
    # Standard unversioned routes
    path("health/", views.health_check, name="health"),
    path("status/", views.status_endpoint, name="status"),
    # Router-based URLs for testing ViewSet integration
    *router_urls,
    # Include versioned API routes automatically managed by django-api-versioning
    # The @endpoint decorators on view functions automatically register with the package
    path("", include(api_urlpatterns)),
]
