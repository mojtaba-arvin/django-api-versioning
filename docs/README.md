# Project documentation

This directory contains the package's canonical technical reference and the source Markdown for the published article library. The root [README](../README.md) is the install and onboarding page distributed on both GitHub and PyPI.

## Start here

- [Install and Quick Start](../README.md): what the package does, installation, a complete Django-native example, DRF boundaries, requirements, and upgrade notes.
- [Official website](https://mojtaba-arvin.github.io/django-api-versioning/): product overview, interactive route playground, lifecycle demonstration, reference, and articles.
- [Online API reference](https://mojtaba-arvin.github.io/django-api-versioning/reference/): settings, decorator arguments, validation, exceptions, and management commands.

## Technical source of truth

These documents have different responsibilities; do not maintain duplicate versions of the same technical contract.

| Source | Owns | Does not own |
| --- | --- | --- |
| [Package source and executable tests](../django_api_versioning/) | Actual runtime behavior and regressions | User onboarding or marketing copy |
| [Root README](../README.md) | Package overview, install, Quick Start, high-level limitations | Complete API semantics |
| [Reference page source](reference/index.md) | Human-facing settings, decorator, exceptions, commands, and public API summary for `/reference/` | Every routing edge case |
| [Canonical routing contract](reference/versioning-contract.md) | Detailed URL construction, registration semantics, precedence, imports, reversal, DRF boundary, lifecycle, and request negotiation | General Django/DRF tutorials |
| [Runtime architecture and request flow](design/runtime-architecture.md) | End-to-end Mermaid flow from startup registration through negotiation, Django resolution, DRF dispatch, and lifecycle processing | A promise of serializer/payload compatibility or tenant policy |
| [Request version negotiation design](design/request-version-negotiation.md) | One configured version transport per deployment, middleware ordering, dispatch, reversal, cache and host security | Tenant policy, serializer/payload transformation, or release evidence | 
| [Governance](../GOVERNANCE.md) | Contributor-to-maintainer progression, release handover, and ownership continuity | A guarantee that a successor has already been appointed |
| [Community adoption and sustainability plan](community-sustainability.md) | Reproducible external evaluation, consumer integration checklist, outreach draft, contributor path, and evidence-based community reporting | Evidence that independent adoption, external review, or successor commitment has already occurred |
| [Changelog](../CHANGELOG.md) | Versioned release notes and migration notes | Current compatibility results |
| [Compatibility configuration](../tox.ini) | Exact configured Python/Django test environments | Proof that an environment passed |
| [Compatibility workflow](../.github/workflows/compatibility.yml) | How the configured environments are executed in CI | Results for commits that have not run |
| [Quality and release gates](quality/release-gates.md) | Mutation, coverage, consumer contracts, compatibility, adversarial, and release evidence requirements | A claim that an unverified commit has passed |
| [Dated quality evidence](reports/quality-2026-11-23.md) | Exact-head CI evidence and explicitly unresolved release checks for 23 November 2026 | A timeless guarantee or evidence for another commit |
| [Article corpus](articles/) | Task-focused tutorials and worked examples | A replacement for source or canonical API contracts |

If a tutorial conflicts with the package implementation, tests, or canonical routing contract, verify the behavior and correct the document that is wrong.

## Articles

The files in `articles/` are the only editable article sources. Each article's front matter owns its published slug, title, description, author, and keywords. The website copies these files locally during build and generates individual article pages, RSS, sitemap, and robots metadata from the same corpus. Edit the source Markdown here—not the generated copies under `website/content/`.

### Concepts and route design

- [Choosing a Django API versioning model](articles/001-django-api-versioning-packages.md)
- [URL path-based versioning](articles/003-url-path-versioning.md)
- [Declarative routing libraries and route inheritance](articles/004-api-routing-library.md)
- [Versioning without duplicated URL patterns](articles/006-versioning-without-duplicating-url-patterns.md)
- [Inheriting unchanged endpoints between versions](articles/007-inherit-unchanged-endpoints-between-versions.md)
- [Overriding only the endpoints that change in v2](articles/008-api-v2-inherit-endpoints-override-changed-views.md)
- [Declarative registration of versioned endpoints](articles/009-declarative-registration-versioned-endpoints-django.md)
- [Mapping a logical endpoint to different views](articles/010-map-endpoint-to-different-views-per-version.md)
- [Segment-based API version routing](articles/011-segment-based-api-version-routing.md)
- [What django-api-versioning does and how it works](articles/022-what-is-django-api-versioning.md)

### Django REST Framework choices and integration

- [DRF versioning schemes and their trade-offs](articles/002-drf-versioning-schemes.md)
- [Supporting v1 and v2 endpoints in a Django REST API](articles/005-support-v1-v2-endpoints.md)
- [Caching versioned DRF APIs](articles/012-drf-version-negotiation-vs-endpoint-registration.md)
- [DRF version negotiation vs endpoint registration](articles/013-drf-built-in-versioning-vs-dedicated-package.md)
- [Different views per API version in DRF](articles/014-drf-alternatives-different-views-per-version.md)
- [Versioning DRF APIView endpoints with URL prefixes](articles/015-version-drf-apiview-url-prefixes.md)
- [Using DRF routers with django-api-versioning](articles/016-integrate-url-based-versioning-drf-routers.md)
- [ViewSet support and limitations](articles/025-django-api-versioning-viewset-support.md)

### OpenAPI contract and schema compatibility

- [Executable versioned OpenAPI contract example](../examples/openapi_contract/README.md): a real consumer project that generates and validates one drf-spectacular schema per VersionedRouter API version, checks serializer selection, inherited actions, explicit endpoint removal, endpoint-level lifecycle deprecation for both VersionedRouter and decorator endpoints, runtime 404 behavior, and deterministic output. The committed per-version schema baselines and `oasdiff breaking` CI gate are implemented. This does not imply that route-matrix checks or schema diffs prove business-level response compatibility.

### Routing operations and API compatibility

- [Reverse URL lookup for versioned endpoints](articles/017-reverse-url-lookup-versioned-endpoints.md)
- [Deprecating API versions with Deprecation and Sunset headers](articles/018-deprecate-django-api-versioning-routes-sunset-headers.md)
- [Preserving backward compatibility in Django APIs](articles/019-preserve-backward-compatibility-django-api.md)
- [Migrating a Django REST API from v1 to v2](articles/020-migrate-django-rest-api-v1-v2-without-duplicating.md)

### Installation, production evaluation, and compatibility

- [Production evaluation of django-api-versioning](articles/021-django-api-versioning-library-requirements.md)
- [Installing and configuring django-api-versioning](articles/023-django-api-versioning-pypi-installation.md)
- [Python and Django compatibility](articles/024-django-api-versioning-supported-versions.md)

### Community adoption and maintenance continuity

- [Community adoption and sustainability plan](community-sustainability.md): reproducible real-project evaluation, middleware/cache/host checks, consumer adapter and OpenAPI adoption, contribution tasks, outreach draft, and a staged 90-day plan.
- [Governance and maintenance continuity](../GOVERNANCE.md): how contributors become maintainers, how GitHub and PyPI ownership can be handed over safely, and what to do if active maintenance stops.

## Historical release evidence

- [Compatibility report for v0.3.8](reports/compatibility-0.3.8.md) is a dated record for that release only. It is not the current matrix or a statement that today's commit passed. Use `tox.ini` for configured combinations and the [GitHub Actions run history](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/compatibility.yml) for actual results tied to a source commit.

## Website synchronization

- `reference/index.md` is copied by `website/scripts/sync-reference.mjs` into the generated `website/content/reference/index.md` build input. The canonical website route is `/reference/`; `/docs` and `/docs/` are legacy aliases.
- `articles/*.md` is copied by `website/scripts/sync-articles.mjs` into generated article input. The same script generates `rss.xml`, `sitemap.xml`, `robots.txt`, and redirect rules.

Never edit files under `website/content/` or generated feed/discovery files directly. Change the source Markdown and let the website build regenerate them.
