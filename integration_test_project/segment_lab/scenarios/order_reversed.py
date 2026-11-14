"""
"order_reversed": the same declarations as catalog/views.py, but the v3
declaration is imported BEFORE the v1 declaration.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=3, view_name="user-list")
def list_users_v3(request):
    return JsonResponse({"handler": "list_users_v3"})


@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse({"handler": "list_users_v1"})


@endpoint("users/<int:pk>/", version=1, view_name="user-detail")
def user_detail(request, pk):
    return JsonResponse({"handler": "user_detail", "id": pk})


@endpoint("health/", view_name="health")
def health(request):
    return JsonResponse({"handler": "health", "status": "ok"})
