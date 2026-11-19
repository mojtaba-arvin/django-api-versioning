# Explicit endpoint removal and reintroduction

**Status:** Implemented in consolidated PR #58 and merged to `main` as `a8b39343c478bb5a8afbe1de20d95a2b10630f37`. The earlier exploratory PRs #43 and #44 were closed unmerged; this document records the final delivered contract. Issue #39's post-merge acceptance audit was completed and closed on 2026-11-19. The feature is included in the 1.2.0 release candidate; PyPI publication is pending.  
**Runtime policy:** Removed endpoint routes are absent and resolve to 404  
**Scope:** Django-native endpoints and DRF VersionedRouter routes

## Problem

Forward route inheritance intentionally carries unchanged registrations into later API versions. It currently has no explicit inverse operation: omitting an endpoint from a later declaration does not remove the inherited route.

Removal must be a first-class declaration, not an accidental side effect of missing imports or manual URLPattern mutation.

## Public API

For decorator-registered Django endpoints:

~~~python
from django_api_versioning import endpoint, remove_endpoint

@endpoint("orders/", version=1, view_name="orders")
def orders_v1(request):
    ...

remove_endpoint("orders/", from_version=3)
~~~

For DRF ViewSets, target one generated route by its stable URL name:

~~~python
router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.remove("orders", "order-archive", from_version=3)
~~~

The DRF route name is the URL name generated from the basename and action. The logical identity is router prefix plus route name; it is not the generated regex string.

## Segment semantics

A removal declaration at version N suppresses an earlier source declaration from N through API_MAX_VERSION. A later registration with source_version greater than N explicitly reintroduces the route from that version onward.

Examples:

| Version | v1 declaration | Removal from v3 | Reintroduced at v4 |
| --- | --- | --- | --- |
| v1 | active | active | active |
| v2 | inherited | inherited | inherited |
| v3 | inherited | removed | removed |
| v4 | inherited | removed | new implementation |
| v5 | inherited | removed | new implementation inherited |

A registration whose source version is equal to or lower than the removal boundary remains suppressed. Only a declaration with a strictly higher source version reintroduces the route. Import order must not change the result: a late-imported v1 declaration cannot resurrect a route removed from v3.

For explicit registrations, only declared versions are candidates. A tombstone suppresses a matching explicit route at or after its boundary until a later source declaration reintroduces it.

## Registry model

- Keep active URLPattern objects in the existing urlpatterns list only.
- Store tombstone boundaries separately by logical endpoint and version.
- When a boundary is declared, remove already-registered patterns whose source version is equal to or lower than the boundary.
- When an older pattern is registered after a boundary, suppress it and retain an explicit removed-state record.
- When a later source version reintroduces the operation, register it normally and clear the removed state for the reintroduced concrete versions.
- Keep the original URLPattern as tombstone evidence so route-matrix output can identify the removed physical path and version.

## Observable state and compatibility

The state-aware version matrix must distinguish:
- active: a registered callback exists;
- removed: an explicit tombstone suppresses the route;
- missing: no route or tombstone declaration exists.

Do not silently change the historical snapshot JSON format for consumers that do not use removal. Extend its output only when tombstones exist, with a stable marker such as REMOVED. The CLI must display removed routes explicitly and must not report them as ordinary missing gaps.

Strict snapshots must detect an accidental deletion, an intentional removal, and an unexpected reintroduction as distinct changes.

## Runtime and integrations

- Removed paths are absent from urlpatterns, so Django returns 404.
- api_reverse(name, version=removed_version) raises NoReverseMatch; it never falls back.
- VersionedRouter.urls omits the tombstoned operation.
- drf-spectacular naturally excludes the route from that version's schema; the OpenAPI consumer example must test this.
- Version-wide LifecycleMiddleware continues to own Deprecation, Sunset, and 410. Endpoint tombstones do not synthesize 410.

## Required tests

1. Removal after registration and removal before registration produce identical results.
2. Older declarations imported after a tombstone cannot restore the route.
3. A later version reintroduces the endpoint and its URL reversal.
4. Explicit versions and internal version gaps remain correct.
5. Removing one DRF custom action preserves list/detail and unrelated actions.
6. The route matrix distinguishes active, removed, and missing states.
7. Strict snapshots detect tombstone changes.
8. api_reverse fails for the removed version and succeeds for the reintroduced version.
9. OpenAPI excludes the removed operation and includes a later reintroduction.
10. Existing decorator/router precedence and import behavior remain backward-compatible.
