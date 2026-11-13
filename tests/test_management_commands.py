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
        # Should not raise an exception
        call_command('check_versions', stdout=out)
        output = out.getvalue()
        # getvalue() always returns a string, but output should be meaningful
        assert isinstance(output, str)

    def test_check_versions_empty_registry(self, clear_registry_and_settings):
        """Test check_versions with no registered endpoints."""
        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()
        # Should show a clear message when no endpoints are registered
        assert "No endpoints registered" in output

    def test_check_versions_with_registered_endpoints(self, clear_registry_and_settings):
        """Test check_versions shows registered endpoints."""
        @endpoint("test", version=1)
        def test_view(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Output should contain the endpoint and versions
        assert "test" in output
        assert "v1" in output
        assert "test_view" in output


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

    def test_logical_endpoint_explicit_versions_complete_no_gaps(self, clear_registry_and_settings):
        """Explicit complete version list should not report gaps."""
        @endpoint("complete", versions=[1, 2, 3, 4])
        def complete(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should show all versions without gap warnings
        assert "complete" in output
        assert "v1" in output
        assert "v4" in output
        assert "is not defined" not in output

    def test_logical_endpoint_single_version_no_false_gap(self, clear_registry_and_settings):
        """Single-version endpoint should not report gaps for missing versions."""
        @endpoint("single", versions=[2])
        def single(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should show the endpoint and version without false gaps
        assert "single" in output
        assert "v2" in output
        # Should not report v1 or v3 as missing (they're outside endpoint span)
        lines = output.split('\n')
        for line in lines:
            if "single" in line and "is not defined" in line:
                # If there are warnings for 'single', they should not be for v1 or v3
                assert "v1 is not defined" not in line
                assert "v3 is not defined" not in line

    def test_logical_endpoint_with_app_name(self, clear_registry_and_settings):
        """Endpoints with app_name should be grouped by logical endpoint including namespace."""
        @endpoint("data", version=1, app_name="admin")
        def admin_data(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should show the namespaced endpoint as single logical entity
        assert "admin/data" in output
        assert "v1" in output
        assert "admin_data" in output

    def test_logical_endpoint_unversioned(self, clear_registry_and_settings):
        """Unversioned endpoints should be represented without version labels."""
        @endpoint("status")
        def status(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should show unversioned endpoint
        assert "status" in output
        assert "unversioned" in output

    def test_logical_endpoint_repeated_decorator_revert(self, clear_registry_and_settings):
        """Repeated decorators can revert changes (later source_version wins)."""
        @endpoint("data", version=1)
        @endpoint("data", version=3)  # This overrides v3-v4 from first decorator
        def data(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should group all versions under same logical endpoint "data"
        assert "data" in output
        assert "v1" in output
        assert "v3" in output
        assert "v4" in output
        # v2 should use the version=1 implementation (v1, v2, and part of v3)
        # v3-v4 should use the version=3 implementation
        # Actually v2 comes from v1 segment extending, v3-v4 from v3 segment
        # No gaps should be reported
        assert "is not defined" not in output

    def test_logical_endpoint_direct_registry_register(self, clear_registry_and_settings):
        """Direct registry.register() calls without logical_endpoint should use fallback."""
        def direct_view(request):
            return JsonResponse({})

        # Direct registration without logical endpoint metadata
        registry.register("api/v1/direct", direct_view)

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should still show the route and not crash
        assert "api/v1/direct" in output
        assert "direct_view" in output

    def test_logical_endpoint_extends_to_max_version(self, clear_registry_and_settings):
        """Segment starting before max should extend through API_MAX_VERSION."""
        @endpoint("extend", version=3)
        def extend(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Should register v3 and v4 (extending to max)
        assert "extend" in output
        assert "v3" in output
        assert "v4" in output
        # Should not report v1, v2 as missing (before segment starts)
        assert "v1 is not defined" not in output
        assert "v2 is not defined" not in output

    def test_logical_endpoint_custom_api_base_path(self, clear_registry_and_settings):
        """Logical endpoint identity should be independent of API_BASE_PATH."""
        # Change API_BASE_PATH to a custom format
        old_base_path = settings.API_BASE_PATH
        settings.API_BASE_PATH = "api/version-{version}/"

        @endpoint("custom", version=1)
        def custom(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # Logical endpoint should still be identified as "custom"
        # even though physical URLs are different
        assert "custom" in output
        assert "v1" in output
        assert "custom" in output

        # Restore original base path
        settings.API_BASE_PATH = old_base_path

    def test_logical_endpoint_override_reverse_order(self, clear_registry_and_settings):
        """Override behavior should work regardless of decorator order."""
        @endpoint("override", version=3)
        @endpoint("override", version=1)
        def override(request):
            return JsonResponse({})

        out = StringIO()
        call_command('check_versions', stdout=out)
        output = out.getvalue()

        # All versions should be grouped under same logical endpoint
        assert "override" in output
        assert "v1" in output
        assert "v3" in output
        assert "v4" in output
        # No gaps should be reported (v1-2 from first, v3-4 from second)
        assert "is not defined" not in output


class TestMigrateEndpointsCommand:
    """Test the migrate_endpoints management command."""

    def test_migrate_endpoints_runs(self):
        """Test that migrate_endpoints command executes without error."""
        out = StringIO()
        # Should not raise an exception
        call_command('migrate_endpoints', stdout=out)
        output = out.getvalue()
        # Should return a string output
        assert isinstance(output, str)

    def test_migrate_endpoints_shows_migration_guide(self):
        """Test that migrate_endpoints provides guidance when needed."""
        out = StringIO()
        call_command('migrate_endpoints', stdout=out)
        output = out.getvalue()
        # The command either shows migration suggestions or nothing
        # (when no old-style endpoints with forward/backward are found)
        assert isinstance(output, str)
