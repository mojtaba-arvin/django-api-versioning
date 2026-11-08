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

    DRF_AVAILABLE = True
except ImportError:
    DRF_AVAILABLE = False
