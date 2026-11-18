"""Tests for management commands."""

import ast
import os
import stat
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import JsonResponse

from django_api_versioning.decorators import endpoint
from django_api_versioning.management.commands import (
    migrate_endpoints as migrate_module,
)
from django_api_versioning.management.commands.migrate_endpoints import (
    _has_comments,
    _rewrite_args,
    _suggest,
)
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
        call_command("check_versions", stdout=out)
        output = out.getvalue()
        # getvalue() always returns a string, but output should be meaningful
        assert isinstance(output, str)

    def test_check_versions_empty_registry(self, clear_registry_and_settings):
        """Test check_versions with no registered endpoints."""
        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()
        # Should show a clear message when no endpoints are registered
        assert "No endpoints registered" in output

    def test_check_versions_can_fail_when_registry_is_empty(
        self, clear_registry_and_settings
    ):
        out = StringIO()

        with pytest.raises(CommandError, match="No endpoints registered"):
            call_command("check_versions", fail_on_empty=True, stdout=out)

        assert "imports the modules containing @endpoint" in out.getvalue()

    def test_check_versions_with_registered_endpoints(
        self, clear_registry_and_settings
    ):
        """Test check_versions shows registered endpoints."""

        @endpoint("test", version=1)
        def test_view(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Output should contain the endpoint and versions
        assert "test" in output
        assert "v1" in output
        assert "test_view" in output


class TestLogicalEndpointMatrix:
    """Test logical endpoint grouping in check_versions."""

    def test_logical_endpoint_continuous_no_false_gaps(
        self, clear_registry_and_settings
    ):
        """Multiple versions of same endpoint should not report false gaps."""

        @endpoint("users", version=2)
        def users(request):
            return JsonResponse({})

        # Should register v2, v3, v4 with no gaps
        out = StringIO()
        call_command("check_versions", stdout=out)
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
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Should report v2 as a gap (between v1 and v3)
        assert "v2 is not defined" in output

        # But should NOT report v4 (beyond endpoint's range)
        # Check that there's no "v4 is not defined" for items
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "items" in line and i + 1 < len(lines):
                # Look for gap warnings for this endpoint
                gap_lines = []
                j = i + 1
                while j < len(lines) and lines[j].startswith("  "):
                    gap_lines.append(lines[j])
                    j += 1
                gap_text = "\n".join(gap_lines)
                if "is not defined" in gap_text:
                    # Only v2 should be reported, not v4
                    assert "v2" in gap_text
                    assert "v4" not in gap_text

    def test_multiple_logical_endpoints_no_interference(
        self, clear_registry_and_settings
    ):
        """Multiple endpoints should not generate false cross-endpoint gaps."""

        @endpoint("users", version=1)
        def users(request):
            return JsonResponse({})

        @endpoint("posts", version=2)
        def posts(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # users: v1, v2, v3, v4 (no gaps)
        # posts: v2, v3, v4 (no gaps, starts at v2)
        # Should not report any gaps
        assert "is not defined" not in output

    def test_logical_endpoint_callback_name_resolution(
        self, clear_registry_and_settings
    ):
        """Callback name should be resolved correctly for different view types."""

        @endpoint("test", version=1)
        def test_view(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Should show the function name
        assert "test_view" in output
        assert "v1" in output

    def test_logical_endpoint_explicit_versions_complete_no_gaps(
        self, clear_registry_and_settings
    ):
        """Explicit complete version list should not report gaps."""

        @endpoint("complete", versions=[1, 2, 3, 4])
        def complete(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Should show all versions without gap warnings
        assert "complete" in output
        assert "v1" in output
        assert "v4" in output
        assert "is not defined" not in output

    def test_logical_endpoint_single_version_no_false_gap(
        self, clear_registry_and_settings
    ):
        """Single-version endpoint should not report gaps for missing versions."""

        @endpoint("single", versions=[2])
        def single(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Should show the endpoint and version without false gaps
        assert "single" in output
        assert "v2" in output
        # Should not report v1 or v3 as missing (they're outside endpoint span)
        lines = output.split("\n")
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
        call_command("check_versions", stdout=out)
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
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # Should show unversioned endpoint
        assert "status" in output
        assert "unversioned" in output

    def test_logical_endpoint_repeated_decorator_revert(
        self, clear_registry_and_settings
    ):
        """Repeated decorators can revert changes (later source_version wins)."""

        @endpoint("data", version=1)
        @endpoint("data", version=3)  # This overrides v3-v4 from first decorator
        def data(request):
            return JsonResponse({})

        out = StringIO()
        call_command("check_versions", stdout=out)
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

    def test_logical_endpoint_direct_registry_register(
        self, clear_registry_and_settings
    ):
        """Direct registry.register() calls without logical_endpoint should use fallback."""

        def direct_view(request):
            return JsonResponse({})

        # Direct registration without logical endpoint metadata
        registry.register("api/v1/direct", direct_view)

        out = StringIO()
        call_command("check_versions", stdout=out)
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
        call_command("check_versions", stdout=out)
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
        call_command("check_versions", stdout=out)
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
        call_command("check_versions", stdout=out)
        output = out.getvalue()

        # All versions should be grouped under same logical endpoint
        assert "override" in output
        assert "v1" in output
        assert "v3" in output
        assert "v4" in output
        # No gaps should be reported (v1-2 from first, v3-4 from second)
        assert "is not defined" not in output


class TestMigrateEndpointsRewriting:
    """Test the legacy argument conversion rules."""

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (
                '"users", version=3, backward=True, forward=True',
                '"users", version=1',
            ),
            (
                '"users", version=3, backward=True, forward=False',
                '"users", versions=list(range(1, 4))',
            ),
            (
                '"users", version=3, backward=False, forward=False',
                '"users", versions=[3]',
            ),
            (
                '"users", version=3, backward=False, forward=True',
                '"users", version=3',
            ),
            (
                '"users", version=3, backward=False, forward=None',
                '"users", versions=[3]',
            ),
        ],
    )
    def test_rewrites_legacy_flag_combinations(self, args, expected):
        assert _rewrite_args(args) == expected

    def test_without_version_is_left_unchanged(self):
        args = '"users", backward=True, forward=False'
        assert _rewrite_args(args) == args

    def test_positional_version_is_left_unchanged(self):
        args = '"users", 2, backward=True, forward=False'
        assert _rewrite_args(args) == args

    def test_existing_explicit_versions_are_left_unchanged(self):
        args = '"users", version=2, versions=[1], backward=True, forward=False'
        assert _rewrite_args(args) == args

    def test_forward_defaults_to_true_when_omitted(self):
        args = '"users", version=2, backward=True'
        assert _rewrite_args(args) == '"users", version=1'

    def test_duplicate_legacy_flags_are_not_rewritten(self):
        args = '"users", version=2, backward=True, backward=False'
        assert _rewrite_args(args) == args

    def test_invalid_syntax_is_not_rewritten(self):
        args = '"users", version=2, backward=True, forward='
        assert _rewrite_args(args) == args
        assert _suggest("@endpoint(\\n") == []

    def test_tokenizer_errors_are_treated_as_unsafe_comments(self):
        assert _has_comments("endpoint(\\n")

    @pytest.mark.parametrize(
        "args",
        [
            '"users", version=3, forward=FORWARD_FLAG',
            '"users", version=3, backward=BACKWARD_FLAG',
        ],
    )
    def test_dynamic_flag_expressions_are_not_rewritten(self, args):
        assert _rewrite_args(args) == args

    def test_preserves_escaped_quotes_and_commas_in_string_literals(self):
        args = r'"users, \"admin\"", version=3, backward=True, forward=False'
        assert _rewrite_args(args) == (
            r'"users, \"admin\"", versions=list(range(1, 4))'
        )

    def test_suggest_ignores_modern_and_noop_declarations(self):
        source = (
            '@endpoint("users", version=2)\n'
            "def users(request):\n"
            "    return None\n"
            '@endpoint("posts", forward=True)\n'
            "def posts(request):\n"
            "    return None\n"
        )
        assert _suggest(source) == []

    def test_suggest_preserves_unrelated_arguments_and_string_contents(self):
        decorator = (
            '@endpoint("users,admin", version=2, backward=True, '
            'forward=False, app_name="public")'
        )
        source = decorator + "\ndef view(request):\n    return None\n"
        assert _suggest(source) == [
            (
                decorator,
                '@endpoint("users,admin", app_name="public", '
                "versions=list(range(1, 3)))",
            )
        ]

    def test_suggest_handles_nested_unrelated_expressions(self):
        decorator = (
            '@endpoint("users", version=2, backward=True, forward=False, '
            'app_name=build_name("public", suffix="v1"))'
        )
        source = decorator + "\ndef view(request):\n    return None\n"
        assert _suggest(source) == [
            (
                decorator,
                '@endpoint("users", app_name=build_name("public", suffix="v1"), '
                "versions=list(range(1, 3)))",
            )
        ]

    def test_suggest_ignores_comments_and_string_literals(self):
        source = (
            '# @endpoint("users", version=2, backward=True, forward=False)\n'
            'example = \'@endpoint("users", version=2, backward=True, '
            "forward=False)'\n"
        )
        assert _suggest(source) == []

    def test_suggest_leaves_decorators_with_comments_unchanged(self):
        source = (
            '@endpoint("users", version=2, backward=True, # keep this note\n'
            "          forward=False)\n"
            "def view(request):\n"
            "    return None\n"
        )
        assert _suggest(source) == []


class TestMigrateEndpointsCommand:
    """Test safe preview defaults and explicit writes against isolated files."""

    def test_migrate_endpoints_runs(self, tmp_path):
        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)
        assert out.getvalue() == ""

    def test_non_directory_path_raises_command_error(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        with pytest.raises(CommandError, match="Migration path is not a directory"):
            call_command("migrate_endpoints", path=str(missing))

    def test_dry_run_reports_changes_without_modifying_files(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        migration_file = migrations / "0001_initial.py"
        migration_file.write_text(source)

        out = StringIO()
        call_command(
            "migrate_endpoints",
            path=str(tmp_path),
            dry_run=True,
            stdout=out,
        )

        output = out.getvalue()
        assert str(view_file) in output
        assert "versions=list(range(1, 3))" in output
        assert view_file.read_text() == source
        assert migration_file.read_text() == source

    def test_default_mode_previews_changes_without_modifying_files(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        migration_file = migrations / "0001_initial.py"
        migration_file.write_text(source)
        unrelated_file = tmp_path / "plain.py"
        unrelated_file.write_text("def plain():\n    return None\n")
        modern_file = tmp_path / "modern.py"
        modern_source = (
            '@endpoint("modern", version=2)\n'
            "def modern(request):\n"
            "    return None\n"
        )
        modern_file.write_text(modern_source)
        hidden_file = tmp_path / ".hidden.py"
        hidden_file.write_text(source)
        symlink_target = tmp_path.parent / f"{tmp_path.name}-outside.py"
        symlink_target.write_text(source)
        symlink_file = tmp_path / "linked.py"
        symlink_file.symlink_to(symlink_target)
        virtualenv = tmp_path / ".venv" / "site-packages" / "example"
        virtualenv.mkdir(parents=True)
        virtualenv_file = virtualenv / "views.py"
        virtualenv_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        assert "versions=list(range(1, 3))" in out.getvalue()
        assert view_file.read_text() == source
        assert migration_file.read_text() == source
        assert unrelated_file.read_text() == "def plain():\n    return None\n"
        assert modern_file.read_text() == modern_source
        assert hidden_file.read_text() == source
        assert symlink_target.read_text() == source
        assert virtualenv_file.read_text() == source
        assert str(view_file) in out.getvalue()
        symlink_target.unlink()

    def test_default_write_result_executes_without_ver_range_import(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        call_command(
            "migrate_endpoints",
            path=str(tmp_path),
            write=True,
            stdout=StringIO(),
        )

        captured = {}

        def endpoint(postfix, **kwargs):
            captured.update(kwargs)
            return lambda view: view

        exec(view_file.read_text(), {"endpoint": endpoint})
        assert captured["versions"] == [1, 2]

    def test_default_write_updates_multiple_decorators_by_source_position(
        self, tmp_path
    ):
        source = (
            '@endpoint("first", version=2, backward=True, forward=False)\n'
            "def first(request):\n"
            "    return None\n"
            '@endpoint("second", version=3, backward=False, forward=False)\n'
            "def second(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        call_command(
            "migrate_endpoints",
            path=str(tmp_path),
            write=True,
            stdout=StringIO(),
        )

        updated = view_file.read_text()
        assert "versions=list(range(1, 3))" in updated
        assert "versions=[3]" in updated
        ast.parse(updated)

    def test_diff_mode_is_deterministic_and_does_not_modify_files(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        first = StringIO()
        second = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), diff=True, stdout=first)
        call_command("migrate_endpoints", path=str(tmp_path), diff=True, stdout=second)

        output = first.getvalue()
        assert output == second.getvalue()
        assert output.startswith("--- views.py\n+++ views.py\n")
        assert '-@endpoint("users", version=2, backward=True, forward=False)' in output
        assert '+@endpoint("users", versions=list(range(1, 3)))' in output
        assert view_file.read_text() == source

    @pytest.mark.skipif(
        os.name == "nt",
        reason="POSIX permission bits are not fully supported on Windows",
    )
    def test_atomic_write_preserves_file_permissions(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)
        view_file.chmod(0o640)

        call_command(
            "migrate_endpoints",
            path=str(tmp_path),
            write=True,
            stdout=StringIO(),
        )

        assert "versions=list(range(1, 3))" in view_file.read_text()
        assert stat.S_IMODE(view_file.stat().st_mode) == 0o640
        assert list(tmp_path.glob(".views.py.*.tmp")) == []

    def test_failed_atomic_replace_keeps_original_and_cleans_temp_file(
        self, tmp_path, monkeypatch
    ):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def view(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        def fail_replace(source_path, target_path):
            raise OSError("simulated atomic replace failure")

        monkeypatch.setattr(migrate_module.os, "replace", fail_replace)

        out = StringIO()
        with pytest.raises(CommandError, match="Could not update views.py"):
            call_command(
                "migrate_endpoints",
                path=str(tmp_path),
                write=True,
                stdout=out,
            )

        assert "Already updated files: none" in out.getvalue()
        assert view_file.read_text() == source
        assert list(tmp_path.glob(".views.py.*.tmp")) == []

    def test_dynamic_legacy_decorator_is_reported_with_path_line_and_reason(
        self, tmp_path
    ):
        source = (
            '@endpoint("users", version=VERSION, backward=True, forward=False)\n'
            "def users(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        output = out.getvalue()
        assert "views.py:1:" in output
        assert "version must be a literal integer" in output
        assert "1 skipped for manual review" in output
        assert view_file.read_text() == source

    def test_positional_version_and_comments_are_reported_separately(self, tmp_path):
        source = (
            '@endpoint("users", 2, backward=True, forward=False)\n'
            "def users(request):\n"
            "    return None\n"
            '@endpoint("posts", version=2, backward=True, # preserve this note\n'
            "          forward=False)\n"
            "def posts(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        output = out.getvalue()
        assert "views.py:1:" in output
        assert "version positionally" in output
        assert "views.py:4:" in output
        assert "contains comments inside the decorator" in output
        assert "2 skipped for manual review" in output

    def test_diff_reports_skipped_occurrences_in_a_separate_section(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def users(request):\n"
            "    return None\n"
            '@endpoint("posts", version=VERSION, backward=True, forward=False)\n'
            "def posts(request):\n"
            "    return None\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), diff=True, stdout=out)

        output = out.getvalue()
        assert output.startswith("--- views.py\n+++ views.py\n")
        assert "Skipped legacy decorators (manual review required):" in output
        assert "views.py:4: version must be a literal integer" in output
        assert view_file.read_text() == source

    def test_syntax_error_with_legacy_markers_is_reported(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def broken(\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        output = out.getvalue()
        assert "file syntax error prevents safe inspection" in output
        assert "views.py:" in output
        assert view_file.read_text() == source

    def test_file_processing_order_is_deterministic(self, tmp_path):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def users(request):\n"
            "    return None\n"
        )
        z_file = tmp_path / "z.py"
        a_file = tmp_path / "a.py"
        z_file.write_text(source)
        a_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        output = out.getvalue()
        assert output.index(str(a_file)) < output.index(str(z_file))

    def test_write_failure_reports_files_already_updated(self, tmp_path, monkeypatch):
        source = (
            '@endpoint("users", version=2, backward=True, forward=False)\n'
            "def users(request):\n"
            "    return None\n"
        )
        first_file = tmp_path / "a.py"
        second_file = tmp_path / "b.py"
        first_file.write_text(source)
        second_file.write_text(source)
        original_replace = os.replace

        def fail_second_replace(source_path, target_path):
            if os.path.basename(target_path) == "b.py":
                raise OSError("simulated second-file replace failure")
            return original_replace(source_path, target_path)

        monkeypatch.setattr(migrate_module.os, "replace", fail_second_replace)
        out = StringIO()

        with pytest.raises(CommandError, match="Could not update b.py"):
            call_command(
                "migrate_endpoints",
                path=str(tmp_path),
                write=True,
                stdout=out,
            )

        assert "Already updated files: a.py" in out.getvalue()
        assert "versions=list(range(1, 3))" in first_file.read_text()
        assert second_file.read_text() == source
        assert list(tmp_path.glob(".*.tmp")) == []

    @pytest.mark.parametrize(
        ("decorator", "expected_reason"),
        [
            (
                '@endpoint("users", version=2, backward=True, backward=False)',
                "duplicate backward= arguments",
            ),
            (
                '@endpoint("users", version=2, backward=True, versions=[1])',
                "explicit versions argument",
            ),
            (
                '@endpoint("users", version=2, backward=True, forward=False, **options)',
                "**kwargs expansion",
            ),
            (
                '@endpoint("users", version=2, backward=FLAG, forward=False)',
                "backward must be a literal boolean",
            ),
            (
                '@endpoint("users", version=2, backward=True, forward=FLAG)',
                "forward must be a literal boolean or None",
            ),
        ],
    )
    def test_unsupported_legacy_forms_are_reported(
        self, tmp_path, decorator, expected_reason
    ):
        source = decorator + "\n" + "def view(request):\n    return None\n"
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        output = out.getvalue()
        assert "views.py:1:" in output
        assert expected_reason in output
        assert "1 skipped for manual review" in output
        assert view_file.read_text() == source

    def test_imported_endpoint_alias_is_rewritten(self, tmp_path):
        source = (
            "from django_api_versioning import endpoint as api_endpoint\\n"
            '@api_endpoint("users", version=2, backward=True, forward=False)\\n'
            "def users(request):\\n"
            "    return None\\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        assert "@api_endpoint(" in out.getvalue()
        assert "versions=[2]" in out.getvalue()
        assert view_file.read_text() == source

    def test_dynamic_imported_endpoint_alias_is_reported(self, tmp_path):
        source = (
            "from django_api_versioning.decorators import endpoint as api_endpoint\\n"
            '@api_endpoint("users", version=VERSION, backward=True, forward=False)\\n'
            "def users(request):\\n"
            "    return None\\n"
        )
        view_file = tmp_path / "views.py"
        view_file.write_text(source)

        out = StringIO()
        call_command("migrate_endpoints", path=str(tmp_path), stdout=out)

        assert "views.py:2:" in out.getvalue()
        assert "version must be a literal integer" in out.getvalue()
