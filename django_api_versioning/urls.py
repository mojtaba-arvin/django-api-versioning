from typing import List
from django.urls import URLPattern
from .registry import registry

urlpatterns: List[URLPattern] = registry.urlpatterns
