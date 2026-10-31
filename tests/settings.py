"""Django settings for the django-api-versioning test suite."""

SECRET_KEY = "test-secret-key-not-for-production"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_api_versioning",  # for management commands
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "django_api_versioning.urls"

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 5
