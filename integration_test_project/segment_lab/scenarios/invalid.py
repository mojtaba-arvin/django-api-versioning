"""
"invalid": declarations the package rejects, and when it rejects them.

Each case runs in its own try/except so one module import can record all of
them; without the try/except, the first error aborts the import (and with
it the whole URLconf). API_MIN_VERSION = 1, API_MAX_VERSION = 3.
"""

from django.http import JsonResponse
from django.test import override_settings
from django.views import View

from django_api_versioning import endpoint, ver_range

RECORDED_ERRORS: list[dict] = []


def _record(case, func):
    try:
        func()
    except Exception as exc:  # noqa: BLE001 - recording is the point
        RECORDED_ERRORS.append(
            {"case": case, "error": type(exc).__name__, "message": str(exc)}
        )
    else:
        RECORDED_ERRORS.append({"case": case, "error": None, "message": None})


def view(request):
    return JsonResponse({"handler": "view"})


class Plain(View):
    def get(self, request):
        return JsonResponse({"handler": "Plain.get"})


_record(
    'endpoint("a/", version=4)  # API_MAX_VERSION is 3',
    lambda: endpoint("a/", version=4)(view),
)
_record(
    'endpoint("b/", version=1, versions=[2])',
    lambda: endpoint("b/", version=1, versions=[2])(view),
)
_record(
    'endpoint("c/", version=True)',
    lambda: endpoint("c/", version=True)(view),
)
_record(
    'endpoint("d/", version="2")',
    lambda: endpoint("d/", version="2")(view),
)
_record("ver_range(3, 1)", lambda: ver_range(3, 1))
_record(
    'endpoint("e/", version=1)(Plain())  # an instance, not the class',
    lambda: endpoint("e/", version=1)(Plain()),
)


def _late_registration():
    # Django settings say 5 inside this block; the package read its settings
    # once, when django_api_versioning.settings was first imported.
    with override_settings(API_MAX_VERSION=5):
        endpoint("late/", version=5)(view)


_record(
    'with override_settings(API_MAX_VERSION=5): endpoint("late/", version=5)',
    _late_registration,
)
