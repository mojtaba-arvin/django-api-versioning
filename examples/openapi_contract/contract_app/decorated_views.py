"""DRF function view whose URL registration is owned by the project adapter."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.versioning import URLPathVersioning
from rest_framework.versioning import URLPathVersioning



class DecoratedStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


@extend_schema(responses=DecoratedStatusSerializer)
@api_view(["GET"])
def decorated_status(request):
    return Response({"status": "available"})

# drf-spectacular's version-filtered schema generation uses DRF's URL-path adapter.
decorated_status.cls.versioning_class = URLPathVersioning
