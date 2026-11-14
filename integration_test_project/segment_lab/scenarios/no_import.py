"""
"no_import": this module is NOT imported by lab/urls.py in its scenario
(LAB_VIEWS_MODULE = None). The declaration below is valid but never runs.
"""
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse({"handler": "list_users_v1"})