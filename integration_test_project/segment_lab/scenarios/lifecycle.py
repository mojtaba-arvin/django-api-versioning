"""
"lifecycle": LifecycleMiddleware enabled (see lab/scenarios.py for
API_VERSION_LIFECYCLE). The routes themselves are ordinary @endpoint routes.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse({"handler": "list_users_v1"})


@endpoint("users/", version=3, view_name="user-list")
def list_users_v3(request):
    return JsonResponse({"handler": "list_users_v3"})
