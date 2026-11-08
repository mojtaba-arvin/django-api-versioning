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
