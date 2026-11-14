"""
Main scenario: the /users/ contract changes in v3.

API_MIN_VERSION = 1, API_MAX_VERSION = 3 (lab/settings.py).
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse(
        {
            "handler": "list_users_v1",
            "results": [{"id": 7, "name": "Noor Haddad"}],
        }
    )


@endpoint("users/", version=3, view_name="user-list")
def list_users_v3(request):
    # v3 contract: "name" is split, and the list gains a "count" envelope.
    return JsonResponse(
        {
            "handler": "list_users_v3",
            "count": 1,
            "results": [{"id": 7, "given_name": "Noor", "family_name": "Haddad"}],
        }
    )


@endpoint("users/<int:pk>/", version=1, view_name="user-detail")
def user_detail(request, pk):
    return JsonResponse({"handler": "user_detail", "id": pk})


@endpoint("health/", view_name="health")
def health(request):
    return JsonResponse({"handler": "health", "status": "ok"})
