"""Executable fixture for the CLI output shown in the website."""

from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def users_list_v1(request):
    return JsonResponse({"handler": "users_list_v1"})


@endpoint("users/", version=2, view_name="user-list")
def users_list_v2(request):
    return JsonResponse({"handler": "users_list_v2"})
