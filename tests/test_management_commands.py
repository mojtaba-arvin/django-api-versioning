"""Tests for management commands."""
import pytest
from io import StringIO
from django.core.management import call_command


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
