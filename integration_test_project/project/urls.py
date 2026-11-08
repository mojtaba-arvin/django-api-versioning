"""
URL configuration for integration test project.

IMPORTANT: The views MUST be imported before django_api_versioning.urls
so that the @endpoint decorators execute and register the routes.
"""
# Import views first to trigger @endpoint decorator registration
from api import views  # noqa: F401

from django.urls import path, include
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # Standard unversioned routes
    path("health/", views.health_check, name="health"),
    # Include versioned API routes automatically managed by django-api-versioning
    # The @endpoint decorators on view functions automatically register with the package
    path("", include(api_urlpatterns)),
]
