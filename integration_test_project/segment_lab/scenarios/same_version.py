"""
"same_version": two different views declare the same route with the same
starting version.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_original(request):
    return JsonResponse({"handler": "list_users_original"})


# Same postfix, same version, different function (e.g. a copy-paste or a
# second app declaring the same path).
@endpoint("users/", version=1, view_name="user-list")
def list_users_duplicate(request):
    return JsonResponse({"handler": "list_users_duplicate"})