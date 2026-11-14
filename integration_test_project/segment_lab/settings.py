"""
Scenario settings layered on the repository's existing integration project.

Every scenario runs in a fresh interpreter because the package registry and
API settings are process-global and initialized during imports.
"""

from pathlib import Path

from project import settings as project_settings
from segment_lab.scenario_catalog import active_scenario

# Reuse the actual integration project's settings and installed applications.
for _name in dir(project_settings):
    if _name.isupper():
        globals()[_name] = getattr(project_settings, _name)

BASE_DIR = Path(project_settings.BASE_DIR)
SECRET_KEY = "segment-lab-local-test-only"
DEBUG = True
ALLOWED_HOSTS = ["*", "testserver", "localhost", "127.0.0.1"]

INSTALLED_APPS = list(project_settings.INSTALLED_APPS)
if "rest_framework" not in INSTALLED_APPS:
    INSTALLED_APPS.append("rest_framework")

# Each scenario controls whether lifecycle middleware is active.
MIDDLEWARE = []
ROOT_URLCONF = "segment_lab.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

LAB_VIEWS_MODULE = "segment_lab.scenarios.main"
SCENARIO = active_scenario()
globals().update(SCENARIO["settings"])
