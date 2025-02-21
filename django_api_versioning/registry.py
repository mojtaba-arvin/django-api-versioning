from typing import Callable, List, Optional
from django.urls import path
from django.http import HttpRequest, HttpResponse


class UrlRegistry:
    """Registry for managing API versioning URLs."""

    def __init__(self):
        self.urlpatterns: List[path] = []
    
    def register(self, route: str, view: Callable[[HttpRequest], HttpResponse], name: Optional[str] = None) -> None:
        """Register a new API endpoint."""
        if self._is_duplicate(route):
            self._remove_duplicate(route)
        
        if not callable(view) and hasattr(view, "as_view"):
            view = view.as_view()

        path_dict = {"name": name} if name else {}
        self.urlpatterns.append(path(route, view, **path_dict))
    
    def _is_duplicate(self, full_path):
        """Check if the route is already registered."""
        return any(str(pattern.pattern) == full_path for pattern in self.urlpatterns)
    
    def _remove_duplicate(self, full_path):
        """Remove any existing route with the same path."""
        self.urlpatterns = [p for p in self.urlpatterns if str(p.pattern) != full_path]


registry = UrlRegistry()

