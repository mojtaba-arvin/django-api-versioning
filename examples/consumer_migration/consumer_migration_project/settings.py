"""Minimal Django settings for the three-version consumer migration walkthrough."""

import sys
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EXAMPLE_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

SECRET_KEY = "consumer-migration-example-only"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
ROOT_URLCONF = "consumer_migration_project.urls"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "django_api_versioning",
    "consumer_app",
]
MIDDLEWARE = ["django_api_versioning.lifecycle.LifecycleMiddleware"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
TEMPLATES = []

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3
API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "deprecated_at": "2026-01-01T00:00:00+00:00",
        "sunset": "2027-06-30",
    },
    2: {"status": "active"},
    3: {"status": "active"},
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
    "DEFAULT_VERSION": "1",
    "ALLOWED_VERSIONS": ["1", "2", "3"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Consumer API Migration Walkthrough",
    "DESCRIPTION": (
        "A runnable V1 to V2 to V3 migration showing coexistence, route "
        "inheritance, explicit removal, and version lifecycle headers."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": False,
}
