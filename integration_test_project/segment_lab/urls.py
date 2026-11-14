"""
Root URLconf.

@endpoint registers routes as a side effect of importing the module that
contains the decorated views, so that module is imported here, before the
package's generated patterns are included.
"""
from importlib import import_module

from django.conf import settings
from django.urls import include, path

views = import_module(settings.LAB_VIEWS_MODULE) if settings.LAB_VIEWS_MODULE else None

urlpatterns = [
    # Scenario-only hook (used by the DRF router scenario): plain Django
    # patterns that sit in front of the generated ones.
    *getattr(views, "urlpatterns_before_registry", []),
    # Every route registered by @endpoint (django_api_versioning.urls
    # exposes the registry's own urlpatterns list).
    path("", include("django_api_versioning.urls")),
]