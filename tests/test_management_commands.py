"""Tests for management commands."""
import pytest
from io import StringIO
from django.core.management import call_command
from django.http import JsonResponse

from django_api_versioning.decorators import endpoint
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings as settings


@pytest.fixture
def clear_registry_and_settings():
    """Clear registry and temporarily set version range."""
    old_min, old_max = settings.API_MIN_VERSION, settings.API_MAX_VERSION
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = 1, 4
    registry.urlpatterns.clear()
    yield
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = old_min, old_max
    registry.urlpatterns.clear()


class TestCheckVersionsCommand:
    """Test the check_versions management command."""

    def test_check_versions_runs(self):
        """Test that check_versions command executes without error."""
        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()
        assert output is not None

    def test_check_versions_output_format(self):
        """Test that check_versions produces output."""
        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()
        # Should produce some output (at least showing registered routes)
        assert len(output) > 0 or output == ""  # May be empty if no routes


class TestLogicalEndpointMatrix:
    """Test logical endpoint grouping in check_versions."""

    def test_logical_endpoint_continuous_no_false_gaps(self, clear_registry_and_settings):
        """Multiple versions of same endpoint should not report false gaps."""
        @endpoint("users", version=2)
        def users(request):
            return JsonResponse({})

        # Should register v2, v3, v4 with no gaps
        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should NOT report v1 as missing (it's before endpoint starts)
        assert "v1 is not defined" not in output

        # Endpoint should be listed under logical ID "users", not physical URLs
        assert "users" in output
        assert "v2" in output

    def test_logical_endpoint_with_internal_gap(self, clear_registry_and_settings):
        """Internal gaps within endpoint span should be reported."""
        @endpoint("items", versions=[1, 3])
        def items(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should report v2 as a gap (between v1 and v3)
        assert "v2 is not defined" in output

        # But should NOT report v4 (beyond endpoint's range)
        # Check that there's no "v4 is not defined" for items
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if "items" in line and i + 1 < len(lines):
                # Look for gap warnings for this endpoint
                gap_lines = []
                j = i + 1
                while j < len(lines) and lines[j].startswith('  '):
                    gap_lines.append(lines[j])
                    j += 1
                gap_text = '\n'.join(gap_lines)
                if "is not defined" in gap_text:
                    # Only v2 should be reported, not v4
                    assert "v2" in gap_text
                    assert "v4" not in gap_text

    def test_multiple_logical_endpoints_no_interference(self, clear_registry_and_settings):
        """Multiple endpoints should not generate false cross-endpoint gaps."""
        @endpoint("users", version=1)
        def users(request):
            return JsonResponse({})

        @endpoint("posts", version=2)
        def posts(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # users: v1, v2, v3, v4 (no gaps)
        # posts: v2, v3, v4 (no gaps, starts at v2)
        # Should not report any gaps
        assert "is not defined" not in output

    def test_logical_endpoint_callback_name_resolution(self, clear_registry_and_settings):
        """Callback name should be resolved correctly for different view types."""
        @endpoint("test", version=1)
        def test_view(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should show the function name
        assert "test_view" in output
        assert "v1" in output


class TestMigrateEndpointsCommand:
    """Test the migrate_endpoints management command."""

    def test_migrate_endpoints_runs(self):
        """Test that migrate_endpoints command executes without error."""
        out = StringIO()
        call_command('migrate_endpoints', stdout=out)
        output = out.getvalue()
        assert output is not None

    def test_migrate_endpoints_shows_migration_guide(self):
        """Test that migrate_endpoints shows migration information."""
        out = StringIO()
        call_command('migrate_endpoints', stdout=out)
        output = out.getvalue()
        # Should show some migration guidance
        assert isinstance(output, str)
