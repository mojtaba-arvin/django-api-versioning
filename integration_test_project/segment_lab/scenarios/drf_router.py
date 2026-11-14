"""
"drf_router": a DRF router mounted for v2 next to @endpoint routes.

lab/urls.py places ``urlpatterns_before_registry`` in front of the
package's generated patterns.
"""

from django.http import JsonResponse
from django.urls import include, path
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter

from django_api_versioning import endpoint


@endpoint("users/", version=1, view_name="user-list")
def list_users_v1(request):
    return JsonResponse({"handler": "list_users_v1"})


class UserViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"handler": "UserViewSet.list"})

    def retrieve(self, request, pk=None):
        return Response({"handler": "UserViewSet.retrieve", "pk": pk})


router = SimpleRouter()
router.register("users", UserViewSet, basename="router-user")

urlpatterns_before_registry = [path("api/v2/", include(router.urls))]
