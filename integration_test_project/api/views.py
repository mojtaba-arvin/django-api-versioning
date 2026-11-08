"""
API views for integration testing.
Tests various versioning scenarios.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django_api_versioning.decorators import endpoint


# Unversioned health check endpoint
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint."""
    return JsonResponse({"status": "ok"})


# User endpoints with versioning
@endpoint("users/", version=1, view_name="user-list-v1")
@require_http_methods(["GET"])
def user_list(request):
    """List users - v1 implementation."""
    return JsonResponse({
        "version": 1,
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
    })


@endpoint("users/", version=2, view_name="user-list-v2")
@require_http_methods(["GET"])
def user_list_v2(request):
    """List users - v2 implementation with additional fields."""
    return JsonResponse({
        "version": 2,
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]
    })


@endpoint("users/", version=3, view_name="user-list-v3")
@require_http_methods(["GET"])
def user_list_v3(request):
    """List users - v3 implementation with pagination."""
    return JsonResponse({
        "version": 3,
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com", "status": "active"},
            {"id": 2, "name": "Bob", "email": "bob@example.com", "status": "active"},
        ],
        "pagination": {"total": 2, "page": 1}
    })


@endpoint("users/<int:user_id>/", version=1, view_name="user-detail-v1")
@require_http_methods(["GET"])
def user_detail(request, user_id):
    """Get user detail - v1 implementation."""
    return JsonResponse({
        "version": 1,
        "id": user_id,
        "name": f"User {user_id}"
    })


@endpoint("users/<int:user_id>/", version=2, view_name="user-detail-v2")
@require_http_methods(["GET"])
def user_detail_v2(request, user_id):
    """Get user detail - v2 implementation."""
    return JsonResponse({
        "version": 2,
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    })


# Post endpoints
@endpoint("posts/", version=1, view_name="post-list-v1")
@require_http_methods(["GET"])
def post_list(request):
    """List posts - v1 implementation."""
    return JsonResponse({
        "version": 1,
        "posts": [
            {"id": 1, "title": "Post 1"},
            {"id": 2, "title": "Post 2"},
        ]
    })


@endpoint("posts/", version=2, view_name="post-list-v2")
@require_http_methods(["GET"])
def post_list_v2(request):
    """List posts - v2 implementation with content."""
    return JsonResponse({
        "version": 2,
        "posts": [
            {"id": 1, "title": "Post 1", "content": "Content 1"},
            {"id": 2, "title": "Post 2", "content": "Content 2"},
        ]
    })


@endpoint("posts/<int:post_id>/", version=1, view_name="post-detail-v1")
@require_http_methods(["GET"])
def post_detail(request, post_id):
    """Get post detail - v1 implementation."""
    return JsonResponse({
        "version": 1,
        "id": post_id,
        "title": f"Post {post_id}"
    })


@endpoint("posts/<int:post_id>/", version=2, view_name="post-detail-v2")
@require_http_methods(["GET"])
def post_detail_v2(request, post_id):
    """Get post detail - v2 implementation."""
    return JsonResponse({
        "version": 2,
        "id": post_id,
        "title": f"Post {post_id}",
        "content": f"Content for post {post_id}"
    })


# Class-Based Views
from django.views import View


@endpoint("comments/", version=1, view_name="comment-list-v1-cbv")
class CommentListV1(View):
    """CBV: List comments - v1 implementation."""
    def get(self, request):
        return JsonResponse({
            "version": 1,
            "comments": [
                {"id": 1, "text": "Great post!"},
            ]
        })


@endpoint("comments/", version=2, view_name="comment-list-v2-cbv")
class CommentListV2(View):
    """CBV: List comments - v2 implementation with author."""
    def get(self, request):
        return JsonResponse({
            "version": 2,
            "comments": [
                {"id": 1, "text": "Great post!", "author": "Alice"},
            ]
        })


# DRF APIViews
try:
    from rest_framework.views import APIView
    from rest_framework.response import Response

    @endpoint("articles/", version=1, view_name="article-list-v1-drf")
    class ArticleListV1(APIView):
        """DRF APIView: List articles - v1 implementation."""
        def get(self, request):
            return Response({
                "version": 1,
                "articles": [
                    {"id": 1, "title": "Django Tips"},
                ]
            })

    @endpoint("articles/", version=2, view_name="article-list-v2-drf")
    class ArticleListV2(APIView):
        """DRF APIView: List articles - v2 implementation with summary."""
        def get(self, request):
            return Response({
                "version": 2,
                "articles": [
                    {"id": 1, "title": "Django Tips", "summary": "Best practices"},
                ]
            })

    # DRF Generic Views
    from rest_framework.generics import ListAPIView
    from rest_framework.serializers import Serializer, IntegerField, CharField

    class ArticleSerializer(Serializer):
        id = IntegerField()
        title = CharField()
        summary = CharField(required=False, allow_blank=True)

    @endpoint("docs/", version=1, view_name="doc-list-v1-drf-generic")
    class DocListV1(ListAPIView):
        """DRF Generic View: List docs - v1 implementation."""
        serializer_class = ArticleSerializer

        def get_queryset(self):
            # Return a list instead of queryset for simplicity
            return [{"id": 1, "title": "Doc 1"}]

    # DRF APIViews with multiple HTTP methods
    from rest_framework import status

    @endpoint("orders/", version=1, view_name="order-list-v1-drf-methods")
    class OrderListV1(APIView):
        """DRF APIView: Orders - v1 with POST support."""

        def get(self, request):
            return Response({
                "version": 1,
                "orders": [
                    {"id": 1, "total": "19.99"},
                    {"id": 2, "total": "29.99"},
                ]
            })

        def post(self, request):
            return Response({
                "version": 1,
                "id": 3,
                "total": request.data.get("total", "0.00")
            }, status=status.HTTP_201_CREATED)

    @endpoint("orders/", version=2, view_name="order-list-v2-drf-methods")
    class OrderListV2(APIView):
        """DRF APIView: Orders - v2 with currency and POST support."""

        def get(self, request):
            return Response({
                "version": 2,
                "orders": [
                    {"id": 1, "total": 1999, "currency": "USD"},
                    {"id": 2, "total": 2999, "currency": "USD"},
                ]
            })

        def post(self, request):
            return Response({
                "version": 2,
                "id": 3,
                "total": request.data.get("total", 0),
                "currency": request.data.get("currency", "USD")
            }, status=status.HTTP_201_CREATED)

    @endpoint("orders/<int:order_id>/", version=1, view_name="order-detail-v1-drf-methods")
    class OrderDetailV1(APIView):
        """DRF APIView: Order detail - v1 with PUT/PATCH/DELETE support."""

        def get(self, request, order_id):
            return Response({
                "version": 1,
                "id": order_id,
                "total": "99.99"
            })

        def put(self, request, order_id):
            return Response({
                "version": 1,
                "id": order_id,
                "total": request.data.get("total", "99.99")
            })

        def patch(self, request, order_id):
            return Response({
                "version": 1,
                "id": order_id,
                "total": request.data.get("total", "99.99")
            })

        def delete(self, request, order_id):
            return Response(status=status.HTTP_204_NO_CONTENT)

    @endpoint("orders/<int:order_id>/", version=2, view_name="order-detail-v2-drf-methods")
    class OrderDetailV2(APIView):
        """DRF APIView: Order detail - v2 with currency and PUT/PATCH/DELETE support."""

        def get(self, request, order_id):
            return Response({
                "version": 2,
                "id": order_id,
                "total": 9999,
                "currency": "USD"
            })

        def put(self, request, order_id):
            return Response({
                "version": 2,
                "id": order_id,
                "total": request.data.get("total", 9999),
                "currency": request.data.get("currency", "USD")
            })

        def patch(self, request, order_id):
            return Response({
                "version": 2,
                "id": order_id,
                "total": request.data.get("total", 9999),
                "currency": request.data.get("currency", "USD")
            })

        def delete(self, request, order_id):
            return Response(status=status.HTTP_204_NO_CONTENT)

    # Error response testing
    @endpoint("items/", version=1, view_name="item-list-v1-errors")
    class ItemListV1(APIView):
        """DRF APIView: Items - v1 with error handling."""

        def get(self, request):
            return Response({
                "version": 1,
                "items": []
            })

        def post(self, request):
            if not request.data.get("name"):
                return Response(
                    {"error": "name is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({
                "version": 1,
                "id": 1,
                "name": request.data["name"]
            }, status=status.HTTP_201_CREATED)

    DRF_AVAILABLE = True
except ImportError:
    DRF_AVAILABLE = False


# Explicit version sets (only v2 and v4, v3 unavailable)
@endpoint("premium-features/", versions=[2, 4], view_name="premium-features")
@require_http_methods(["GET"])
def premium_features(request):
    """Feature available only in v2 and v4."""
    return JsonResponse({
        "feature": "premium",
        "available_in_v2_and_v4_only": True
    })


# Bounded range (v1 through v3 only, then removed)
from django_api_versioning.decorators import ver_range

@endpoint("legacy-api/", versions=ver_range(1, 3), view_name="legacy-api")
@require_http_methods(["GET"])
def legacy_api(request):
    """Legacy API available only in v1-v3."""
    return JsonResponse({
        "type": "legacy",
        "available_v1_through_v3_only": True
    })


# Unversioned endpoint (no version prefix, omit version parameter)
@endpoint("status/", view_name="status-check")
@require_http_methods(["GET"])
def status_endpoint(request):
    """Unversioned status endpoint."""
    return JsonResponse({
        "status": "operational",
        "unversioned": True
    })


# Nested/namespaced endpoints for testing URL inclusion patterns
# These will be included in a nested URL configuration
@endpoint("analytics/overview/", version=1, view_name="analytics-overview")
@require_http_methods(["GET"])
def analytics_overview_v1(request):
    """Analytics overview - v1."""
    return JsonResponse({
        "version": 1,
        "metrics": {
            "users": 1000,
            "sessions": 5000,
        }
    })


@endpoint("analytics/overview/", version=2, view_name="analytics-overview-v2")
@require_http_methods(["GET"])
def analytics_overview_v2(request):
    """Analytics overview - v2 with detailed metrics."""
    return JsonResponse({
        "version": 2,
        "metrics": {
            "daily_active_users": 500,
            "weekly_active_users": 800,
            "monthly_active_users": 1000,
            "sessions": 5000,
            "bounce_rate": 0.35
        }
    })


# Test different path converters
@endpoint("products/<int:product_id>/", version=1, view_name="product-by-int")
@require_http_methods(["GET"])
def product_by_int_v1(request, product_id):
    """Product by integer ID - v1."""
    return JsonResponse({
        "version": 1,
        "product_id": product_id,
        "id_type": "integer"
    })


@endpoint("posts/<slug:slug>/", version=1, view_name="post-by-slug")
@require_http_methods(["GET"])
def post_by_slug_v1(request, slug):
    """Post by slug - v1."""
    return JsonResponse({
        "version": 1,
        "slug": slug,
        "slug_type": "slug"
    })
