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
