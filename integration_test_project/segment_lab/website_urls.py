# isort: skip_file
from django.urls import include, path
from segment_lab.scenarios import website_quick_start as views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
