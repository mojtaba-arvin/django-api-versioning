# django-api-versioning: canonical routing contract

> **Applies to:** django-api-versioning 0.3.4  
> **Verified against:** main-branch source and tests on 2026-11-12.
>
> This page is the canonical source for package-specific claims about version identifiers, imports, URL construction, endpoint registration, precedence, and DRF router/ViewSet boundaries. If another article conflicts with this page, update that article or revise this contract after verifying a source change.

## 1. Version identifiers

The package uses **integer API version identifiers** in Python configuration and decorator arguments. Use integers such as 1, 2, and 3 for the version argument, entries in versions, and API_MIN_VERSION / API_MAX_VERSION.

The default URL template is "api/v{version}/". Integer version 2 therefore produces the URL segment "v2". The "v" prefix belongs to the URL representation; it is not part of the Python version identifier.

Do not copy DRF examples using string identifiers such as "v1" or "1.0" into this package's decorator arguments. Those are values used by DRF versioning configurations and are not accepted by this package's integer-only version and versions arguments.

## 2. Canonical imports and public API

The package exposes `endpoint` and `ver_range` from its top-level namespace.

Use the public import path:

    from django_api_versioning import endpoint, ver_range

The decorators are implemented in `django_api_versioning.decorators`, so importing directly from that module also works:

    from django_api_versioning.decorators import endpoint, ver_range

For application code and documentation examples, prefer the top-level import path. It is the package's public API and avoids coupling consumers to the internal module structure.

Import the generated URL patterns from:

    from django_api_versioning.urls import urlpatterns as api_urlpatterns

The decorator signature in 0.3.4 is:

    endpoint(
        postfix: str,
        version: int | None = None,
        versions: list[int] | None = None,
        app_name: str | None = None,
        view_name: str | None = None,
    )

postfix is the resource path. app_name, when supplied, is a literal grouping segment prepended to that path. view_name is an optional explicit Django URL pattern name.

## 3. URL construction

For a versioned declaration, the registry constructs the route from:

1. API_BASE_PATH formatted with the integer version.
2. The optional app_name segment followed by a slash.
3. postfix.

With the default API_BASE_PATH = "api/v{version}/":

    @endpoint(
        "users/<int:user_id>/",
        app_name="accounts",
        version=2,
        view_name="accounts-user-detail",
    )
    def user_detail(request, user_id):
        ...

the route is api/v2/accounts/users/<int:user_id>/, which resolves under the project root as /api/v2/accounts/users/42/ for user id 42.

API_BASE_PATH must contain the literal {version} placeholder. It is a template for the versioned prefix, not a separate mount prefix to be duplicated elsewhere.

An endpoint with neither version nor versions is unversioned. Its route is registered without API_BASE_PATH; it appears at the URL include prefix plus its optional app_name and postfix.

Django path converters in postfix, such as <int:user_id> and <slug:slug>, are passed to Django's path() and are supported by the routing layer.

## 4. Registration semantics

Exactly one of version or versions may be supplied.

### Segment registration: version=N

version=N registers that implementation for every integer version from N through API_MAX_VERSION, inclusive.

For API_MIN_VERSION = 1 and API_MAX_VERSION = 4:

    @endpoint("orders/", version=2)
    def orders_v2(request):
        ...

registers the implementation for v2, v3, and v4. It does not register it for v1.

A later declaration for the same route at a higher source version replaces the earlier implementation from that version onward. For example, a declaration at v3 takes the route for v3 and v4, while the v2 declaration remains active for v2.

### Explicit registration: versions=[...]

versions=[...] registers the implementation only for the listed versions:

    @endpoint("reports/", versions=[1, 3, 4])
    def reports(request):
        ...

This registers v1, v3, and v4, but not v2. Use ver_range(start, end) when a bounded inclusive set is clearer:

    from django_api_versioning import endpoint, ver_range

    @endpoint("legacy/", versions=ver_range(1, 3))
    def legacy(request):
        ...

ver_range(1, 3) returns [1, 2, 3].

### Unversioned registration

When neither argument is supplied, the endpoint is registered once without a version prefix:

    @endpoint("health/")
    def health(request):
        ...

### Validation and boundaries

- Supplying both version and versions raises VersionRangeError.
- Version values must be integers; booleans are rejected even though bool is an int subclass in Python.
- A value greater than API_MAX_VERSION raises InvalidVersionError.
- A segment start below API_MIN_VERSION logs a warning and registers no routes.
- In an explicit list, entries below API_MIN_VERSION are warned about and skipped.
- API_MIN_VERSION and API_MAX_VERSION must be integers, and the minimum cannot exceed the maximum.

## 5. Collision precedence and ordering

The registry identifies a collision by the complete route string. When a new registration collides with an existing route:

1. If both declarations have integer source_version values, the higher source version wins.
2. If the source versions are equal, the last registration wins.
3. If either source version is None (for example, an unversioned route or a direct registry registration), the last registration wins.

For segment registration, the source version is the segment's starting version. For explicit registration, each listed route version is its own source version.

After registration, URL patterns are ordered with unversioned routes first and versioned routes in ascending route-version order. Do not turn this implementation detail into an unsupported guarantee about Django reverse lookup across duplicate names.

## 6. URLconf integration and import order

Decorators register routes when their Python modules are imported. Django does not automatically import every application view module just because it exists. Import all modules containing endpoint declarations **before** importing the package's urlpatterns.

    # project/urls.py
    from django.urls import include, path

    from accounts import views as account_views  # noqa: F401
    from orders import views as order_views  # noqa: F401

    from django_api_versioning.urls import urlpatterns as api_urlpatterns

    urlpatterns = [
        path("", include(api_urlpatterns)),
    ]

The import aliases are intentionally unused: importing the modules executes their decorators and populates the registry. Importing api_urlpatterns first risks capturing an empty or incomplete pattern list before declarations have run.

Alternatively, django_api_versioning.urls can be selected as ROOT_URLCONF when appropriate. Do not combine a package prefix template with a second mount prefix that unintentionally duplicates the path.

## 7. Supported view types and the ViewSet/router boundary

The registry accepts function-based views, Django class-based view classes whose as_view() method returns a Django view callable, and DRF APIView and generic-view classes, which use the Django class-based view as_view() lifecycle.

For a class-based view, the registry calls as_view() when it receives the class. Do not pass an instantiated view object.

**A DRF ViewSet class cannot be decorated directly with endpoint.** The registry calls as_view() without the required actions mapping, while DRF ViewSets require an action map. This is a concrete limitation, not a general incompatibility between DRF routers and URL versioning.

Use DRF's DefaultRouter or SimpleRouter to register ViewSets and mount the generated router URLs explicitly under the desired versioned prefixes. That router setup is separate from the package's endpoint registry; it does not mean the package automatically registers or inherits ViewSet actions. A manually configured callable such as MyViewSet.as_view({"get": "list"}) is a specific callable route, not a substitute for router-generated list, detail, and custom-action routes.

## 8. Routing inheritance is not Python inheritance or contract compatibility

The package's segment behavior is **route-registration inheritance**:

- A declaration at version N supplies the route implementation for N through API_MAX_VERSION.
- A later declaration for the same route at a higher source version overrides it from that version onward.
- Explicit versions=[...] declarations opt into only the listed versions.

This behavior does not create a Python subclass, copy methods, merge serializers, or prove that a response remains semantically backward compatible. Two view classes may be unrelated Python classes; the registry selects which callable is attached to each generated URL.

Automatic carry-forward has a real trade-off: if an endpoint's contract changes but its registration is not updated, the newer implementation continues to serve later versions. Conversely, an implementation intended only for one version can remain exposed across the configured range when declared with version=N. Teams must deliberately choose between segment registration and explicit version sets, review the version matrix when contracts change, and test each supported version's behavior—including serializers, permissions, filtering, pagination, and schema output where relevant.

The package manages routing. It does not decide whether a change is backward compatible, maintain a semantic API contract, or automatically version OpenAPI schemas.

## 9. Function names and URL names

The Python function or class name is **not** used to derive the URL path. The URL path comes from API_BASE_PATH, app_name, and postfix.

Likewise, the registry does not infer a Django URL name from the Python function name. Supply view_name explicitly when a named route is needed:

    @endpoint(
        "orders/",
        version=2,
        view_name="orders-list",
    )
    def list_orders(request):
        ...

A view_name is a Django URL pattern name; it is not a URL path segment. If multiple versioned patterns use the same name, use the package's documented reverse helper with an explicit version rather than assuming Django's plain reverse() selects the intended version.

## 10. Article authoring rules

When writing about this package:

- Keep DRF's version-identification mechanism distinct from this package's route-registration mechanism.
- Do not imply that DRF requires one view or URLconf per version; shared views, conditional dispatch, namespaces, and routers are valid DRF options.
- Compare the package with the closest viable DRF-only alternative, not a deliberately duplicated worst case.
- State the package version and assessment date when describing maturity or compatibility.
- Identify the author-maintainer relationship when promoting the package.
- Explain the risk of implicit segment carry-forward and the need to verify the version matrix and API contract.
- Do not present a numeric version-count threshold as a universal decision rule. Recommend the package only when the incremental endpoint-change pattern and avoided URLconf maintenance justify learning and adopting its registration model.
- Do not claim direct ViewSet support, automatic router integration, semantic backward compatibility, or automatic schema versioning.

## Primary source files

The contract above is based on the following implementation and project files:

- [decorators.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py)
- [registry.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/registry.py)
- [urls.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/urls.py)
- [settings.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/settings.py)
- [integration URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py)
- [README and installation requirements](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/README.md)
- [DRF ViewSets documentation](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/)
