# Defect: DRF ViewSet Incompatibility

## Summary
The `@endpoint` decorator does not support DRF ViewSets. Attempting to use `@endpoint` on a ViewSet class results in a `TypeError`.

## Root Cause
In `django_api_versioning/registry.py`, the `_create_pattern()` method calls `view.as_view()` without arguments (line 112):

```python
if isinstance(view, type) and callable(getattr(view, "as_view", None)):
    view = view.as_view()
```

This works for:
- Django class-based views (View, TemplateView, etc.)
- DRF APIView and generic views (ListAPIView, RetrieveAPIView, etc.)

But it fails for DRF ViewSets because ViewSets require an `actions` mapping:

```python
# DRF ViewSet.as_view() requires actions:
ProductViewSet.as_view({'get': 'list'})  # ✅ Works
ProductViewSet.as_view()                # ❌ TypeError
```

## Error Details
```
TypeError: The `actions` argument must be provided when calling `.as_view()` on a ViewSet.
For example `.as_view({'get': 'list'})`
```

## Impact
- **Affected Users**: Anyone trying to use DRF ViewSets with the @endpoint decorator
- **Severity**: HIGH - Feature incompatibility
- **Documentation**: Not documented in README or docstrings

## Current Workaround
Users must manually register ViewSet routes using DRF's routers OUTSIDE the @endpoint decorator:

```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('products', ProductViewSet, basename='products')

# Then add router.urls to URL configuration manually
# This defeats the purpose of @endpoint (automatic registration)
```

## Proposed Solutions

### Option 1: Detect ViewSets and skip them
Modify `_create_pattern()` to detect ViewSets and raise a clear error with guidance:
```python
from rest_framework.viewsets import ViewSetMixin

if isinstance(view, type) and issubclass(view, ViewSetMixin):
    raise TypeError(
        f"ViewSet {view.__name__!r} is not supported by @endpoint. "
        f"Use DRF's DefaultRouter with manual URL registration instead."
    )
```

### Option 2: Support ViewSets with actions mapping
This would require:
- Adding an optional `actions` parameter to the @endpoint decorator
- Determining action mappings (complex, depends on HTTP method routing)
- Significant architectural changes

### Option 3: Document as unsupported
Update README and docstrings to clearly state ViewSets are not supported, with workaround.

## Recommendation
**Option 1 + Option 3**: Raise a clear error and document the limitation.

This prevents silent failures and guides users to appropriate alternatives (DRF routers).

## Test Case
```python
from rest_framework import viewsets
from django_api_versioning.decorators import endpoint

@endpoint("products/", version=1)
class ProductViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

# Results in: TypeError: The `actions` argument must be provided...
```

## Files Affected
- `django_api_versioning/registry.py` (line 111-112)
- `django_api_versioning/decorators.py` (docstring should document limitation)
- `README.md` (compatibility matrix should note ViewSet incompatibility)

## Related Documentation
- [DRF Viewsets](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF Routers](https://www.django-rest-framework.org/api-guide/routers/)
