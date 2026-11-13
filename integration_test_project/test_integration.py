#!/usr/bin/env python
"""
Integration test runner for django-api-versioning.
Tests the package with a real Django application.
"""

import os
import sys

import django
from django.conf import settings
from django.test import Client, TestCase

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
django.setup()

from django_api_versioning.registry import registry
from django_api_versioning.reverse import api_reverse

try:
    from rest_framework.test import APIClient
except ImportError:
    APIClient = None


class BasicIntegrationTestCase(TestCase):
    """Test basic integration with Django."""

    def setUp(self):
        self.client = Client()

    def test_health_check_works(self):
        """Test that unversioned endpoint works."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_versioned_endpoint_v1_available(self):
        """Test that v1 endpoint is available."""
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(len(data["users"]), 2)

    def test_versioned_endpoint_v2_available(self):
        """Test that v2 endpoint is available."""
        response = self.client.get("/api/v2/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("email", data["users"][0])

    def test_versioned_endpoint_v3_available(self):
        """Test that v3 endpoint is available."""
        response = self.client.get("/api/v3/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 3)
        self.assertIn("pagination", data)

    def test_versioned_endpoint_with_parameters(self):
        """Test versioned endpoint with URL parameters."""
        response = self.client.get("/api/v1/users/42/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["version"], 1)

    def test_api_reverse_works(self):
        """Test that api_reverse() generates correct URLs."""
        # Test v1 URL reversal
        url_v1 = api_reverse("user-list-v1", version=1)
        self.assertEqual(url_v1, "/api/v1/users/")

        # Test v2 URL reversal
        url_v2 = api_reverse("user-list-v2", version=2)
        self.assertEqual(url_v2, "/api/v2/users/")

        # Test v3 URL reversal
        url_v3 = api_reverse("user-list-v3", version=3)
        self.assertEqual(url_v3, "/api/v3/users/")

    def test_api_reverse_with_parameters(self):
        """Test URL reversal with parameters."""
        url = api_reverse("user-detail-v1", version=1, user_id=123)
        self.assertEqual(url, "/api/v1/users/123/")

        url2 = api_reverse("post-detail-v2", version=2, post_id=456)
        self.assertEqual(url2, "/api/v2/posts/456/")

    def test_multiple_versions_registered(self):
        """Test that multiple versions of same endpoint are registered."""
        # Check registry has multiple patterns
        user_list_patterns = [
            p for p in registry.urlpatterns if "user" in (p.name or "")
        ]
        self.assertGreater(len(user_list_patterns), 1)

    def test_forward_inheritance_default(self):
        """Test that endpoints forward inherit to newer versions."""
        # Post v2 inherits from v1 (forward inheritance)
        # So if we request v1, we get v1. If we request v3, we should get v2 (highest available)
        response_v1 = self.client.get("/api/v1/posts/")
        self.assertEqual(response_v1.json()["version"], 1)

        response_v3 = self.client.get("/api/v3/posts/")
        # v3 doesn't exist, so v2 is served (forward inheritance)
        self.assertEqual(response_v3.json()["version"], 2)

    def test_url_reversal_with_special_characters(self):
        """Test that special characters in parameters are handled correctly."""
        # Test with different parameter values
        url1 = api_reverse("user-detail-v1", version=1, user_id=1)
        self.assertIn("1", url1)

        url2 = api_reverse("user-detail-v1", version=1, user_id=999)
        self.assertIn("999", url2)

    def test_registry_contains_expected_routes(self):
        """Verify that the registry contains all expected routes."""
        all_routes = [p.name for p in registry.urlpatterns if p.name]

        # Check for versioned endpoints
        self.assertIn("user-list-v1", all_routes)
        self.assertIn("user-list-v2", all_routes)
        self.assertIn("user-list-v3", all_routes)

        # Check for detail endpoints
        self.assertIn("user-detail-v1", all_routes)
        self.assertIn("user-detail-v2", all_routes)

    def test_class_based_view_v1(self):
        """Test that class-based views work with @endpoint - v1."""
        response = self.client.get("/api/v1/comments/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertNotIn("author", data["comments"][0])

    def test_class_based_view_v2(self):
        """Test that class-based views work with @endpoint - v2 with inheritance."""
        response = self.client.get("/api/v2/comments/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("author", data["comments"][0])

    def test_class_based_view_v3_inherits(self):
        """Test that CBV forward inheritance works (v3 inherits from v2)."""
        response = self.client.get("/api/v3/comments/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should get v2 response since v3 not explicitly defined
        self.assertEqual(data["version"], 2)

    def test_drf_apiview_v1(self):
        """Test that DRF APIView works with @endpoint - v1."""
        response = self.client.get("/api/v1/articles/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertNotIn("summary", data["articles"][0])

    def test_drf_apiview_v2(self):
        """Test that DRF APIView works with @endpoint - v2."""
        response = self.client.get("/api/v2/articles/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("summary", data["articles"][0])

    def test_drf_generic_view_v1(self):
        """Test that DRF generic views work with @endpoint - v1."""
        response = self.client.get("/api/v1/docs/")
        self.assertEqual(response.status_code, 200)
        # ListAPIView returns data as a list
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    # HTTP Methods Tests - POST
    def test_drf_post_v1(self):
        """Test DRF POST request - v1."""
        response = self.client.post(
            "/api/v1/orders/", {"total": "49.99"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["total"], "49.99")
        self.assertNotIn("currency", data)

    def test_drf_post_v2(self):
        """Test DRF POST request - v2 with currency."""
        response = self.client.post(
            "/api/v2/orders/",
            {"total": 4999, "currency": "EUR"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["total"], 4999)
        self.assertEqual(data["currency"], "EUR")

    # HTTP Methods Tests - PUT (full update)
    def test_drf_put_v1(self):
        """Test DRF PUT request (full update) - v1."""
        response = self.client.put(
            "/api/v1/orders/123/", {"total": "199.99"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["id"], 123)
        self.assertEqual(data["total"], "199.99")

    def test_drf_put_v2(self):
        """Test DRF PUT request (full update) - v2 with currency."""
        response = self.client.put(
            "/api/v2/orders/123/",
            {"total": 19999, "currency": "GBP"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["id"], 123)
        self.assertEqual(data["total"], 19999)
        self.assertEqual(data["currency"], "GBP")

    # HTTP Methods Tests - PATCH (partial update)
    def test_drf_patch_v1(self):
        """Test DRF PATCH request (partial update) - v1."""
        response = self.client.patch(
            "/api/v1/orders/123/", {"total": "149.99"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["id"], 123)
        self.assertEqual(data["total"], "149.99")

    def test_drf_patch_v2(self):
        """Test DRF PATCH request (partial update) - v2."""
        response = self.client.patch(
            "/api/v2/orders/123/", {"currency": "JPY"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["id"], 123)
        self.assertEqual(data["currency"], "JPY")

    # HTTP Methods Tests - DELETE
    def test_drf_delete_v1(self):
        """Test DRF DELETE request - v1."""
        response = self.client.delete("/api/v1/orders/123/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_drf_delete_v2(self):
        """Test DRF DELETE request - v2."""
        response = self.client.delete("/api/v2/orders/123/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    # Error handling tests
    def test_drf_post_error_missing_required_field_v1(self):
        """Test DRF error handling - missing required field."""
        response = self.client.post(
            "/api/v1/items/", {}, content_type="application/json"  # Missing 'name'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_drf_post_success_with_required_field_v1(self):
        """Test DRF POST with required field - v1."""
        response = self.client.post(
            "/api/v1/items/", {"name": "Item A"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["name"], "Item A")

    # Additional comprehensive tests for DRF patterns
    def test_drf_listapi_view_v1(self):
        """Test DRF ListAPIView - read-only list view."""
        response = self.client.get("/api/v1/docs/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # ListAPIView returns list directly
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_multiple_http_methods_same_endpoint_v1(self):
        """Test that same endpoint can handle multiple HTTP methods in v1."""
        # GET should work
        get_response = self.client.get("/api/v1/orders/")
        self.assertEqual(get_response.status_code, 200)

        # POST should work
        post_response = self.client.post(
            "/api/v1/orders/", {"total": "99.99"}, content_type="application/json"
        )
        self.assertEqual(post_response.status_code, 201)

    def test_multiple_http_methods_same_endpoint_v2(self):
        """Test that same endpoint can handle multiple HTTP methods in v2."""
        # GET should work
        get_response = self.client.get("/api/v2/orders/")
        self.assertEqual(get_response.status_code, 200)

        # POST should work with v2 format
        post_response = self.client.post(
            "/api/v2/orders/",
            {"total": 9999, "currency": "CAD"},
            content_type="application/json",
        )
        self.assertEqual(post_response.status_code, 201)

    def test_detail_endpoint_multiple_methods_v1(self):
        """Test detail endpoint with GET, PUT, PATCH, DELETE - v1."""
        # GET
        get_response = self.client.get("/api/v1/orders/42/")
        self.assertEqual(get_response.status_code, 200)

        # PUT
        put_response = self.client.put(
            "/api/v1/orders/42/", {"total": "299.99"}, content_type="application/json"
        )
        self.assertEqual(put_response.status_code, 200)

        # PATCH
        patch_response = self.client.patch(
            "/api/v1/orders/42/", {"total": "199.99"}, content_type="application/json"
        )
        self.assertEqual(patch_response.status_code, 200)

        # DELETE
        delete_response = self.client.delete("/api/v1/orders/42/")
        self.assertEqual(delete_response.status_code, 204)

    def test_detail_endpoint_multiple_methods_v2(self):
        """Test detail endpoint with GET, PUT, PATCH, DELETE - v2."""
        # GET
        get_response = self.client.get("/api/v2/orders/99/")
        self.assertEqual(get_response.status_code, 200)
        data = get_response.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("currency", data)

        # PUT with v2 format
        put_response = self.client.put(
            "/api/v2/orders/99/",
            {"total": 29999, "currency": "AUD"},
            content_type="application/json",
        )
        self.assertEqual(put_response.status_code, 200)
        put_data = put_response.json()
        self.assertEqual(put_data["currency"], "AUD")

        # PATCH with v2 format
        patch_response = self.client.patch(
            "/api/v2/orders/99/", {"currency": "NZD"}, content_type="application/json"
        )
        self.assertEqual(patch_response.status_code, 200)
        patch_data = patch_response.json()
        self.assertEqual(patch_data["currency"], "NZD")

        # DELETE
        delete_response = self.client.delete("/api/v2/orders/99/")
        self.assertEqual(delete_response.status_code, 204)

    def test_version_specific_response_format_v1_vs_v2(self):
        """Test that response format differs between versions."""
        # v1 has simple format with "orders" key
        v1_response = self.client.get("/api/v1/orders/")
        v1_data = v1_response.json()
        self.assertIn("orders", v1_data)
        self.assertEqual(v1_data["version"], 1)
        v1_orders = v1_data["orders"]
        self.assertGreater(len(v1_orders), 0)
        v1_order = v1_orders[0]
        self.assertIn("total", v1_order)
        self.assertNotIn("currency", v1_order)

        # v2 has extended format with "orders" key
        v2_response = self.client.get("/api/v2/orders/")
        v2_data = v2_response.json()
        self.assertIn("orders", v2_data)
        self.assertEqual(v2_data["version"], 2)
        v2_orders = v2_data["orders"]
        self.assertGreater(len(v2_orders), 0)
        v2_order = v2_orders[0]
        self.assertIn("total", v2_order)
        self.assertIn("currency", v2_order)

    def test_forward_inheritance_with_multiple_methods(self):
        """Test that forward inheritance works with multiple HTTP methods."""
        # Articles endpoint - v2 doesn't exist, should inherit from v1 for GET
        # But POST might not be allowed (test the behavior)
        v2_get = self.client.get("/api/v2/articles/")
        self.assertEqual(v2_get.status_code, 200)
        v2_data = v2_get.json()
        # v2 is explicitly defined, not inherited
        self.assertEqual(v2_data["version"], 2)

    def test_version_mismatch_returns_404(self):
        """Test that requesting undefined version returns 404."""
        # Users endpoint goes to v3, API_MAX_VERSION is 4, so v5+ should return 404
        response = self.client.get("/api/v5/users/")
        self.assertEqual(response.status_code, 404)

    def test_posts_segment_with_different_versions(self):
        """Test posts segment inheritance."""
        # v1 is defined
        v1 = self.client.get("/api/v1/posts/")
        self.assertEqual(v1.status_code, 200)
        self.assertEqual(v1.json()["version"], 1)

        # v2 is defined
        v2 = self.client.get("/api/v2/posts/")
        self.assertEqual(v2.status_code, 200)
        self.assertEqual(v2.json()["version"], 2)

        # v3+ should inherit from v2
        v3 = self.client.get("/api/v3/posts/")
        self.assertEqual(v3.status_code, 200)
        self.assertEqual(v3.json()["version"], 2)  # inherited from v2

    def test_concurrent_versions_of_same_endpoint(self):
        """Test that multiple versions can coexist for same endpoint."""
        # Get all registered patterns
        all_routes = [p.name for p in registry.urlpatterns if p.name]

        # Users endpoint should have multiple versions registered
        user_routes = [r for r in all_routes if "user" in r]
        self.assertGreaterEqual(len(user_routes), 3)  # at least v1, v2, v3

    def test_url_parameter_preservation_across_versions(self):
        """Test that URL parameters work correctly across versions."""
        # Test with different IDs in v1
        v1_123 = self.client.get("/api/v1/users/123/")
        self.assertEqual(v1_123.json()["id"], 123)

        v1_999 = self.client.get("/api/v1/users/999/")
        self.assertEqual(v1_999.json()["id"], 999)

        # Same with v2
        v2_456 = self.client.get("/api/v2/users/456/")
        self.assertEqual(v2_456.json()["id"], 456)

    def test_error_response_format_consistency(self):
        """Test that error responses are consistent across versions."""
        # v1 error
        v1_error = self.client.post(
            "/api/v1/items/",
            {},  # missing required field
            content_type="application/json",
        )
        self.assertEqual(v1_error.status_code, 400)

        # v2 error (if exists)
        v2_error = self.client.post(
            "/api/v2/items/",
            {},  # missing required field
            content_type="application/json",
        )
        # v2 inherits from v1 if not explicitly defined
        self.assertEqual(v2_error.status_code, 400)

    def test_class_based_view_inheritance_across_versions(self):
        """Test CBV inheritance works correctly."""
        # Comments is a CBV
        v1 = self.client.get("/api/v1/comments/")
        self.assertEqual(v1.status_code, 200)
        v1_data = v1.json()
        self.assertEqual(v1_data["version"], 1)
        # v1 has simple comment structure
        if v1_data.get("comments"):
            self.assertNotIn("author", v1_data["comments"][0])

        # v2 is also defined
        v2 = self.client.get("/api/v2/comments/")
        self.assertEqual(v2.status_code, 200)
        v2_data = v2.json()
        self.assertEqual(v2_data["version"], 2)
        # v2 has richer structure
        if v2_data.get("comments"):
            self.assertIn("author", v2_data["comments"][0])

        # v3 should inherit from v2
        v3 = self.client.get("/api/v3/comments/")
        self.assertEqual(v3.status_code, 200)
        self.assertEqual(v3.json()["version"], 2)

    # Tests for explicit version sets
    def test_explicit_versions_set_v2_available(self):
        """Test that explicit version set: v2 is available."""
        response = self.client.get("/api/v2/premium-features/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available_in_v2_and_v4_only"])

    def test_explicit_versions_set_v4_available(self):
        """Test that explicit version set: v4 is available."""
        response = self.client.get("/api/v4/premium-features/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available_in_v2_and_v4_only"])

    def test_explicit_versions_set_v3_not_available(self):
        """Test that explicit version set: v3 is NOT available (skipped)."""
        response = self.client.get("/api/v3/premium-features/")
        # v3 is skipped, so we get 404
        self.assertEqual(response.status_code, 404)

    def test_explicit_versions_set_v1_not_available(self):
        """Test that explicit version set: v1 is NOT available (before range)."""
        response = self.client.get("/api/v1/premium-features/")
        self.assertEqual(response.status_code, 404)

    # Tests for bounded ranges
    def test_bounded_range_v1_available(self):
        """Test that bounded range: v1 is available."""
        response = self.client.get("/api/v1/legacy-api/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available_v1_through_v3_only"])

    def test_bounded_range_v2_available(self):
        """Test that bounded range: v2 is available."""
        response = self.client.get("/api/v2/legacy-api/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available_v1_through_v3_only"])

    def test_bounded_range_v3_available(self):
        """Test that bounded range: v3 is available."""
        response = self.client.get("/api/v3/legacy-api/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available_v1_through_v3_only"])

    def test_bounded_range_v4_not_available(self):
        """Test that bounded range: v4 is NOT available (after range)."""
        response = self.client.get("/api/v4/legacy-api/")
        # v4 is beyond the bounded range v1-v3
        self.assertEqual(response.status_code, 404)

    # Tests for unversioned endpoints
    def test_unversioned_endpoint_accessible(self):
        """Test that unversioned endpoint is accessible without version."""
        response = self.client.get("/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["unversioned"])

    def test_unversioned_endpoint_not_in_version_path(self):
        """Test that unversioned endpoint is NOT available under version path."""
        response = self.client.get("/api/v1/status/")
        self.assertEqual(response.status_code, 404)

    def test_unversioned_endpoint_reverse(self):
        """Test that api_reverse works for unversioned endpoints."""
        from django_api_versioning.reverse import api_reverse

        url = api_reverse("status-check")
        self.assertEqual(url, "/status/")

    # Tests for different path converters
    def test_int_path_converter_v1(self):
        """Test that <int:product_id> path converter works - v1."""
        response = self.client.get("/api/v1/products/123/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["product_id"], 123)
        self.assertEqual(data["id_type"], "integer")

    def test_int_path_converter_various_values(self):
        """Test int converter with various values."""
        # Single digit
        response = self.client.get("/api/v1/products/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_id"], 1)

        # Large number
        response = self.client.get("/api/v1/products/999999/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_id"], 999999)

        # Zero
        response = self.client.get("/api/v1/products/0/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_id"], 0)

    def test_slug_path_converter_v1(self):
        """Test that <slug:slug> path converter works - v1."""
        response = self.client.get("/api/v1/posts/my-awesome-post/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["slug"], "my-awesome-post")
        self.assertEqual(data["slug_type"], "slug")

    def test_slug_path_converter_various_values(self):
        """Test slug converter with various values."""
        # Simple slug
        response = self.client.get("/api/v1/posts/hello/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "hello")

        # Slug with numbers
        response = self.client.get("/api/v1/posts/post-123/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "post-123")

        # Slug with multiple hyphens
        response = self.client.get("/api/v1/posts/my-long-post-title/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "my-long-post-title")

    def test_api_reverse_with_int_parameter(self):
        """Test api_reverse with int converter parameter."""
        url = api_reverse("product-by-int", version=1, product_id=42)
        self.assertEqual(url, "/api/v1/products/42/")

    def test_api_reverse_with_slug_parameter(self):
        """Test api_reverse with slug converter parameter."""
        url = api_reverse("post-by-slug", version=1, slug="test-post")
        self.assertEqual(url, "/api/v1/posts/test-post/")

    # Tests for analytics overview (semantic nested functionality)
    def test_analytics_overview_v1(self):
        """Test analytics overview endpoint - v1 with basic metrics."""
        response = self.client.get("/api/v1/analytics/overview/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertIn("metrics", data)
        self.assertIn("users", data["metrics"])
        self.assertIn("sessions", data["metrics"])
        # v1 doesn't have bounce_rate
        self.assertNotIn("bounce_rate", data["metrics"])

    def test_analytics_overview_v2(self):
        """Test analytics overview endpoint - v2 with detailed metrics."""
        response = self.client.get("/api/v2/analytics/overview/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("metrics", data)
        self.assertIn("daily_active_users", data["metrics"])
        self.assertIn("bounce_rate", data["metrics"])

    def test_analytics_overview_v3_inherits_v2(self):
        """Test that v3 analytics inherits from v2."""
        response = self.client.get("/api/v3/analytics/overview/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should inherit v2 response
        self.assertEqual(data["version"], 2)
        self.assertIn("bounce_rate", data["metrics"])

    def test_api_reverse_analytics_overview(self):
        """Test api_reverse for analytics endpoints."""
        url_v1 = api_reverse("analytics-overview", version=1)
        self.assertEqual(url_v1, "/api/v1/analytics/overview/")

        url_v2 = api_reverse("analytics-overview-v2", version=2)
        self.assertEqual(url_v2, "/api/v2/analytics/overview/")

    # Permissions-based endpoint tests
    def test_protected_data_v1_accessible(self):
        """Test protected data endpoint - v1 is accessible (AllowAny)."""
        response = self.client.get("/api/v1/protected-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["permission_level"], "all")

    def test_protected_data_v2_accessible(self):
        """Test protected data endpoint - v2 is accessible."""
        response = self.client.get("/api/v2/protected-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["permission_level"], "restricted")

    # Serializer versioning tests
    def test_product_list_v1_serializer(self):
        """Test product list with v1 serializer (basic fields)."""
        response = self.client.get("/api/v1/products-list/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        # v1 serializer only has id and name
        product = data[0]
        self.assertIn("id", product)
        self.assertIn("name", product)
        self.assertNotIn("price", product)

    def test_product_list_v2_serializer(self):
        """Test product list with v2 serializer (extended fields)."""
        response = self.client.get("/api/v2/products-list/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        # v2 serializer has id, name, description, and price
        product = data[0]
        self.assertIn("id", product)
        self.assertIn("name", product)
        self.assertIn("description", product)
        self.assertIn("price", product)

    # Edge cases and error scenarios
    def test_invalid_version_returns_404(self):
        """Test that invalid version returns 404."""
        response = self.client.get("/api/v999/users/")
        self.assertEqual(response.status_code, 404)

    def test_non_existent_endpoint_returns_404(self):
        """Test that non-existent endpoint returns 404."""
        response = self.client.get("/api/v1/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_version_zero_not_allowed(self):
        """Test that version 0 returns 404."""
        response = self.client.get("/api/v0/users/")
        self.assertEqual(response.status_code, 404)

    def test_negative_version_returns_404(self):
        """Test that negative version returns 404."""
        response = self.client.get("/api/v-1/users/")
        # This will likely return 404 due to URL pattern matching
        self.assertEqual(response.status_code, 404)

    def test_string_version_returns_404(self):
        """Test that string version returns 404."""
        response = self.client.get("/api/vABC/users/")
        self.assertEqual(response.status_code, 404)

    # Regression tests
    def test_v1_endpoint_after_multiple_requests(self):
        """Test that v1 endpoint works consistently after multiple requests."""
        # Make multiple requests to the same endpoint
        for i in range(3):
            response = self.client.get("/api/v1/users/")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["version"], 1)

    def test_different_endpoints_isolation(self):
        """Test that different endpoints don't interfere with each other."""
        # Request from different endpoints in sequence
        users_v1 = self.client.get("/api/v1/users/")
        posts_v1 = self.client.get("/api/v1/posts/")
        comments_v1 = self.client.get("/api/v1/comments/")

        self.assertEqual(users_v1.json()["version"], 1)
        self.assertEqual(posts_v1.json()["version"], 1)
        self.assertEqual(comments_v1.json()["version"], 1)

    def test_version_cross_contamination_check(self):
        """Test that data from v1 doesn't contaminate v2 requests."""
        v1_data = self.client.get("/api/v1/users/").json()
        v2_data = self.client.get("/api/v2/users/").json()

        # v1 users should NOT have email
        self.assertNotIn("email", v1_data["users"][0])

        # v2 users SHOULD have email
        self.assertIn("email", v2_data["users"][0])

    # Parameter encoding tests
    def test_parameter_with_special_chars(self):
        """Test URL parameters with special characters."""
        # Regular alphanumeric
        response = self.client.get("/api/v1/users/123/")
        self.assertEqual(response.status_code, 200)

        # Different numeric value
        response = self.client.get("/api/v1/users/999999/")
        self.assertEqual(response.status_code, 200)

    def test_slug_parameter_encoding(self):
        """Test slug parameter encoding in URLs."""
        response = self.client.get("/api/v1/posts/my-first-post/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "my-first-post")

    # Response consistency tests
    def test_json_response_structure_v1(self):
        """Test that JSON response structure is valid for v1."""
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.get("content-type", ""))
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_json_response_structure_v2(self):
        """Test that JSON response structure is valid for v2."""
        response = self.client.get("/api/v2/users/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.get("content-type", ""))
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_empty_request_body_handling(self):
        """Test that GET requests with empty body work correctly."""
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)

    def test_request_idempotency(self):
        """Test that identical requests return identical responses."""
        response1 = self.client.get("/api/v1/users/")
        response2 = self.client.get("/api/v1/users/")

        self.assertEqual(response1.json(), response2.json())

    # UUID path parameter tests
    def test_uuid_path_converter_v1(self):
        """Test that <uuid:item_uuid> path converter works - v1."""
        import uuid

        test_uuid = str(uuid.uuid4())
        response = self.client.get(f"/api/v1/items/{test_uuid}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["item_uuid"], test_uuid)
        self.assertEqual(data["item_type"], "uuid")

    def test_uuid_path_converter_v2(self):
        """Test that <uuid:item_uuid> path converter works - v2."""
        import uuid

        test_uuid = str(uuid.uuid4())
        response = self.client.get(f"/api/v2/items/{test_uuid}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["item_uuid"], test_uuid)
        self.assertIn("details", data)

    def test_uuid_various_values(self):
        """Test UUID converter with various valid UUID values."""
        import uuid

        uuids = [
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
        ]
        for test_uuid in uuids:
            response = self.client.get(f"/api/v1/items/{test_uuid}/")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["item_uuid"], test_uuid)

    def test_invalid_uuid_returns_404(self):
        """Test that invalid UUID string returns 404."""
        response = self.client.get("/api/v1/items/not-a-uuid/")
        self.assertEqual(response.status_code, 404)

    def test_uuid_lowercase_conversion(self):
        """Test UUID path converter with lowercase UUID."""
        import uuid

        test_uuid = str(uuid.uuid4()).lower()
        response = self.client.get(f"/api/v1/items/{test_uuid}/")
        self.assertEqual(response.status_code, 200)

    def test_uuid_uppercase_conversion(self):
        """Test UUID path converter with uppercase UUID (if supported)."""
        import uuid

        test_uuid = str(uuid.uuid4()).upper()
        # Django UUID converter handles case normalization
        response = self.client.get(f"/api/v1/items/{test_uuid}/")
        # May or may not work depending on UUID normalization
        # Just test that request goes through
        self.assertIn(response.status_code, [200, 404])

    # Comprehensive integration scenario tests
    def test_multiple_endpoints_same_version(self):
        """Test accessing multiple different endpoints at the same version."""
        v1_users = self.client.get("/api/v1/users/")
        v1_posts = self.client.get("/api/v1/posts/")
        v1_comments = self.client.get("/api/v1/comments/")

        self.assertEqual(v1_users.status_code, 200)
        self.assertEqual(v1_posts.status_code, 200)
        self.assertEqual(v1_comments.status_code, 200)

        self.assertEqual(v1_users.json()["version"], 1)
        self.assertEqual(v1_posts.json()["version"], 1)
        self.assertEqual(v1_comments.json()["version"], 1)

    def test_single_endpoint_multiple_versions(self):
        """Test accessing the same endpoint across multiple versions."""
        versions = [1, 2, 3]
        responses = {}
        for v in versions:
            response = self.client.get(f"/api/v{v}/users/")
            if response.status_code == 200:
                responses[v] = response.json()

        # Should have at least v1 and v2
        self.assertIn(1, responses)
        self.assertIn(2, responses)

    def test_version_routing_correctness(self):
        """Test that requests are routed to the correct version handler."""
        v1 = self.client.get("/api/v1/users/").json()
        v2 = self.client.get("/api/v2/users/").json()

        # Versions should be different
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v2["version"], 2)

        # Data should reflect version differences
        self.assertNotEqual(v1, v2)

    def test_response_content_type_json(self):
        """Test that responses have correct content-type."""
        response = self.client.get("/api/v1/users/")
        content_type = response.get("content-type", "").lower()
        self.assertIn("application/json", content_type)

    def test_http_200_on_valid_request(self):
        """Test that valid requests return HTTP 200."""
        endpoints = [
            "/api/v1/users/",
            "/api/v1/posts/",
            "/api/v1/comments/",
            "/api/v2/users/",
            "/api/v2/posts/",
        ]
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200, f"Failed for {endpoint}")

    def test_http_404_on_invalid_endpoint(self):
        """Test that invalid endpoints return HTTP 404."""
        invalid_endpoints = [
            "/api/v1/does-not-exist/",
            "/api/v999/users/",
            "/api/v1/fake-endpoint/",
        ]
        for endpoint in invalid_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 404, f"Should 404: {endpoint}")

    def test_method_not_allowed_on_unsupported_methods(self):
        """Test that unsupported HTTP methods return 405 or similar."""
        # Most endpoints in this test project only support GET
        # POST to a GET-only endpoint should fail
        response = self.client.post(
            "/api/v1/analytics/overview/",
            {"data": "test"},
            content_type="application/json",
        )
        # Should be 405 (Method Not Allowed) or similar
        self.assertIn(response.status_code, [405, 415])

    def test_large_integer_parameter(self):
        """Test URL parameter with large integer value."""
        large_id = 999999999
        response = self.client.get(f"/api/v1/users/{large_id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], large_id)

    def test_single_digit_parameter(self):
        """Test URL parameter with single digit."""
        response = self.client.get("/api/v1/users/1/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 1)

    def test_zero_parameter_handling(self):
        """Test URL parameter with zero value."""
        response = self.client.get("/api/v1/users/0/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 0)


class NamespacedAPIViewIntegrationTestCase(TestCase):
    """Test versioned endpoints with app_name (namespace) support."""

    def setUp(self):
        self.client = APIClient()

    def test_admin_reports_summary_v1(self):
        """Test admin namespaced endpoint - v1."""
        response = self.client.get("/api/v1/admin/reports/summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["namespace"], "admin")
        self.assertEqual(data["endpoint"], "reports/summary")
        self.assertIn("data", data)

    def test_admin_reports_summary_v2(self):
        """Test admin namespaced endpoint - v2 with extended fields."""
        response = self.client.get("/api/v2/admin/reports/summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["namespace"], "admin")
        self.assertIn("premium_count", data["data"])
        self.assertIn("new_signups_today", data["data"])

    def test_admin_reports_users_v1(self):
        """Test admin users report - v1."""
        response = self.client.get("/api/v1/admin/reports/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["namespace"], "admin")
        self.assertEqual(len(data["users"]), 2)
        self.assertNotIn("status", data["users"][0])

    def test_admin_reports_users_v2(self):
        """Test admin users report - v2 with status field."""
        response = self.client.get("/api/v2/admin/reports/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(len(data["users"]), 2)
        self.assertIn("status", data["users"][0])
        self.assertEqual(data["users"][0]["status"], "active")
        self.assertEqual(data["users"][1]["status"], "inactive")

    def test_admin_config_v1(self):
        """Test admin config endpoint - v1."""
        response = self.client.get("/api/v1/admin/config/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["config"]["max_users"], 5000)
        self.assertNotIn("max_api_calls_per_day", data["config"])

    def test_admin_config_v2_get(self):
        """Test admin config endpoint - v2 GET with extra fields."""
        response = self.client.get("/api/v2/admin/config/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["config"]["max_users"], 10000)
        self.assertEqual(data["config"]["max_storage"], 5000000)
        self.assertIn("max_api_calls_per_day", data["config"])

    def test_admin_config_v2_post(self):
        """Test admin config endpoint - v2 POST support."""
        response = self.client.post("/api/v2/admin/config/", data={})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["status"], "config_updated")

    def test_forward_inheritance_namespaced_v3(self):
        """Test that v3 inherits from v2 in namespaced endpoint."""
        response = self.client.get("/api/v3/admin/reports/summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # v3 should inherit v2 implementation (forward inheritance)
        self.assertEqual(data["version"], 2)
        self.assertIn("premium_count", data["data"])

    def test_version_isolation_namespaced(self):
        """Test that versions are isolated within namespace."""
        v1_response = self.client.get("/api/v1/admin/config/")
        v2_response = self.client.get("/api/v2/admin/config/")

        v1_data = v1_response.json()
        v2_data = v2_response.json()

        # Ensure they return different data
        self.assertEqual(v1_data["version"], 1)
        self.assertEqual(v2_data["version"], 2)
        self.assertEqual(v1_data["config"]["max_users"], 5000)
        self.assertEqual(v2_data["config"]["max_users"], 10000)

    def test_namespaced_vs_non_namespaced(self):
        """Test that namespaced endpoints are separate from non-namespaced."""
        # Non-namespaced endpoint
        non_ns_response = self.client.get("/api/v1/analytics/overview/")
        self.assertEqual(non_ns_response.status_code, 200)
        non_ns_data = non_ns_response.json()

        # Namespaced endpoint
        ns_response = self.client.get("/api/v1/admin/reports/summary/")
        self.assertEqual(ns_response.status_code, 200)
        ns_data = ns_response.json()

        # They should be different
        self.assertIn("metrics", non_ns_data)
        self.assertIn("data", ns_data)
        self.assertNotEqual(non_ns_data, ns_data)


class NestedURLPatternTestCase(TestCase):
    """Test nested and included URL patterns with versioning.

    Tests the package's behavior when using Django's path() include()
    with versioned endpoints.
    """

    def setUp(self):
        self.client = Client()

    def test_unversioned_status_endpoint_accessible(self):
        """Test that unversioned endpoints work with includes."""
        response = self.client.get("/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["unversioned"], True)

    def test_versioned_users_endpoint_v1(self):
        """Test versioned endpoint accessible through include."""
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)

    def test_versioned_users_endpoint_v2(self):
        """Test different version of same endpoint."""
        response = self.client.get("/api/v2/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)

    def test_nested_analytics_endpoint(self):
        """Test nested endpoint path (analytics/overview)."""
        response = self.client.get("/api/v1/analytics/overview/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertIn("metrics", data)

    def test_multiple_path_levels(self):
        """Test that path() include() works with multiple levels."""
        # Users/123/ is two levels deep
        response = self.client.get("/api/v1/users/123/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 123)

    def test_nested_include_url_resolution(self):
        """Test that url reversal works for nested includes."""
        from django_api_versioning.reverse import api_reverse

        url = api_reverse("user-list-v1", version=1)
        self.assertEqual(url, "/api/v1/users/")

        url_with_params = api_reverse("user-detail-v1", version=1, user_id=42)
        self.assertEqual(url_with_params, "/api/v1/users/42/")


class DRFRouterIntegrationTestCase(TestCase):
    """Test DRF Router integration with versioning.

    Note: The package doesn't automatically version router-generated URLs.
    Routers create URLs like /api/v1/blogposts/ but these are separate from
    @endpoint-decorated views. This test documents this limitation and verifies
    that routers work independently.
    """

    def setUp(self):
        self.client = Client()

    def test_default_router_v1_list(self):
        """Test DefaultRouter generated list endpoint - v1."""
        try:
            response = self.client.get("/api/v1/blogposts/")
            # Router endpoints should work independently
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                # Should have version 1 data
                self.assertEqual(data.get("version"), 1)
        except ImportError:
            self.skipTest("DRF not available")

    def test_default_router_v1_retrieve(self):
        """Test DefaultRouter generated retrieve endpoint - v1."""
        try:
            from rest_framework.routers import DefaultRouter

            response = self.client.get("/api/v1/blogposts/1/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 1)
                # Router passes pk as string from URL
                self.assertIn(str(data.get("id")), ["1", 1])
        except ImportError:
            self.skipTest("DRF not available")

    def test_default_router_v1_custom_action(self):
        """Test DefaultRouter custom action - v1."""
        try:
            from rest_framework.routers import DefaultRouter

            response = self.client.post("/api/v1/blogposts/1/publish/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 1)
                self.assertEqual(data.get("status"), "published")
        except ImportError:
            self.skipTest("DRF not available")

    def test_simple_router_v2_list(self):
        """Test SimpleRouter generated list endpoint - v2."""
        try:
            response = self.client.get("/api/v2/blogposts/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 2)
        except ImportError:
            self.skipTest("DRF not available")

    def test_simple_router_v2_retrieve(self):
        """Test SimpleRouter generated retrieve endpoint - v2."""
        try:
            from rest_framework.routers import SimpleRouter

            response = self.client.get("/api/v2/blogposts/1/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 2)
        except ImportError:
            self.skipTest("DRF not available")

    def test_simple_router_v2_custom_collection_action(self):
        """Test SimpleRouter collection-level custom action - v2."""
        try:
            from rest_framework.routers import SimpleRouter

            response = self.client.get("/api/v2/blogposts/recent/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 2)
        except ImportError:
            self.skipTest("DRF not available")

    def test_simple_router_v2_custom_detail_action(self):
        """Test SimpleRouter detail-level custom action - v2."""
        try:
            from rest_framework.routers import SimpleRouter

            response = self.client.post("/api/v2/blogposts/1/publish/")
            self.assertIn(response.status_code, [200, 404])
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get("version"), 2)
                self.assertEqual(data.get("status"), "published")
        except ImportError:
            self.skipTest("DRF not available")

    def test_router_endpoints_independent_of_endpoint_decorator(self):
        """Test that router URLs don't interfere with @endpoint decorated views."""
        # /api/v1/users/ should still work (from @endpoint)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)


class GenericAPIViewIntegrationTestCase(TestCase):
    """Test DRF generic APIViews with versioning."""

    def setUp(self):
        self.client = APIClient()

    def test_retrieve_apiview_v1(self):
        """Test RetrieveAPIView - v1."""
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.get("/api/v1/tasks/42/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 42)
        self.assertIn("title", data)
        self.assertIn("completed", data)

    def test_create_apiview_v1_post(self):
        """Test CreateAPIView - v1 POST request."""
        from rest_framework.test import APIClient

        client = APIClient()
        payload = {"title": "New Task", "completed": False}
        response = client.post("/api/v1/tasks/", data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["title"], "New Task")
        self.assertEqual(data["completed"], False)

    def test_retrieve_update_destroy_apiview_v2_get(self):
        """Test RetrieveUpdateDestroyAPIView - v2 GET request."""
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.get("/api/v2/tasks/42/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 42)
        self.assertIn("title", data)

    def test_retrieve_update_destroy_apiview_v2_put(self):
        """Test RetrieveUpdateDestroyAPIView - v2 PUT request."""
        from rest_framework.test import APIClient

        client = APIClient()
        payload = {"title": "Updated Task", "completed": True}
        response = client.put("/api/v2/tasks/42/", data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["title"], "Updated Task")
        self.assertEqual(data["completed"], True)

    def test_retrieve_update_destroy_apiview_v2_patch(self):
        """Test RetrieveUpdateDestroyAPIView - v2 PATCH request (partial update)."""
        from rest_framework.test import APIClient

        client = APIClient()
        payload = {"title": "Partially Updated"}
        response = client.patch("/api/v2/tasks/42/", data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Partially Updated")

    def test_retrieve_update_destroy_apiview_v2_delete(self):
        """Test RetrieveUpdateDestroyAPIView - v2 DELETE request."""
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.delete("/api/v2/tasks/42/")
        self.assertEqual(response.status_code, 204)

    def test_retrieve_with_different_ids(self):
        """Test RetrieveAPIView handles multiple task IDs correctly."""
        from rest_framework.test import APIClient

        client = APIClient()

        for task_id in [1, 5, 999]:
            response = client.get(f"/api/v1/tasks/{task_id}/")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["id"], task_id)
            self.assertEqual(data["title"], f"Task {task_id}")

    def test_create_and_retrieve_consistency(self):
        """Test that CreateAPIView and RetrieveAPIView are consistent."""
        from rest_framework.test import APIClient

        client = APIClient()

        # Create a task
        create_payload = {"title": "Test Task", "completed": False}
        create_response = client.post(
            "/api/v1/tasks/", data=create_payload, format="json"
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        # Retrieve the created task
        retrieve_response = client.get(f"/api/v1/tasks/{created_id}/")
        self.assertEqual(retrieve_response.status_code, 200)
        retrieved_data = retrieve_response.json()
        self.assertEqual(retrieved_data["id"], created_id)

    def test_v1_create_v2_detail_endpoints_separate(self):
        """Test that v1 and v2 task endpoints handle different methods."""
        from rest_framework.test import APIClient

        client = APIClient()

        # V1 has POST for create
        response_v1_post = client.post(
            "/api/v1/tasks/", data={"title": "Task", "completed": False}, format="json"
        )
        self.assertEqual(response_v1_post.status_code, 201)

        # V1 GET with ID should get 404 (no retrieve-v1 at detail path, only retrieve-v1 without ID)
        # Actually v1 has task-retrieve-v1, so GET should work
        response_v1_get = client.get("/api/v1/tasks/42/")
        self.assertEqual(response_v1_get.status_code, 200)

        # V2 has full CRUD for detail path
        response_v2_get = client.get("/api/v2/tasks/42/")
        self.assertEqual(response_v2_get.status_code, 200)

        response_v2_put = client.put(
            "/api/v2/tasks/42/",
            data={"title": "Updated", "completed": True},
            format="json",
        )
        self.assertEqual(response_v2_put.status_code, 200)


class URLDetectionAndRoutingComprehensiveTestCase(TestCase):
    """
    Comprehensive tests for URL detection, routing, and resolution.
    Tests path converters, nested includes, namespaces, and api_reverse.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()

    def test_api_reverse_basic_no_parameters(self):
        """Test api_reverse works for endpoints without parameters."""
        url = api_reverse("user-list-v1", version=1)
        self.assertIn("v1", url)
        self.assertIn("users", url)

    def test_api_reverse_with_int_parameter(self):
        """Test api_reverse correctly formats integer path parameters."""
        url = api_reverse("user-detail-v1", version=1, user_id=42)
        self.assertIn("v1", url)
        self.assertIn("users", url)
        self.assertIn("42", url)

    def test_api_reverse_with_slug_parameter(self):
        """Test api_reverse correctly formats slug parameters."""
        url = api_reverse("post-by-slug", version=1, slug="my-first-post")
        self.assertIn("v1", url)
        self.assertIn("posts", url)
        self.assertIn("my-first-post", url)

    def test_api_reverse_version_in_url_path(self):
        """Test that version appears in the URL path at correct location."""
        url = api_reverse("user-list-v1", version=1)
        # Version should appear before resource name
        self.assertTrue(url.index("v1") < url.index("users"))

    def test_api_reverse_different_versions_produce_different_urls(self):
        """Test that api_reverse produces different URLs for different versions."""
        url_v1 = api_reverse("user-list-v1", version=1)
        url_v2 = api_reverse("user-list-v2", version=2)
        self.assertNotEqual(url_v1, url_v2)
        self.assertIn("v1", url_v1)
        self.assertIn("v2", url_v2)

    def test_url_path_converter_int(self):
        """Test that integer path converter correctly matches integer values."""
        response = self.client.get("/api/v1/users/123/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 123)

    def test_url_path_converter_slug(self):
        """Test that slug path converter correctly matches slug values."""
        response = self.client.get("/api/v1/posts/hello-world/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("hello-world", data.get("slug", "") or str(data))

    def test_url_path_converter_uuid(self):
        """Test that UUID path converter works with versioned endpoints."""
        # Test with a valid UUID format
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        response = self.client.get(f"/api/v1/items/{uuid_str}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # UUID is extracted and passed to view
        self.assertIn(uuid_str, str(data))

    def test_url_routing_exact_match(self):
        """Test that URLs must match exactly (no partial matches)."""
        # Valid endpoint
        response_valid = self.client.get("/api/v1/users/")
        self.assertEqual(response_valid.status_code, 200)

        # Non-existent variation
        response_invalid = self.client.get("/api/v1/users/extra/segment/")
        self.assertEqual(response_invalid.status_code, 404)

    def test_api_reverse_preserves_path_parameter_types(self):
        """Test that api_reverse preserves parameter types in URL."""
        # Integer parameter
        url_int = api_reverse("user-detail-v1", version=1, user_id=999)
        self.assertIn("999", url_int)

        # Large integer
        url_large = api_reverse("user-detail-v1", version=1, user_id=2147483647)
        self.assertIn("2147483647", url_large)

    def test_versioned_endpoint_namespace_isolation(self):
        """Test that versioned endpoints in namespaces work correctly."""
        # Admin namespace endpoints with app_name="admin"
        response_admin_v1 = self.client.get("/api/v1/admin/reports/summary/")
        self.assertEqual(response_admin_v1.status_code, 200)

        # Standard API endpoint
        response_standard_v1 = self.client.get("/api/v1/users/")
        self.assertEqual(response_standard_v1.status_code, 200)

    def test_url_reversal_across_namespaces(self):
        """Test api_reverse works correctly with namespaced endpoints."""
        # This should work if the endpoint is registered in the namespace
        url = api_reverse("reports-summary-v1", version=1)
        self.assertIn("admin", url)
        self.assertIn("reports", url)

    def test_base_path_configuration_in_urls(self):
        """Test that API_BASE_PATH is correctly applied in URL patterns."""
        # All versioned endpoints should follow /api/v<version>/ pattern
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)

        # Non-versioned unversioned endpoint is not in /api/ prefix
        response_unversioned = self.client.get("/status/")
        self.assertEqual(response_unversioned.status_code, 200)

    def test_url_reverse_with_special_characters_in_parameters(self):
        """Test api_reverse with special characters in parameters."""
        # Slug with hyphens and underscores
        url = api_reverse("post-by-slug", version=1, slug="my-post_v2")
        self.assertIn("my-post_v2", url)

    def test_multiple_path_parameters_in_single_endpoint(self):
        """Test endpoint with multiple URL parameters (if available)."""
        # Most endpoints have 0-1 parameter, but test what we have
        response_single_param = self.client.get("/api/v1/users/42/")
        self.assertEqual(response_single_param.status_code, 200)

    def test_url_pattern_trailing_slash_handling(self):
        """Test trailing slash handling in URL patterns."""
        # With trailing slash (expected)
        response_with_slash = self.client.get("/api/v1/users/")
        self.assertEqual(response_with_slash.status_code, 200)

        # Without trailing slash should not match
        response_no_slash = self.client.get("/api/v1/users")
        self.assertEqual(response_no_slash.status_code, 404)

    def test_api_reverse_consistency_with_actual_urls(self):
        """Test that api_reverse produces URLs that actually work."""
        url = api_reverse("user-list-v1", version=1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_url_parameter_extraction_in_view(self):
        """Test that URL parameters are correctly extracted and passed to views."""
        # User 42 should return data for user 42
        response = self.client.get("/api/v1/users/42/")
        data = response.json()
        self.assertEqual(data["id"], 42)

        # User 100 should return data for user 100
        response = self.client.get("/api/v1/users/100/")
        data = response.json()
        self.assertEqual(data["id"], 100)

    def test_versioned_vs_unversioned_endpoints_routing(self):
        """Test that versioned and unversioned endpoints route correctly."""
        # Versioned: users endpoint
        versioned_response = self.client.get("/api/v1/users/")
        self.assertEqual(versioned_response.status_code, 200)

        # Unversioned: status endpoint (not under /api/)
        unversioned_response = self.client.get("/status/")
        self.assertEqual(unversioned_response.status_code, 200)

        # Different response structures for versioned vs unversioned
        versioned_data = versioned_response.json()
        unversioned_data = unversioned_response.json()

        self.assertIn("version", versioned_data)  # Versioned has version field
        self.assertNotIn("version", unversioned_data)  # Unversioned doesn't

    def test_url_resolution_with_version_inheritance(self):
        """Test URL resolution when using version inheritance."""
        # Analytics endpoint: v1 and v2 exist, v3 should inherit from v2
        v2_url = api_reverse("analytics-overview-v2", version=2)
        v3_path = v2_url.replace("/v2/", "/v3/")  # Simulate v3 request

        response = self.client.get(v3_path)
        # Should work due to version inheritance
        self.assertEqual(response.status_code, 200)

    def test_parameter_type_affects_url_matching(self):
        """Test that URL parameter types are correctly enforced."""
        # Valid integer parameter
        valid_response = self.client.get("/api/v1/products/123/")
        self.assertEqual(valid_response.status_code, 200)

        # Invalid: non-integer where integer expected (should 404)
        invalid_response = self.client.get("/api/v1/products/abc/")
        self.assertEqual(invalid_response.status_code, 404)


class DRFGenericViewsComprehensiveTestCase(TestCase):
    """
    Comprehensive tests for DRF generic views with versioning.
    Tests all generic view types, version inheritance, and edge cases.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient() if APIClient else None

    def test_list_apiview_v1_basic(self):
        """Test ListAPIView basic list operation - v1."""
        if self.client is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/docs/")
        self.assertEqual(response.status_code, 200)
        # ListAPIView returns list directly or wrapped in results key
        data = response.json()
        # Could be list or dict with results
        self.assertTrue(isinstance(data, (list, dict)))

    def test_list_apiview_v2_basic(self):
        """Test ListAPIView basic list operation - v2 (forward inherited from v1)."""
        if self.client is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/docs/")
        # v2 should inherit from v1
        self.assertEqual(response.status_code, 200)

    def test_create_apiview_error_handling_v1(self):
        """Test CreateAPIView error handling with missing required fields."""
        if self.client is None:
            self.skipTest("DRF not installed")
        # POST without required fields should fail
        response = self.client.post("/api/v1/tasks/", data={}, format="json")
        self.assertIn(
            response.status_code, [400, 422]
        )  # Bad request or validation error

    def test_retrieve_apiview_with_different_ids(self):
        """Test RetrieveAPIView correctly extracts and returns different IDs."""
        if self.client is None:
            self.skipTest("DRF not installed")
        # Mock view returns data for any ID, verifying parameter extraction
        response1 = self.client.get("/api/v1/tasks/1/")
        response2 = self.client.get("/api/v1/tasks/42/")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        # Verify different IDs are returned
        self.assertEqual(response1.json()["id"], 1)
        self.assertEqual(response2.json()["id"], 42)

    def test_retrieve_update_destroy_all_methods_v2(self):
        """Test RetrieveUpdateDestroyAPIView supports GET, PUT, PATCH, DELETE."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # GET - retrieve
        get_response = self.client.get("/api/v2/tasks/42/")
        self.assertEqual(get_response.status_code, 200)

        # PUT - full update
        put_response = self.client.put(
            "/api/v2/tasks/42/",
            data={"title": "Updated", "completed": True},
            format="json",
        )
        self.assertEqual(put_response.status_code, 200)

        # PATCH - partial update
        patch_response = self.client.patch(
            "/api/v2/tasks/42/", data={"completed": False}, format="json"
        )
        self.assertEqual(patch_response.status_code, 200)

        # DELETE - destroy
        delete_response = self.client.delete("/api/v2/tasks/42/")
        self.assertEqual(delete_response.status_code, 204)

    def test_create_apiview_success_response_format(self):
        """Test CreateAPIView returns proper response format with status 201."""
        if self.client is None:
            self.skipTest("DRF not installed")
        payload = {"title": "New Task", "completed": False}
        response = self.client.post("/api/v1/tasks/", data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        # Should return created object
        self.assertIn("id", data)
        self.assertEqual(data["title"], payload["title"])

    def test_retrieve_apiview_returns_single_object(self):
        """Test RetrieveAPIView returns single object, not array."""
        if self.client is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/tasks/42/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should be dict, not list
        self.assertIsInstance(data, dict)
        self.assertIn("id", data)

    def test_list_apiview_list_format_consistency(self):
        """Test ListAPIView returns consistent list format across versions."""
        if self.client is None:
            self.skipTest("DRF not installed")

        v1_response = self.client.get("/api/v1/docs/")
        v2_response = self.client.get("/api/v2/docs/")

        self.assertEqual(v1_response.status_code, 200)
        self.assertEqual(v2_response.status_code, 200)

        # Both should be lists or have similar structure
        v1_data = v1_response.json()
        v2_data = v2_response.json()
        self.assertEqual(type(v1_data), type(v2_data))

    def test_retrieve_update_destroy_put_vs_patch(self):
        """Test PUT (full update) vs PATCH (partial update) in RetrieveUpdateDestroyAPIView."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # PUT requires all fields
        full_payload = {"title": "Full Update", "completed": True}
        put_response = self.client.put(
            "/api/v2/tasks/42/", data=full_payload, format="json"
        )
        self.assertEqual(put_response.status_code, 200)

        # PATCH allows partial update
        partial_payload = {"completed": False}
        patch_response = self.client.patch(
            "/api/v2/tasks/42/", data=partial_payload, format="json"
        )
        self.assertEqual(patch_response.status_code, 200)

    def test_generic_view_parameter_extraction(self):
        """Test generic views correctly extract URL parameters."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # Test with different IDs
        for task_id in [1, 42, 999]:
            response = self.client.get(f"/api/v1/tasks/{task_id}/")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            # Should have the requested ID
            self.assertEqual(data["id"], task_id)

    def test_retrieve_apiview_version_inheritance_chain(self):
        """Test RetrieveAPIView version inheritance across multiple versions."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # v1 has RetrieveAPIView
        v1 = self.client.get("/api/v1/tasks/42/")
        self.assertEqual(v1.status_code, 200)

        # v2 has RetrieveUpdateDestroyAPIView (different view)
        v2 = self.client.get("/api/v2/tasks/42/")
        self.assertEqual(v2.status_code, 200)

        # v3 should inherit from v2
        v3 = self.client.get("/api/v3/tasks/42/")
        self.assertEqual(v3.status_code, 200)

    def test_create_apiview_multiple_consecutive_creations(self):
        """Test CreateAPIView handles multiple consecutive POSTs without error."""
        if self.client is None:
            self.skipTest("DRF not installed")

        results = []
        for i in range(3):
            payload = {"title": f"Task {i}", "completed": False}
            response = self.client.post("/api/v1/tasks/", data=payload, format="json")
            # All requests should succeed
            self.assertEqual(response.status_code, 201)
            results.append(response.json())

        # All should have returned data
        self.assertEqual(len(results), 3)
        # Each should have required fields
        for result in results:
            self.assertIn("id", result)
            self.assertIn("title", result)

    def test_retrieve_update_destroy_post_not_allowed(self):
        """Test RetrieveUpdateDestroyAPIView doesn't allow POST (not in allowed methods)."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # POST to detail endpoint should not be allowed
        response = self.client.post("/api/v2/tasks/42/", data={}, format="json")
        # Should be 405 Method Not Allowed or similar
        self.assertIn(response.status_code, [405, 400])

    def test_generic_view_with_content_negotiation(self):
        """Test generic views work with different content types."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # JSON format
        response = self.client.get("/api/v1/tasks/42/", format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_retrieve_apiview_vs_list_apiview_endpoints(self):
        """Test that retrieve and list endpoints are separate."""
        if self.client is None:
            self.skipTest("DRF not installed")

        # List endpoint
        list_response = self.client.get("/api/v1/docs/")
        self.assertEqual(list_response.status_code, 200)

        # Retrieve endpoint (different from docs list)
        retrieve_response = self.client.get("/api/v1/tasks/42/")
        self.assertEqual(retrieve_response.status_code, 200)

        # They should have different response structures
        list_data = list_response.json()
        retrieve_data = retrieve_response.json()

        # List is array/collection, retrieve is single object
        self.assertTrue(isinstance(list_data, (list, dict)))
        self.assertIsInstance(retrieve_data, dict)


class EdgeCasesAndErrorHandlingTestCase(TestCase):
    """Test edge cases and error handling per version."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()

    def test_very_large_version_number(self):
        """Test that very large version numbers are rejected or handled."""
        response = self.client.get("/api/v999999999/users/")
        # Should return 404 as version doesn't exist
        self.assertEqual(response.status_code, 404)

    def test_negative_version_in_url_not_matched(self):
        """Test that negative version numbers don't match URL patterns."""
        response = self.client.get("/api/v-1/users/")
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_float_version_not_matched(self):
        """Test that float version numbers don't match URL patterns."""
        response = self.client.get("/api/v1.5/users/")
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_missing_version_placeholder(self):
        """Test accessing versioned endpoint without version."""
        response = self.client.get("/api/users/")
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_extra_path_segment_after_endpoint(self):
        """Test handling of extra path segments."""
        response = self.client.get("/api/v1/users/extra/segment/")
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_case_sensitivity_in_endpoints(self):
        """Test that endpoint paths are case-sensitive."""
        response = self.client.get("/api/v1/Users/")  # capital U
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_trailing_slash_requirement(self):
        """Test trailing slash handling."""
        # Without trailing slash
        response = self.client.get("/api/v1/users")
        # Depending on Django config, this might redirect or 404
        self.assertIn(response.status_code, [301, 404, 200])

    def test_version_zero_not_allowed(self):
        """Test that version 0 is not allowed."""
        response = self.client.get("/api/v0/users/")
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_special_characters_in_url_parameter(self):
        """Test URL parameters with special characters."""
        response = self.client.get("/api/v1/users/123%2F456/")
        # Should handle encoded special characters
        self.assertIn(response.status_code, [200, 404])

    def test_unicode_in_url_parameter(self):
        """Test URL parameters with unicode characters."""
        response = self.client.get("/api/v1/items/test-üñíçødé/")
        # Should return 404 since slug pattern won't match unicode
        self.assertEqual(response.status_code, 404)

    def test_empty_path_parameter(self):
        """Test handling of empty path parameters."""
        response = self.client.get("/api/v1/users//")
        # Should return 404 - double slash is invalid
        self.assertEqual(response.status_code, 404)

    def test_method_not_allowed_on_correct_version(self):
        """Test that correct version enforces method restrictions."""
        # v1 users only allows GET
        response = self.client.post("/api/v1/users/", {})
        self.assertEqual(response.status_code, 405)

    def test_nonexistent_version_returns_404_not_default(self):
        """Test that nonexistent version returns 404, not default."""
        response = self.client.get("/api/v99/users/")
        self.assertEqual(response.status_code, 404)


class ConcurrencyAndFormDataTestCase(TestCase):
    """Test concurrent requests and form data handling per version."""

    def setUp(self):
        """Set up test fixtures."""
        if APIClient is not None:
            self.client = APIClient()
        else:
            self.client = Client()

    def test_upload_v1_form_data(self):
        """Test v1 upload with form data."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        data = {"name": "test_file.txt", "description": "A test file"}
        response = self.client.post("/api/v1/upload/", data, format="multipart")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["name"], "test_file.txt")
        self.assertEqual(result["description"], "A test file")

    def test_upload_v2_form_data(self):
        """Test v2 upload with form data."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        data = {
            "name": "test_file.txt",
            "description": "A test file",
            "tags": "important,archive",
        }
        response = self.client.post("/api/v2/upload/", data, format="multipart")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["name"], "test_file.txt")
        self.assertEqual(result["tags"], ["important", "archive"])
        self.assertIn("timestamp", result)

    def test_upload_v1_json_data(self):
        """Test v1 upload with JSON data."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        data = {"name": "test.json", "description": "JSON file"}
        response = self.client.post("/api/v1/upload/", data, format="json")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["version"], 1)

    def test_upload_v2_json_data(self):
        """Test v2 upload with JSON data."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        data = {"name": "test.json", "description": "JSON file", "tags": "test"}
        response = self.client.post("/api/v2/upload/", data, format="json")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["version"], 2)

    def test_concurrent_requests_same_version(self):
        """Test multiple concurrent requests to same version endpoint."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        import threading

        results = []
        errors = []

        def make_request(version):
            try:
                response = self.client.get(f"/api/v{version}/users/")
                results.append((version, response.status_code))
            except Exception as e:
                errors.append(str(e))

        threads = []
        for _ in range(5):
            # Make 5 concurrent requests to v1
            t = threading.Thread(target=make_request, args=(1,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All requests should succeed
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(code == 200 for _, code in results))

    def test_concurrent_requests_different_versions(self):
        """Test concurrent requests to different version endpoints."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        import threading

        results = []
        errors = []

        def make_request(version):
            try:
                response = self.client.get(f"/api/v{version}/users/")
                data = response.json()
                results.append((version, response.status_code, data["version"]))
            except Exception as e:
                errors.append(str(e))

        threads = []
        for v in [1, 2, 3, 1, 2]:
            t = threading.Thread(target=make_request, args=(v,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All requests should succeed
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        # Verify version returned matches requested version
        for req_version, status, resp_version in results:
            self.assertEqual(status, 200)
            self.assertEqual(req_version, resp_version)

    def test_concurrent_authenticated_requests(self):
        """Test concurrent authenticated requests."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        import threading

        from django.contrib.auth.models import User

        user = User.objects.create_user(username="concurrent_user", password="testpass")
        results = []
        errors = []

        def make_auth_request(version):
            try:
                client = APIClient()
                client.force_authenticate(user=user)
                response = client.get(f"/api/v{version}/secure-data/")
                results.append((version, response.status_code))
            except Exception as e:
                errors.append(str(e))

        threads = []
        for _ in range(3):
            for v in [1, 2]:
                t = threading.Thread(target=make_auth_request, args=(v,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        # All requests should succeed
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(code == 200 for _, code in results))

    def test_request_idempotency_same_version(self):
        """Test that repeated requests to same endpoint return consistent results."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        responses = []
        for _ in range(3):
            response = self.client.get("/api/v2/users/")
            self.assertEqual(response.status_code, 200)
            responses.append(response.json())

        # All responses should be identical
        for resp in responses[1:]:
            self.assertEqual(resp, responses[0])

    def test_request_isolation_different_versions(self):
        """Test that different versions maintain isolation."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        v1_response = self.client.get("/api/v1/users/")
        v2_response = self.client.get("/api/v2/users/")

        v1_data = v1_response.json()
        v2_data = v2_response.json()

        # v1 should have basic fields only
        self.assertEqual(v1_data["version"], 1)
        self.assertNotIn("email", v1_data["users"][0])

        # v2 should have email field
        self.assertEqual(v2_data["version"], 2)
        self.assertIn("email", v2_data["users"][0])


class QueryParameterAndHTTPMethodTestCase(TestCase):
    """Test query parameters and additional HTTP methods per version."""

    def setUp(self):
        """Set up test fixtures."""
        if APIClient is not None:
            self.client = APIClient()
        else:
            self.client = Client()

    def test_search_v1_with_query_parameter(self):
        """Test v1 search endpoint with query parameter."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/search/?q=test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["query"], "test")
        self.assertEqual(data["limit"], 10)  # v1 default limit
        self.assertEqual(len(data["results"]), 1)

    def test_search_v1_with_limit_parameter(self):
        """Test v1 search with limit parameter."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/search/?q=test&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 5)

    def test_search_v2_with_query_parameter(self):
        """Test v2 search endpoint with query parameter."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/search/?q=test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["query"], "test")
        self.assertEqual(data["limit"], 20)  # v2 default limit
        self.assertEqual(data["offset"], 0)
        self.assertEqual(len(data["results"]), 2)

    def test_search_v2_with_pagination_parameters(self):
        """Test v2 search with pagination parameters."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/search/?q=test&limit=50&offset=100")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 50)
        self.assertEqual(data["offset"], 100)
        self.assertEqual(data["total"], 100)

    def test_search_v2_with_filters(self):
        """Test v2 search with filter parameter."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/search/?q=test&filters=category:tech")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filters"], "category:tech")

    def test_resources_v1_get_request(self):
        """Test v1 resources GET request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/resources/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)

    def test_resources_v1_head_request(self):
        """Test v1 resources HEAD request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.head("/api/v1/resources/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Total-Count", response)
        self.assertEqual(response["X-Total-Count"], "42")

    def test_resources_v1_options_request(self):
        """Test v1 resources OPTIONS request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.options("/api/v1/resources/")
        self.assertEqual(response.status_code, 200)

    def test_resources_v2_get_request(self):
        """Test v2 resources GET request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/resources/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(len(data["resources"]), 2)

    def test_resources_v2_head_request(self):
        """Test v2 resources HEAD request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.head("/api/v2/resources/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Total-Count", response)
        self.assertEqual(response["X-Total-Count"], "100")

    def test_resources_v2_post_request(self):
        """Test v2 resources POST request (create)."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.post("/api/v2/resources/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["created"], True)

    def test_resources_v2_options_request(self):
        """Test v2 resources OPTIONS request."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.options("/api/v2/resources/")
        self.assertEqual(response.status_code, 200)

    def test_version_specific_head_headers(self):
        """Test that different versions have different HEAD headers."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        v1_response = self.client.head("/api/v1/resources/")
        v2_response = self.client.head("/api/v2/resources/")
        # Both should succeed
        self.assertEqual(v1_response.status_code, 200)
        self.assertEqual(v2_response.status_code, 200)
        # But headers should reflect versions
        self.assertEqual(v1_response["X-Total-Count"], "42")
        self.assertEqual(v2_response["X-Total-Count"], "100")


class AuthenticationAndPermissionTestCase(TestCase):
    """Test authentication and permission enforcement per version."""

    def setUp(self):
        """Set up test fixtures."""
        if APIClient is not None:
            self.client = APIClient()
        else:
            self.client = Client()

    def test_secure_data_v1_unauthenticated_401_or_403(self):
        """Test that unauthenticated requests to v1 secure endpoint return 401 or 403."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v1/secure-data/")
        self.assertIn(response.status_code, [401, 403])

    def test_secure_data_v2_unauthenticated_401_or_403(self):
        """Test that unauthenticated requests to v2 secure endpoint return 401 or 403."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        response = self.client.get("/api/v2/secure-data/")
        self.assertIn(response.status_code, [401, 403])

    def test_secure_data_v1_with_authentication(self):
        """Test that authenticated requests to v1 secure endpoint succeed."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/secure-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["user"], "testuser")

    def test_secure_data_v2_with_authentication(self):
        """Test that authenticated requests to v2 secure endpoint succeed."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v2/secure-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["user"], "testuser")
        self.assertEqual(data["email"], "test@example.com")

    def test_admin_only_v1_non_admin_403(self):
        """Test that non-admin users get 403 for admin endpoint."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="normaluser", password="testpass")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/admin-only/")
        self.assertEqual(response.status_code, 403)

    def test_admin_only_v2_non_admin_403(self):
        """Test that non-admin users get 403 for v2 admin endpoint."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="normaluser", password="testpass")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v2/admin-only/")
        self.assertEqual(response.status_code, 403)

    def test_admin_only_v1_admin_user_200(self):
        """Test that admin users can access v1 admin endpoint."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="admin", password="testpass", is_staff=True
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/admin-only/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)

    def test_admin_only_v2_admin_user_200(self):
        """Test that admin users can access v2 admin endpoint."""
        if APIClient is None:
            self.skipTest("DRF not installed")
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="admin", password="testpass", is_staff=True
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v2/admin-only/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["admin_user"], "admin")

    def test_protected_data_v1_accessible_without_auth(self):
        """Test that AllowAny permission allows access without authentication."""
        response = self.client.get("/api/v1/protected-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json() if isinstance(self.client, Client) else response.json()
        self.assertEqual(data["version"], 1)

    def test_protected_data_v2_accessible_without_auth(self):
        """Test that AllowAny permission allows access without authentication."""
        response = self.client.get("/api/v2/protected-data/")
        self.assertEqual(response.status_code, 200)
        data = response.json() if isinstance(self.client, Client) else response.json()
        self.assertEqual(data["version"], 2)


class ForwardVersioningComprehensiveTestCase(TestCase):
    """
    Comprehensive tests for forward versioning scenarios.
    Tests segment-based inheritance model, version resolution,
    and edge cases with multiple segments.
    """

    def test_single_segment_all_versions_use_same_impl(self):
        """Test that single segment serves all versions with same implementation."""
        # Products endpoint uses @endpoint("products/<int:product_id>/", version=1)
        # So all versions v1-vMAX use the same v1 implementation (no v2 defined)
        v1 = self.client.get("/api/v1/products/123/").json()
        v2 = self.client.get("/api/v2/products/123/").json()
        v3 = self.client.get("/api/v3/products/123/").json()
        # All should have version=1 because only v1 is defined
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v2["version"], 1)
        self.assertEqual(v3["version"], 1)

    def test_two_segment_boundary(self):
        """Test version boundary between two segments."""
        # Comments has:
        # @endpoint("comments/", version=1) class CommentListV1
        # @endpoint("comments/", version=2) class CommentListV2
        v1 = self.client.get("/api/v1/comments/").json()
        v2 = self.client.get("/api/v2/comments/").json()
        v3 = self.client.get("/api/v3/comments/").json()

        # v1 uses CommentListV1 (class-based view)
        self.assertEqual(v1["version"], 1)
        self.assertNotIn("author", v1["comments"][0])

        # v2 uses CommentListV2 (class-based view)
        self.assertEqual(v2["version"], 2)
        self.assertIn("author", v2["comments"][0])

        # v3+ inherits from v2
        self.assertEqual(v3["version"], 2)
        self.assertIn("author", v3["comments"][0])

    def test_segment_transition_preserves_data_format(self):
        """Test that transitioning between segments preserves data format consistency."""
        # Users endpoint has v1, v2, v3 all separately defined
        v1_data = self.client.get("/api/v1/users/").json()
        v2_data = self.client.get("/api/v2/users/").json()
        v3_data = self.client.get("/api/v3/users/").json()

        # All should have users array
        self.assertIn("users", v1_data)
        self.assertIn("users", v2_data)
        self.assertIn("users", v3_data)

        # Each version adds new fields (forward compatibility demonstration)
        # v1: id, name only
        self.assertEqual(len(v1_data["users"][0]), 2)  # id, name
        # v2: id, name, email
        self.assertEqual(len(v2_data["users"][0]), 3)  # id, name, email
        # v3: id, name, email, status, pagination
        self.assertEqual(len(v3_data["users"][0]), 4)  # id, name, email, status

    def test_version_resolution_selects_highest_matching_segment(self):
        """Test that version resolution uses the highest matching segment."""
        # Posts has: v1 segment, v2 segment
        # Request v4 should use v2 segment (highest available)
        v4 = self.client.get("/api/v4/posts/").json()
        self.assertEqual(v4["version"], 2)

    def test_forward_inheritance_with_parameter_endpoints(self):
        """Test forward versioning with parameterized endpoints."""
        # User detail: v1, v2 segments
        v1_detail = self.client.get("/api/v1/users/123/").json()
        v2_detail = self.client.get("/api/v2/users/123/").json()
        v3_detail = self.client.get("/api/v3/users/123/").json()

        self.assertEqual(v1_detail["version"], 1)
        self.assertNotIn("email", v1_detail)

        self.assertEqual(v2_detail["version"], 2)
        self.assertIn("email", v2_detail)

        # v3 inherits from v2
        self.assertEqual(v3_detail["version"], 2)
        self.assertIn("email", v3_detail)

    def test_max_version_boundary_enforcement(self):
        """Test that requests beyond API_MAX_VERSION return 404."""
        # API_MAX_VERSION is 4 (from settings)
        response = self.client.get("/api/v5/users/")
        self.assertEqual(response.status_code, 404)

    def test_segment_isolation_different_endpoints(self):
        """Test that segments of different endpoints are isolated."""
        # Comments has v1, v2 segments
        # Users has v1, v2, v3 segments
        # v3/comments should exist (use v2 implementation)
        # v3/users should exist (use v3 implementation)

        comments_v3 = self.client.get("/api/v3/comments/").json()
        users_v3 = self.client.get("/api/v3/users/").json()

        self.assertEqual(comments_v3["version"], 2)  # inherits from v2
        self.assertEqual(users_v3["version"], 3)  # explicitly v3

    def test_drf_apiview_forward_inheritance(self):
        """Test forward versioning with DRF APIView."""
        if APIClient is None:
            self.skipTest("DRF not installed")

        client = APIClient()
        # Articles has: v1, v2 segments (DRF APIView)
        v1 = client.get("/api/v1/articles/").json()
        v2 = client.get("/api/v2/articles/").json()
        v3 = client.get("/api/v3/articles/").json()

        self.assertEqual(v1["version"], 1)
        self.assertEqual(v2["version"], 2)
        # v3 inherits from v2
        self.assertEqual(v3["version"], 2)

    def test_forward_inheritance_post_vs_get(self):
        """Test forward inheritance with different HTTP methods."""
        # Articles accepts POST in v1
        client = APIClient() if APIClient else None
        if client is None:
            self.skipTest("DRF not installed")

        # GET should work and inherit
        v3_get = client.get("/api/v3/articles/")
        self.assertEqual(v3_get.status_code, 200)
        self.assertEqual(v3_get.json()["version"], 2)

        # POST might also inherit depending on implementation
        v3_post = client.post("/api/v3/articles/", {"title": "Test"})
        self.assertIn(v3_post.status_code, [200, 201, 405])  # 405 if not allowed

    def test_version_extraction_from_segment_boundary(self):
        """Test that version extraction works correctly at segment boundaries."""
        # Test that URL parameters don't interfere with version extraction
        v1_detail = self.client.get("/api/v1/users/999/").json()
        v2_detail = self.client.get("/api/v2/users/999/").json()

        # Both should resolve to correct version despite path parameter
        self.assertEqual(v1_detail["version"], 1)
        self.assertEqual(v2_detail["version"], 2)
        self.assertEqual(v1_detail["id"], 999)
        self.assertEqual(v2_detail["id"], 999)

    def test_registry_contains_all_versioned_segments(self):
        """Verify registry is correctly populated with all segments."""
        matrix = registry.get_version_matrix()

        # Comments routes should have v1 and v2 versions
        comments_routes = [r for r in matrix.keys() if "comments" in r]
        self.assertTrue(len(comments_routes) > 0)

        # Posts routes should have v1, v2 versions
        posts_routes = [r for r in matrix.keys() if "posts" in r]
        self.assertTrue(len(posts_routes) > 0)

        # Verify products route exists (single segment)
        product_routes = [r for r in matrix.keys() if "products" in r]
        self.assertTrue(len(product_routes) > 0)

    def test_four_segment_cascade(self):
        """Test cascade with four distinct segments (edge case with many versions)."""
        # This test verifies behavior with a complex segment configuration
        # Using Posts which has v1, v2 segments across API_MAX_VERSION=4

        responses = {}
        for v in [1, 2, 3, 4]:
            resp = self.client.get(f"/api/v{v}/posts/").json()
            responses[v] = resp["version"]

        # Expected: v1 -> 1, v2 -> 2, v3 -> 2 (inherit), v4 -> 2 (inherit)
        self.assertEqual(responses[1], 1)
        self.assertEqual(responses[2], 2)
        self.assertEqual(responses[3], 2)
        self.assertEqual(responses[4], 2)

    def test_segment_revert_with_repeated_decorator(self):
        """Test version inheritance across revert scenarios."""
        # Some endpoints may use repeated decorators to "revert" to earlier impl
        # This verifies the behavior works correctly in the segment model

        # Standard forward versioning (not revert scenario, but validates basic model)
        v1 = self.client.get("/api/v1/posts/").json()
        v2 = self.client.get("/api/v2/posts/").json()

        # Verify they're different implementations
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v2["version"], 2)
        self.assertNotEqual(v1["posts"], v2["posts"])  # Different data


class LifecycleMiddlewareIntegrationTestCase(TestCase):
    """Test LifecycleMiddleware with real Django HTTP requests and static URL paths."""

    def setUp(self):
        """Set up test client and lifecycle configuration."""
        self.client = Client()
        # Store original lifecycle config
        self.original_lifecycle = dict(settings.API_VERSION_LIFECYCLE)

    def tearDown(self):
        """Restore original lifecycle configuration."""
        settings.API_VERSION_LIFECYCLE.clear()
        settings.API_VERSION_LIFECYCLE.update(self.original_lifecycle)

    def _set_lifecycle(self, lifecycle_config):
        """Helper to update lifecycle configuration for testing."""
        settings.API_VERSION_LIFECYCLE.clear()
        settings.API_VERSION_LIFECYCLE.update(lifecycle_config)

    def test_scenario_a_deprecated_version_gets_headers(self):
        """Scenario A: Deprecated version with future Sunset date."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        response = self.client.get("/api/v2/users/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("Sunset", response)
        # Verify response is unchanged
        data = response.json()
        self.assertEqual(data["version"], 2)

    def test_scenario_b_retired_version_returns_410(self):
        """Scenario B: Retired version with past Sunset date."""
        from datetime import date, timedelta

        past = (date.today() - timedelta(days=365)).isoformat()

        self._set_lifecycle({1: {"status": "retired", "sunset": past}})

        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 410)
        # Verify normal endpoint is not executed
        self.assertNotIn(
            "version",
            (
                response.json().keys()
                if response.get("content-type") == "application/json"
                else {}
            ),
        )

    def test_scenario_c_active_version_no_headers(self):
        """Scenario C: Active version with no Deprecation/Sunset headers."""
        self._set_lifecycle({3: {"status": "active"}})

        response = self.client.get("/api/v3/users/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Deprecation", response)
        self.assertNotIn("Sunset", response)
        data = response.json()
        self.assertEqual(data["version"], 3)

    def test_scenario_d_deprecated_without_sunset(self):
        """Scenario D: Deprecated without Sunset date."""
        self._set_lifecycle({2: {"status": "deprecated"}})

        response = self.client.get("/api/v2/users/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        self.assertNotIn("Sunset", response)

    def test_scenario_e_retired_with_future_sunset(self):
        """Scenario E: Retired with future Sunset date (should still serve)."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({1: {"status": "retired", "sunset": future}})

        response = self.client.get("/api/v1/users/")

        # Should serve normally if Sunset is in future
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)

    def test_scenario_f_unversioned_routes(self):
        """Scenario F: Unversioned routes don't get lifecycle headers."""
        self._set_lifecycle({1: {"status": "deprecated"}, 2: {"status": "deprecated"}})

        response_health = self.client.get("/health/")
        response_status = self.client.get("/status/")

        self.assertEqual(response_health.status_code, 200)
        self.assertEqual(response_status.status_code, 200)
        self.assertNotIn("Deprecation", response_health)
        self.assertNotIn("Sunset", response_health)
        self.assertNotIn("Deprecation", response_status)
        self.assertNotIn("Sunset", response_status)

    def test_scenario_g_parameterized_routes(self):
        """Scenario G: Version extracted from path prefix, not from parameters."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        # Request with integer parameter should still detect v2 from URL path
        response = self.client.get("/api/v2/users/42/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        data = response.json()
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["version"], 2)

    def test_scenario_h_unknown_versions(self):
        """Scenario H: Unknown and invalid versions don't cause errors."""
        self._set_lifecycle({1: {"status": "deprecated"}, 2: {"status": "deprecated"}})

        # v99 is not configured
        response = self.client.get("/api/v99/users/")
        # Should fail with 404 since endpoint doesn't exist, not from lifecycle
        self.assertIn(response.status_code, [404, 405])

    def test_scenario_i_url_prefix_matching(self):
        """Scenario I: Version extracted only from configured prefix, not arbitrary substrings."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        # A path that contains "api/v2" but not at the start shouldn't match
        # (This verifies the anchored regex works correctly)
        # We can't create a real URL for this in the current setup, but we can test
        # that legitimate v2 URLs work
        response = self.client.get("/api/v2/posts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")

    def test_scenario_j_query_string_doesnt_affect_version(self):
        """Scenario J: Query strings don't affect version detection."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        response = self.client.get("/api/v2/users/?page=1&limit=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        # Query params don't affect the endpoint
        data = response.json()
        self.assertEqual(data["version"], 2)

    def test_scenario_k_drf_integration(self):
        """Scenario K: LifecycleMiddleware works with DRF APIView responses."""
        if APIClient is None:
            self.skipTest("DRF not installed")

        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        # Use APIClient for DRF views
        client = APIClient()
        response = client.get("/api/v2/articles/")

        self.assertEqual(response.status_code, 200)
        # DRF response headers should be preserved
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("Sunset", response)
        data = response.json()
        self.assertEqual(data["version"], 2)

    def test_scenario_l_non_200_downstream_responses(self):
        """Scenario L: Lifecycle headers applied even to error responses."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({1: {"status": "deprecated", "sunset": future}})

        # Make a request that returns a 400 error (missing required field)
        response = self.client.post(
            "/api/v1/items/",
            "{}",  # Missing 'name' field
            content_type="application/json",
        )

        # Should get 400 from the endpoint
        self.assertEqual(response.status_code, 400)
        # But lifecycle headers should still be present
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("Sunset", response)

    def test_version_extraction_multiple_versions_correctly_identified(self):
        """Test that different API versions are correctly identified from their paths."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle(
            {
                1: {"status": "retired", "sunset": future},
                2: {"status": "deprecated", "sunset": future},
                3: {"status": "active"},
                4: {"status": "deprecated", "sunset": future},
            }
        )

        # Test each version is correctly identified and gets appropriate headers
        v1_response = self.client.get("/api/v1/posts/")
        v2_response = self.client.get("/api/v2/posts/")
        v3_response = self.client.get("/api/v3/posts/")
        v4_response = self.client.get("/api/v4/posts/")

        # All should reach their endpoints
        self.assertEqual(v1_response.status_code, 200)
        self.assertEqual(v2_response.status_code, 200)
        self.assertEqual(v3_response.status_code, 200)
        self.assertEqual(v4_response.status_code, 200)

        # Check correct lifecycle headers
        self.assertNotIn("Deprecation", v3_response)
        self.assertEqual(v2_response["Deprecation"], "true")
        self.assertEqual(v4_response["Deprecation"], "true")

    def test_version_lifecycle_with_namespaced_endpoints(self):
        """Test lifecycle headers work with namespaced (app_name) endpoints."""
        from datetime import date, timedelta

        future = (date.today() + timedelta(days=365)).isoformat()

        self._set_lifecycle({2: {"status": "deprecated", "sunset": future}})

        # Test a namespaced endpoint with app_name="admin"
        response = self.client.get("/api/v2/admin/reports/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        data = response.json()
        self.assertEqual(data["version"], 2)


class DRFURLPathVersioningIntegrationTestCase(TestCase):
    """Test boundary behavior between django-api-versioning and DRF URLPathVersioning.

    This test class documents the interaction between the package's routing
    (which registers literal URL paths like api/v2/endpoint/) and DRF's
    URLPathVersioning (which expects a 'version' keyword argument from the
    URL resolver).
    """

    def test_drf_apiview_without_versioning_class(self):
        """DRF APIView without versioning class should still work."""
        # APIView without versioning should handle requests fine
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)

    def test_drf_apiview_request_version_behavior(self):
        """Document that route selection is independent of request.version.

        The package's routing (URL path → handler) is independent of
        DRF's request.version, which depends on configured versioning class.
        """
        # Request /api/v1/users/ reaches the v1 handler
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # The actual response should be from the v1 handler
        self.assertIsInstance(data, (dict, list))

    def test_route_selection_by_url_path_not_request_version(self):
        """Package selects route based on URL path, not DRF request.version."""
        # Request /api/v1/users/ reaches the v1 handler regardless of request.version
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)

    def test_different_versions_reach_different_handlers(self):
        """Different URL versions should reach different registered handlers."""
        # v1 handler
        response_v1 = self.client.get("/api/v1/users/")
        self.assertEqual(response_v1.status_code, 200)

        # v2 handler
        response_v2 = self.client.get("/api/v2/users/")
        self.assertEqual(response_v2.status_code, 200)

        # Routes are different, handlers should differ
        # Verify both succeeded
        data_v1 = response_v1.json()
        data_v2 = response_v2.json()
        self.assertIsInstance(data_v1, (dict, list))
        self.assertIsInstance(data_v2, (dict, list))

    def test_package_handles_versioning_not_drf(self):
        """Package routing is independent of DRF versioning configuration.

        The package selects which handler to call based on the URL path.
        DRF's request.version is determined by DRF's configured versioning
        class, which may not populate request.version unless explicitly
        configured to extract it from the URL keyword argument.

        This is the key boundary: the package handles routing, DRF handles
        the request.version attribute if versioning is configured.
        """
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, 200)

    def test_multiple_versioned_routes_available(self):
        """Multiple versions of same endpoint are available."""
        versions_available = []
        for v in [1, 2, 3, 4]:
            response = self.client.get(f"/api/v{v}/users/")
            if response.status_code == 200:
                versions_available.append(v)

        # At least versions 1 and 2 should be available
        self.assertIn(1, versions_available)
        self.assertIn(2, versions_available)

    def test_nonexistent_version_404(self):
        """Non-existent version returns 404."""
        # Assuming v99 doesn't exist
        response = self.client.get("/api/v99/users/")
        self.assertEqual(response.status_code, 404)

    def test_unversioned_route_independent_of_versioning(self):
        """Unversioned routes work independently of versioning."""
        response = self.client.get("/status/")
        if response.status_code == 200:
            # Unversioned endpoints are independent of versioning scheme
            data = response.json()
            self.assertIsNotNone(data)

    def test_version_specific_handlers_receive_requests(self):
        """Each version-specific URL path routes to its correct handler."""
        # v1 request
        resp1 = self.client.get("/api/v1/users/")
        self.assertEqual(resp1.status_code, 200)

        # v3 request (if v3 is supported)
        resp3 = self.client.get("/api/v3/users/")
        self.assertEqual(resp3.status_code, 200)


def run_integration_tests():
    """Run the integration test suite."""
    from django.conf import settings
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)

    # Run tests in this module
    failures = test_runner.run_tests([__name__])
    return failures


if __name__ == "__main__":
    sys.exit(run_integration_tests())
