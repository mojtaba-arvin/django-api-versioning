"""WSGI entry point used by Schemathesis for in-process API testing."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_project.settings")

application = get_wsgi_application()
