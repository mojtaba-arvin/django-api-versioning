"""
Django settings for integration test project.
"""
import os
import sys

# Build paths inside the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Add parent directory to path so we can import django_api_versioning
sys.path.insert(0, PROJECT_ROOT)

SECRET_KEY = "test-secret-key-for-integration-testing"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_api_versioning",
    "api",
]

MIDDLEWARE = []

ROOT_URLCONF = "project.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# API Versioning Settings
API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3
API_VERSIONING_CHANNELS = ["path"]
API_DEPRECATED_VERSIONS = {
    2: {
        "deprecated_date": "2026-01-01",
        "sunset_date": "2026-06-01",
    }
}

TEMPLATES = []

USE_TZ = True
