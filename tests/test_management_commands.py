from io import StringIO

from django.core.management import call_command

from django_api_versioning.decorators import endpoint
from django_api_versioning.registry import registry


def test_check_versions_prints_matrix():
    registry.urlpatterns.clear()

    @endpoint("users", version=2)
    def users_v2(request):
        pass

    out = StringIO()
    call_command("check_versions", stdout=out)
    text = out.getvalue()
    assert "api/v2/users" in text
    assert "users_v2" in text


def test_migrate_endpoints_dry_run(tmp_path):
    code = """
@endpoint("x", version=3, forward=False)
def x(request): ...
"""
    py = tmp_path / "views.py"
    py.write_text(code)

    out = StringIO()
    call_command("migrate_endpoints", "--path", str(tmp_path), "--dry-run", stdout=out)
    assert "versions=[3]" in out.getvalue()
