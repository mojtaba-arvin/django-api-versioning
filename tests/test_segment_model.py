import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from django_api_versioning.decorators import endpoint, ver_range
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings as settings


@pytest.fixture
def versions_1_to_5():
    old_min, old_max = settings.API_MIN_VERSION, settings.API_MAX_VERSION
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = 1, 5
    yield
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = old_min, old_max


def _routes():
    return {str(p.pattern) for p in registry.urlpatterns}


def test_segment_introduction_and_continuation(versions_1_to_5):
    @endpoint("reports", version=3)
    def reports(request):
        return JsonResponse({"v": 3})

    assert _routes() == {
        "api/v3/reports",
        "api/v4/reports",
        "api/v5/reports",
    }


def test_segment_removal_at_v4(versions_1_to_5):
    @endpoint("legacy", versions=ver_range(1, 3))
    def legacy(request):
        return JsonResponse({"legacy": True})

    assert _routes() == {
        "api/v1/legacy",
        "api/v2/legacy",
        "api/v3/legacy",
    }


def test_single_version_island(versions_1_to_5):
    @endpoint("beta", versions=[3])
    def beta(request):
        return JsonResponse({"beta": True})

    assert _routes() == {"api/v3/beta"}


def test_multiple_islands(versions_1_to_5):
    @endpoint("audit", versions=[2, 4])
    def audit_ok(request):
        return JsonResponse({})

    assert _routes() == {"api/v2/audit", "api/v4/audit"}


def test_backward_fix_declare_at_min(versions_1_to_5):
    @endpoint("users", version=1)
    def users(request):
        return JsonResponse({"patched": True})

    assert _routes() == {
        "api/v1/users",
        "api/v2/users",
        "api/v3/users",
        "api/v4/users",
        "api/v5/users",
    }


def test_revert_via_repeated_decorator(versions_1_to_5):
    @endpoint("x", version=1)
    def x_a(request):
        return JsonResponse({"impl": "A"})

    @endpoint("x", version=2)
    @endpoint("x", version=4)
    def x_b(request):
        return JsonResponse({"impl": "B"})

    @endpoint("x", version=3)
    def x_c(request):
        return JsonResponse({"impl": "C"})

    routes = {str(p.pattern): p.callback for p in registry.urlpatterns}
    factory = RequestFactory()
    responses = {}
    for path, cb in routes.items():
        version = int(path.split("/")[1].lstrip("v"))
        responses[version] = cb(factory.get(path)).content

    assert b"A" in responses[1]
    assert b"B" in responses[2]
    assert b"C" in responses[3]
    assert b"B" in responses[4]
    assert b"B" in responses[5]
