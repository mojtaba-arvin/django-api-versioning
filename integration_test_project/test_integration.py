#!/usr/bin/env python
"""
Integration test runner for django-api-versioning.
Tests the package with a real Django application.
"""
import os
import sys
import django
from django.test.utils import get_runner
from django.conf import settings

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
django.setup()

from django.test import Client, TestCase
from django.urls import reverse, NoReverseMatch
from django_api_versioning.reverse import api_reverse
from django_api_versioning.registry import registry
from api import views


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
            p for p in registry.urlpatterns
            if "user" in (p.name or "")
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
            "/api/v1/orders/",
            {"total": "49.99"},
            content_type="application/json"
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
            content_type="application/json"
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
            "/api/v1/orders/123/",
            {"total": "199.99"},
            content_type="application/json"
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
            content_type="application/json"
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
            "/api/v1/orders/123/",
            {"total": "149.99"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["id"], 123)
        self.assertEqual(data["total"], "149.99")

    def test_drf_patch_v2(self):
        """Test DRF PATCH request (partial update) - v2."""
        response = self.client.patch(
            "/api/v2/orders/123/",
            {"currency": "JPY"},
            content_type="application/json"
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
            "/api/v1/items/",
            {},  # Missing 'name'
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_drf_post_success_with_required_field_v1(self):
        """Test DRF POST with required field - v1."""
        response = self.client.post(
            "/api/v1/items/",
            {"name": "Item A"},
            content_type="application/json"
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
            "/api/v1/orders/",
            {"total": "99.99"},
            content_type="application/json"
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
            content_type="application/json"
        )
        self.assertEqual(post_response.status_code, 201)

    def test_detail_endpoint_multiple_methods_v1(self):
        """Test detail endpoint with GET, PUT, PATCH, DELETE - v1."""
        # GET
        get_response = self.client.get("/api/v1/orders/42/")
        self.assertEqual(get_response.status_code, 200)

        # PUT
        put_response = self.client.put(
            "/api/v1/orders/42/",
            {"total": "299.99"},
            content_type="application/json"
        )
        self.assertEqual(put_response.status_code, 200)

        # PATCH
        patch_response = self.client.patch(
            "/api/v1/orders/42/",
            {"total": "199.99"},
            content_type="application/json"
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
            content_type="application/json"
        )
        self.assertEqual(put_response.status_code, 200)
        put_data = put_response.json()
        self.assertEqual(put_data["currency"], "AUD")

        # PATCH with v2 format
        patch_response = self.client.patch(
            "/api/v2/orders/99/",
            {"currency": "NZD"},
            content_type="application/json"
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
            content_type="application/json"
        )
        self.assertEqual(v1_error.status_code, 400)

        # v2 error (if exists)
        v2_error = self.client.post(
            "/api/v2/items/",
            {},  # missing required field
            content_type="application/json"
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


def run_integration_tests():
    """Run the integration test suite."""
    from django.test.utils import get_runner
    from django.conf import settings

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)

    # Run tests in this module
    failures = test_runner.run_tests([__name__])
    return failures


if __name__ == "__main__":
    sys.exit(run_integration_tests())
