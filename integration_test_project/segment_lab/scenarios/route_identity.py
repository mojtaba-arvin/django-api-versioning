"""
"route_identity": routes that a human reads as "the same endpoint" but that
are different strings.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_slash(request):
    return JsonResponse({"handler": "list_users_slash"})


# No trailing slash.
@endpoint("users", version=2, view_name="user-list")
def list_users_no_slash(request):
    return JsonResponse({"handler": "list_users_no_slash"})


@endpoint("users/<int:pk>/", version=1, view_name="user-detail")
def user_detail_pk(request, pk):
    return JsonResponse({"handler": "user_detail_pk", "kwargs": {"pk": pk}})


# Same URL shape, different converter name.
@endpoint("users/<int:id>/", version=2, view_name="user-detail")
def user_detail_id(request, id):
    return JsonResponse({"handler": "user_detail_id", "kwargs": {"id": id}})
