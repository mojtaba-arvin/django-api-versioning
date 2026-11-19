"""DRF function view registered through the package decorator API."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.versioning import URLPathVersioning

from django_api_versioning import endpoint, set_endpoint_lifecycle
from django_api_versioning.registry import registry


class DecoratedStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


@extend_schema(responses=DecoratedStatusSerializer)
@api_view(["GET"])
def decorated_status(request):
    return Response({"status": "available"})


# drf-spectacular's URLPathVersioning integration supplies the selected schema
# version in view.kwargs, even though endpoint() registers concrete static URLs.
decorated_status.cls.versioning_class = URLPathVersioning
decorated_status = endpoint(
    "decorated-status/",
    versions=[1, 2],
    view_name="decorated-status",
)(decorated_status)

set_endpoint_lifecycle(
    "decorated-status/",
    version=1,
    methods=["GET"],
    deprecated_at="2030-01-01T00:00:00Z",
)


def get_urlpatterns():
    """Return only this fixture's concrete decorator-generated URL patterns."""
    return [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
        == "decorated-status/"
    ]
