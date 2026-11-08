"""
Nested URL patterns for testing include() and namespacing.
These are imported into the main urls.py via include().
"""
from django.urls import path
from . import views

# This file demonstrates nested URL patterns
# that work with @endpoint decorator versioning

app_name = 'api'

# These views are decorated with @endpoint
# So they register with django-api-versioning automatically
# This file just needs to be imported in the main urls.py

# Note: The @endpoint decorator on views handles all the URL pattern registration
# This file is just a namespace container for documentation

urlpatterns = [
    # Views are imported from views.py
    # The @endpoint decorator registers them automatically
]
