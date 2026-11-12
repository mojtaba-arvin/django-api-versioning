---
slug: "019-preserve-backward-compatibility-changing-django-api-endpoints"
title: "Preserving Backward Compatibility in Django API Endpoints"
description: "Use django-api-versioning to route versioned contracts while handling additive fields, request aliases, and legacy response behavior safely in Django REST Framework."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "backward compatibility"
  - "API versioning"
  - "breaking changes"
  - "Django REST Framework"
  - "django-api-versioning"
---

# Preserving Backward Compatibility in Django API Endpoints

An API endpoint is a contract with its clients. Changing a response field, request format, status code, or URL can break integrations that depend on the existing behavior.

A practical compatibility strategy has two separate layers:

- **Contract compatibility:** deciding which request and response shapes remain available to clients.
- **Routing compatibility:** making each API version resolve to the implementation that provides its contract.

For Django REST Framework projects, [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/0.3.4/) provides declarative registration for versioned endpoint implementations. Its `@endpoint` decorator registers a route for the declared version and later versions, until another declaration takes precedence for that route.

The package handles routing, not compatibility policy. You still decide which changes are additive, which changes require a new contract, and how long older contracts remain available.

The examples use a `User` model with `first_name`, `last_name`, `email`, `is_active`, `phone`, and `bio` fields. They demonstrate how to keep older representations available while introducing new behavior without manually maintaining every versioned URL.

For the package's canonical routing rules, including version identifiers, registration precedence, URL names, imports, and ViewSet boundaries, see the [versioning contract reference](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Start with versioned endpoint contracts

Suppose an existing API exposes a flat user representation:

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```

A new client needs a nested `name` object instead:

```json
{
  "id": 1,
  "name": {
    "first": "John",
    "last": "Doe"
  },
  "email": "john@example.com"
}
```

Changing the existing response in place would break clients that still read `first_name` and `last_name`. Keep the original implementation for v1 and register a separate implementation for v2.

### Define the model and serializers

```python
# models.py
from django.db import models


class User(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
```

The serializers make the response contracts explicit:

```python
# serializers.py
from rest_framework import serializers

from .models import User


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "bio",
        ]


class UserSerializerV3(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "bio"]

    def get_name(self, obj):
        return {
            "first": obj.first_name,
            "last": obj.last_name,
        }
```

### Register each contract

For this initial two-version example, configure the supported range:

```python
# settings.py
INSTALLED_APPS += [
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Register the two implementations:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import RetrieveAPIView

from .models import User
from .serializers import UserSerializerV1, UserSerializerV2


@endpoint(
    "users/<int:pk>/",
    version=1,
    view_name="user-detail-v1",
)
class UserDetailV1(RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializerV1


@endpoint(
    "users/<int:pk>/",
    version=2,
    view_name="user-detail-v2",
)
class UserDetailV2(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2
```

The package derives the versioned URL prefix from `API_BASE_PATH` and appends the endpoint path supplied to `@endpoint`. With these settings and declarations, the routes are:

| Request path | Handler | Response contract |
| --- | --- | --- |
| `/api/v1/users/1/` | `UserDetailV1` | Original flat v1 representation |
| `/api/v2/users/1/` | `UserDetailV2` | Flat representation plus `phone` and `bio` |

The URLconf must import the modules containing the decorated views before including the package's generated URL patterns:

```python
# urls.py
from django.urls import include, path

from . import views  # noqa: F401 — import first so decorators register
from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The two view classes represent separate API contracts. A v1 client continues receiving the original representation, while a v2 client receives the additional fields.

What this gains:

- Existing clients do not have to migrate immediately.
- New clients can use the new response contract.
- Each version has an explicit implementation.
- The URLconf does not need a manually maintained list of every versioned route.

What this costs:

You maintain multiple implementations and test each supported contract. The package reduces repeated URL registration; it does not eliminate the code required to implement genuinely different behavior.

## Carry unchanged endpoints into later versions

Not every endpoint needs a new implementation at every version boundary.

The package's `version=N` argument registers an endpoint from version `N` through `API_MAX_VERSION`, inclusive. A declaration with a higher source version takes precedence for the same route in the versions it covers.

For example, expand the supported range:

```python
# settings.py
API_MAX_VERSION = 3
```

Suppose the user list endpoint changes in v2, while v3 changes only its serializer. The declarations can be:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView

from .models import User
from .serializers import (
    UserSerializerV1,
    UserSerializerV2,
    UserSerializerV3,
)


@endpoint("users/", version=1, view_name="user-list-v1")
class UserListV1(ListAPIView):
    serializer_class = UserSerializerV1

    def get_queryset(self):
        return User.objects.filter(is_active=True)


@endpoint("users/", version=2, view_name="user-list-v2")
class UserListV2(ListAPIView):
    serializer_class = UserSerializerV2

    def get_queryset(self):
        return User.objects.all()


@endpoint("users/", version=3, view_name="user-list-v3")
class UserListV3(UserListV2):
    serializer_class = UserSerializerV3
```

The v3 class inherits the v2 queryset behavior and changes only the serializer. Python inheritance reuses implementation behavior; the `@endpoint` declarations determine which implementation is registered for each API version.

The resulting routes are:

| Route | Handler | Behavior |
| --- | --- | --- |
| `/api/v1/users/` | `UserListV1` | Active users, v1 representation |
| `/api/v2/users/` | `UserListV2` | All users, v2 representation |
| `/api/v3/users/` | `UserListV3` | All users, v3 representation |

For a requested API version N, the effective handler is the declaration with the highest source version that is less than or equal to N. The package precomputes this mapping when endpoint declarations are registered: each `version=N` declaration initially covers N through `API_MAX_VERSION`, and a declaration with a higher source version replaces it for overlapping routes.

A declaration for a higher source version never serves a lower version. If no declaration covers a particular endpoint and version, no URL pattern is generated for that combination.

A version outside the configured `API_MIN_VERSION`–`API_MAX_VERSION` range likewise has no generated package route.

Now:

- A request to `/api/v1/users/` resolves to `UserListV1`.
- A request to `/api/v2/users/` resolves to `UserListV2`.
- A request to `/api/v3/users/` resolves to `UserListV3`.

Scope: routing only. The package selects the registered view for a versioned route. It does not decide whether adding a field is backward-compatible, transform response data, or negotiate a serializer automatically.

The same registration pattern applies to detail endpoints:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import RetrieveAPIView

from .models import User
from .serializers import (
    UserSerializerV1,
    UserSerializerV2,
    UserSerializerV3,
)


@endpoint("users/<int:pk>/", version=1, view_name="user-detail-v1")
class UserDetailV1(RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializerV1


@endpoint("users/<int:pk>/", version=2, view_name="user-detail-v2")
class UserDetailV2(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2


@endpoint("users/<int:pk>/", version=3, view_name="user-detail-v3")
class UserDetailV3(UserDetailV2):
    serializer_class = UserSerializerV3
```

Here, v1 list and detail endpoints both restrict access to active users. The later versions allow retrieving inactive users. If that behavior changes, it should be an explicit API policy rather than an accidental queryset difference.

### Registration counts

For the two endpoint paths shown above (`users/` and `users/<int:pk>/`) and three versions:

- The two v1 declarations each cover three versions: six candidate route registrations.
- The two v2 declarations each cover two versions: four candidate route registrations.
- The two v3 declarations each cover one version: two candidate route registrations.

That is six declarations and twelve candidate registrations. After the later declarations take precedence for their routes, six final URL patterns remain: two endpoint paths for each of the three versions.

When you add v4, increase `API_MAX_VERSION` to 4. Existing v3 declarations extend to v4 automatically. Add a v4 declaration only for endpoints whose behavior changes in that version.

### Organize larger APIs by contract version

A version-oriented directory structure keeps serializers, views, and contract-specific behavior discoverable:

```text
users/
    api/
        v1/
            serializers.py
            views.py
        v2/
            serializers.py
            views.py
        v3/
            serializers.py
            views.py
    models.py
    urls.py
```

This is a code-organization choice, not a requirement imposed by the package. The package handles URL registration while the directory structure organizes contract-specific code.

## Additive changes: keep the current contract when clients allow them

Adding an optional response field is often backward-compatible because most clients ignore fields they do not recognize.

That guarantee is not universal. Clients that validate responses against a strict JSON Schema with `additionalProperties: false`, or generated models that reject unknown fields, may fail when a new field appears.

The `UserSerializerV2` above adds `phone` and `bio` while preserving the original fields. If clients tolerate unknown response fields, you may add those fields to the current contract. If that tolerance is unknown or clients require a stable schema, expose the new representation through a new version.

A v1 client receives:

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```

A v2 client receives:

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+1-555-1234",
  "bio": "Software engineer"
}
```

The package keeps these representations attached to their respective routes. The serializer defines the fields; the endpoint registration ensures that clients requesting v1 do not accidentally receive the v2 serializer.

What this gains: clients that tolerate unknown fields can continue using the current version, while clients that need the new fields can opt into the newer contract.

What this costs: the additional fields are included in every response for the version that exposes them, even when some clients do not use them.

Adding optional fields is not a safe substitute for changing the meaning or structure of existing fields. Those changes need a separate compatibility strategy.

## Rename a request field without breaking existing clients

Suppose an API accepts `surname`, but the preferred request field is now `last_name`.

Removing `surname` immediately breaks clients that still send it. A serializer can accept both names during a migration period while storing one canonical model attribute.

The following serializer maps `surname` to `last_name`:

```python
# serializers.py
from rest_framework import serializers

from .models import User


class UserNameAliasSerializer(serializers.ModelSerializer):
    surname = serializers.CharField(
        source="last_name",
        required=False,
        write_only=True,
    )

    class Meta:
        model = User
        fields = ["last_name", "surname"]
        extra_kwargs = {
            "last_name": {"required": False},
        }

    def validate(self, data):
        if "surname" in self.initial_data and "last_name" in self.initial_data:
            raise serializers.ValidationError(
                'Provide either "last_name" or "surname", not both.'
            )

        if not self.partial and "last_name" not in data:
            raise serializers.ValidationError(
                {
                    "last_name": (
                        'This field (or its alias "surname") is required.'
                    )
                }
            )

        return data
```

Register the serializer through an actual update endpoint:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import UpdateAPIView

from .models import User
from .serializers import UserNameAliasSerializer


@endpoint(
    "users/<int:pk>/name/",
    version=2,
    view_name="user-name-update-v2",
)
class UserNameUpdateV2(UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserNameAliasSerializer
```

Because `version=2` carries forward through `API_MAX_VERSION`, this endpoint is available in v2 and later configured versions unless a later declaration replaces it.

A client can send the canonical field:

```json
{
  "last_name": "Doe"
}
```

Or the legacy alias:

```json
{
  "surname": "Doe"
}
```

Both produce validated data containing the model's canonical `last_name` attribute. The serializer rejects a request that sends both names, avoiding ambiguity when two input fields map to the same model attribute.

For this dedicated endpoint, a PATCH request may update the name using either accepted field; a full PUT must provide one of them.

Because `surname` is `write_only`, it is not included in serialized responses. The API returns `last_name` as the canonical output field.

What this gains:

- Existing clients can continue sending `surname`.
- New clients can use `last_name`.
- The model stores one canonical value.
- The transition does not require two model fields.

What this costs:

The serializer carries compatibility logic for the duration of the migration. Multiple simultaneous renames can make this pattern difficult to maintain.

Use an alias for a defined transition period. If the request contract is changing more substantially, a separate API version is usually clearer. The package keeps the versioned route available; the serializer remains responsible for accepting and validating both request names.

## Restructure a response without changing older clients

Changing a flat response:

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```

into a nested response:

```json
{
  "id": 1,
  "name": {
    "first": "John",
    "last": "Doe"
  },
  "email": "john@example.com",
  "phone": "+1-555-1234",
  "bio": "Software engineer"
}
```

is a breaking change for clients that depend on the original fields.

The three serializers defined earlier make the contracts explicit:

- v1 keeps the original flat fields.
- v2 adds `phone` and `bio` while preserving the original structure.
- v3 replaces the flat name fields with a nested `name` object.

The v1, v2, and v3 view declarations route each client to the corresponding serializer. No client is forced to handle two incompatible response structures within the same version.

The trade-off is additional serializers and view implementations for versions whose contracts differ. The package reduces repeated URL registration; it does not remove the need to maintain distinct API contracts.

## Choose the right registration boundary for ViewSets

The examples above use DRF generic views. They fit endpoints that can be represented by a single view callable and registered directly with `@endpoint`.

Resource-shaped endpoints implemented with `ModelViewSet` should generally continue using DRF routers. The package does not automatically replace router-generated routes or register every ViewSet action.

For example, an application can use DRF routers as an alternative for its versioned user resource:

```python
# views.py
from rest_framework.viewsets import ModelViewSet

from .models import User
from .serializers import UserSerializerV1, UserSerializerV2


class UserViewSetV1(ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializerV1


class UserViewSetV2(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2
```

The corresponding URLconf can register the routers:

```python
# urls.py
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

This router-based example is an alternative to registering the same `users/` routes with `@endpoint`. Do not register both sets of patterns for the same paths.

For non-resource endpoints implemented with `APIView` or generic views, `@endpoint` provides declarative registration.

A mixed project can therefore use:

- DRF routers for resource-shaped `ModelViewSet` endpoints.
- `@endpoint` for non-resource APIViews and generic views.

A `ModelViewSet` class cannot be passed directly to `@endpoint` as if it were an ordinary class-based view. A configured callable created with `UserViewSetV1.as_view({"get": "list"})` can be registered for one explicit route, but that does not register the ViewSet's other routes or actions. Each additional route would need its own configured callable.

For the router's route-generation behavior, see the [Django REST Framework router documentation](https://www.django-rest-framework.org/api-guide/routers/).

## Verify the response contract, not only the route

A status-code assertion does not prove that an older client still receives its expected representation. Test the response fields and values for each supported version.

For the detail views above, a contract test can verify the v1, v2, and v3 response shapes:

```python
# tests/test_user_api_contracts.py
import pytest
from rest_framework.test import APIClient

from users.models import User


@pytest.mark.django_db
def test_user_detail_contracts_remain_versioned():
    user = User.objects.create(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone="+1-555-1234",
        bio="Software engineer",
    )

    client = APIClient()

    v1_response = client.get(f"/api/v1/users/{user.pk}/")
    v2_response = client.get(f"/api/v2/users/{user.pk}/")
    v3_response = client.get(f"/api/v3/users/{user.pk}/")

    assert v1_response.status_code == 200
    assert v2_response.status_code == 200
    assert v3_response.status_code == 200

    assert set(v1_response.data) == {
        "id",
        "first_name",
        "last_name",
        "email",
    }

    assert set(v2_response.data) == {
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "bio",
    }

    assert set(v3_response.data) == {
        "id",
        "name",
        "email",
        "phone",
        "bio",
    }

    assert v1_response.data["first_name"] == "John"
    assert v1_response.data["last_name"] == "Doe"

    assert v2_response.data["phone"] == "+1-555-1234"
    assert v2_response.data["bio"] == "Software engineer"

    assert v3_response.data["name"] == {
        "first": "John",
        "last": "Doe",
    }
```

This test assumes the project uses the `users` app label and that the test database is configured. If the app has a different Python import path, adjust the model import accordingly.

The test verifies both layers: the requested version reaches the intended implementation, and that implementation returns the expected contract. It does not prove that every client can tolerate a new field; that remains a client-compatibility requirement.

The alias serializer should also have dedicated tests for:

- PUT with `last_name`.
- PUT with `surname`.
- PUT with neither field.
- PATCH with `last_name`.
- PATCH with `surname`.
- Requests containing both names.
- Response serialization, ensuring `surname` is omitted.

These cases are important because both input fields map to the same model attribute.

## Backward compatibility checklist

### Usually safe without a new version

These changes are often compatible when clients tolerate unknown fields and optional inputs:

- Add an optional response field.
- Add a new endpoint.
- Add an optional request parameter.
- Accept an additional request field name as an alias.
- Add optional metadata without changing existing response fields.

Verify client behavior before deploying these changes into an existing version.

### Usually breaking

These changes should normally be introduced in a new API version:

- Remove a response field.
- Change a field's type.
- Replace flat fields with a nested structure.
- Change the meaning of an existing field.
- Change a status code or error contract for an existing operation.
- Change a URL path.
- Remove an endpoint.
- Make an optional request field required.

The important question is not whether the implementation changed. It is whether an existing client can continue using the same request and response contract.

## Deprecate versions as a separate lifecycle decision

Keeping an older endpoint available is only one part of a compatibility strategy. Clients also need a clear signal when a version is approaching retirement.

`django-api-versioning` includes `LifecycleMiddleware` and the `API_VERSION_LIFECYCLE` setting for version-level lifecycle behavior. For example:

```python
# settings.py
API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "sunset": "2027-06-01",
    },
    2: {
        "status": "active",
    },
    3: {
        "status": "active",
    },
}
```

Add the middleware without replacing the project's existing middleware:

```python
# settings.py
MIDDLEWARE += [
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
```

The date above is illustrative and must be reviewed before deployment. Do not treat it as a permanent production date.

For a version configured as `deprecated` with a sunset date, the middleware adds `Deprecation` and `Sunset` response headers. Once the sunset date has passed, requests for that version receive `410 Gone`.

There are important distinctions:

- `status: "retired"` by itself does not trigger `410 Gone`; the middleware uses the sunset date to determine when to return 410.
- A future sunset date with `status: "retired"` does not produce the deprecation headers; those are associated with the `deprecated` status.
- The current middleware emits `Deprecation: true`. That is a legacy draft form, not the date-valued Structured Field specified by [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745.html).
- The middleware does not automatically generate a `Link` header with `rel="deprecation"`.

The `Sunset` response header is defined separately in [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594.html). If the application also emits an RFC 9745 date-valued `Deprecation` field, ensure that the `Sunset` date is not earlier than the deprecation date. The two headers describe different lifecycle milestones and should be planned together.

The package supplies routing and middleware behavior. Your team still owns the retirement policy, communication to clients, monitoring, and the decision to remove a version.

## Trade-offs and scope

Manual compatibility logic remains useful for changes that do not require a separate route contract:

- Add an optional response field when clients tolerate unknown fields.
- Accept a temporary request alias.
- Preserve a legacy response field for clients that still depend on it.
- Keep a small amount of serializer-specific behavior during a migration.

With `django-api-versioning`:

- Each endpoint implementation is declared once.
- `version=N` registers the declaration from N through `API_MAX_VERSION`.
- A declaration with a higher source version takes precedence for later versions of the same route.
- Unchanged endpoint implementations can carry forward into later versions.
- The URLconf imports the registered patterns through one include.
- Lifecycle middleware can add version-level deprecation and sunset behavior.

The package is a routing and lifecycle layer. It does not decide which changes are breaking, transform serializers, or define the compatibility policy for clients.

When the benefit is smaller: if your project has only one API version and no plans for another, a hand-written URLconf may be simpler. If every endpoint changes at every version boundary, the package's ability to carry unchanged endpoints forward provides less benefit.

## Next steps

Backward compatibility is a policy, not an automatic property of a versioning library. Decide which changes can remain additive, which require a new contract, and how long old versions will remain supported.

Use `django-api-versioning` to keep versioned endpoint registration explicit as those contracts evolve. Then test the response contract for each supported version and define a lifecycle policy before retiring older routes.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) for the implementation and integration examples.
