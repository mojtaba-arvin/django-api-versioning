"""
"min_version": API_MIN_VERSION is raised to 2 (API_MAX_VERSION = 3) while
declarations that start at v1 are still in the code.
"""

from django.http import JsonResponse

from django_api_versioning import endpoint


# Starts below API_MIN_VERSION.
@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse({"handler": "list_users_v1"})


@endpoint("users/", version=3, view_name="user-list")
def list_users_v3(request):
    return JsonResponse({"handler": "list_users_v3"})


# Explicit list that includes a version below API_MIN_VERSION.
@endpoint("orders/", versions=[1, 2, 3], view_name="order-list")
def list_orders(request):
    return JsonResponse({"handler": "list_orders"})
