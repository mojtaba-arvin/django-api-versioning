---
slug: "012-caching-versioned-drf-apis-headers-paths-and-routes"
title: "Caching Versioned DRF APIs: Headers, Paths, and Routes"
description: "Compare cache behavior when API versions live in Accept headers, URL paths, or endpoint registrations, and understand the routing trade-offs."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "DRF versioning"
  - "API caching"
  - "django-api-versioning"
  - "HTTP Vary header"
  - "API routing"
---

# Caching Versioned DRF APIs: Headers, Paths, and Routes

API versioning affects more than how a view selects a serializer. It also affects how HTTP caches distinguish responses belonging to different API versions.

Consider two clients requesting the same resource:

- One expects the v1 representation.
- The other expects the v2 representation.

If both requests use the same URL, the cache must distinguish them using request headers. If the version is part of the URL, the URL itself provides a separate cache identity.

There is another consideration: how the application registers the views serving each version.

For APIs where most endpoints remain unchanged between releases and only selected endpoints need new implementations, [`django-api-versioning`](https://pypi.org/project/django-api-versioning/) provides declarative endpoint registration. It generates versioned URL patterns from view declarations instead of requiring version-dispatch branches in every shared view.

This article examines the relationship between cache identity and three implementation approaches:

1. `AcceptHeaderVersioning`: the version is carried in the `Accept` header.
2. `URLPathVersioning`: the version is captured from the URL path.
3. `django-api-versioning`: version-specific implementations are registered at the view declaration, and the package generates their URLs.

These approaches address different concerns. DRF's versioning schemes determine the request version, while the package manages endpoint registration.

*Disclosure: I maintain django-api-versioning.*

## 1. Endpoint registration and URL-based cache identity

With `django-api-versioning`, the version is declared next to the view implementation:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

```python
# views.py
from django.contrib.auth import get_user_model
from rest_framework.generics import ListCreateAPIView

from django_api_versioning import endpoint

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@endpoint("users/", version=1)
class UserListV1(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2)
class UserListV2(UserListV1):
    serializer_class = UserSerializerV2
```

The example assumes both serializers are defined in the application's `serializers.py`.

With the default `API_BASE_PATH = "api/v{version}/"`, the package generates:

```text
/api/v1/users/ -> UserListV1
/api/v2/users/ -> UserListV2
```

The v1 declaration covers versions 1 through `API_MAX_VERSION`. The v2 declaration replaces it for v2.

The generated URLs are different, so an ordinary HTTP cache that includes the request URL in its cache key can distinguish the two representations:

```text
GET /api/v1/users/
GET /api/v2/users/
```

The cache does not need to inspect a version parameter in the `Accept` header to distinguish these two URLs.

This does not mean that the package implements HTTP caching. It generates routes. Cache-control policies, expiration, invalidation, authorization-aware caching, and other cache behavior remain application and infrastructure concerns.

### Importing the generated URL patterns

The modules containing decorated views must be imported before the package's URL patterns:

```python
# urls.py
from django.urls import include, path

from . import views  # noqa: F401 — execute endpoint declarations first

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import executes the decorators and registers the views. The package does not automatically discover application view modules.

If endpoint declarations are distributed across multiple modules, import each relevant module before importing `api_urlpatterns`.

For the exact registration, collision, and URL construction rules, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

### Registration precedence

A segment declaration such as `version=1` registers an implementation from v1 through `API_MAX_VERSION`.

When registrations collide on the same route:

- If both source versions are integers, the higher source version wins.
- If the source versions are equal, the latest registration wins.
- If either source version is `None`, the latest registration wins.

This is route-registration precedence, not request-time traversal. It also does not establish semantic backward compatibility: carrying an implementation forward does not prove that its response contract remains appropriate for newer API versions.

## 2. AcceptHeaderVersioning: one URL, multiple cache variants

DRF's `AcceptHeaderVersioning` extracts the version from a media-type parameter in the request's `Accept` header.

For example:

```http
GET /api/users/
Accept: application/json; version=v1
```

and:

```http
GET /api/users/
Accept: application/json; version=v2
```

Both requests target the same URL. The version is part of the representation negotiation.

Configure DRF:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.AcceptHeaderVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

A shared view can branch on `request.version`:

```python
# views.py
from django.contrib.auth import get_user_model
from django.utils.cache import patch_vary_headers
from rest_framework.generics import ListCreateAPIView

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


class UserList(ListCreateAPIView):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.version == "v1":
            return UserSerializerV1

        return UserSerializerV2

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(
            request,
            response,
            *args,
            **kwargs,
        )
        patch_vary_headers(response, ("Accept",))
        return response
```

The URLconf contains one entry:

```python
# urls.py
from django.urls import path

from .views import UserList

urlpatterns = [
    path("api/users/", UserList.as_view(), name="user-list"),
]
```

The two requests have the same URL but can produce different response bodies.

### Why Vary: Accept matters

A cache needs to know which request headers influence a response representation.

For header-based versioning, the relevant header is `Accept`. The response should include:

```http
Vary: Accept
```

This tells compliant caches that the response can vary according to the request's `Accept` header.

The example uses Django's `patch_vary_headers()` rather than assigning `Vary` directly. This preserves existing `Vary` values instead of overwriting them.

DRF may add `Vary: Accept` in some renderer configurations, but header-based versioning should not rely on renderer configuration as a universal guarantee. Explicitly ensuring the header is present makes the cache requirement clear.

Without the appropriate `Vary` behavior, a shared cache could reuse a v1 response for a v2 request because both requests have the same URL.

There is one more infrastructure requirement: the cache in front of the application must actually respect `Vary`. Some CDNs or reverse proxies may use a custom cache-key policy that ignores selected headers. In that case, configure the cache key to include `Accept`, or prevent unsafe shared caching of those responses.

### Trade-offs

- One URL represents the resource across all supported versions.
- Version selection happens through request headers.
- A shared view can branch on `request.version`.
- Cache behavior depends on the cache respecting `Vary: Accept`.
- The version is not visible in the URL, which can make manual inspection and debugging less convenient.

This approach is appropriate when a stable URL is important and clients can reliably send the required `Accept` header.

## 3. URLPathVersioning: version in the cache key

`URLPathVersioning` obtains the version from a named URL keyword argument.

Configure DRF:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.URLPathVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

The URL pattern captures the version:

```python
# urls.py
from django.urls import path

from .views import UserList

urlpatterns = [
    path(
        "api/<str:version>/users/",
        UserList.as_view(),
        name="user-list",
    ),
]
```

The default `VERSION_PARAM` is `"version"`, which is why the converter uses `<str:version>`. If you customize `VERSION_PARAM`, the URL pattern must use the corresponding keyword argument.

The view can use the same `get_serializer_class()` implementation shown in the previous section. DRF exposes the extracted value as `request.version`.

Clients request different URLs:

```bash
curl http://api.example.com/api/v1/users/
curl http://api.example.com/api/v2/users/
```

Both URLs match the same URL pattern. DRF then validates the captured version against `ALLOWED_VERSIONS`.

### Cache behavior

Unlike header-based versioning, the version is already part of the URL:

```text
/api/v1/users/
/api/v2/users/
```

A normal URL-based cache key distinguishes these requests without needing `Vary: Accept` specifically for version separation.

The cache can store separate entries for the two URLs:

```text
cache key: /api/v1/users/
cache key: /api/v2/users/
```

This is a simpler cache identity model when the API version is part of the public URL.

However, this does not remove the need for correct cache policies. Responses may still vary by other headers, authentication, content negotiation, or application-specific conditions.

### A common URLconf misconception

`URLPathVersioning` does not require a separate URL pattern for every version.

This single pattern:

```python
path(
    "api/<str:version>/users/",
    UserList.as_view(),
    name="user-list",
)
```

matches both v1 and v2. DRF then validates the captured value against `ALLOWED_VERSIONS`.

The URL pattern does not itself restrict the version to the values in `ALLOWED_VERSIONS`; the versioning scheme performs that validation.

A literal route such as:

```python
path("api/v1/users/", UserList.as_view(), name="user-list")
```

does not provide a `version` keyword argument. Consequently, `URLPathVersioning` cannot extract the version from that pattern and falls back to `DEFAULT_VERSION`.

### Trade-offs

- The version is visible in the URL and browser history.
- Different versions naturally have different URL-based cache keys.
- A shared view can still branch on `request.version`.
- The URLconf needs one dynamic pattern per endpoint, not one pattern per version.
- Version-specific behavior remains inside the shared view unless you introduce separate view implementations.

This is a practical DRF-native choice when URL-based version identity is desirable and a shared view with conditional behavior is manageable.

For the official behavior of these schemes, see [DRF's versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/).

## 4. Comparing the three approaches

The main difference is where the version is represented and how that affects route registration and cache identity.

| Concern | AcceptHeaderVersioning | URLPathVersioning | `django-api-versioning` |
| --- | --- | --- | --- |
| Version source | `Accept` header | URL keyword argument | Endpoint declaration |
| Version visible in URL | No | Yes | Yes, in generated routes |
| Separate URL per version | No | Yes | Yes |
| DRF populates `request.version` | Yes | Yes | Not by itself |
| Cache separation by URL | No | Yes | Yes |
| Header-based cache variation | `Vary: Accept` when representations differ | Not for version separation | Not for version separation |
| Version-specific view registration | Application-managed | Application-managed | Declarative |
| Unchanged endpoint carry-forward | Application-managed | Application-managed | Supported by segment registration |

The important distinction is that `django-api-versioning` is not another DRF version-negotiation scheme.

It generates routes from declarations. It does not determine the request version for DRF, and it does not automatically populate `request.version`.

If a view registered through the package needs DRF's `request.version`, configure a compatible DRF versioning scheme separately. Do not assume that a generated literal version path automatically provides the URL keyword argument expected by `URLPathVersioning`.

## 5. Adding an endpoint that changes between versions

Consider an API that already exposes `users/` in v1 and v2. You now need an `articles/` endpoint whose response contract changes between those versions.

With either DRF versioning scheme, a shared view can branch on `request.version`:

```python
# views.py
from rest_framework.generics import ListCreateAPIView

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


class ArticleList(ListCreateAPIView):
    queryset = Article.objects.all()

    def get_serializer_class(self):
        if self.request.version == "v1":
            return ArticleSerializerV1

        return ArticleSerializerV2
```

The URL configuration differs.

**With `AcceptHeaderVersioning`:**

```python
path("api/articles/", ArticleList.as_view(), name="article-list")
```

Both versions use the same URL. The cache must distinguish the representations through `Vary: Accept`.

**With `URLPathVersioning`:**

```python
path(
    "api/<str:version>/articles/",
    ArticleList.as_view(),
    name="article-list",
)
```

Both versions use the same pattern, but different URLs. The version is part of the URL-based cache key.

With `django-api-versioning`, the implementations can be registered separately:

```python
# views.py
from rest_framework.generics import ListCreateAPIView

from django_api_versioning import endpoint

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


@endpoint("articles/", version=1)
class ArticleListV1(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1


@endpoint("articles/", version=2)
class ArticleListV2(ArticleListV1):
    serializer_class = ArticleSerializerV2
```

The package generates:

```text
/api/v1/articles/ -> ArticleListV1
/api/v2/articles/ -> ArticleListV2
```

There is no endpoint-specific URLconf change. The two declarations describe the two implementations, and the generated URLs provide separate cache identities.

If the endpoint does not change between v1 and v2, only one declaration is needed:

```python
@endpoint("articles/", version=1)
class ArticleListV1(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1
```

That registration remains active through `API_MAX_VERSION`, unless another registration replaces it.

When you introduce v3, update `API_MAX_VERSION` to 3. Existing segment registrations are then carried forward through v3, while new declarations can replace selected routes.

This is the central registration benefit: unchanged endpoints do not need duplicate declarations for every release.

It is also a responsibility. Carry-forward is routing behavior, not proof that the old response contract remains compatible with a newer API version. Review the version matrix whenever an endpoint's behavior changes.

## 6. ViewSets and router-based endpoints

The examples above use DRF generic views. Resource-shaped endpoints implemented with `ModelViewSet` should normally continue to use DRF routers.

The package cannot decorate a `ModelViewSet` class directly because it calls `.as_view()` without the action mapping required by a ViewSet.

A configured callable such as:

```python
UserViewSetV1.as_view({
    "get": "list",
    "post": "create",
})
```

can be registered for one explicitly configured route. It is not a replacement for router-generated list, detail, and custom-action routes.

For mixed projects:

- Use DRF routers for resource-shaped ViewSets.
- Use `@endpoint` for non-resource views and generic views that benefit from declarative version registration.
- Mount router-generated URL patterns under the desired version prefixes explicitly.

The package does not automatically integrate with or mount DRF routers.

## 7. Trade-offs and scope

**AcceptHeaderVersioning** is useful when one stable URL should represent multiple API versions. Its cache behavior requires careful handling of `Vary: Accept`, and every shared cache must respect that header.

**URLPathVersioning** is useful when the version should be visible in the URL. Distinct versioned URLs provide natural separation for ordinary URL-keyed caches, while DRF still allows a shared view to branch on `request.version`.

**`django-api-versioning`** is useful when endpoint implementations are version-specific and many endpoints remain unchanged across releases. It generates versioned URL patterns from declarations and carries forward unchanged registrations through the configured maximum version.

The package also introduces an import-order requirement: modules containing decorated views must be imported before its generated `urlpatterns` are loaded. It manages routing, not HTTP caching, DRF version negotiation, semantic compatibility, or automatic schema versioning.

When the benefit is smaller: for a single-version API, a project that relies heavily on `ModelViewSet` and `@action`, or an application whose existing views depend on DRF's `request.version`, a DRF-native scheme may require less architectural change.

For details about how Django handles cache keys and `Vary` headers, see [Django's cache framework documentation](https://docs.djangoproject.com/en/6.1/topics/cache/).

## Next steps

If your API needs declarative registration of version-specific views and automatic carry-forward of unchanged routes, explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
