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


# Permissions-based views (permission testing)
try:
    from rest_framework.permissions import IsAuthenticated, AllowAny
    from rest_framework.decorators import api_view, permission_classes as drf_permission_classes

    @endpoint("protected-data/", version=1, view_name="protected-v1")
    @api_view(["GET"])
    @drf_permission_classes([AllowAny])  # v1 allows all
    def protected_data_v1(request):
        """Protected data endpoint - v1 with AllowAny permission."""
        return Response({
            "version": 1,
            "data": "public",
            "permission_level": "all",
        })

    @endpoint("protected-data/", version=2, view_name="protected-v2")
    @api_view(["GET"])
    @drf_permission_classes([AllowAny])  # v2 also allows all for testing
    def protected_data_v2(request):
        """Protected data endpoint - v2 with different permission."""
        return Response({
            "version": 2,
            "data": "sensitive",
            "permission_level": "restricted",
        })

    # Serializer-based versioning views
    from rest_framework.serializers import Serializer, CharField, IntegerField
    from rest_framework.generics import ListAPIView
    import uuid

    class ProductV1Serializer(Serializer):
        """v1 product serializer - basic fields only."""
        id = IntegerField()
        name = CharField()

    class ProductV2Serializer(Serializer):
        """v2 product serializer - extended fields."""
        id = IntegerField()
        name = CharField()
        description = CharField(required=False)
        price = IntegerField(required=False)

    @endpoint("products-list/", version=1, view_name="products-list-v1")
    class ProductListV1(ListAPIView):
        """Product list - v1 with basic serializer."""
        serializer_class = ProductV1Serializer

        def get_queryset(self):
            return [
                {"id": 1, "name": "Product 1"},
                {"id": 2, "name": "Product 2"},
            ]

    @endpoint("products-list/", version=2, view_name="products-list-v2")
    class ProductListV2(ListAPIView):
        """Product list - v2 with extended serializer."""
        serializer_class = ProductV2Serializer

        def get_queryset(self):
            return [
                {"id": 1, "name": "Product 1", "description": "First product", "price": 100},
                {"id": 2, "name": "Product 2", "description": "Second product", "price": 200},
            ]

    # UUID path converter tests
    @endpoint("items/<uuid:item_uuid>/", version=1, view_name="item-by-uuid-v1")
    class ItemByUUIDV1(APIView):
        """Get item by UUID - v1."""
        def get(self, request, item_uuid):
            return Response({
                "version": 1,
                "item_uuid": str(item_uuid),
                "item_type": "uuid",
            })

    @endpoint("items/<uuid:item_uuid>/", version=2, view_name="item-by-uuid-v2")
    class ItemByUUIDV2(APIView):
        """Get item by UUID - v2 with extended info."""
        def get(self, request, item_uuid):
            return Response({
                "version": 2,
                "item_uuid": str(item_uuid),
                "item_type": "uuid",
                "details": f"Item {item_uuid} details",
            })

    # ViewSet examples (for router integration testing)
    # Note: ViewSets with @endpoint decorator work with explicit as_view() calls
    from rest_framework import viewsets
    from rest_framework.decorators import action
    from rest_framework.response import Response as DRFResponse

    class BlogPostSerializer(Serializer):
        """Blog post serializer."""
        id = IntegerField()
        title = CharField()
        content = CharField(required=False)

    class BlogPostViewSetV1(viewsets.ViewSet):
        """Blog post viewset - v1 with basic fields."""

        def list(self, request):
            """List blog posts."""
            return DRFResponse({
                "version": 1,
                "posts": [
                    {"id": 1, "title": "Post 1"},
                    {"id": 2, "title": "Post 2"},
                ]
            })

        def retrieve(self, request, pk=None):
            """Get a single blog post."""
            return DRFResponse({
                "version": 1,
                "id": pk,
                "title": f"Post {pk}"
            })

        @action(detail=True, methods=['post'])
        def publish(self, request, pk=None):
            """Publish a blog post."""
            return DRFResponse({
                "version": 1,
                "status": "published",
                "id": pk
            })

    class BlogPostViewSetV2(viewsets.ViewSet):
        """Blog post viewset - v2 with extended fields."""

        def list(self, request):
            """List blog posts."""
            return DRFResponse({
                "version": 2,
                "posts": [
                    {"id": 1, "title": "Post 1", "content": "Content 1"},
                    {"id": 2, "title": "Post 2", "content": "Content 2"},
                ]
            })

        def retrieve(self, request, pk=None):
            """Get a single blog post."""
            return DRFResponse({
                "version": 2,
                "id": pk,
                "title": f"Post {pk}",
                "content": f"Content for post {pk}"
            })

        @action(detail=False, methods=['get'])
        def recent(self, request):
            """Get recent blog posts."""
            return DRFResponse({
                "version": 2,
                "posts": [
                    {"id": 1, "title": "Post 1", "content": "Content 1"},
                ]
            })

        @action(detail=True, methods=['post'])
        def publish(self, request, pk=None):
            """Publish a blog post."""
            return DRFResponse({
                "version": 2,
                "status": "published",
                "id": pk,
                "timestamp": "2026-11-08T00:00:00Z"
            })

    # Generic APIView tests (Retrieve, Create, Update, Destroy)
    from rest_framework.generics import RetrieveAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
    from rest_framework import status
    from rest_framework.serializers import BooleanField

    class TaskSerializer(Serializer):
        """Task serializer for generic view tests."""
        id = IntegerField(read_only=True)
        title = CharField(max_length=100)
        completed = BooleanField(default=False)

    @endpoint("tasks/<int:task_id>/", version=1, view_name="task-retrieve-v1")
    class TaskRetrieveV1(RetrieveAPIView):
        """Retrieve a task - v1."""
        serializer_class = TaskSerializer

        def get_object(self):
            """Mock task object retrieval."""
            task_id = self.kwargs.get('task_id', 1)
            return {
                'id': task_id,
                'title': f'Task {task_id}',
                'completed': False
            }

    @endpoint("tasks/", version=1, view_name="task-create-v1")
    class TaskCreateV1(CreateAPIView):
        """Create a new task - v1."""
        serializer_class = TaskSerializer

        def create(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(
                {'id': 1, **serializer.validated_data},
                status=status.HTTP_201_CREATED
            )

    from rest_framework.generics import RetrieveUpdateDestroyAPIView

    @endpoint("tasks/<int:task_id>/", version=2, view_name="task-detail-v2")
    class TaskDetailV2(RetrieveUpdateDestroyAPIView):
        """Retrieve, update, or delete a task - v2."""
        serializer_class = TaskSerializer

        def get_object(self):
            """Mock task object retrieval."""
            task_id = self.kwargs.get('task_id', 1)
            return {
                'id': task_id,
                'title': f'Task {task_id}',
                'completed': False
            }

        def update(self, request, *args, **kwargs):
            """Handle PUT requests (full update)."""
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=False)
            serializer.is_valid(raise_exception=True)
            return Response({
                'id': instance['id'],
                'title': serializer.validated_data.get('title', instance['title']),
                'completed': serializer.validated_data.get('completed', instance.get('completed', False))
            })

        def partial_update(self, request, *args, **kwargs):
            """Handle PATCH requests (partial update)."""
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            return Response({
                'id': instance['id'],
                'title': serializer.validated_data.get('title', instance['title']),
                'completed': serializer.validated_data.get('completed', instance.get('completed', False))
            })

        def destroy(self, request, *args, **kwargs):
            """Handle DELETE requests."""
            task_id = self.kwargs.get('task_id', 1)
            return Response(
                {'id': task_id, 'deleted': True},
                status=status.HTTP_204_NO_CONTENT
            )

except ImportError:
    pass

# Namespaced endpoint views for testing namespace integration
# Note: app_name="admin" adds "admin/" to the path, so we don't duplicate it in postfix
@endpoint("reports/summary/", version=1, view_name="reports-summary-v1", app_name="admin")
@require_http_methods(["GET"])
def admin_reports_summary_v1(request):
    """Admin reports summary - v1."""
    return JsonResponse({
        "version": 1,
        "namespace": "admin",
        "endpoint": "reports/summary",
        "data": {
            "total_users": 1000,
            "active_sessions": 50,
        }
    })


@endpoint("reports/summary/", version=2, view_name="reports-summary-v2", app_name="admin")
@require_http_methods(["GET"])
def admin_reports_summary_v2(request):
    """Admin reports summary - v2 with extended metrics."""
    return JsonResponse({
        "version": 2,
        "namespace": "admin",
        "endpoint": "reports/summary",
        "data": {
            "total_users": 1050,
            "active_sessions": 55,
            "new_signups_today": 12,
            "premium_count": 150,
        }
    })


@endpoint("reports/users/", version=1, view_name="reports-users-v1", app_name="admin")
@require_http_methods(["GET"])
def admin_reports_users_v1(request):
    """Admin user reports - v1."""
    return JsonResponse({
        "version": 1,
        "namespace": "admin",
        "endpoint": "reports/users",
        "users": [
            {"id": 1, "email": "user1@example.com"},
            {"id": 2, "email": "user2@example.com"},
        ]
    })


@endpoint("reports/users/", version=2, view_name="reports-users-v2", app_name="admin")
@require_http_methods(["GET"])
def admin_reports_users_v2(request):
    """Admin user reports - v2 with status."""
    return JsonResponse({
        "version": 2,
        "namespace": "admin",
        "endpoint": "reports/users",
        "users": [
            {"id": 1, "email": "user1@example.com", "status": "active"},
            {"id": 2, "email": "user2@example.com", "status": "inactive"},
        ]
    })


@endpoint("config/", version=1, view_name="config-v1", app_name="admin")
@require_http_methods(["GET"])
def admin_config_v1(request):
    """Admin configuration - v1."""
    return JsonResponse({
        "version": 1,
        "namespace": "admin",
        "config": {
            "max_users": 5000,
            "max_storage": 1000000,
        }
    })


@endpoint("config/", version=2, view_name="config-v2", app_name="admin")
@require_http_methods(["GET", "POST"])
def admin_config_v2(request):
    """Admin configuration - v2 with update support."""
    if request.method == 'POST':
        return JsonResponse({
            "version": 2,
            "namespace": "admin",
            "status": "config_updated"
        })
    return JsonResponse({
        "version": 2,
        "namespace": "admin",
        "config": {
            "max_users": 10000,
            "max_storage": 5000000,
            "max_api_calls_per_day": 100000,
        }
    })
