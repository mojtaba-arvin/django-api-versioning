# Historical Compatibility Report — v0.3.8

> Historical release evidence only. This report describes package version 0.3.8 and must not be used as the current compatibility matrix or as a description of current package behavior. The current configured matrix is defined by the repository-root `tox.ini` and checked against GitHub Actions; actual pass/fail status must be read from a workflow run for the commit in question.

**Package version:** 0.3.8  
**Release source commit:** `a372e2faa3e915d31083f70cb1b6c7e56fdc0372`  
**Release tag:** [`v0.3.8`](https://github.com/mojtaba-arvin/django-api-versioning/releases/tag/v0.3.8)  
**Release workflow:** [GitHub Actions run #43772378437](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43772378437)  
**PyPI artifact provenance:** [django-api-versioning 0.3.8](https://pypi.org/project/django-api-versioning/0.3.8/)

This report records the actual verification performed for the 0.3.8 release. The release workflow ran the complete compatibility matrix, built and verified both distributions, smoke-tested the installed wheel, checked distribution boundaries, and published the verified artifacts through PyPI Trusted Publishing. The annotated-tag and `main`-ancestry verification now present in the current publish workflow was added after this release run; it is not claimed as a v0.3.8 run result.

## Release verification result

All **19 workflow jobs succeeded**:

- 1 tox/workflow matrix validator;
- 15 Python/Django test environments;
- 1 lint environment;
- 1 distribution build and verification job;
- 1 isolated PyPI publication job.

The 15 test environments each reported **247 unit tests passed**, **260 Django integration tests passed**, and **96% package-source coverage**. The logs identify the package artifact as `django_api_versioning-0.3.8.tar.gz` in every environment.

The workflow also validated every configured tox environment against the explicit GitHub Actions matrix. The release workflow's successful build job ran strict Twine metadata validation, installed-wheel smoke testing from outside the source checkout, and wheel/sdist content verification. The separate publication job downloaded the verified artifact and published it using GitHub Actions OIDC. PyPI's provenance attestation identifies the release source commit above.

## Configured Python/Django matrix

| Django | Python versions | Environments |
| --- | --- | ---: |
| 4.2 | 3.10, 3.11, 3.12 | 3 |
| 5.2 | 3.10, 3.11, 3.12, 3.13, 3.14 | 5 |
| 6.0 | 3.12, 3.13, 3.14 | 3 |
| 6.1 | 3.12, 3.13, 3.14, 3.15 | 4 |
| **Total** | **Python 3.10–3.15** | **15** |

The separate lint environment passed:

- Flake8;
- `black --check .`;
- `isort --check-only .`.

The resolved DRF version was 3.17.2 in the Django 4.2 environments and 3.18.3 in the other environments. DRF is a development/test dependency, not a core runtime dependency. The matrix does not pin DRF to one exact version across all environments.

## Declared requirements and verified boundaries

The package metadata declares:

- Python `>=3.10`;
- Django `>=4.2`;
- Django REST Framework as optional, not a runtime dependency.

The matrix verifies only the combinations listed above. Django 5.0 and 5.1 are not included in the current support matrix. Do not infer support for unlisted Python/Django combinations from the broad minimum requirement or from classifiers.

The matrix ran on GitHub-hosted Ubuntu runners. It does not establish separate Windows or macOS compatibility. The test project uses SQLite; PostgreSQL, MySQL, MariaDB, Oracle, and other database configurations have not been separately verified by this matrix.

## Additional repository checks

- [Website build and static verification #69](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43761608641) passed for the 25-article corpus and the configured static build checks.
- The website remains **not deployed**. Browser-level accessibility, performance, and external-host smoke testing remain open; a successful static build is not evidence that those gates passed.
- The Segment Lab records 18 executable scenarios from the repository checkout. Its committed snapshot is generated evidence, not live Python execution in the browser.
- The package's 0.3.8 release files have PyPI provenance. This verifies their publishing origin, not every possible application deployment or runtime configuration.

## Implemented capabilities and known boundaries

At v0.3.8, the implementation and tests supported path-based endpoint registration, forward segment inheritance, explicit version sets, URL reversal for registered routes, lifecycle middleware, route-matrix inspection, and preview-first legacy endpoint migration.

The following are not end-to-end capabilities of the package:

- `extract_version()` and the configured channel names provide helper/configuration behavior; header/query channels are not integrated into registry route selection.
- `API_EFFECTIVE_VERSION_RESOLVER` is validated as configuration but does not select registered routes.
- The package does not automatically populate DRF's `request.version`.
- A DRF ViewSet class cannot be passed directly to `@endpoint` without an action map. A configured callable such as `MyViewSet.as_view({"get": "list"})` can be registered; router-generated route construction remains the application's responsibility.
- Route registration does not prove semantic compatibility of serializers, permissions, response payloads, or database behavior across API versions.
- At v0.3.8, the lifecycle middleware emitted the legacy `Deprecation: true` value, not the date-valued Structured Field required by RFC 9745. Application teams still own deprecation policy and client migration.

The `migrate_endpoints` command uses AST/tokenizer-aware inspection and previews changes by default. Dynamic expressions and unsupported declarations may be skipped. A suggested rewrite is not proof of semantic equivalence; review each change, inspect `check_versions`, and test affected requests.

## Interpretation

The 0.3.8 release has reproducible evidence for the configured Linux/Python/Django matrix and its built artifacts. It is not evidence of universal platform/database compatibility, automatic DRF request-version handling, multi-channel route dispatch, browser-level website acceptance, or external production deployment.

Update this report only when a new run is tied to an identified package source commit and the actual job results have been inspected. Configured environments are not evidence that they passed.
