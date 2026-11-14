"""
"explicit_versions": versions=[...] and ver_range(...) next to version=N.

API_MIN_VERSION = 1, API_MAX_VERSION = 4.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint, ver_range


# Only v2. Not carried forward.
@endpoint("export/", versions=[2], view_name="export")
def export_v2(request):
    return JsonResponse({"handler": "export_v2"})


# v1 and v2 only: an endpoint that is removed from v3 onward.
@endpoint("legacy/", versions=ver_range(1, 2), view_name="legacy")
def legacy(request):
    return JsonResponse({"handler": "legacy"})


# A segment from v1 to API_MAX_VERSION ...
@endpoint("search/", version=1, view_name="search")
def search_v1(request):
    return JsonResponse({"handler": "search_v1"})


# ... with only v3 replaced. v4 is still served by search_v1.
@endpoint("search/", versions=[3], view_name="search")
def search_v3_only(request):
    return JsonResponse({"handler": "search_v3_only"})


# Repeated decorators on one function (the package docstring's
# "revert" form): stacked declarations for v1 and v4, another view at v2.
@endpoint("feed/", version=1, view_name="feed")
@endpoint("feed/", version=4, view_name="feed")
def feed_a(request):
    return JsonResponse({"handler": "feed_a"})


@endpoint("feed/", version=2, view_name="feed")
def feed_b(request):
    return JsonResponse({"handler": "feed_b"})