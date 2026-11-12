---
slug: "014-drf-alternatives-different-views-api-versions"
title: "Different Views per API Version in Django REST Framework"
description: "Register version-specific DRF views declaratively with django-api-versioning, understand route carry-forward, and compare the approach with ViewSet routers and mixins."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django REST Framework"
  - "API versioning"
  - "ViewSets"
  - "Endpoint registration"
  - "Django"
---

# Different Views per API Version in Django REST Framework

When an API evolves, some endpoints need different implementations in different versions. The change may involve more than a serializer: a newer version might introduce additional actions, different query behavior, or a different response structure.

For projects using `APIView` or DRF generic views, [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) provides declarative registration of version-specific implementations. Each view declares the version from which it should serve, and the package generates the corresponding URL patterns.

The package is maintained by the author of this article. Its purpose is to manage endpoint-to-version registration, not to replace DRF's request handling, serializers, or ViewSet routers.

## Register different views for different API versions

Consider an API with two versions. Both versions expose user-list and user-detail endpoints, but v2 changes their serializers and adds a profile endpoint.

The examples assume:

- `User` is the project's configured user model.
- `UserSerializerV1` and `UserSerializerV2` are existing serializers.
- `User` has a reverse one-to-one `Profile` relation accessible as `user.profile`.
- Every user returned by the profile endpoint has an associated profile. Otherwise, access to `user.profile.bio` must handle the missing related object.

Configure the supported version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Declare the v1 views:

```python
# accounts/views.py

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@endpoint("users/", version=1)
class UserListViewV1(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/<int:pk>/", version=1)
class UserDetailViewV1(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1
```

Now declare the v2 implementations:

```python
# accounts/views.py

@endpoint("users/", version=2)
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2


@endpoint("users/<int:pk>/", version=2)
class UserDetailViewV2(UserDetailViewV1):
    serializer_class = UserSerializerV2


@endpoint("users/<int:pk>/profile/", version=2)
class UserProfileViewV2(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response({
            "bio": user.profile.bio,
        })
```

Here, Python class inheritance and route-registration inheritance are separate mechanisms:

- Python inheritance reuses the implementation of the v1 generic views.
- The `@endpoint` declarations determine which implementation is registered for each API version.

The v2 classes inherit the generic-view behavior but replace the serializer. The profile endpoint is a new v2-only route.

### Mount the generated URL patterns

Import the modules containing endpoint declarations before importing the package's generated URL patterns:

```python
# project/urls.py

from django.urls import include, path

from accounts import views as account_views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The `account_views` import executes the decorators and populates the registry. The package does not automatically discover and import application view modules.

With the default `API_BASE_PATH = "api/v{version}/"`, the declarations produce these routes:

| URL pattern | Registered view | Registration |
| --- | --- | --- |
| `/api/v1/users/` | `UserListViewV1` | v1 |
| `/api/v2/users/` | `UserListViewV2` | v2 replaces the v1 registration for v2 |
| `/api/v1/users/<int:pk>/` | `UserDetailViewV1` | v1 |
| `/api/v2/users/<int:pk>/` | `UserDetailViewV2` | v2 replaces the v1 registration for v2 |
| `/api/v2/users/<int:pk>/profile/` | `UserProfileViewV2` | v2 |

There are five declarations and five final URL patterns: two routes in v1 and three in v2.

### Understand route carry-forward and replacement

The package supports two version-registration modes:

- `version=N` registers the implementation from version N through `API_MAX_VERSION`, inclusive.
- `versions=[...]` registers the implementation only for the explicitly listed versions.

For example, `version=1` initially registers an endpoint for both v1 and v2 when the configured maximum is 2. A later declaration for the same route with `version=2` replaces the v2 registration.

This is registration-time behavior. The package does not search older view classes when a request arrives, and it does not create Python inheritance between them.

**Now:**

- `/api/v1/users/` resolves to `UserListViewV1`.
- `/api/v2/users/` resolves to `UserListViewV2`.
- `/api/v2/users/<int:pk>/profile/` resolves to `UserProfileViewV2`.
- The profile endpoint has no v1 registration.

**Scope: routing only.** The package does not decide whether a response change is backward compatible, merge serializers, or share business logic between versions.

For the exact behavior of version validation, route construction, collision precedence, and import order, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## When the project uses ModelViewSet

The preceding example uses DRF generic views. This is an important boundary: `@endpoint` does not directly support decorating a `ModelViewSet` class.

A ViewSet requires an action mapping when converted into a Django view callable. The package's class-based view handling calls `as_view()` without that mapping, so decorating a ViewSet class directly does not work.

For resource-oriented endpoints that rely on `ModelViewSet`, DRF routers remain the appropriate registration mechanism.

For example, each API version can have its own ViewSet:

```python
# accounts/views.py

from django.contrib.auth import get_user_model
from rest_framework import viewsets

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


class UserViewSetV1(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


class UserViewSetV2(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2
```

Register them with separate routers:

```python
# accounts/urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import UserViewSetV1, UserViewSetV2


v1_router = SimpleRouter()
v1_router.register("users", UserViewSetV1, basename="v1-user")

v2_router = SimpleRouter()
v2_router.register("users", UserViewSetV2, basename="v2-user")


urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

This is standard DRF router configuration. The router generates the list, detail, and applicable action routes for each ViewSet.

The router-based configuration is separate from the package's endpoint registry. The package does not automatically discover, mount, or inherit router-generated routes.

### A configured ViewSet callable is a narrower option

A configured `as_view()` callable can be registered with `@endpoint` for one specific route:

```python
# accounts/versioned_routes.py

from django_api_versioning import endpoint

from .views import UserViewSetV1


user_list_v1 = endpoint("users/", version=1)(
    UserViewSetV1.as_view({
        "get": "list",
        "post": "create",
    })
)
```

This registers the explicitly configured list/create callable. It does not generate the ViewSet's detail route or its other actions. Those still require their own configured callables or normal router registration.

Do not mount the same route through both this callable and a router unless the duplicate registration is intentional and its precedence is understood.

## Share behavior with mixins when versions overlap

Separate ViewSet classes do not require duplicating all their behavior. When several versions share CRUD operations, DRF's generic mixins can provide a common base.

For example:

```python
# accounts/mixins.py

from rest_framework.decorators import action
from rest_framework.response import Response


class UserV2ExtendedMixin:
    @action(detail=True, methods=["get"])
    def profile_extended(self, request, pk=None):
        user = self.get_object()
        return Response({
            "bio": user.profile.bio,
        })

    @action(detail=False, methods=["get"])
    def trending(self, request):
        users = self.get_queryset().order_by("-followers")[:10]
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
```

Compose the shared CRUD behavior and the v2-specific actions:

```python
# accounts/views.py

from django.contrib.auth import get_user_model
from rest_framework import mixins, viewsets

from .mixins import UserV2ExtendedMixin
from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


class BaseUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()


class UserViewSetV1(BaseUserViewSet):
    serializer_class = UserSerializerV1


class UserViewSetV2(UserV2ExtendedMixin, BaseUserViewSet):
    serializer_class = UserSerializerV2
```

The routers still need to register each version's ViewSet. The mixins reduce duplicated view behavior; they do not replace URL registration.

DRF routers discover the extra actions declared on the ViewSet, including inherited methods decorated with `@action`. Keep mixins cohesive and avoid building a deep composition hierarchy that makes the effective behavior difficult to trace.

## Compare the registration responsibilities

The approaches solve related but different problems:

| Concern | `django-api-versioning` with generic views | Per-version ViewSets and routers | Mixin-based ViewSets |
| --- | --- | --- | --- |
| Main registration mechanism | `@endpoint` declarations | `SimpleRouter` registrations | `SimpleRouter` registrations |
| Version-specific implementations | Separate decorated views | Separate ViewSet classes | Separate ViewSet classes |
| Shared behavior | Python inheritance or shared helpers | Optional Python inheritance | Composed mixins and shared base classes |
| Carry-forward of unchanged routes | Supported through `version=N` | Must be represented in router configuration | Must be represented in router configuration |
| `ModelViewSet` and `@action` | Not supported by direct class decoration | Supported | Supported |
| URLconf structure | One include for generated package routes | Router URLs mounted under each version | Router URLs mounted under each version |
| Import requirement | Import decorated view modules before package URL patterns | Import ViewSets before router registration | Import ViewSets and mixins before router registration |

The package is most useful when the main maintenance problem is registering endpoint implementations across versions, particularly when many endpoints remain unchanged and only selected implementations need replacement.

The router approaches are more appropriate when the API is organized around resource-oriented ViewSets and depends heavily on `ModelViewSet` and `@action`.

## Trade-offs and scope

Declarative registration reduces the need to repeat version-specific URL configuration. It also keeps the route's version declaration next to the view implementation.

However, segment registration has an important consequence: a declaration such as `version=1` remains registered through `API_MAX_VERSION` unless a later declaration replaces it.

If an endpoint's contract changes but its registration does not, the earlier implementation can continue serving later versions. Teams should review the route matrix whenever they change API contracts and test the behavior of each supported version.

The package does not:

- Create Python inheritance between view classes.
- Merge serializers, permissions, or business logic.
- Determine whether a response change is backward compatible.
- Directly decorate `ModelViewSet` classes.
- Automatically integrate DRF router-generated routes.
- Generate or maintain version-specific OpenAPI schemas.

For projects that only need a small number of version-specific ViewSets, per-version routers may be sufficient. For projects that use generic views and need a declarative mapping between endpoint implementations and versions, the package offers a different registration model.

The choice should follow the project's endpoint structure and the maintenance burden of its versioned routing—not an arbitrary threshold based on the number of versions.

## Conclusion

Different API versions can use separate view implementations without requiring every endpoint to be implemented from scratch.

For generic views, `django-api-versioning` provides declarative endpoint registration and explicit carry-forward and replacement behavior. For resource-oriented ViewSets, DRF routers remain the appropriate mechanism, with mixins available when versions share behavior.

The important distinction is between selecting an implementation for a versioned route and composing the Python behavior of that implementation. Those responsibilities can be handled independently.

**Next step:** review the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) and compare its generated route matrix with the version-specific endpoints in your project.
